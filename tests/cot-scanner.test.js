const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),vm=require("node:vm");
test("Lo Shark Radar usa solo indici COT 52 rilevazioni e dati CFTC",()=>{
 const html=fs.readFileSync("mercati.html","utf8");
 assert.ok(html.includes('data-scan="extremes"'));
 assert.ok(html.includes('cot-indices-core.js'));
 assert.ok(html.includes('REMURA_COT_INDEX_CORE.evaluate(data,52)'));
 assert.ok(html.includes('groupIndex<=10||groupIndex>=90'));
 assert.ok(html.includes('gapIndex<=10||gapIndex>=90'));
 assert.ok(html.includes("if(age>14||age<0"));
 const scripts=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(match=>match[1]).filter(Boolean);
 assert.equal(scripts.length,1);
 assert.doesNotThrow(()=>new vm.Script(scripts[0]));
});
test("Le nuove metriche restano prima dei due blocchi sentiment, prezzo dopo",()=>{
 const html=fs.readFileSync("asset.html","utf8");
 assert.ok(html.indexOf('id="cot-indices"')<html.indexOf('id="retail-module"'));
 assert.ok(html.indexOf('id="retail-module"')<html.indexOf('id="remura-tradingview"'));
 assert.ok(html.includes('id="cot-period"'));
 assert.ok(html.includes('id="cot-gap-chart"'));
 assert.ok(html.includes('remura-capital'));
});

test("Squalincome v1.27 validates multi-source data and limits iPhone requests",()=>{
 const html=fs.readFileSync("mercati.html","utf8");
 for(const term of ['id="squalincome-cross"','id="cross-run"',
  'private-api/prices/status','private-api/prices/','private-api/retail/latest.json',
  'private-api/capital/latest.json','quality.integrity!=="verified"',
  'quality.freshness','const candidates=allSymbols','selectCrossCandidates(available,crossMode,4)',
  'trendCore.analyze(records,current,"24h",now)',
  'crossCore.verdict.evaluate','NON LIVE','NON segnali live'])
   assert.ok(html.includes(term),term);
 assert.ok(!html.includes('private-api/ctrader/token'));
 // The first scanner regression test already verifies inline script syntax.
});

test("v1.28 separates COT group disagreement, preliminary divergence and historical alignment",()=>{
 const html=fs.readFileSync("mercati.html","utf8");
 const snippet=html.slice(html.indexOf("function cotSummary(cot){"),
   html.indexOf("async function getCapitalSources("));
 assert.ok(snippet.includes("function crossHeadline"));
 const functions=vm.runInNewContext(snippet+"\n({crossHeadline,cotSummary})",{
  fmt:{format:x=>x},fdate:x=>x,pp:x=>x
 });
 const quality={integrity:"verified",freshness:"weekend"};
 const conflict={state:"conflict",conflict:true,bias:1,stale:false};
 assert.match(functions.crossHeadline(conflict,quality,{state:"watch",side:1},{state:"mixed"}),/discordanti/);
 assert.match(functions.cotSummary(conflict),/non univoca/);
 assert.doesNotMatch(functions.crossHeadline(conflict,quality,{state:"watch",side:1},{state:"mixed"}),/neutrale/i);
 const bullish={state:"trend",conflict:false,bias:1,stale:false};
 assert.match(functions.crossHeadline(bullish,quality,{state:"watch",side:-1},{state:"divergent"}),/possibile divergenza/);
 assert.match(functions.crossHeadline(bullish,quality,{state:"confirmed",side:1},{state:"aligned"}),/STORICO/);
 assert.match(functions.crossHeadline(bullish,{integrity:"invalid",freshness:"recent"},{state:"confirmed",side:1},{state:"aligned"}),/non verificato/);
});
test("v1.28 reuses only already authenticated private Google Capital sentiment",()=>{
 const html=fs.readFileSync("mercati.html","utf8");
 for(const key of ["capital-cloud-config.js","capital-cloud.js","sentiment-core.js",
   "capitalCloud.isSignedIn()","capitalCloud.latest()","capitalCloud.history(symbol)",
   "capitalCore.cleanCapitalLatest","capitalCore.cleanCapitalHistory",
   "nessun campione VPS; Google non collegato","manca un campione vicino a 24h fa",
   "STORICO ·"]) {
   assert.ok(html.includes(key),key);
 }
 assert.ok(!html.includes("capitalCloud.signIn("));
});

test("v1.29 hides floating menu on downward scroll in scanners, without losing upward access",()=>{
 const nav=fs.readFileSync("nav.js","utf8");
 assert.ok(nav.includes('["stato-prezzi.html","mercati.html","asset.html"].includes(page)'));
 assert.ok(nav.includes('trigger.classList.toggle("rm-scrolled-away",!on)'));
 assert.ok(nav.includes('trigger.tabIndex=on?0:-1'));
 assert.ok(nav.includes('diff< -5'));
 const css=fs.readFileSync("nav.css","utf8");
 assert.ok(css.includes('#rm-menu-trigger.rm-scrolled-away'));
});

test("v1.30 lets the user retain strongest mode or reduce overlapping FX currencies",()=>{
 const html=fs.readFileSync("mercati.html","utf8");
 for(const word of ['data-cross-mode="diverse"','data-cross-mode="strongest"',
 'selectCrossCandidates(available,crossMode,4)','function selectCrossCandidates(rows,mode=',
 'function nextVerification(cot,quality,price,verdict)','cross-title',
 'Divergenza ≠ inversione','cross-watch'])
  assert.ok(html.includes(word),word);
 assert.ok(!html.includes('Analizza 4 candidati COT'));
 assert.ok(!html.includes('Mettere ordini automaticamente'));
});

