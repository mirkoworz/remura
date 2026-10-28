const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const core=require('../price-status-core.js');
const SERVER='2026-10-23T11:00:00Z';
const mk=(minutes,count=1)=>({counts:{M15:count},lastComplete:new Date(Date.parse(SERVER)-minutes*60000).toISOString()});
test('Price statuses reflect timestamps and truly missing OHLC',()=>{
 assert.equal(core.interpret(mk(30),SERVER).state,'recent');
 assert.equal(core.interpret(mk(180),SERVER).state,'recent');
 assert.equal(core.interpret(mk(181),SERVER).state,'stale');
 assert.equal(core.interpret(mk(20,0),SERVER).state,'missing');
 assert.equal(core.interpret({counts:{M15:42},lastComplete:null},SERVER).state,'missing');
 assert.equal(core.interpret(mk(-7),SERVER).state,'stale');
});
test('Summary categories never treat an unavailable broker as real price',()=>{
 const data=[mk(40),mk(400),{symbol:'DXY',counts:{M15:0},lastComplete:null}];
 assert.deepEqual(core.summarize(data,SERVER),{recent:1,stale:1,missing:1});
 assert.ok(core.OUTCOMES.ticker_unavailable.includes('Ticker'));
});
test('Dashboard uses only lightweight authenticated API, no token or fake data',()=>{
 const page=fs.readFileSync('stato-prezzi.html','utf8');
 const client=fs.readFileSync('stato-prezzi.js','utf8');
 const backend=fs.readFileSync('scripts/private_server.py','utf8');
 assert.ok(page.includes('nav.js?v=145'));
 assert.ok(client.includes('./private-api/prices/status'));
 assert.ok(backend.includes('PRICE_OVERVIEW_PATH'));
 assert.ok(backend.includes('stato-prezzi.html'));
 assert.ok(!client.includes('ctrader-tokens.json'));
 assert.ok(!page.includes('example-candles'));
});

test('Mobile monitoring keeps source diagnostics accessible in compact disclosure',()=>{
 const html=fs.readFileSync('stato-prezzi.html','utf8');
 const js=fs.readFileSync('stato-prezzi.js','utf8');
 const nav=fs.readFileSync('nav.js','utf8');
 const navCss=fs.readFileSync('nav.css','utf8');
 assert.ok(js.includes('node("details","market-more")'));
 assert.ok(js.includes('rowText("Fonte:"'));
 assert.ok(js.includes('rowText("Ultimo tentativo:"'));
 assert.ok(js.includes('Ultimo esito:'));
 assert.ok(html.includes('Come leggere i dati e la freschezza'));
 assert.ok(nav.includes('["stato-prezzi.html","mercati.html","asset.html","statistica-squali.html"].includes(page)'));
 assert.ok(navCss.includes('rm-scrolled-away'));
 assert.ok(navCss.includes('prefers-reduced-motion'));
});

