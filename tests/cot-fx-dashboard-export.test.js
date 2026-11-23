/* REMURA Filone B v21.1 — NEW offline dashboard export contract tests.
 * Synthetic-only fixtures; no CFTC request, DB, broker or filesystem mutation.
 */
"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const os=require("node:os");
const path=require("node:path");
const child=require("node:child_process");
const watch=require("../cot-intelligence-watchlist.js");
const cli=require("../scripts/cot_fx_dashboard_export.js");
const NOW="2026-11-23T20:30:00Z";
const DATES=["2026-11-03","2026-11-10","2026-11-17"];
function sample(source="official_public_cftc_socrata"){
 const rows=DATES.flatMap((day,i)=>
  Object.entries(watch.EXPECTED).flatMap(([dataset,codes])=>
   codes.map((code,j)=>({
    dataset,code,report_date:day,oi:10000,
    first_long:2300+i*12+j,first_short:1200+j,
    second_long:3000+j,second_short:1900+i*4+j,
    first_seen_at:source==="existing_private_cftc_cache"
       ?new Date(Date.parse(day+"T00:00:00Z")+3*86400000).toISOString():null
   }))
  )
 );
 return {schema:"remura-cot-intelligence-snapshot-v1",source,
  captureClock:source==="existing_private_cftc_cache"
    ?"first_local_capture_not_official_publication"
    :"public_api_read_at_not_official_publication",
  ...(source==="official_public_cftc_socrata"?{readAtUtc:"2026-11-23T18:00:00Z"}:{}),
  rows,rowCount:rows.length,truncated:false};
}
test("seven CFTC contracts and 28 derived crosses are descriptive-only, no trading",()=>{
 const r=cli.render(sample(),{nowUtc:NOW});
 assert.equal(r.schema,"remura-cot-dashboard-fx-v1");
 assert.equal(r.version,"B_V21_1_LAB");
 assert.equal(r.state,"descriptive_ready");
 assert.equal(r.factors.length,7);
 assert.equal(r.crosses.length,28);
 assert.equal(new Set(r.factors.map(x=>x.cftcContractCode)).size,7);
 assert.equal(r.latestCftcReportDate,"2026-11-17");
 assert.equal(r.factors[0].historyStatus,"insufficient");
 assert.equal(r.factors[0].cotIndex52AssetManagers,null);
 assert.equal(r.timeClaims.sourceAuthenticatedByExporter,false);
 assert.ok(r.crosses.every(x=>x.derivedNotDirectSpot));
 assert.ok(r.use.includes("NOT_TRADING_SIGNALS"));
});
test("GBP/AUD output is factor change difference, not direct forex institutional positioning",()=>{
 const r=cli.render(sample(),{nowUtc:NOW});
 const f=Object.fromEntries(r.factors.map(x=>[x.currency,x]));
 const pair=r.crosses.find(x=>x.symbol==="GBPAUD");
 assert.ok(Math.abs(pair.assetManagerWeeklyRelativeChangePp-
   (f.GBP.weeklyAssetManagerChangePp-f.AUD.weeklyAssetManagerChangePp))<1e-9);
 assert.deepEqual(pair.legs,[{currency:"GBP",weight:1},{currency:"AUD",weight:-1}]);
});
test("incomplete CFTC contract refuses a misleading six-factor dashboard",()=>{
 const s=sample();
 s.rows=s.rows.filter(r=>!(r.code==="099741"&&r.report_date==="2026-11-17"));
 s.rowCount=s.rows.length;
 const r=cli.render(s,{nowUtc:NOW});
 assert.equal(r.state,"blocked");
 assert.equal(r.factors.length,0);
 assert.equal(r.crosses.length,0);
 assert.equal(r.underlyingCount,0);
 assert.equal(r.reason,"incomplete_latest");
});
test("historic public as-of refused, private self-reported first-seen remains labeled",()=>{
 assert.throws(()=>cli.render(sample(),{nowUtc:NOW,observedAt:"2026-11-22T20:00:00Z"}),
               /PUBLIC_SNAPSHOT_CANNOT_PROVE_HISTORICAL_ASOF/);
 const privateReport=cli.render(sample("existing_private_cftc_cache"),
                  {nowUtc:NOW,observedAt:"2026-11-22T20:00:00Z"});
 assert.equal(privateReport.mode,"first_local_capture_asof");
 assert.ok(privateReport.factors.every(f=>f.localFirstSeenUtc));
 assert.equal(privateReport.timeClaims.privateFirstSeenIsSelfReported,true);
 assert.equal(privateReport.timeClaims.sourceAuthenticatedByExporter,false);
});
test("offline CLI reads only a bounded existing file, no input is NO DATA",()=>{
 const script=path.join(__dirname,"..","scripts","cot_fx_dashboard_export.js");
 const empty=JSON.parse(child.execFileSync(process.execPath,[script],{encoding:"utf8"}));
 assert.equal(empty.status,"NO_OFFLINE_CFTC_SNAPSHOT_NO_REAL_FACTORS");
 assert.equal(empty.networkCalls,0);
 const folder=fs.mkdtempSync(path.join(os.tmpdir(),"remura-b-fx-"));
 try{
  const file=path.join(folder,"cftc-offline.json");
  fs.writeFileSync(file,JSON.stringify(sample()));
  const output=child.execFileSync(process.execPath,
   [script,"--snapshot",file,"--now-utc",NOW],{encoding:"utf8"});
  const r=JSON.parse(output);
  assert.equal(r.factors.length,7);
  assert.ok(!output.includes("BUY"));
  assert.ok(!output.includes("profitProbability"));
  assert.throws(()=>cli.argsOf(["--snapshot",file,"--snapshot",file,"--now-utc",NOW]),
    /INVALID_OFFLINE_ARGUMENTS/);
 }finally{fs.rmSync(folder,{recursive:true,force:true});}
});
