/* REMURA B V21.4 — NEW offline-only real 12-row stdout presentation contract tests.
 * Source file is the preserved actual GitHub stdout excerpt, NOT a full CFTC
 * snapshot, broker price, live institutional flow or tradable strategy.
 */
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const {build,SCHEMA,VERSION}=require("../scripts/cot_real_partial_presentation.js");
const input=JSON.parse(fs.readFileSync(path.join(__dirname,"../research/real-proofs/REMURA-B-CFTC-20261123-STDOUT-PARTIAL-EXCERPT.json"),"utf8"));
const now="2026-11-23T21:00:00Z";
const render=(doc=input,clock=now)=>build(doc,{nowUtc:clock});
const clone=x=>JSON.parse(JSON.stringify(x));

test("12 prior real printed CFTC values become safe 3-group HISTORIC partial display contract",()=>{
 const r=render();
 assert.equal(r.schema,SCHEMA);
 assert.equal(r.version,VERSION);
 assert.equal(r.state,"HISTORIC_PARTIAL");
 assert.equal(r.groups.tff_fx.length,5);
 assert.equal(r.groups.tff_direct.length,4);
 assert.equal(r.groups.disagg_direct.length,3);
 assert.equal(r.numberOfDisplayedObservations,12);
 assert.equal(r.numberOfDisplayedFxCrosses,5);
 assert.equal(r.numberOfTotalFxCrossesRecomputed,0);
 assert.equal(r.groups.tff_fx[0].symbol,"GBPAUD");
 assert.equal(r.groups.tff_fx[0].weeklyNetDeltaPp,7.6571);
 assert.equal(r.groups.disagg_direct[0].symbol,"XAUUSD");
 assert.equal(r.groups.disagg_direct[0].weeklyNetDeltaPp,-2.5162);
 assert.equal(r.publicEvidenceUrl,"https://github.com/mirkoworz/remura/actions/runs/45206837974");
 assert.equal(r.runId,45206837974);
 assert.equal(r.sourceReadAtUtc,"2026-11-23T15:35:17.664069Z");
});
test("raw 980 rows, first seen, private parity, predictions and live orders remain false",()=>{
 const r=render();
 for(const field of ["raw980SourceRowsRecovered","firstSeenAuthenticated","privatePublicParityVerified",
                    "institutionalLiveOrders","forecastOrTradeSignals","alphaProven"]){
  assert.equal(r[field],false,field);
 }
 assert.match(r.mode,/HISTORICAL_DESCRIPTIVE_PARTIAL_ONLY/);
 assert.equal(r.reportDateNotReleaseDate,true);
 assert.equal(r.labels.tffA,"Asset Manager/Institutional");
 assert.equal(r.labels.disaggA,"Managed Money");
});
test("two-week-old fixed proof is visibly stale, never silently a fresh market signal",()=>{
 const r=render(input,"2026-12-04T21:00:00Z");
 assert.equal(r.state,"STALE_HISTORIC_PARTIAL");
 assert.equal(r.forecastOrTradeSignals,false);
 assert.ok(r.ageDaysFromCftcReportDate>14);
});
test("fake public proof, missing 12th row, duplicate symbols or future as-of fail closed",()=>{
 for(const mutate of [
  x=>x.evidence.githubRunId=777,
  x=>x.evidence.fullSourceSnapshotRecoverableFromThisExcerpt=true,
  x=>x.observations.pop(),
  x=>x.observations[1].symbol=x.observations[0].symbol,
  x=>x.observations[2].weeklyCategoryANetChangePp=Infinity
 ]){
  const x=clone(input); mutate(x);
  assert.throws(()=>render(x));
 }
 assert.throws(()=>render(input,"2026-11-23T14:00:00Z"));
});
test("real data pipeline remains dependency free and no browser/network APIs are used",()=>{
 const code=fs.readFileSync(path.join(__dirname,"../scripts/cot_real_partial_presentation.js"),"utf8");
 assert.doesNotMatch(code,/https?\.(?:get|request)|\bfetch\s*\(|require\(["'](?:axios|node:https|https)["']\)/);
 assert.doesNotMatch(code,/writeFile|appendFile|fs\.createWriteStream/);
});
