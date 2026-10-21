/* Offline regression for explainable shark hypotheses — no predictive win-rates. */
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const engine=require("../squalo-core.js");
const when=Date.parse("2026-10-21T18:30:00Z");
const asof="2026-10-13";
const row=(l,s)=>({t:new Date(when-60000).toISOString(),lPct:l,sPct:s});
const cot={state:"trend",bias:-1,weekly:-1.8,fourWeeks:-4.3,
 currentNet:-25,sustained:true,stale:false,conflict:false,asof,
 specLabel:"Leveraged Funds"};
const price={state:"confirmed",metrics:{
 H4:{state:"ok",trend:-1},H1:{state:"ok",trend:-1},M15:{state:"ok",trend:-1}
}};
const both={symbol:"EURUSD",cot,price,retail:{row:row(82,18),fresh:true},
 capital:{row:row(70,30),fresh:true}};
test("all five checks must explain full score, never a probability",()=>{
 const result=engine.evaluate(both,when);
 assert.equal(result.stage,"coerente");
 assert.equal(result.score,100);
 assert.equal(result.coverage,5);
 assert.match(result.title,/SHORT/);
 assert.match(result.summary,/Non prova ordini istituzionali in corso/);
 assert.ok(result.checks.every(c=>c.status==="support"));
});
test("missing or stale COT never yields a shark verdict",()=>{
 for(const value of [null,{...cot,stale:true},{...cot,state:"missing",bias:0}]){
  const result=engine.evaluate({...both,cot:value},when);
  assert.equal(result.score,null);
  assert.equal(result.stage,"non-valutabile");
  assert.equal(result.side,0);
 }
});
test("stale or invalid retail cannot inflate the score",()=>{
 const expired={...row(80,20),t:new Date(when-5*3600000).toISOString()};
 const result=engine.evaluate({...both,retail:{row:expired,fresh:true},
   capital:{row:{...row(90,10),sPct:null},fresh:true}},when);
 assert.equal(result.score,80);
 assert.equal(result.coverage,3);
 assert.equal(result.stage,"preparazione");
});
test("net long decreasing does not count as current net short",()=>{
 const result=engine.evaluate({...both,cot:{...cot,currentNet:22}},when);
 assert.match(result.checks[0].detail,/posizione netta ancora dal lato opposto/);
 assert.match(result.checks[0].detail,/netto \+22% OI/);
});
test("institutional disagreement caps any evidence score",()=>{
 const result=engine.evaluate({...both,cot:{...cot,conflict:true}},when);
 assert.equal(result.stage,"discordante");
 assert.ok(result.score<=39);
});
test("without verified price, no coherent live movement classification",()=>{
 const result=engine.evaluate({...both,price:null},when);
 assert.ok(result.score<80);
 assert.notEqual(result.stage,"coerente");
 assert.equal(result.checks[3].status,"missing");
});
test("browser integrates new source events, settings and scanner",()=>{
 const grab=f=>fs.readFileSync(path.join(__dirname,"..",f),"utf8");
 const asset=grab("asset.html"),nav=grab("nav.js"),scanner=grab("squalo-scanner.js");
 for(const link of ["squalo-core.js?v=1","squalo.js?v=1","squalo.css?v=1","remura-settings.js?v=1"])
  assert.ok(asset.includes(link),link);
 assert.match(nav,/Scanner Squalo/);
 assert.match(nav,/Impostazioni e connessioni/);
 assert.match(scanner,/\/private-api\/retail\/latest\.json/);
 assert.match(scanner,/\/private-api\/prices\//);
 assert.match(scanner,/REMURA_CAPITAL_CLOUD/);
 assert.match(grab("squalo.html"),/squalo-scanner\.js/);
});