// REMURA v1.18 quality and correlation regression tests
const macro=core.macro;
const HOUR=3600000,QUARTER=900000,END=Date.parse("2026-10-23T16:00:00Z");
const iso=t=>new Date(t).toISOString();
function bars(hours=100,start=END-100*HOUR,base=100,rate=0.002){
 const m15=[];
 for(let i=0;i<hours*4;i++){
  const t=start+i*QUARTER;
  const p=base*Math.exp(rate*i/4+0.002*Math.sin(i/4));
  m15.push({t:iso(t),o:p,h:p*1.002,l:p*0.998,c:p*1.0003});
 }
 function frame(n){
  const rows=[];
  for(let i=0;i<m15.length;i+=n){
   const part=m15.slice(i,i+n);
   if(part.length!==n)continue;
   const t=Date.parse(part[0].t);
   if(t%(n*QUARTER))continue;
   rows.push({t:iso(t),o:part[0].o,h:Math.max(...part.map(x=>x.h)),l:Math.min(...part.map(x=>x.l)),c:part.at(-1).c});
  }
  return rows;
 }
 return {symbol:"GER30",provider:"ctrader",timeframes:{M15:m15,H1:frame(4),H4:frame(16)}};
}
test("OHLC integrity and contiguity are audited without inventing bars",()=>{
 const data=bars(240,END-240*HOUR),q=macro.audit(data,END);
 assert.equal(q.state,"recent");
 assert.equal(q.recentGaps,0);
 assert.equal(q.h1.mismatched,0);assert.equal(q.h4.mismatched,0);
 assert.equal(q.h1.verified,q.h1.checked);
 assert.equal(q.h4.verified,q.h4.checked);
 assert.ok(q.ready);
 const broken=structuredClone(data);
 broken.timeframes.H1.at(-1).h*=1.2;
 assert.equal(macro.audit(broken,END).state,"invalid");
 const interrupted=structuredClone(data);
 interrupted.timeframes.M15.splice(-10,1);
 assert.equal(macro.audit(interrupted,END).recentGaps,1);
 assert.ok(macro.audit(interrupted,END).h1.missingInputs>0);
 const weekend=macro.audit(data,END+48*HOUR);
 assert.equal(weekend.state,"weekend");
 assert.equal(macro.pulse(data,{now:END+48*HOUR}).state,"ok");
 assert.equal(macro.pulse(data,{now:END+48*HOUR}).historical,true);
 assert.equal(macro.pairEligible(data,data,END+48*HOUR),true);
 assert.equal(macro.audit(data,END+96*HOUR).state,"stale");
});
test("H1 Pearson uses only aligned contiguous hourly log returns",()=>{
 const a=bars(100,END-100*HOUR,100,0.004);
 const b=structuredClone(a);
 for(const tf of ["H1","H4","M15"])for(const bar of b.timeframes[tf]){
   bar.o*=2;bar.c*=2;bar.h*=2;bar.l*=2;
 }
 const pos=macro.correlation(a,b,{now:END});
 assert.equal(pos.state,"ok");assert.ok(Math.abs(pos.value-1)<1e-9);assert.equal(pos.samples,99);
 const lag=structuredClone(b);
 lag.timeframes.H1=lag.timeframes.H1.filter((_,i)=>i%2===0);
 const fewer=macro.correlation(a,lag,{now:END});
 assert.ok(fewer.samples<pos.samples);
 const missing=macro.correlation(a,null,{now:END});
 assert.equal(missing.state,"insufficient");
});
test("Macro page has a private-readonly architecture and correct menu version",()=>{
 const html=fs.readFileSync("stato-prezzi.html","utf8");
 const ui=fs.readFileSync("stato-prezzi.js","utf8");
 const nav=fs.readFileSync("nav.js","utf8");
 const service=fs.readFileSync("sw.js","utf8");
 for(const script of ["nav.js?v=145","price-status-core.js?v=123","stato-prezzi.js?v=126"])assert.ok(html.includes(script));
 assert.ok(html.includes('id="macro"'));
 assert.ok(ui.includes('window.addEventListener("hashchange",initialize)'));
 assert.ok(ui.includes("./private-api/prices/"));
 assert.ok(ui.includes("ULTIMA SESSIONE DEL VENERDÌ"));
 assert.ok(!ui.includes("apiKey")&&!ui.includes("CTRADER_ACCESS_TOKEN"));
 assert.ok(nav.includes('href="./stato-prezzi.html#macro"'));
 assert.ok(service.includes('"./stato-prezzi.html"'));assert.ok(!service.includes('"./macro.html"'));
});

