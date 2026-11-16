// REMURA Contributors v0.27 LAB — 16/11/2026 07:24 CET
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {webcrypto} from "node:crypto";
import {assets} from "./contributors_candidate_assets.mjs";
import {workerCandidate} from "./contributors_worker_candidate.mjs";
import {SQL} from "./d1_access_candidate.mjs";
import {SQL as I} from "./operation_intent_candidate.mjs";
if(!globalThis.crypto)globalThis.crypto=webcrypto;
for(const [path,name] of Object.entries({"/":"contributors_candidate.html","/contributors_candidate.css":"contributors_candidate.css","/contributors_candidate_ui.mjs":"contributors_candidate_ui.mjs","/contributors_candidate_client.mjs":"contributors_candidate_client.mjs"})){
 assert.equal(assets[path].body,readFileSync(new URL("./"+name,import.meta.url),"utf8"));
}
assert.equal(Object.keys(assets).length,4);
const origin="https://staging.example.invalid";
let db=0,limits=0,allowed=true,primary=true,limit=true,gen=true;
const env={WORKER_CANDIDATE_ENABLED:"LAB_ONLY",HTTP_CANDIDATE_ENABLED:"LAB_ONLY",STAGING_ENABLED:"D1_CANDIDATE",STAGING_ORIGIN:origin,ACCESS_AUD:"a".repeat(64),ACCESS_ACCOUNT:"b".repeat(32),IDENTITY_HMAC_KEY:"12".repeat(32),INTENT_HMAC_KEY:"34".repeat(32),CONTRIBUTORS_GENERATION:"4".repeat(32),CONTRIBUTORS_JOURNAL_PIN:"5".repeat(64)};
const id={account_id:env.ACCESS_ACCOUNT,user_uuid:"12345678-1234-1234-1234-123456789abc",email:"fixture@example.invalid",service_token_status:false};
const ctx={access:{aud:env.ACCESS_AUD,getIdentity:async()=>id}};
env.CONTRIBUTORS_RATE_LIMITER={async limit(){limits++;return {success:limit};}};
env.CONTRIBUTORS_DB={withSession(mode){assert.equal(mode,"first-primary");return {prepare(sql){return {bind(){return {async all(){db++;const results=sql===I.generation?(gen?[{id:1}]:[]):sql===SQL.profile?(allowed?[{role:"OWNER",slot:"owner",write_enabled:1,read_enabled:1,recovery_enabled:1}]:[]):[];return {success:true,meta:{served_by_primary:primary},results};}};}};}};}};
const call=(p="/",e=env,c=ctx,method="GET",host=origin)=>workerCandidate(new Request(host+p,{method,...(method==="POST"?{body:"{}",headers:{"Origin":origin,"Sec-Fetch-Site":"same-origin","X-Remura-CSRF":"1","Content-Type":"application/json"}}:{})}),e,c);
for(const [p,e,c,m,h] of [["/",{...env,WORKER_CANDIDATE_ENABLED:undefined},ctx],["/",env,{}],["/?x=1",env,ctx],["/README.md",env,ctx],["/d1_access_candidate.sql",env,ctx],["/",env,ctx,"HEAD"],["/",env,ctx,"GET","https://evil.invalid"],["/owner/revoke",env,ctx,"POST"]])assert.equal((await call(p,e,c,m,h)).status,403);
assert.equal(db,0);assert.equal(limits,0);
const r=await call();assert.equal(r.status,200);assert.match(await r.text(),/v0\.27 LAB/);assert.match(r.headers.get("Content-Security-Policy"),/frame-ancestors 'none'/);assert.equal(r.headers.get("Cache-Control"),"no-store, max-age=0");
for(const path of Object.keys(assets).filter(x=>x!=="/"))assert.equal((await call(path)).status,200);
assert.equal(db,5);assert.equal(limits,4);
allowed=false;assert.equal((await call()).status,403);allowed=true;
gen=false;assert.equal((await call("/contributors_candidate.css")).status,403);gen=true;
primary=false;assert.equal((await call()).status,403);primary=true;
limit=false;assert.equal((await call()).status,429);limit=true;
const api=await call("/api/profile",env,ctx,"POST");assert.equal(api.status,200);assert.equal((await api.json()).data.role,"OWNER");
console.log("Direct candidate Worker exact asset and API checks passed");
