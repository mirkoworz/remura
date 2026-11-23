/* REMURA B v20.9: official public CFTC audit is descriptive-only.
 * All fixtures are synthetic; no network.
 */
const test=require("node:test");
const assert=require("node:assert/strict");
const watch=require("../cot-intelligence-watchlist.js");
const NOW="2026-11-23T15:30:00Z";
const weeks=["2026-11-03","2026-11-10","2026-11-17"];
function make(){
 const rows=weeks.flatMap((d,i)=>Object.entries(watch.EXPECTED).flatMap(([dataset,codes])=>
  codes.map((code,j)=>({
   dataset,code,report_date:d,oi:2000,
   first_long:400+i*20+j*3,first_short:200,second_long:200,second_short:100,
   first_seen_at:null
  }))
 ));
 return {schema:"remura-cot-intelligence-snapshot-v1",
   source:"official_public_cftc_socrata",
   captureClock:"public_api_read_at_not_official_publication",
   readAtUtc:"2026-11-23T15:00:00Z",
   datasetIds:{tff:"gpe5-46if",disagg:"72hh-3qpy"},
   rows,rowCount:rows.length,truncated:false};
}
test("public CFTC input can produce descriptive only rankings without first-seen invention",()=>{
 const r=watch.build(make(),{nowUtc:NOW,window:52});
 assert.equal(r.state,"descriptive_ready");
 assert.equal(r.mode,"descriptive_only");
 assert.equal(r.source,"CFTC official public API (read-only audit)");
 assert.equal(r.publicReadAtUtc,"2026-11-23T15:00:00.000Z");
 assert.deepEqual(r.groups.map(x=>x.entries.length),[28,4,3]);
 assert.ok(r.groups[0].entries.every(x=>x.firstLocalCaptureUtc.every(t=>t===null)));
});
test("public audit read time cannot validate an earlier historical as-of",()=>{
 assert.throws(()=>watch.build(make(),{nowUtc:NOW,observedAt:"2026-11-22T00:00:00Z"}),/PUBLIC_SNAPSHOT_CANNOT_PROVE_HISTORICAL_ASOF/);
});
test("public audit cannot claim private REMURA first capture metadata",()=>{
 const s=make();s.rows[0].first_seen_at="2026-11-20T20:35:00Z";
 assert.throws(()=>watch.build(s,{nowUtc:NOW}),/PUBLIC_SNAPSHOT_MUST_NOT_INVENT_LOCAL_CAPTURE/);
});
test("public snapshot wrong capture provenance or clock fails closed",()=>{
 const s=make();
 assert.throws(()=>watch.build({...s,readAtUtc:"2026-12-01T00:00:00Z"},{nowUtc:NOW}),/INVALID_OR_TRUNCATED_SNAPSHOT/);
 assert.throws(()=>watch.build({...s,readAtUtc:"unknown"},{nowUtc:NOW}),/INVALID_OR_TRUNCATED_SNAPSHOT/);
 assert.throws(()=>watch.build({...s,captureClock:"first_local_capture_not_official_publication"},{nowUtc:NOW}),/INVALID_OR_TRUNCATED_SNAPSHOT/);
});
test("public source is independent of existing private-cache provenance gate",()=>{
 const s=make();
 const old={...s,source:"existing_private_cftc_cache",captureClock:"first_local_capture_not_official_publication"};
 const r=watch.build(old,{nowUtc:NOW,observedAt:"2026-11-23T12:00:00Z"});
 assert.equal(r.state,"no_data"); // unknown first-seen rows excluded; never retroactively known
});
