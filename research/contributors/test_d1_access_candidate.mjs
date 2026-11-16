// REMURA Contributors v0.20 LAB — 16/11/2026 07:02 CET
import assert from "node:assert/strict";
import {webcrypto} from "node:crypto";
import {accessBinding} from "./access_binding_candidate.mjs";
import {SQL,receipts,queue,history,revokeContributor,review} from "./d1_access_candidate.mjs";
if(!globalThis.crypto)globalThis.crypto=webcrypto;
const env={STAGING_ENABLED:"D1_CANDIDATE",ACCESS_AUD:"a".repeat(64),ACCESS_ACCOUNT:"b".repeat(32),IDENTITY_HMAC_KEY:"12".repeat(32)};
const identity={account_id:env.ACCESS_ACCOUNT,user_uuid:"12345678-1234-1234-1234-123456789abc",email:"fixture@example.invalid",service_token_status:false};
const ctx=(i=identity,aud=env.ACCESS_AUD)=>({access:{aud,getIdentity:async()=>i}});
const b=await accessBinding(ctx(),env);
assert.match(b.subject,/^[0-9a-f]{64}$/);assert.notEqual(b.subject,b.email_tag);
assert.deepEqual(await accessBinding(ctx(),env),b);
const changed=await accessBinding(ctx({...identity,email:"changed@example.invalid"}),env);
assert.equal(changed.subject,b.subject);assert.notEqual(changed.email_tag,b.email_tag);
assert.notEqual((await accessBinding(ctx({...identity,user_uuid:"22345678-1234-1234-1234-123456789abc"}),env)).subject,b.subject);
for(const c of [{},ctx(null),ctx(identity,"wrong"),ctx({...identity,account_id:"wrong"}),ctx({...identity,user_uuid:null}),ctx({...identity,email:"bad"}),ctx({...identity,service_token_status:true}),ctx({...identity,service_token_status:undefined}),ctx({...identity,service_token_id:"token"})])await assert.rejects(accessBinding(c,env),/access_denied/);
await assert.rejects(accessBinding(ctx(),{...env,STAGING_ENABLED:"DISABLED"}));
await assert.rejects(accessBinding(ctx(),{...env,IDENTITY_HMAC_KEY:"x"}));
let calls=[],role="CONTRIBUTOR",primary=true,changes=1,allowed=true;
env.CONTRIBUTORS_DB={withSession(mode){
 assert.equal(mode,"first-primary");let used=false;
 return {prepare(sql){assert.equal(used,false);used=true;return {bind(...args){calls.push({sql,args});return {
 async all(){
 const results=sql===SQL.contributor?(allowed&&role==="CONTRIBUTOR"?[{slot:"friend-a"}]:[]):sql===SQL.owner?(allowed&&role==="OWNER"?[{id:1}]:[]):[];
 return {success:true,meta:{served_by_primary:primary},results};
 },
 async run(){return {success:true,meta:{served_by_primary:primary,changes}};}
 };}}}};
}};
await receipts(ctx(),env);assert.deepEqual(calls.at(-1).args,[b.subject,b.email_tag,0]);
await assert.rejects(queue(ctx(),env));
await assert.rejects(revokeContributor(ctx(),env,"friend-b"));
role="OWNER";await queue(ctx(),env);await history(ctx(),env,1);
assert.equal(calls.at(-2).args[2],"RECOVERY");
await review(ctx(),env,1,"REVOKED","synthetic");assert.equal(calls.at(-2).args[2],"RECOVERY");
await revokeContributor(ctx(),env,"friend-a");assert.equal(calls.at(-1).args[2],"friend-a");
assert.equal(calls.at(-1).args[3],b.subject);
changes=0;await assert.rejects(revokeContributor(ctx(),env,"friend-a"),/write_unknown/);
primary=false;await assert.rejects(queue(ctx(),env));primary=true;
allowed=false;await assert.rejects(history(ctx(),env,1));
console.log("Access binding and primary-gated candidate checks passed");
