// REMURA v0.97 Contributors pilot readiness — only new evidence gate tests.
// Fixtures use invented aggregate counts; no account IDs, people, tokens or Cloudflare API.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {LIMITS,EVIDENCE_SCHEMA,REQUIRED_ATTESTATIONS,report} from "./contributors_free_readiness_v097_lab.mjs";
const NOW=Date.parse("2026-11-22T22:00:00Z");
function evidence(){
 return {
  schema:EVIDENCE_SCHEMA,evidenceSource:"CLOUDFLARE_DASHBOARD_MANUAL_READ_ONLY",
  operatorCheckedReadOnly:true,observedAtUtc:"2026-11-22T21:30:00Z",
  account:{
   access:{plan:"ZERO_TRUST_FREE",activeSeatsUsed:2,seatsAllocated:50},
   workers:{plan:"WORKERS_FREE",requestsTodayUtc:20000,cpuP95Ms:2},
   d1:{databases:4,storageBytes:4000000,rowsReadTodayUtc:100000,
       rowsWrittenTodayUtc:1000,databaseSizesBytes:[1000000,1000000,1000000,1000000]}
  },
  pilot:{contributors:2,additionalSeats:2,newDatabases:0,dailyWorkerRequests:200,
    dailyD1RowsRead:10000,dailyD1RowsWritten:100,newStorageBytes:0,cpuP95MsEstimate:3},
  billing:{extraPaidServicesConfirmedAbsent:true,planPriceZeroConfirmed:true,noPaidUpgradeAuthorized:true},
  attestations:Object.fromEntries(REQUIRED_ATTESTATIONS.map(k=>[k,true]))
 };
}
const fail=(x,code)=>assert.ok(report(x,NOW).blockers.includes(code),code);
test("Cloudflare limits frozen to verified Nov-2026 Free values",()=>{
 assert.equal(LIMITS.accessFreeSeats,50);
 assert.equal(LIMITS.workerRequestsPerUtcDay,100000);
 assert.equal(LIMITS.d1RowsReadPerUtcDay,5000000);
 assert.equal(LIMITS.d1RowsWrittenPerUtcDay,100000);
 assert.equal(LIMITS.d1DatabasesPerAccount,10);
 assert.equal(LIMITS.d1AccountStorageBytes,5000000000);
 assert.equal(LIMITS.d1DatabaseStorageBytes,500000000);
 assert.equal(LIMITS.usageBudgetFraction,0.75);
});
test("blank public manifest is strictly NO_GO with all account values unknown",()=>{
 const x=JSON.parse(fs.readFileSync(new URL("./REMURA-CONTRIBUTORS-V097-EVIDENCE-BLANK.json",import.meta.url),"utf8"));
 const r=report(x,NOW);
 assert.equal(r.status,"NO_GO");assert.equal(r.goLive,false);
 assert.equal(r.deployAuthorized,false);
 assert.equal(r.accountFreeHeadroomVerified,false);
 assert.ok(r.blockers.length>5);
});
test("fully hypothetical green evidence is STILL not permission to deploy",()=>{
 const r=report(evidence(),NOW);
 assert.equal(r.status,"EVIDENCE_READY_FOR_INDEPENDENT_REVIEW");
 assert.equal(r.blockers.length,0);
 assert.equal(r.goLive,false);
 assert.equal(r.deployAuthorized,false);
 assert.equal(r.verification,"MANUAL_DASHBOARD_EVIDENCE_NOT_AN_AUTHORIZATION");
});
test("missing or malformed evidence fails closed without throw",()=>{
 for(const x of [undefined,null,42,[],{},Object.create(null)])assert.equal(report(x,NOW).status,"NO_GO");
});
test("unknown source, dashboard read-only observation and stale proof block",()=>{
 const x=evidence();x.evidenceSource="PRIVILEGED_API";fail(x,"LIVE_ACCOUNT_DASHBOARD_PROVENANCE_UNKNOWN");
 x.evidenceSource="CLOUDFLARE_DASHBOARD_MANUAL_READ_ONLY";
 x.operatorCheckedReadOnly=false;fail(x,"READ_ONLY_INSPECTION_NOT_CONFIRMED");
 x.operatorCheckedReadOnly=true;
 x.observedAtUtc="2026-11-20T21:30:00Z";fail(x,"EVIDENCE_TIME_UNVERIFIED_OR_STALE");
});
test("daily UTC counters cannot carry over after midnight even within 24h",()=>{
 const x=evidence();x.observedAtUtc="2026-11-22T23:55:00Z";
 const res=report(x,Date.parse("2026-11-23T00:05:00Z"));
 assert.ok(res.blockers.includes("DAILY_COUNTERS_NOT_SAME_UTC_DAY"));
});
test("future and invalid timestamp observations never pass",()=>{
 const x=evidence();x.observedAtUtc="2026-11-23T10:00:00Z";
 fail(x,"EVIDENCE_TIME_UNVERIFIED_OR_STALE");
 x.observedAtUtc="2026-11-31T21:00:00Z";
 fail(x,"EVIDENCE_TIME_UNVERIFIED_OR_STALE");
});
test("Cloudflare Access must truly have Free plan and 2 new seats",()=>{
 const x=evidence();x.account.access.plan="PAY_AS_YOU_GO";
 fail(x,"ACCESS_FREE_SEATS_NOT_ATTESTED");
 const y=evidence();y.account.access.activeSeatsUsed=49;
 fail(y,"NOT_ENOUGH_AVAILABLE_FREE_ACCESS_SEATS");
 const z=evidence();z.pilot.additionalSeats=1;
 fail(z,"NOT_ENOUGH_NEW_ACCESS_SEATS_RESERVED");
});
test("Worker request headroom is conservative and includes pilot forecast",()=>{
 const x=evidence();x.account.workers.requestsTodayUtc=74800;
 x.pilot.dailyWorkerRequests=300;
 fail(x,"WORKER_DAILY_HEADROOM_TOO_SMALL");
 x.account.workers.plan="WORKERS_PAID";
 fail(x,"WORKERS_FREE_USAGE_UNKNOWN");
});
test("Worker CPU estimate cannot silently cross 10 ms Free budget",()=>{
 const x=evidence();x.pilot.cpuP95MsEstimate=10;
 fail(x,"WORKER_CPU_FREE_LIMIT_NOT_PROTECTED");
 const y=evidence();y.account.workers.cpuP95Ms=11;
 fail(y,"WORKER_CPU_FREE_LIMIT_NOT_PROTECTED");
});
test("D1 read-rows headroom accounts for all databases and pilot",()=>{
 const x=evidence();x.account.d1.rowsReadTodayUtc=3750000;
 x.pilot.dailyD1RowsRead=1;fail(x,"D1_READ_ROWS_HEADROOM_TOO_SMALL");
});
test("D1 write-rows headroom accounts for D1 index additional writes via forecast",()=>{
 const x=evidence();x.account.d1.rowsWrittenTodayUtc=74990;
 x.pilot.dailyD1RowsWritten=20;fail(x,"D1_WRITE_ROWS_HEADROOM_TOO_SMALL");
});
test("D1 account storage and new DB count fail closed",()=>{
 const x=evidence();x.account.d1.storageBytes=4000000000;
 x.account.d1.databaseSizesBytes=[1000000000,1000000000,1000000000,1000000000];
 fail(x,"D1_TOTAL_STORAGE_HEADROOM_TOO_SMALL");
 const y=evidence();y.account.d1.databases=10;y.account.d1.databaseSizesBytes=Array(10).fill(1000000);
 y.account.d1.storageBytes=10000000;y.pilot.newDatabases=1;
 fail(y,"D1_DATABASE_COUNT_FREE_LIMIT");
});
test("D1 individual 500MB Free database storage must leave reserve",()=>{
 const x=evidence();x.account.d1.databaseSizesBytes=[400000000,1000000,1000000,1000000];
 x.account.d1.storageBytes=403000000;
 fail(x,"EXISTING_D1_DATABASE_TOO_LARGE_FOR_REMURA_RESERVE");
});
test("new storage cannot be falsely assigned to a noncreated DB",()=>{
 const x=evidence();x.pilot.newStorageBytes=5000000;
 fail(x,"STAGING_EXISTING_DATABASE_CAPACITY_NOT_ATTESTED");
 const y=evidence();y.pilot.newDatabases=1;y.pilot.newStorageBytes=400000000;
 fail(y,"NEW_D1_DATABASE_SIZE_HEADROOM_TOO_SMALL");
});
test("each independent security proof is required, including Access and D1 revocation",()=>{
 for(const key of REQUIRED_ATTESTATIONS){
  const x=evidence();x.attestations[key]=false;
  fail(x,"SECURITY_PROOF_REQUIRED_"+key.toUpperCase());
 }
 assert.ok(REQUIRED_ATTESTATIONS.includes("access_sessions_revoked_and_login_blocked"));
 assert.ok(REQUIRED_ATTESTATIONS.includes("d1_identity_revocation_enforced"));
});
test("invalid billing plan/add-ons or unapproved paid upgrade blocks pilot",()=>{
 const x=evidence();x.billing.planPriceZeroConfirmed=false;
 fail(x,"BILLING_FREE_CONFIGURATION_UNVERIFIED");
 const y=evidence();y.billing.noPaidUpgradeAuthorized=false;
 fail(y,"BILLING_FREE_CONFIGURATION_UNVERIFIED");
});
test("pilot only supports one or two contributors and sane forecast bounds",()=>{
 const x=evidence();x.pilot.contributors=3;
 fail(x,"PILOT_FORECAST_UNKNOWN_OR_UNBOUNDED");
 const y=evidence();y.pilot.dailyD1RowsWritten=null;
 fail(y,"PILOT_FORECAST_UNKNOWN_OR_UNBOUNDED");
});
test("evaluator and evidence template contain neither network calls nor secrets",()=>{
 const code=fs.readFileSync(new URL("./contributors_free_readiness_v097_lab.mjs",import.meta.url),"utf8");
 const file=fs.readFileSync(new URL("./REMURA-CONTRIBUTORS-V097-EVIDENCE-BLANK.json",import.meta.url),"utf8");
 assert.ok(!code.includes("fetch(")&&!code.includes("wrangler "));
 assert.ok(!code.includes("process.env"));
 assert.ok(!file.includes("api_token")&&!file.includes("account_id"));
 assert.ok(!file.includes("@"));
});
