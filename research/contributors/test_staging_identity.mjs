// REMURA Contributors v0.18 LAB — 15/11/2026 08:34 CET
import assert from "node:assert/strict";
import fs from "node:fs";
import worker from "./staging_identity_worker.mjs";
const origin="https://staging.example.invalid",aud="a".repeat(64),account="b".repeat(32),uuid="c".repeat(8)+"-cccc-cccc-cccc-"+"c".repeat(12);
const env={STAGING_ENABLED:"IDENTITY_ONLY",ACCESS_AUD:aud,ACCESS_ACCOUNT:account,TEST_UUID:uuid,TEST_EMAIL:"test@example.invalid",STAGING_ORIGIN:origin};
const identity={account_id:account,user_uuid:uuid,email:env.TEST_EMAIL,service_token_status:false};
const context=(i=identity,a=aud)=>({access:{aud:a,getIdentity:async()=>i}});
const req=(url=origin+"/",init={})=>new Request(url,init);
let n=0;
async function check(expected,request,e,c){
 const result=await worker.fetch(request,e,c);
 assert.equal(result.status,expected);
 assert.match(result.headers.get("cache-control"),/no-store/);
 assert.match(result.headers.get("content-security-policy"),/frame-ancestors 'none'/);
 assert.equal(result.headers.get("access-control-allow-origin"),null);
 const body=await result.text();
 for(const secret of [uuid,account,aud,env.TEST_EMAIL])assert.ok(!body.includes(secret));
 if(expected===403)assert.equal(body,"REMURA Contributors staging closed");
 n++;
}
await check(200,req(),env,context());
await check(403,req(),{},context());
await check(403,req(),{...env,STAGING_ENABLED:"DISABLED"},context());
for(const key of Object.keys(env)){const e={...env};delete e[key];await check(403,req(),e,context());}
await check(403,req(),env,{});
await check(403,req(origin+"/",{headers:{"Cf-Access-Jwt-Assertion":"fake","Cf-Access-Authenticated-User-Email":env.TEST_EMAIL}}),env,{});
await check(403,req(),env,context(identity,"d".repeat(64)));
for(const [key,value] of [["account_id","wrong"],["user_uuid","wrong"],["email","other@example.invalid"],["service_token_status",true],["service_token_status",undefined],["service_token_id","token"]]){
 await check(403,req(),env,context({...identity,[key]:value}));
}
await check(403,req(),env,context(null));
await check(403,req(),env,{access:{aud,getIdentity:async()=>{throw Error("internal detail")}}});
await check(403,req(),env,{access:{aud}});
for(const url of [origin+"/api",origin+"/?x=1","https://other.example.invalid/","http://staging.example.invalid/"])await check(403,req(url),env,context());
for(const method of ["HEAD","POST","OPTIONS","PUT","DELETE"])await check(403,req(origin+"/",{method}),env,context());
for(const val of ["http://staging.example.invalid","https://staging.example.invalid/","broken"])await check(403,req(),{...env,STAGING_ORIGIN:val},context());
const cfg=JSON.parse(fs.readFileSync(new URL("./wrangler.staging.json",import.meta.url),"utf8"));
assert.equal(cfg.workers_dev,false);
assert.equal(cfg.preview_urls,false);
assert.deepEqual(cfg.routes,[]);
assert.deepEqual(cfg.vars,{STAGING_ENABLED:"DISABLED"});
assert.deepEqual(Object.keys(cfg).sort(),["name","main","compatibility_date","workers_dev","preview_urls","routes","vars","observability"].sort());
assert.equal(cfg.observability.enabled,false);
console.log("Identity staging: "+n+" synthetic HTTP checks; closed config verified.");
