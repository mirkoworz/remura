// REMURA Contributors v0.51 LAB — 20/11/2026 CET
// Direct Worker boundary only, synthetic requests; no Cloudflare or D1 provider.
import assert from "node:assert/strict";
import {webcrypto} from "node:crypto";
import worker from "./contributors_worker_candidate.mjs";
if(!globalThis.crypto)globalThis.crypto=webcrypto;
const origin="https://staging.example.invalid";
const env={WORKER_CANDIDATE_ENABLED:"LAB_ONLY",HTTP_CANDIDATE_ENABLED:"LAB_ONLY",STAGING_ENABLED:"D1_CANDIDATE",STAGING_ORIGIN:origin,ACCESS_AUD:"a".repeat(64),ACCESS_ACCOUNT:"b".repeat(32),IDENTITY_HMAC_KEY:"12".repeat(32)};
const id={account_id:env.ACCESS_ACCOUNT,user_uuid:"12345678-1234-1234-1234-123456789abc",email:"fixture@example.invalid",service_token_status:false};
const context=(value=id,aud=env.ACCESS_AUD)=>({access:{aud,getIdentity:async()=>value}});
const forged={"Cf-Access-Authenticated-User-Email":id.email,"Cf-Access-Jwt-Assertion":"synthetic.invalid.token","Cookie":"CF_Authorization=synthetic","Origin":origin,"Sec-Fetch-Site":"same-origin","X-Remura-CSRF":"1","Content-Type":"application/json"};
let db=0,limits=0,passed=0;
env.CONTRIBUTORS_DB={withSession(){db++;throw Error("synthetic-private-db-detail");}};
env.CONTRIBUTORS_RATE_LIMITER={async limit(){limits++;return {success:true};}};
function request(path,method){return new Request(origin+path,{method,headers:forged,...(method==="POST"?{body:"{}"}:{})});}
async function check(path,method,ctx,e,status,n){
 const before=limits;
 const res=await worker.fetch(request(path,method),e,ctx);
 assert.equal(res.status,status);
 assert.equal(res.headers.get("Cache-Control"),"no-store, max-age=0");
 assert.equal(res.headers.get("Access-Control-Allow-Origin"),null);
 assert.equal(res.headers.get("Set-Cookie"),null);
 assert.doesNotMatch(await res.text(),/fixture@example|synthetic-private|synthetic\.invalid/);
 assert.equal(db,0);assert.equal(limits-before,n);passed++;
}
for(const [path,method] of [["/","GET"],["/api/profile","POST"]]){
 for(const c of [{},context(id,"c".repeat(64)),context({...id,account_id:"d".repeat(32)}),context({...id,service_token_status:true}),context({...id,service_token_id:"synthetic-service"}),context({...id,service_token_status:undefined}),context({...id,user_uuid:"not-a-uuid"}),{access:{aud:env.ACCESS_AUD,getIdentity:async()=>{throw Error("synthetic-private-identity");}}}])await check(path,method,c,env,403,0);
 for(const flags of [{WORKER_CANDIDATE_ENABLED:"DISABLED"},{HTTP_CANDIDATE_ENABLED:"DISABLED"},{STAGING_ENABLED:"DISABLED"}])await check(path,method,context(),{...env,...flags},403,0);
 for(const [result,status] of [[{success:false},429],[{success:"true"},403],[{},403]]){
  const e={...env,CONTRIBUTORS_RATE_LIMITER:{async limit(){limits++;return result;}}};
  await check(path,method,context(),e,status,1);
 }
 await check(path,method,context(),{...env,CONTRIBUTORS_RATE_LIMITER:{async limit(){limits++;throw Error("synthetic-private-limiter");}}},403,1);
}
console.log("REMURA direct Worker perimeter synthetic cases: "+passed+" PASS");
