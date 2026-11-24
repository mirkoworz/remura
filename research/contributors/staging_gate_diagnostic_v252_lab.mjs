// REMURA V25.2 — temporary closed diagnostic — 24/11/2026 Europe/Rome.
// OWNER-reported Google login followed by staging_not_authorized; config values reported correct.
// REVIEW ONLY. Separate approval for deployment and one test. Always denies every request.
// No D1 calls, identity retrieval, outbound fetch, secret values, or client diagnostic output.
// Use dashboard Live logs only; keep persistent logs/traces off.
const hex=(v,n)=>typeof v==="string"&&v.length===n&&/^[a-f0-9]+$/.test(v);
function inspect(env,ctx){
 const a=ctx?.access;
 return {
  mode:env?.PRIVATE_WORKER_V078==="STAGING_AUTHENTICATED_READONLY",
  readonly:env?.CONTRIBUTORS_STAGE_READONLY==="EXPLICIT_STAGING_ONLY",
  enabled:env?.STAGING_ENABLED==="D1_CANDIDATE",
  aud_format:hex(env?.ACCESS_AUD,64),
  account_format:hex(env?.ACCESS_ACCOUNT,32),
  hmac_format:hex(env?.IDENTITY_HMAC_KEY,64)&&!/^0+$/.test(env.IDENTITY_HMAC_KEY),
  d1_prepare:typeof env?.CONTRIBUTORS_DB?.prepare==="function",
  d1_session:typeof env?.CONTRIBUTORS_DB?.withSession==="function",
  access_present:!!a,
  aud_matches:!!a&&hex(env?.ACCESS_AUD,64)&&a.aud===env.ACCESS_AUD,
  identity_method:typeof a?.getIdentity==="function"
 };
}
export default {
 async fetch(req,env,ctx){
  try {
   const u=new URL(req.url);
   if(req.method==="GET"&&u.origin==="https://remura-contributors-staging.mirkoworz.workers.dev"&&u.pathname==="/owner/"&&!u.search&&!u.hash){
    console.log("REMURA_DIAG_V252 "+JSON.stringify(inspect(env,ctx)));
   }
  }catch{console.log("REMURA_DIAG_V252 inspection_failed");}
  return new Response('{"error":"staging_not_authorized"}',{status:403,headers:{"Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store, max-age=0","X-Content-Type-Options":"nosniff"}});
 }
};
