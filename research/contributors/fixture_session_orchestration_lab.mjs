// REMURA Contributors v0.53 LAB — 20/11/2026 CET
// Synthetic dependency injection only. No Wrangler import or remote entry point.
// One shot per in-memory closure, not durable cross-process lock or provider attestation.
function makeSyntheticSession(gate,probe,openSynthetic){
 let used=false;
 return async function run(cfg,evidence,explicit=false){
  if(used||explicit!==true)throw Error("fixture_session_denied");
  used=true;
  let proxy,receipt,failed=false,closed=false;
  try{
   // Snapshot JSON data before the first await. Never pass a caller's mutable config to the adapter.
   const config=JSON.parse(JSON.stringify(cfg)),expected=JSON.parse(JSON.stringify(evidence));
   gate(config,expected);
   proxy=await openSynthetic(config);
   if(!proxy||typeof proxy.dispose!=="function"||!proxy.env||Object.keys(proxy.env).length!==1||!Object.hasOwn(proxy.env,"CONTRIBUTORS_FIXTURE_DB")||!proxy.env.CONTRIBUTORS_FIXTURE_DB)throw Error("fixture_session_denied");
   receipt=await probe({FIXTURE_BATCH_MODE:"SYNTHETIC_ONLY",FIXTURE_DATABASE_NAME:"remura-contributors-fixture",CONTRIBUTORS_FIXTURE_DB:proxy.env.CONTRIBUTORS_FIXTURE_DB},true);
   if(receipt?.status!=="FIXTURE_BATCH_ROLLBACK_OBSERVED"||receipt.primary_reads!==4||receipt.batch_attempts!==1||receipt.marker_absent_after!==true||receipt.binding_identity_attested!==false||receipt.provider_cost_verified!==false||receipt.real_users!==false)throw Error("fixture_session_denied");
  }catch{failed=true;}
  finally{
   if(proxy){
    try{await proxy.dispose();closed=true;}catch{failed=true;}
   }
  }
  if(failed||!closed)throw Error("fixture_session_blocked_no_retry");
  return Object.freeze({status:"SYNTHETIC_SESSION_OBSERVED",session_dispose_returned:true,primary_reads:4,batch_attempts:1,provider_identity_attested:false,provider_cost_verified:false,remote_session_closed_verified:false});
 };
}
export {makeSyntheticSession};
