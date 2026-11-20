// REMURA Contributors v0.49 LAB — 20/11/2026 CET
// Inert diagnostic, no fetch handler or deployment config. Fixture DB ONLY.
// A caller flag is not proof of the binding identity or owner authorization.
// Never invoke remotely before explicit approval and independent DB UUID check.
const MARK = "REMURA_BATCH_ROLLBACK_FIXTURE_V1";
const SQL = Object.freeze({
 state: "SELECT write_enabled,read_enabled,recovery_enabled FROM lab_state WHERE id=1",
 marker: "SELECT count(*) AS n FROM lab_catalog WHERE market=? AND provider=? AND ticker=? AND product=? AND contract=?",
 insert: "INSERT INTO lab_catalog(market,provider,ticker,product,contract,source_group,active) VALUES(?,?,?,?,?,?,?)"
});
const KEYS = [MARK,"FIXTURE","ROLLBACK","SPOT",""];
const VALUES = [...KEYS,"FIXTURE_ONLY",0];
const deny=()=>Error("fixture_gate_denied");
function need(ok){if(!ok)throw deny();}
async function primaryRows(db,sql,args){
 const x=await db.withSession("first-primary").prepare(sql).bind(...args).all();
 need(x?.success===true && x.meta?.served_by_primary===true &&
      Number.isSafeInteger(x.meta.rows_read) && x.meta.rows_read>=0 &&
      x.meta.rows_written===0 && Array.isArray(x.results) && x.results.length===1);
 return x.results[0];
}
async function closed(db){
 const r=await primaryRows(db,SQL.state,[]);
 need(r.write_enabled===0 && r.read_enabled===0 && r.recovery_enabled===0);
}
async function markerAbsent(db){
 const r=await primaryRows(db,SQL.marker,KEYS);
 need(r.n===0);
}
async function fixtureBatchProbe(env,explicit=false){
 // Separate binding name. No default fallback to CONTRIBUTORS_DB.
 need(explicit===true && env?.FIXTURE_BATCH_MODE==="SYNTHETIC_ONLY" &&
      env.FIXTURE_DATABASE_NAME==="remura-contributors-fixture" &&
      !env.CONTRIBUTORS_DB && env.CONTRIBUTORS_FIXTURE_DB);
 const db=env.CONTRIBUTORS_FIXTURE_DB;
 await closed(db); await markerAbsent(db);
 // Both statements individually valid in the pinned schema; the second
 // duplicates the first primary key. Failed batch must roll back both.
 let failed=false,expected=false;
 try{
  await db.batch([db.prepare(SQL.insert).bind(...VALUES),db.prepare(SQL.insert).bind(...VALUES)]);
 }catch(e){
  failed=true;
  // Provider error format can vary; unknown errors are never PASS.
  expected=typeof e?.message==="string" &&
    /UNIQUE constraint failed: lab_catalog\.market, lab_catalog\.provider, lab_catalog\.ticker, lab_catalog\.product, lab_catalog\.contract/i.test(e.message);
 }
 // Readback even after unknown failure; never repair, delete, retry, or log raw error.
 await closed(db); await markerAbsent(db);
 need(failed && expected);
 return Object.freeze({status:"FIXTURE_BATCH_ROLLBACK_OBSERVED",primary_reads:4,
  batch_attempts:1,expected_unique_error:true,marker_absent_after:true,
  lab_database_touched:false,real_users:false,provider_cost_verified:false});
}
export {fixtureBatchProbe,SQL,MARK};
