/* REMURA Filone B v20.8 — offline CFTC watchlist regression tests.
 * All rows are synthetic, explicitly NOT real institutional observations.
 */
const test=require("node:test");
const assert=require("node:assert/strict");
const core=require("../cot-intelligence-core.js");
const watch=require("../cot-intelligence-watchlist.js");
const utc="2026-11-23T15:00:00+01:00";
const dates=["2026-11-03","2026-11-10","2026-11-17"];
const firstSeen=d=>new Date(Date.parse(d+"T00:00:00Z")+3*86400000).toISOString();
const fixture=(weeks=dates)=>({
 schema:"remura-cot-intelligence-snapshot-v1",
 source:"existing_private_cftc_cache",
 captureClock:"first_local_capture_not_official_publication",
 rows:weeks.flatMap((d,i)=>Object.entries(watch.EXPECTED).flatMap(([dataset,codes])=>
  codes.map((code,j)=>({
   dataset,code,report_date:d,oi:1000,
   first_long:300+i*(j===0?100:j+1),first_short:200,
   second_long:100,second_short:300-i*(j%4),
   first_seen_at:firstSeen(d)
  }))
 )),
 rowCount:0,truncated:false
});
function make(weeks=dates){
 const s=fixture(weeks);
 s.rowCount=s.rows.length;
 return s;
}
function compute(s=make(),opts={}){return watch.build(s,{nowUtc:utc,...opts});}
test("read-only snapshot is gated by schema, row count and truncation",()=>{
 const s=make();
 assert.equal(s.rowCount,42);
 assert.equal(compute(s).schema,"remura-cot-watchlist-v1");
 assert.throws(()=>compute({...s,truncated:true}),/INVALID_OR_TRUNCATED_SNAPSHOT/);
 assert.throws(()=>compute({...s,rowCount:s.rowCount-1}),/INVALID_OR_TRUNCATED_SNAPSHOT/);
 assert.throws(()=>compute({...s,source:"unverified_online_cache"}),/INVALID_OR_TRUNCATED_SNAPSHOT/);
});
test("14 required contracts divided by proper TFF and Disaggregated, latest and previous complete",()=>{
 const r=compute();
 assert.equal(watch.EXPECTED.tff.length,11);
 assert.equal(watch.EXPECTED.disagg.length,3);
 assert.equal(r.periods.tff.state,"complete");
 assert.equal(r.periods.disagg.state,"complete");
 assert.equal(r.periods.tff.latest,"2026-11-17");
 assert.equal(r.periods.tff.previous,"2026-11-10");
 assert.equal(r.periods.tff.latestPresent,11);
 assert.equal(r.periods.disagg.latestPresent,3);
});
test("3 separate lanes: 28 FX synthetic, 4 TFF direct and 3 disaggregated futures",()=>{
 const r=compute();
 assert.equal(r.groups.length,3);
 assert.deepEqual(r.groups.map(g=>g.entries.length),[28,4,3]);
 assert.ok(r.groups.every(g=>g.state==="descriptive"));
 assert.equal(r.groups[0].ordering.includes("NOT prediction"),true);
 assert.equal(r.state,"descriptive_ready");
 assert.equal(r.mode,"descriptive_only");
});
test("ranks by magnitude of weekly first-category net% OI change, stable tie alphabetical",()=>{
 const r=compute(),f=r.groups.find(g=>g.id==="tff_futures");
 assert.equal(f.entries.length,4);
 for(let i=1;i<f.entries.length;i++){
  assert.ok(Math.abs(f.entries[i-1].deltaA_Pp)>=Math.abs(f.entries[i].deltaA_Pp));
 }
 assert.equal(r.groups[0].entries.every(x=>x.referenceType==="synthetic_fx_relative"),true);
 assert.equal(r.groups[0].entries.every(x=>x.observationMode==="descriptive_only"),true);
});
test("cross overlap is explicit, and unsupported markets are NEVER inferred",()=>{
 const r=compute();
 assert.deepEqual(r.unsupported,["GER30","VIX","UKOIL"]);
 const pair=r.groups[0].entries.find(x=>x.symbol==="CADJPY");
 assert.deepEqual(pair.exposureTags,["CAD","JPY"]);
 assert.deepEqual(pair.codes,["090741","097741"]);
 assert.ok(r.notes.some(x=>x.includes("NON indipendenti")));
 const usd=r.groups[0].entries.find(x=>x.symbol==="USDJPY");
 assert.deepEqual(usd.exposureTags,["JPY"]);
});
test("dataset partial coverage suppresses that group's ranking without breaking independent datasets",()=>{
 const s=make();
 s.rows=s.rows.filter(x=>!(x.dataset==="disagg"&&x.code==="084691"&&x.report_date==="2026-11-17"));
 s.rowCount=s.rows.length;
 const r=compute(s);
 assert.equal(r.periods.disagg.state,"incomplete_latest");
 assert.deepEqual(r.periods.disagg.missingLatest,["084691"]);
 assert.equal(r.groups.find(g=>g.id==="disagg_futures").state,"blocked");
 assert.equal(r.groups.find(g=>g.id==="tff_futures").entries.length,4);
});
test("missing previous complete week blocks dataset, instead of ranking on partial baseline",()=>{
 const s=make();
 s.rows=s.rows.filter(x=>!(x.dataset==="tff"&&x.code==="099741"&&x.report_date==="2026-11-10"));
 s.rowCount=s.rows.length;
 const r=compute(s);
 assert.equal(r.periods.tff.state,"incomplete_previous");
 assert.equal(r.groups.find(g=>g.id==="fx_relative").entries.length,0);
 assert.equal(r.groups.find(g=>g.id==="disagg_futures").entries.length,3);
});
test("reports separated by 14 days are cadence-review, not weekly directional ranking",()=>{
 const r=compute(make(["2026-11-03","2026-11-17"]));
 assert.equal(r.periods.tff.state,"cadence_review");
 assert.equal(r.groups[0].state,"blocked");
});
test("future faster-than-weekly report is explicitly held for cadence review",()=>{
 const s=make(["2026-11-10","2026-11-13"]);
 const r=compute(s);
 assert.equal(r.periods.tff.intervalDays,3);
 assert.equal(r.periods.tff.state,"cadence_review");
 assert.equal(r.groups[1].entries.length,0);
});
test("stale data blocked; no false institutional movement claims",()=>{
 const r=compute(make(["2026-10-06","2026-10-13"]));
 assert.equal(r.periods.tff.state,"stale");
 assert.equal(r.groups[0].entries.length,0);
});
test("historical as-of strictly excludes later first capture (report time is not availability)",()=>{
 const r=compute(make(),{observedAt:"2026-11-19T12:00:00Z"});
 assert.equal(r.mode,"first_local_capture_asof");
 assert.equal(r.periods.tff.latest,"2026-11-10");
 assert.equal(r.periods.tff.previous,"2026-11-03");
 assert.equal(r.groups[0].state,"capture_asof");
 assert.ok(r.groups[0].entries.every(x=>x.reportDate==="2026-11-10"));
 assert.ok(r.groups[0].entries.every(x=>x.firstLocalCaptureUtc.every(Boolean)));
});
test("unknown firstSeen prevents historical as-of, never silently backfill legacy reports",()=>{
 const s=make();
 for(const row of s.rows)if(row.report_date==="2026-11-10"&&row.dataset==="tff"&&row.code==="099741")row.first_seen_at=null;
 const r=compute(s,{observedAt:"2026-11-23T12:00:00Z"});
 assert.equal(r.periods.tff.state,"incomplete_previous");
 assert.equal(r.groups[0].state,"blocked");
 const descriptive=compute(s);
 assert.equal(descriptive.groups[0].state,"descriptive");
});
test("future observation and future raw capture clocks rejected, not displayed as verified",()=>{
 assert.throws(()=>compute(make(),{observedAt:"2026-12-01T00:00:00Z"}),/FUTURE_OBSERVATION/);
 const s=make();s.rows[0].first_seen_at="2028-01-01T00:00:00Z";
 assert.throws(()=>compute(s),/CFTC_FUTURE_CLOCK/);
 assert.throws(()=>watch.build(make()),/NOW_UTC_REQUIRED/);
});
test("insufficient data, invalid dates, and invalid CFTC numbers fail closed",()=>{
 const s=make();s.rows[0].oi=-1;
 assert.throws(()=>compute(s),/INVALID_CFTC_ROWS/);
 const empty=make([]),r=compute(empty);
 assert.equal(r.state,"no_data");assert.equal(r.groups.length,0);
});
test("index is not presented as prediction and remains unavailable with insufficient history",()=>{
 const r=compute();
 const a=r.groups.find(g=>g.id==="fx_relative").entries[0];
 assert.equal(a.historicalIndex52,null);
 assert.equal(a.relativeStatus,"insufficient");
 assert.ok(r.notes.some(x=>x.includes("NON segnale")));
});
