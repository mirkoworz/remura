/* REMURA Filone B v20.7 — Node built-in test runner, zero dependencies.
 * Synthetic fixtures check logic, NOT real-world prediction or live feed availability.
 */
const test=require("node:test");
const assert=require("node:assert/strict");
const cot=require("../cot-intelligence-core.js");
const first=(report)=>new Date(Date.parse(report+"T00:00:00Z")+3*86400000).toISOString();
const row=(code,report,i=0)=>({
 dataset:"tff",cftc_contract_market_code:code,report_date_as_yyyy_mm_dd:report+"T00:00:00",
 open_interest_all:"1000",asset_mgr_positions_long:String(400+30*i),asset_mgr_positions_short:"200",
 lev_money_positions_long:"100",lev_money_positions_short:"250",firstSeenAt:first(report)
});
const jpy=(report,i=0)=>({
 ...row("097741",report,i),asset_mgr_positions_long:"100",asset_mgr_positions_short:"280",
 lev_money_positions_long:"300",lev_money_positions_short:String(120+20*i)
});
const date=(i)=>new Date(Date.UTC(2026,0,6+i*7)).toISOString().slice(0,10);
const combined=n=>Array.from({length:n},(_,i)=>[row("090741",date(i),i),jpy(date(i),i)]).flat();

