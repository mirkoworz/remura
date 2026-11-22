// REMURA Contributors v0.97 LAB — 22/11/2026, Europe/Rome.
// Pure fail-closed readiness evaluator: does not call Cloudflare or authorize a deploy.
// Official Cloudflare Free limits verified Nov 22, 2026:
// https://developers.cloudflare.com/d1/platform/pricing/
// https://developers.cloudflare.com/d1/platform/limits/
// https://developers.cloudflare.com/workers/platform/limits/
// https://developers.cloudflare.com/cloudflare-one/team-and-resources/users/seat-management/
const LIMITS=Object.freeze({
  accessFreeSeats:50,
  workerRequestsPerUtcDay:100000,
  workerCpuMsPerInvocation:10,
  d1RowsReadPerUtcDay:5000000,
  d1RowsWrittenPerUtcDay:100000,
  d1AccountStorageBytes:5000000000,
  d1DatabaseStorageBytes:500000000,
  d1DatabasesPerAccount:10,
  // Conservative REMURA engineering policy, NOT Cloudflare's official limit:
  usageBudgetFraction:0.75,
  evidenceMaxAgeMs:24*3600000
});
const EVIDENCE_SCHEMA="remura.contributors.cloudflare-free-readiness.v097";
const REQUIRED_ATTESTATIONS=Object.freeze([
  "private_staging_isolated_from_prod",
  "server_verifies_access_jwt",
  "access_allowlist_denies_nonmembers",
  "roles_bound_server_side",
  "catalog_binding_server_authoritative",
  "owner_must_approve_other_peoples_levels",
  "contributor_cannot_modify_other_levels",
  "d1_identity_revocation_enforced",
  "access_sessions_revoked_and_login_blocked",
  "durable_receipt_and_no_blind_retry_verified",
  "owner_session_tested_on_safari",
  "contributor_session_tested_on_safari",
  "no_live_secrets_in_public_repo"
]);
function nonnegative(n){return Number.isSafeInteger(n)&&n>=0;}
function num(n){return typeof n==="number"&&Number.isFinite(n)&&n>=0;}
function report(evidence,now=Date.now()){
  const blockers=[];
  const fail=(code)=>{if(!blockers.includes(code))blockers.push(code);};
  const empty=()=>({schema:EVIDENCE_SCHEMA,status:"NO_GO",goLive:false,
    deployAuthorized:false,accountFreeHeadroomVerified:false,blockers,
    limits:LIMITS,verification:"MANUAL_DASHBOARD_EVIDENCE_NOT_AN_AUTHORIZATION"});
  if(!evidence||Object.getPrototypeOf(evidence)!==Object.prototype||!Number.isFinite(now)){
    fail("EVIDENCE_MISSING_OR_INVALID");return empty();
  }
  if(evidence.schema!==EVIDENCE_SCHEMA)fail("SCHEMA_MISMATCH");
  if(evidence.evidenceSource!=="CLOUDFLARE_DASHBOARD_MANUAL_READ_ONLY")
    fail("LIVE_ACCOUNT_DASHBOARD_PROVENANCE_UNKNOWN");
  if(evidence.operatorCheckedReadOnly!==true)fail("READ_ONLY_INSPECTION_NOT_CONFIRMED");
  let obs=NaN;
  if(typeof evidence.observedAtUtc==="string"&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(evidence.observedAtUtc)){
    obs=Date.parse(evidence.observedAtUtc);
    if(!Number.isFinite(obs)||new Date(obs).toISOString().replace(".000Z","Z")!==evidence.observedAtUtc)
      obs=NaN;
  }
  if(!Number.isFinite(obs)||obs>now||now-obs>LIMITS.evidenceMaxAgeMs)
    fail("EVIDENCE_TIME_UNVERIFIED_OR_STALE");
  else if(new Date(obs).toISOString().slice(0,10)!==new Date(now).toISOString().slice(0,10))
    fail("DAILY_COUNTERS_NOT_SAME_UTC_DAY");
  const account=evidence.account,proposed=evidence.pilot;
  if(!account||Object.getPrototypeOf(account)!==Object.prototype||
     !proposed||Object.getPrototypeOf(proposed)!==Object.prototype){
    fail("ACCOUNT_OR_PILOT_INPUT_MISSING");return empty();
  }
  const access=account.access,workers=account.workers,d1=account.d1;
  if(!access||Object.getPrototypeOf(access)!==Object.prototype||
     access.plan!=="ZERO_TRUST_FREE"||
     !nonnegative(access.activeSeatsUsed)||!nonnegative(access.seatsAllocated)||
     access.seatsAllocated>LIMITS.accessFreeSeats||access.seatsAllocated<1||
     access.activeSeatsUsed>access.seatsAllocated){
    fail("ACCESS_FREE_SEATS_NOT_ATTESTED");
  }
  if(!workers||Object.getPrototypeOf(workers)!==Object.prototype||
     workers.plan!=="WORKERS_FREE"||
     !nonnegative(workers.requestsTodayUtc)||!num(workers.cpuP95Ms)){
    fail("WORKERS_FREE_USAGE_UNKNOWN");
  }
  if(!d1||Object.getPrototypeOf(d1)!==Object.prototype||
     !nonnegative(d1.databases)||!nonnegative(d1.storageBytes)||
     !nonnegative(d1.rowsReadTodayUtc)||!nonnegative(d1.rowsWrittenTodayUtc)||
     !Array.isArray(d1.databaseSizesBytes)||d1.databaseSizesBytes.length!==d1.databases||
     d1.databaseSizesBytes.some(x=>!nonnegative(x))||
     d1.databaseSizesBytes.reduce((a,b)=>a+b,0)!==d1.storageBytes){
    fail("D1_ACCOUNT_USAGE_OR_DATABASE_SIZES_UNKNOWN");
  }
  if(!nonnegative(proposed.contributors)||proposed.contributors<1||proposed.contributors>2||
     !nonnegative(proposed.additionalSeats)||!nonnegative(proposed.newDatabases)||
     !nonnegative(proposed.dailyWorkerRequests)||!nonnegative(proposed.dailyD1RowsRead)||
     !nonnegative(proposed.dailyD1RowsWritten)||!nonnegative(proposed.newStorageBytes)||
     !num(proposed.cpuP95MsEstimate)){
    fail("PILOT_FORECAST_UNKNOWN_OR_UNBOUNDED");
  }
  if(nonnegative(proposed.contributors)&&nonnegative(proposed.additionalSeats)&&
      proposed.additionalSeats<proposed.contributors)
    fail("NOT_ENOUGH_NEW_ACCESS_SEATS_RESERVED");
  if(access&&nonnegative(access.activeSeatsUsed)&&nonnegative(access.seatsAllocated)&&
     nonnegative(proposed.additionalSeats)&&
     access.activeSeatsUsed+proposed.additionalSeats>access.seatsAllocated)
    fail("NOT_ENOUGH_AVAILABLE_FREE_ACCESS_SEATS");
  if(workers&&num(workers.cpuP95Ms)&&num(proposed.cpuP95MsEstimate)&&
     Math.max(workers.cpuP95Ms,proposed.cpuP95MsEstimate)>=LIMITS.workerCpuMsPerInvocation)
    fail("WORKER_CPU_FREE_LIMIT_NOT_PROTECTED");
  const B=LIMITS.usageBudgetFraction;
  if(workers&&nonnegative(workers.requestsTodayUtc)&&nonnegative(proposed.dailyWorkerRequests)&&
     workers.requestsTodayUtc+proposed.dailyWorkerRequests>LIMITS.workerRequestsPerUtcDay*B)
    fail("WORKER_DAILY_HEADROOM_TOO_SMALL");
  if(d1&&nonnegative(d1.rowsReadTodayUtc)&&nonnegative(proposed.dailyD1RowsRead)&&
     d1.rowsReadTodayUtc+proposed.dailyD1RowsRead>LIMITS.d1RowsReadPerUtcDay*B)
    fail("D1_READ_ROWS_HEADROOM_TOO_SMALL");
  if(d1&&nonnegative(d1.rowsWrittenTodayUtc)&&nonnegative(proposed.dailyD1RowsWritten)&&
     d1.rowsWrittenTodayUtc+proposed.dailyD1RowsWritten>LIMITS.d1RowsWrittenPerUtcDay*B)
    fail("D1_WRITE_ROWS_HEADROOM_TOO_SMALL");
  if(d1&&nonnegative(d1.storageBytes)&&nonnegative(proposed.newStorageBytes)&&
     d1.storageBytes+proposed.newStorageBytes>LIMITS.d1AccountStorageBytes*B)
    fail("D1_TOTAL_STORAGE_HEADROOM_TOO_SMALL");
  if(d1&&nonnegative(d1.databases)&&nonnegative(proposed.newDatabases)&&
     d1.databases+proposed.newDatabases>LIMITS.d1DatabasesPerAccount)
    fail("D1_DATABASE_COUNT_FREE_LIMIT");
  if(d1?.databaseSizesBytes?.some(x=>nonnegative(x)&&x>LIMITS.d1DatabaseStorageBytes*B))
    fail("EXISTING_D1_DATABASE_TOO_LARGE_FOR_REMURA_RESERVE");
  if(d1&&nonnegative(proposed.newDatabases)&&nonnegative(proposed.newStorageBytes)){
    if(proposed.newDatabases===0&&proposed.newStorageBytes>0)
      fail("STAGING_EXISTING_DATABASE_CAPACITY_NOT_ATTESTED");
    if(proposed.newDatabases>0&&proposed.newStorageBytes>proposed.newDatabases*
       LIMITS.d1DatabaseStorageBytes*B)
      fail("NEW_D1_DATABASE_SIZE_HEADROOM_TOO_SMALL");
  }
  if(evidence.billing?.extraPaidServicesConfirmedAbsent!==true||
     evidence.billing?.planPriceZeroConfirmed!==true||
     evidence.billing?.noPaidUpgradeAuthorized!==true)
    fail("BILLING_FREE_CONFIGURATION_UNVERIFIED");
  for(const k of REQUIRED_ATTESTATIONS)
    if(evidence.attestations?.[k]!==true)fail("SECURITY_PROOF_REQUIRED_"+k.toUpperCase());
  return {schema:EVIDENCE_SCHEMA,
    status:blockers.length?"NO_GO":"EVIDENCE_READY_FOR_INDEPENDENT_REVIEW",
    goLive:false,deployAuthorized:false,
    accountFreeHeadroomVerified:blockers.length===0,
    blockers,limits:LIMITS,
    verification:"MANUAL_DASHBOARD_EVIDENCE_NOT_AN_AUTHORIZATION"};
}
export {LIMITS,EVIDENCE_SCHEMA,REQUIRED_ATTESTATIONS,report};
