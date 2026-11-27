/* REMURA Filone B v21.0: 7 FX futures versus 28 synthetic cross views.
 * Synthetic test inputs only; no CFTC network access.
 */
const test=require("node:test");
const assert=require("node:assert/strict");
const core=require("../cot-intelligence-core.js");
const factors=require("../cot-intelligence-fx-factors.js");
const watch=require("../cot-intelligence-watchlist.js");
const NOW="2026-11-23T18:00:00Z";
const dates=(n)=>Array.from({length:n},(_,i)=>
 new Date(Date.UTC(2026,10,17)-(n-1-i)*7*86400000).toISOString().slice(0,10));
function fixture(n=3,source="official_public_cftc_socrata"){
 const rows=dates(n).flatMap((date,i)=>Object.entries(watch.EXPECTED).flatMap(([dataset,codes])=>
  codes.map((code,j)=>({
   dataset,code,report_date:date,oi:10000,
   first_long:3000+i*(10+j),first_short:1500,
   second_long:3000,second_short:1200+i*(j%3),
   first_seen_at:source==="official_public_cftc_socrata"?null:new Date(Date.parse(date+"T00:00:00Z")+3*86400000).toISOString()
  }))
 ));
 return {schema:"remura-cot-intelligence-snapshot-v1",source,
  captureClock:source==="official_public_cftc_socrata"?"public_api_read_at_not_official_publication":"first_local_capture_not_official_publication",
  readAtUtc:source==="official_public_cftc_socrata"?"2026-11-23T17:00:00Z":undefined,
  rows,rowCount:rows.length,truncated:false};
}
const build=(s=fixture(),opts={})=>factors.build(s,{nowUtc:NOW,...opts});
test("all 28 FX pairs decompose into exactly 7 distinct underlying futures",()=>{
 const r=build();
 assert.equal(r.state,"descriptive_ready");
 assert.equal(r.uniqueUnderlyingCount,7);
 assert.equal(r.syntheticPairCount,28);
 assert.equal(r.factors.length,7);
 assert.equal(new Set(r.factors.map(f=>f.code)).size,7);
 assert.equal(r.pairs.length,28);
 assert.equal(Object.values(r.occurrence).reduce((a,b)=>a+b,0),49); // 21 cross x 2 + 7 USD legs
});
test("GBPAUD relative change equals GBP minus AUD, never two independent signals",()=>{
 const r=build();
 const a=Object.fromEntries(r.factors.map(x=>[x.currency,x]));
 const cross=r.pairs.find(x=>x.symbol==="GBPAUD");
 assert.ok(cross);
 assert.ok(Math.abs(cross.weeklyAssetManagersPp-(a.GBP.weeklyAssetManagersPp-a.AUD.weeklyAssetManagersPp))<1e-10);
 assert.deepEqual(cross.componentSigns,[{currency:"GBP",weight:1},{currency:"AUD",weight:-1}]);
 assert.deepEqual(cross.underlyingCurrencies,["GBP","AUD"]);
});
test("USDJPY is minus JPY future and EURUSD is EUR future only; USD is not institutional future",()=>{
 const r=build(),j=r.factors.find(x=>x.currency==="JPY"),e=r.factors.find(x=>x.currency==="EUR");
 assert.ok(Math.abs(r.pairs.find(x=>x.symbol==="USDJPY").weeklyAssetManagersPp+j.weeklyAssetManagersPp)<1e-10);
 assert.ok(Math.abs(r.pairs.find(x=>x.symbol==="EURUSD").weeklyAssetManagersPp-e.weeklyAssetManagersPp)<1e-10);
 assert.deepEqual(r.pairs.find(x=>x.symbol==="USDJPY").componentSigns,[{currency:"JPY",weight:-1}]);
 assert.deepEqual(r.pairs.find(x=>x.symbol==="EURUSD").componentSigns,[{currency:"EUR",weight:1}]);
});
test("seven factors sorted by absolute weekly change, stable ties",()=>{
 const r=build();
 for(let i=1;i<r.factors.length;i++){
  const prev=r.factors[i-1],curr=r.factors[i];
  assert.ok(Math.abs(prev.weeklyAssetManagersPp)>=Math.abs(curr.weeklyAssetManagersPp));
 }
 assert.deepEqual(Object.keys(core.FX).sort(),r.factors.map(x=>x.currency).sort());
});
test("52-week COT index computed only for genuinely contiguous observed reports",()=>{
 const r=build(fixture(52));
 assert.equal(r.state,"descriptive_ready");
 assert.ok(r.factors.every(f=>f.historicalStatus==="ok"));
 assert.ok(r.factors.every(f=>f.cotIndex52AssetManagers?.value>=0&&f.cotIndex52AssetManagers.value<=100));
 const gap=fixture(52);
 gap.rows=gap.rows.filter(x=>x.report_date!==dates(52)[12]);gap.rowCount=gap.rows.length;
 const g=build(gap);
 assert.equal(g.state,"descriptive_ready");
 assert.ok(g.factors.every(f=>f.historicalStatus==="insufficient"));
});
test("missing a single currency contract makes factor report blocked, never 6/7 ranked",()=>{
 const s=fixture();
 s.rows=s.rows.filter(x=>!(x.code==="097741"&&x.report_date==="2026-11-17"));s.rowCount=s.rows.length;
 const r=build(s);
 assert.equal(r.state,"blocked");
 assert.equal(r.reason,"incomplete_latest");
 assert.deepEqual(r.factors,[]);
});
test("public CFTC snapshots cannot be used for historical as-of even when rows look old",()=>{
 assert.throws(()=>build(fixture(),{observedAt:"2026-11-22T00:00:00Z"}),/PUBLIC_SNAPSHOT_CANNOT_PROVE_HISTORICAL_ASOF/);
});
test("local timestamps may support a snapshot as-of but never claim official publication time",()=>{
 const r=build(fixture(3,"existing_private_cftc_cache"),{observedAt:"2026-11-22T18:00:00Z"});
 assert.equal(r.state,"descriptive_ready");
 assert.equal(r.mode,"first_local_capture_asof");
 assert.ok(r.factors.every(f=>f.localFirstSeenAtUtc!==null));
 assert.ok(r.notes.some(x=>x.includes("does not prove official")));
});
test("missing unknown first-seen on private cache blocks affected historical series",()=>{
 const s=fixture(3,"existing_private_cftc_cache");
 s.rows.forEach(x=>{if(x.dataset==="tff"&&x.code==="099741"&&x.report_date==="2026-11-10")x.first_seen_at=null;});
 const r=build(s,{observedAt:"2026-11-22T18:00:00Z"});
 assert.equal(r.state,"blocked");
 assert.equal(r.reason,"incomplete_previous");
});
test("future stale latest report blocks ranking, never output directional claims",()=>{
 const s=fixture();s.rows.forEach(row=>{row.report_date=String(Number(row.report_date.slice(0,4))-1)+row.report_date.slice(4);});
 const r=build(s);
 assert.equal(r.state,"blocked");
 assert.equal(r.reason,"stale");
});
