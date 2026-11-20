// REMURA Contributors v0.31 LAB — 16/11/2026 09:08 CET
import assert from "node:assert/strict";
import {webcrypto} from "node:crypto";
import {candidateRequest} from "./http_access_candidate.mjs";
import {SQL} from "./d1_access_candidate.mjs";
import {SQL as intents} from "./operation_intent_candidate.mjs";
import {accessBinding} from "./access_binding_candidate.mjs";
import {SQL as intake} from "./d1_lab_adapter.mjs";
if(!globalThis.crypto)globalThis.crypto=webcrypto;
const origin="https://staging.example.invalid";
const env={HTTP_CANDIDATE_ENABLED:"LAB_ONLY",STAGING_ENABLED:"D1_CANDIDATE",STAGING_ORIGIN:origin,ACCESS_AUD:"a".repeat(64),ACCESS_ACCOUNT:"b".repeat(32),IDENTITY_HMAC_KEY:"12".repeat(32)};
const i={account_id:env.ACCESS_ACCOUNT,user_uuid:"12345678-1234-1234-1234-123456789abc",email:"fixture@example.invalid",service_token_status:false};
Object.assign(env,{CONTRIBUTORS_GENERATION:"4".repeat(32),CONTRIBUTORS_JOURNAL_PIN:"5".repeat(64),INTENT_HMAC_KEY:"34".repeat(32)});
const ctx={access:{aud:env.ACCESS_AUD,getIdentity:async()=>i}}, b=await accessBinding(ctx,env);
let limits=0,queries=[],limitResult=true,role="CONTRIBUTOR",allowed=true,prior=[],failWrite=false,generationOK=true,burned=new Set();
env.CONTRIBUTORS_RATE_LIMITER={async limit(p){assert.deepEqual(p,{key:b.subject});limits++;return {success:limitResult};}};
const payload={request_id:"00000000-0000-0000-0000-000000000001",market:"EURUSD",provider:"OANDA",ticker:"EURUSD",product:"SPOT",contract:"",period:"WEEK",kind:"DELTA_PEAK",price:"1.0854",anchor_utc:"2026-11-15T00:00:00Z",observed_utc:"2026-11-15T00:00:00Z",note:"fixture"};
env.CONTRIBUTORS_DB={withSession(mode){assert.equal(mode,"first-primary");return {prepare(sql){return {bind(...args){queries.push({sql,args});return {
 async all(){let results=sql===SQL.profile?(allowed?[{role,slot:role==="OWNER"?"owner":"friend-a",write_enabled:1,read_enabled:1,recovery_enabled:role==="OWNER"?1:0}]:[]):sql===SQL.catalog?[{market:"EURUSD",provider:"OANDA",ticker:"EURUSD",product:"SPOT",contract:""}]:sql===intents.generation?(generationOK?[{id:1}]:[]):sql===intents.permission?(allowed&&args[3]===role?[{allowed:1}]:[]):sql===SQL.contributor?(allowed&&role==="CONTRIBUTOR"?[{slot:"friend-a"}]:[]):sql===SQL.owner?(allowed&&role==="OWNER"?[{id:1}]:[]):sql===SQL.existing?prior:sql===SQL.receipts?[{id:7}]:[];return {success:true,meta:{served_by_primary:true},results};},
 async run(){if(sql===intents.burn){if(burned.has(args[0])||!allowed||args[3]!==role)throw Error("denied");burned.add(args[0]);return {success:true,meta:{served_by_primary:true,changes:1}};}if(failWrite)throw Error("secret database detail");if(sql===intake.insert)prior=[{id:7,...payload}];return {success:true,meta:{served_by_primary:true,changes:1}};}
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
assert.ok(queries.every(q=>q.sql===intents.generation));
const ok=await call(req());assert.equal(ok.status,200);assert.deepEqual(await ok.json(),{data:[{id:7}]});
assert.equal(ok.headers.get("Cache-Control"),"no-store, max-age=0");assert.equal(ok.headers.get("Access-Control-Allow-Origin"),null);
assert.equal((await call(req("/owner/queue"))).status,403);
assert.equal((await call(req("/owner/review",'{"id":1,"action":"APPROVED","reason":"x"}'))).status,409);
assert.equal((await call(req("/api/submit",JSON.stringify({...payload,role:"OWNER"})))).status,409);
const issue=async(path="/api/submit",body=payload)=>{
 const r=await call(req("/api/intent",JSON.stringify({path,body})));assert.equal(r.status,200);return (await r.json()).data.intent;
};
const send=(token,body=payload)=>call(req("/api/submit",JSON.stringify(body),{"X-Remura-Intent":token}));
const token=await issue();
assert.equal((await send("invalid")).status,409);
assert.equal((await send(token,{...payload,price:"2.5"})).status,409);
const first=await send(token);assert.equal(first.status,200);assert.deepEqual((await first.json()).data,{id:7,status:"UNREVIEWED",duplicate:false});
assert.equal((await send(token)).status,409);
const duplicate=await send(await issue());assert.deepEqual((await duplicate.json()).data,{id:7,status:"UNREVIEWED",duplicate:true});
assert.equal(queries.filter(q=>q.sql===intake.insert).length,1);
prior=[];failWrite=true;const badToken=await issue();const bad=await send(badToken);assert.equal(bad.status,409);assert.deepEqual(await bad.json(),{error:"not_confirmed",retry:false});
assert.equal((await send(badToken)).status,409);
assert.equal(queries.filter(q=>q.sql===intake.insert).length,2);
generationOK=false;assert.equal((await call(req())).status,403);generationOK=true;
assert.equal((await call(req(),ctx,{...env,CONTRIBUTORS_GENERATION:undefined})).status,403);
allowed=false;assert.equal((await call(req())).status,403);
role="OWNER";allowed=true;assert.equal((await call(req("/api/receipts"))).status,403);
assert.equal((await call(req("/owner/queue"))).status,200);
const beforeRevoke=queries.length;
assert.equal((await call(req("/owner/revoke",'{"slot":"friend-a"}'))).status,403);
assert.equal(queries.length,beforeRevoke);
assert.equal((await call(req("/api/intent",'{"path":"/owner/revoke","body":{"slot":"friend-a"}}'))).status,403);
assert.ok(queries.slice(beforeRevoke).every(q=>q.sql===intents.generation));
const p=await call(req("/api/profile","{}"));assert.equal(p.status,200);assert.deepEqual((await p.json()).data,{role:"OWNER",can_write:true,can_read:true,can_recover:true});
assert.equal((await call(req("/api/catalog","{}"))).status,403);
role="CONTRIBUTOR";const cat=await call(req("/api/catalog","{}"));assert.equal(cat.status,200);assert.equal((await cat.json()).data[0].ticker,"EURUSD");
allowed=false;assert.equal((await call(req("/api/profile","{}"))).status,403);
allowed=true;role="CONTRIBUTOR";failWrite=false;prior=[];
const switched=(at,patch)=>{let n=0;return {access:{aud:env.ACCESS_AUD,getIdentity:async()=>++n>=at?{...i,...patch}:i}};};
for(const change of [{user_uuid:"22345678-1234-1234-1234-123456789abc"},{email:"other@example.invalid"}]){
 const n=queries.length;
 assert.equal((await call(req(),switched(2,change))).status,403);
 assert.ok(queries.slice(n).every(q=>q.sql===intents.generation));
 const before=queries.length;
 assert.equal((await call(req("/api/intent",JSON.stringify({path:"/api/submit",body:payload})),switched(2,change))).status,403);
 assert.ok(queries.slice(before).every(q=>q.sql===intents.generation));
 const t=await issue();
 const request=()=>req("/api/submit",JSON.stringify(payload),{"X-Remura-Intent":t});
 const n2=queries.length;
 assert.equal((await call(request(),switched(2,change))).status,409);
 assert.ok(queries.slice(n2).every(q=>q.sql===intents.generation));
 const n3=queries.length;
 assert.equal((await call(request(),switched(3,change))).status,409);
 assert.ok(queries.slice(n3).some(q=>q.sql===intents.burn));
 assert.ok(queries.slice(n3).every(q=>[intents.generation,intents.burn].includes(q.sql)));
}
console.log("HTTP candidate adversarial checks passed");