test("v1.31 detects meaningful changes only after fresh verified source updates",()=>{
 const h=fs.readFileSync("mercati.html","utf8");
 const code=h.slice(h.indexOf("const CROSS_SNAPSHOT_KEY="),h.indexOf("function scanCard("));
 assert.ok(code.startsWith("const CROSS_SNAPSHOT_KEY="));
 const store=new Map();
 const localStorage={getItem:key=>store.has(key)?store.get(key):null,setItem:(key,value)=>store.set(key,value)};
 const check=vm.runInNewContext(code+"\n({eligibleCrossObservation,meaningfulCrossChange,crossRemember})",
  {localStorage,Date});
 const cot={asof:"2026-10-20",bias:1,conflict:false,stale:false,state:"trend"};
 const candidate={sym:"GBPNZD",date:"2026-10-20"};
 const fridayStamp="2026-10-23T20:45:00.000Z";
 const mondayStamp="2026-10-26T08:45:00.000Z";
 const weekendNow=Date.parse("2026-10-24T17:00:00Z");
 const mondayNow=Date.parse("2026-10-26T09:10:00Z");
 function entry({stamp=fridayStamp,kind="divergent",priceState="watch",side=-1,freshness="weekend"}={}){
  return {candidate,cot,quality:{integrity:"verified",freshness},price:{
    state:priceState,side,metrics:{M15:{latest:stamp}}},verdict:{state:kind}};
 }
 const first=check.crossRemember([entry()],weekendNow);
 assert.equal(first.events.size,0,"initial scan cannot signal");
 const historical=check.crossRemember([entry({kind:"aligned",side:1,priceState:"confirmed"})],weekendNow+3600000);
 assert.equal(historical.events.size,0,"weekend cannot signal");
 const newObservation=entry({stamp:mondayStamp,kind:"aligned",side:1,priceState:"confirmed",freshness:"recent"});
 const found=check.crossRemember([newObservation],mondayNow);
 assert.equal(found.events.size,1);
 assert.equal(found.events.get("GBPNZD").key,"alignment");
 assert.equal(check.crossRemember([newObservation],mondayNow+60000).events.size,0,"identical data cannot alert twice");
 const saved=store.values().next().value;
 assert.ok(saved.includes("GBPNZD")&&saved.includes(mondayStamp));
 assert.ok(!saved.includes("timeframes")&&!saved.includes("myfx")&&!saved.includes("token"));
});
test("v1.31 suppresses stale candles, weekend transitions, and classification-only changes",()=>{
 const h=fs.readFileSync("mercati.html","utf8");
 const code=h.slice(h.indexOf("const CROSS_SNAPSHOT_KEY="),h.indexOf("function scanCard("));
 const check=vm.runInNewContext(code+"\n({eligibleCrossObservation,meaningfulCrossChange})",{});
 const now=Date.parse("2026-10-26T09:10:00Z");
 const candidate={sym:"NZDCHF",date:"2026-10-20"};
 const cot={asof:"2026-10-20",bias:-1,conflict:false,stale:false,state:"trend"};
 const price={state:"confirmed",side:-1,metrics:{M15:{latest:"2026-10-26T08:45:00.000Z"}}};
 const observation={candidate,cot,price,verdict:{state:"aligned"},quality:{integrity:"verified",freshness:"recent"}};
 const valid=check.eligibleCrossObservation(observation,now);
 assert.ok(valid);
 assert.equal(check.eligibleCrossObservation({...observation,quality:{integrity:"invalid",freshness:"recent"}},now),null);
 assert.equal(check.eligibleCrossObservation({...observation,cot:{...cot,conflict:true}},now),null);
 assert.equal(check.eligibleCrossObservation({...observation,quality:{integrity:"verified",freshness:"stale"}},now),null);
 assert.equal(check.meaningfulCrossChange({...valid,state:"divergent"},{...valid,historical:true}),null);
 assert.equal(check.meaningfulCrossChange({...valid,state:"divergent"},{...valid}),null);
 assert.equal(check.meaningfulCrossChange({...valid,state:"aligned",priceState:"watch"},{...valid,priceTime:"2026-10-26T09:00:00.000Z"}).key,"confirmation");
 assert.ok(h.includes("Il primo controllo crea soltanto una fotografia iniziale"));
 assert.ok(h.includes("non invia notifiche"));
});

test("v1.32 shows private official COT status without suggesting signals are live",()=>{
 const html=fs.readFileSync("mercati.html","utf8");
 for(const term of ['id="cot-vps-status"','privateJSON("./private-api/cot/status")',
   'cotStatus?.schema!=="remura-cot-status-v1"','Nessun avviso o ordine attivo.',
   'Le notifiche sono ancora disabilitate.'])
   assert.ok(html.includes(term),term);
});

test("v1.37 renders private VPS event register with no notifications",()=>{
 const h=fs.readFileSync("mercati.html","utf8");
 for(const phrase of ['id="squalincome-monitor"','id="monitor-refresh"',
  'id="monitor-events"','privateJSON("./private-api/signals/status")',
  'remura-squalincome-monitor-v1','Telegram NON attivo.','Nuova convergenza',
  'Nuova divergenza','Conferma rafforzata'])
   assert.ok(h.includes(phrase),phrase);
 assert.ok(!h.includes('telegramBotToken'));
});