test("CFTC FX: signed cross net% uses SAME week on BOTH actual currency futures, no fake USD positions",()=>{
 const r=cot.evaluate(combined(3),"CADJPY",{window:26});
 assert.equal(r.state,"ready");
 assert.equal(r.dataset,"tff");
 assert.equal(r.type,"synthetic_fx_relative");
 assert.deepEqual(r.codes,["090741","097741"]);
 assert.equal(r.netPercentOI.a,44);
 assert.equal(r.categoryRelationship,"categorie_opposte");
 assert.equal(r.weeklyChange.aPp,3);
 assert.equal(r.weeklyChange.bPp,2);
 assert.equal(r.openInterestContracts,null);
 assert.equal(r.weeklyChange.openInterestContracts,null);
 assert.equal(r.relative.state,"insufficient");
});
test("USDJPY inversion is minus JPY future: USD zero only MATHEMATICAL benchmark",()=>{
 const r=cot.evaluate([jpy("2026-11-10")],"USDJPY");
 assert.equal(r.state,"no_adjacent_week");
 assert.equal(r.netPercentOI.a,18);
 assert.equal(r.codes.length,1);
 assert.equal(r.type,"synthetic_fx_relative");
});
test("no substitute contract for DAX, VIX and Brent; exact valid direct mappings only",()=>{
 for(const symbol of ["GER30","GER40","VIX","UKOIL","BTCUSD"]){
  assert.equal(cot.evaluate([] ,symbol).state,"unsupported");
 }
 assert.deepEqual(cot.market("USOIL").codes,["067651"]);
 assert.deepEqual(cot.market("US500").codes,["13874A"]);
 assert.deepEqual(cot.market("DXY").codes,["098662"]);
 assert.equal(cot.PAIRS.length,28);
});
test("each CFTC report family uses distinct columns, no conflation of financial and physical categories",()=>{
 const r={dataset:"disagg",code:"088691",report_date:"2026-11-17",oi:1000,
  first_long:500,first_short:100,second_long:200,second_short:600,
  first_seen_at:"2026-11-20T20:00:00Z"};
 const z=cot.evaluate([r],"XAUUSD");
 assert.equal(z.dataset,"disagg");
 assert.equal(z.netPercentOI.a,40);
 assert.equal(z.netPercentOI.b,-40);
 assert.deepEqual(z.labels,["Managed Money","Producer/Merchant"]);
 assert.equal(z.openInterestContracts,1000);
});
test("as-of COT only uses local first-seen <= observation, never the Tuesday report date as publication",()=>{
 const rows=[row("090741","2026-11-10"),jpy("2026-11-10"),
   row("090741","2026-11-17"),jpy("2026-11-17")];
 const r=cot.evaluate(rows,"CADJPY",{observedAt:"2026-11-19T20:00:00Z"});
 assert.equal(r.reportDate,"2026-11-10");
 assert.equal(r.mode,"first_local_capture_asof");
 assert.equal(r.excludedByAsOf,2);
 const later=cot.evaluate(rows,"CADJPY",{observedAt:"2026-11-21T12:00:00Z"});
 assert.equal(later.reportDate,"2026-11-17");
 assert.equal(later.provenance.length,2);
 assert.equal(later.provenance[0].firstLocalCaptureUtc,"2026-11-20T00:00:00.000Z");
});
test("legacy snapshots without firstSeen must NOT pass an historical as-of gate",()=>{
 const rows=combined(2).map(r=>({...r,firstSeenAt:null}));
 assert.equal(cot.evaluate(rows,"CADJPY").mode,"descriptive_only");
 assert.equal(cot.evaluate(rows,"CADJPY",{observedAt:"2026-12-01T00:00:00Z"}).state,"unverified_or_unavailable");
});
test("different latest FX leg weeks MUST be flagged instead of quietly using an older common week",()=>{
 const d1="2026-11-10",d2="2026-11-17";
 const r=cot.evaluate([row("090741",d1),jpy(d1),row("090741",d2)],"CADJPY");
 assert.equal(r.state,"misaligned_latest");
 assert.equal(r.latestLegReports.CAD,d2);
 assert.equal(r.latestLegReports.JPY,d1);
});
test("52-week COT index and category divergence are descriptive, require contiguous evidence",()=>{
 const r=cot.evaluate(combined(52),"CADJPY",{window:52});
 assert.equal(r.state,"ready");
 assert.equal(r.relative.state,"ok");
 assert.equal(r.relative.values.a.value,100);
 assert.equal(r.relative.values.a.empiricalPercentile,100);
 assert.equal(r.relative.values.b.value,100);
 assert.equal(r.relative.values.gap.value,100);
 assert.equal(cot.evaluate(combined(25),"CADJPY",{window:26}).relative.state,"insufficient");
 const hole=combined(52).filter(x=>!x.report_date_as_yyyy_mm_dd.startsWith(date(30)));
 assert.equal(cot.evaluate(hole,"CADJPY",{window:52}).relative.state,"insufficient");
});
test("constant-range index emits null, no arbitrary 50/100 and no fake certainty",()=>{
 assert.equal(cot.cotIndex([10,10,10]),null);
 assert.equal(cot.cotIndex([1,3,2]).value,50);
});
test("a reporting gap must not be called a one-week change",()=>{
 const r=cot.evaluate([row("090741","2026-11-03"),row("090741","2026-11-17")],"USDCAD");
 assert.equal(r.state,"no_adjacent_week");
 assert.equal(r.weeklyChange,null);
});
test("fail closed for invalid numbers, dates, duplicated contradictory rows, unsupported windows",()=>{
 const source=row("090741","2026-11-10");
 assert.equal(cot.evaluate([{...source,asset_mgr_positions_long:"NaN"}],"USDCAD").state,"invalid_rows");
 assert.equal(cot.evaluate([{...source,report_date_as_yyyy_mm_dd:"2026-02-30"}],"USDCAD").state,"invalid_rows");
 assert.throws(()=>cot.evaluate([source,{...source,asset_mgr_positions_long:"999"}],"USDCAD"),/CONFLICTING_CFTC_ROWS/);
});
test("separate tests for duplicate conflict and invalid timestamps",()=>{
 const x=row("090741","2026-11-10");
 assert.throws(()=>cot.evaluate([x,{...x,asset_mgr_positions_long:"500"}],"USDCAD"),/CONFLICTING_CFTC_ROWS/);
 assert.throws(()=>cot.evaluate([x],"USDCAD",{observedAt:"invalid"}),/INVALID_OBSERVATION_TIME/);
 assert.throws(()=>cot.evaluate([x],"USDCAD",{window:5}),/INVALID_WINDOW/);
});