test('Macro contextual movement requires fresh contiguous H1 candles and relative magnitude',()=>{
 const HOUR=3600000,END=Date.parse("2026-10-23T16:00:00Z");
 function factory(direction=1){
  const sample=[];
  for(let i=0;i<160;i++){
   const t=END-160*HOUR+i*HOUR,mid=100*Math.exp(direction*0.003*i+0.001*Math.sin(i*.4));
   sample.push({t:new Date(t).toISOString(),o:mid,h:mid*1.003,l:mid*.997,c:mid*1.0001});
  }
  const m15=sample.flatMap(x=>{
    const start=Date.parse(x.t);
    return Array.from({length:4},(_,i)=>({t:new Date(start+i*900000).toISOString(),o:x.o,h:x.h,l:x.l,c:x.c}));
  });
  const h4=[];
  for(let i=0;i<sample.length;i+=4){
   const p=sample.slice(i,i+4);
   if(p.length<4||Date.parse(p[0].t)%(4*HOUR)!==0)continue;
   h4.push({t:p[0].t,o:p[0].o,h:Math.max(...p.map(v=>v.h)),l:Math.min(...p.map(v=>v.l)),c:p[3].c});
  }
  return {timeframes:{M15:m15,H1:sample,H4:h4}};
 }
 const upward=factory(1),downward=factory(-1);
 const up=macro.pulse(upward,{now:END}),down=macro.pulse(downward,{now:END});
 assert.equal(up.state,"ok");assert.equal(down.state,"ok");
 assert.ok(up.changePct>0);assert.ok(down.changePct<0);
 const missing=macro.context(null,upward,{now:END});
 assert.equal(missing.state,"unavailable");
 const stale=macro.pulse(upward,{now:END+96*HOUR});
 assert.equal(stale.state,"unavailable");
 assert.equal(typeof macro.context(upward,downward,{now:END}).label,"string");
});

test('Macro context distinguishes stationary dollar from contradictory direction',()=>{
 const classify=macro.describeContext;
 const item=d=>({state:"ok",direction:d,changePct:d==="flat"?0.039:d==="down"?-2.274:2.274,referencePct:0.5});
 const observed=classify(item("flat"),item("down"));
 assert.equal(observed.state,"easing");
 assert.match(observed.label,/Volatilità in calo, dollaro sostanzialmente stabile/);
 assert.ok(!observed.label.includes("non concordi"));
 assert.ok(observed.description.includes("Non è un segnale long"));
 const expectations={
  "up/up":["caution","Volatilità e dollaro in aumento"],
  "down/down":["calm","Volatilità e dollaro in calo"],
  "flat/flat":["neutral","senza variazioni significative"],
  "flat/up":["watch","Volatilità in aumento, dollaro sostanzialmente stabile"],
  "flat/down":["easing","Volatilità in calo, dollaro sostanzialmente stabile"],
  "up/flat":["neutral","Dollaro in aumento, volatilità sostanzialmente stabile"],
  "down/flat":["neutral","Dollaro in calo, volatilità sostanzialmente stabile"],
  "up/down":["mixed","Volatilità in calo, dollaro in aumento"],
  "down/up":["mixed","Volatilità in aumento, dollaro in calo"],
 };
 for(const [pair,[state,label]] of Object.entries(expectations)){
  const [d,v]=pair.split("/");
  const res=classify(item(d),item(v));
  assert.equal(res.state,state,pair);
  assert.ok(res.label.includes(label),pair);
  assert.ok(res.description.length>30,pair);
 }
 assert.equal(classify({state:"insufficient"},item("down")).state,"unavailable");
 assert.equal(classify(item("flat"),{state:"ok",direction:null}).state,"unavailable");
});

test('Weekend snapshot only admits the immediate verified Friday session in Rome',()=>{
 const friday=Date.parse('2026-10-23T20:45:00Z')+QUARTER;
 const saturday=Date.parse('2026-10-24T09:30:00Z');
 const sunday=Date.parse('2026-10-25T17:30:00Z'); // Italian DST ends Oct 25
 const monday=Date.parse('2026-10-26T09:30:00Z');
 assert.equal(macro.weekendSnapshot(friday,saturday),true);
 assert.equal(macro.weekendSnapshot(friday,sunday),true);
 assert.equal(macro.weekendSnapshot(friday,monday),false);
 assert.equal(macro.weekendSnapshot(friday-7*24*HOUR,saturday),false);
 assert.equal(macro.weekendSnapshot(Date.parse('2026-10-22T20:00:00Z'),saturday),false);
 assert.equal(macro.weekendSnapshot(Date.parse('2026-10-23T09:00:00Z'),saturday),false);
});
test('Friday macro Pearson remains available as a labelled historical snapshot',()=>{
 const a=bars(100,END-100*HOUR,100,0.004),b=structuredClone(a);
 for(const tf of ['M15','H1','H4'])for(const bar of b.timeframes[tf]){
  bar.o*=2;bar.h*=2;bar.l*=2;bar.c*=2;
 }
 const sunday=END+48*HOUR;
 assert.equal(macro.audit(a,sunday).state,'weekend');
 assert.equal(macro.pairEligible(a,b,sunday),true);
 const c=macro.correlation(a,b,{now:sunday});
 assert.equal(c.state,'ok');
 assert.ok(c.samples>=30);
 const old=END+96*HOUR;
 assert.equal(macro.pairEligible(a,b,old),false);
});

