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
 assert.ok(page.includes('nav.js?v=118'));
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
 assert.ok(nav.includes('if(page==="stato-prezzi.html")'));
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
 assert.equal(weekend.state,"stale");
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
 for(const script of ["nav.js?v=118","price-status-core.js?v=118","stato-prezzi.js?v=118"])assert.ok(html.includes(script));
 assert.ok(html.includes('id="macro"'));
 assert.ok(ui.includes('window.addEventListener("hashchange",initMacro)'));
 assert.ok(ui.includes("./private-api/prices/"));
 assert.ok(!ui.includes("apiKey")&&!ui.includes("CTRADER_ACCESS_TOKEN"));
 assert.ok(nav.includes('href="./stato-prezzi.html#macro"'));
 assert.ok(service.includes('"./stato-prezzi.html"'));assert.ok(!service.includes('"./macro.html"'));
});
