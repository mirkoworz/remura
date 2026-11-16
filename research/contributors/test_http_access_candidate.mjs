// REMURA Contributors v0.21 LAB — 16/11/2026 07:05 CET
import assert from "node:assert/strict";
import {webcrypto} from "node:crypto";
import {candidateRequest} from "./http_access_candidate.mjs";
import {SQL} from "./d1_access_candidate.mjs";
import {accessBinding} from "./access_binding_candidate.mjs";
import {SQL as intake} from "./d1_lab_adapter.mjs";
if(!globalThis.crypto)globalThis.crypto=webcrypto;
const origin="https://staging.example.invalid";
const env={HTTP_CANDIDATE_ENABLED:"LAB_ONLY",STAGING_ENABLED:"D1_CANDIDATE",STAGING_ORIGIN:origin,ACCESS_AUD:"a".repeat(64),ACCESS_ACCOUNT:"b".repeat(32),IDENTITY_HMAC_KEY:"12".repeat(32)};
const i={account_id:env.ACCESS_ACCOUNT,user_uuid:"12345678-1234-1234-1234-123456789abc",email:"fixture@example.invalid",service_token_status:false};
const ctx={access:{aud:env.ACCESS_AUD,getIdentity:async()=>i}}, b=await accessBinding(ctx,env);
let limits=0,queries=[],limitResult=true,role="CONTRIBUTOR",allowed=true,prior=[],failWrite=false;
env.CONTRIBUTORS_RATE_LIMITER={async limit(p){assert.deepEqual(p,{key:b.subject});limits++;return {success:limitResult};}};
const payload={request_id:"00000000-0000-0000-0000-000000000001",market:"EURUSD",provider:"OANDA",ticker:"EURUSD",product:"SPOT",contract:"",period:"WEEK",kind:"DELTA_PEAK",price:"1.0854",anchor_utc:"2026-11-15T00:00:00Z",observed_utc:"2026-11-15T00:00:00Z",note:"fixture"};
env.CONTRIBUTORS_DB={withSession(mode){assert.equal(mode,"first-primary");return {prepare(sql){return {bind(...args){queries.push({sql,args});return {
 async all(){let results=sql===SQL.contributor?(allowed&&role==="CONTRIBUTOR"?[{slot:"friend-a"}]:[]):sql===SQL.owner?(allowed&&role==="OWNER"?[{id:1}]:[]):sql===SQL.existing?prior:sql===SQL.receipts?[{id:7}]:[];return {success:true,meta:{served_by_primary:true},results};},
 async run(){if(failWrite)throw Error("secret database detail");if(sql===intake.insert)prior=[{id:7,...payload}];return {success:true,meta:{served_by_primary:true,changes:1}};}
 };}}}};}};
const defaults={"Origin":origin,"Sec-Fetch-Site":"same-origin","X-Remura-CSRF":"1","Content-Type":"application/json"};
function req(path="/api/receipts",body='{"after":0}',over={},method="POST",host=origin){
 const opts={method,headers:{...defaults,...over}};if(method!=="GET"&&method!=="HEAD")opts.body=body;
 return new Request(host+path,opts);
}
const call=(r,c=ctx,e=env)=>candidateRequest(r,e,c);
for(const r of [req("/api/receipts?x=1"),req("/api/receipts?"),req("/api/receipts/"),req("/private-api/volumetrica"),req("/api/receipts","{}",{},"GET"),req("/api/receipts","{}",{},"OPTIONS"),req("/api/receipts","{}",{Origin:"https://evil.example.invalid"}),req("/api/receipts","{}",{"Sec-Fetch-Site":"same-site"}),req("/api/receipts","{}",{"X-Remura-CSRF":"0"}),req("/api/receipts","{}",{"Content-Type":"text/plain"}),req("/api/receipts","{}",{"Content-Encoding":"gzip"}),req("/api/receipts","{}",{},"POST","https://evil.example.invalid")])assert.equal((await call(r)).status,403);
assert.equal((await call(req(),{})).status,403);
assert.equal((await call(req(),ctx,{...env,HTTP_CANDIDATE_ENABLED:"DISABLED"})).status,403);
assert.equal(limits,0);assert.equal(queries.length,0);
limitResult=false;assert.equal((await call(req())).status,429);assert.equal(queries.length,0);limitResult=true;
for(const r of [req("/api/receipts","x".repeat(4097)),req("/api/receipts","{}",{"Content-Length":"9999"}),req("/api/receipts","{}",{"Content-Length":"3"}),req("/api/receipts","null"),req("/api/receipts","[]"),req("/api/receipts",'{"after":0,"subject":"other"}'),req("/api/receipts",'{"after":0,"role":"OWNER"}')])assert.equal((await call(r)).status,400);
assert.equal(queries.length,0);
const ok=await call(req());assert.equal(ok.status,200);assert.deepEqual(await ok.json(),{data:[{id:7}]});
assert.equal(ok.headers.get("Cache-Control"),"no-store, max-age=0");assert.equal(ok.headers.get("Access-Control-Allow-Origin"),null);
assert.equal((await call(req("/owner/queue"))).status,403);
assert.equal((await call(req("/owner/review",'{"id":1,"action":"APPROVED","reason":"x"}'))).status,409);
assert.equal((await call(req("/api/submit",JSON.stringify({...payload,role:"OWNER"})))).status,409);
const send=()=>call(req("/api/submit",JSON.stringify(payload)));
const first=await send();assert.equal(first.status,200);assert.deepEqual((await first.json()).data,{id:7,status:"UNREVIEWED",duplicate:false});
const replay=await send();assert.deepEqual((await replay.json()).data,{id:7,status:"UNREVIEWED",duplicate:true});
assert.equal(queries.filter(q=>q.sql===intake.insert).length,1);
prior=[];failWrite=true;const bad=await send();assert.equal(bad.status,409);assert.deepEqual(await bad.json(),{error:"not_confirmed",retry:false});
assert.equal(queries.filter(q=>q.sql===intake.insert).length,2);
allowed=false;assert.equal((await call(req())).status,403);
role="OWNER";allowed=true;assert.equal((await call(req("/api/receipts"))).status,403);
assert.equal((await call(req("/owner/queue"))).status,200);
console.log("HTTP candidate adversarial checks passed");