test("Readable macro correlation interprets DAX figures from verified H1 returns",()=>{
 const dxy=macro.describeCorrelation({state:"ok",value:-0.05,samples:198},"DXY");
 assert.equal(dxy.state,"ok");
 assert.equal(dxy.strength,"quasi nulla");
 assert.match(dxy.label,/quasi nulla/);
 const vix=macro.describeCorrelation({state:"ok",value:-0.554,samples:189},"VIX");
 assert.equal(vix.direction,"negative");
 assert.equal(vix.strength,"moderata");
 assert.match(vix.label,/inversa moderata/);
 const contrast=macro.compareMacroRelationships("DAX 40",
  {state:"ok",value:-0.05,samples:198},
  {state:"ok",value:-0.554,samples:189});
 assert.equal(contrast.state,"ok");
 assert.match(contrast.summary,/VIX ha mostrato l'associazione lineare più marcata/);
 assert.match(contrast.summary,/non è un segnale operativo/);
});
test("Correlation interpretation covers direction, minimum samples and unavailable sources",()=>{
 const c=(value,samples=50)=>macro.describeCorrelation({state:"ok",value,samples},"VIX");
 assert.equal(c(0.55).direction,"positive");
 assert.equal(c(0.55).strength,"moderata");
 assert.equal(c(-0.79).strength,"elevata");
 assert.equal(c(0.17).strength,"debole");
 assert.equal(c(-0.03).direction,"none");
 assert.equal(c(0.8,29).state,"unavailable");
 assert.equal(c(1.1).state,"unavailable");
 assert.equal(c(NaN).state,"unavailable");
 const partial=macro.compareMacroRelationships("XAUUSD",
   {state:"unavailable",samples:0,value:null},{state:"ok",samples:60,value:0.5});
 assert.equal(partial.state,"partial");
 assert.equal(macro.compareMacroRelationships("GER30",null,null).state,"unavailable");
 const h=fs.readFileSync("stato-prezzi.html","utf8");
 const js=fs.readFileSync("stato-prezzi.js","utf8");
 assert.ok(h.includes('id="macro-target-interpretation"'));
 assert.ok(js.includes('$("macro-target-interpretation").replaceChildren(explainMarket(symbol))'));
 assert.ok(js.includes("core.pairEligible(one,two)"));
});

test('v1.25 audits one OHLC symbol on demand and identifies markets without data',()=>{
 const html=fs.readFileSync('stato-prezzi.html','utf8');
 const js=fs.readFileSync('stato-prezzi.js','utf8');
 assert.ok(html.includes('id="price-missing-summary"'));
 assert.ok(js.includes('missing.map(e=>e.symbol'));
 assert.ok(js.includes('button.addEventListener("click",async()=>'));
 assert.ok(js.includes('core.macro.audit(doc,Date.parse(serverTime))'));
 assert.ok(js.includes('Verifica qualità M15/H1/H4'));
 assert.ok(!js.includes('CTRADER_CLIENT_SECRET'));
});

test('v1.26 uses the single lightweight server-wide quality audit',()=>{
 const h=fs.readFileSync('stato-prezzi.html','utf8');
 const js=fs.readFileSync('stato-prezzi.js','utf8');
 assert.ok(h.includes('id="price-quality-summary"'));
 assert.ok(h.includes('id="price-quality-list"'));
 assert.ok(js.includes('renderQuality(parsed)'));
 assert.ok(js.includes('overview?.qualityTotals'));
 assert.ok(js.includes('totals.verified+"/38'));
 assert.ok(js.includes('Il server sta ancora usando il vecchio riepilogo'));
 assert.ok(!js.includes('CTRADER_ACCESS_TOKEN'));
});
