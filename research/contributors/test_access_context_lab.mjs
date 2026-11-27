// REMURA Contributors v0.17 LAB — 14/11/2026 23:59 CET
import assert from "node:assert/strict";
import {fixtureActor} from "./access_context_lab.mjs";
const aud="a".repeat(64),account="b".repeat(32);
const uuid="00000000-0000-0000-0000-000000000001";
const identity={user_uuid:uuid,email:"friend@example.invalid",account_id:account,service_token_status:false};
const binding={uuid,email:identity.email,subject:"fixture-a",revoked:false};
const policy={synthetic:true,aud,account,bindings:[binding]};
const ctx=(i=identity,a=aud)=>({access:{aud:a,getIdentity:async()=>i}});
assert.deepEqual(await fixtureActor(ctx(),policy),{subject:"fixture-a",role:"CONTRIBUTOR"});
for(const [label,c,p] of [
 ["missing",{},policy],["wrong_aud",ctx(identity,"x"),policy],
 ["aud_only",{access:{aud}},policy],["missing_identity",ctx(null),policy],
 ["wrong_account",ctx({...identity,account_id:"c".repeat(32)}),policy],
 ["wrong_email",ctx({...identity,email:"other@example.invalid"}),policy],
 ["readded_same_email",ctx({...identity,user_uuid:"00000000-0000-0000-0000-000000000002"}),policy],
 ["service_token",ctx({...identity,service_token_status:true}),policy],
 ["service_id",ctx({...identity,service_token_id:"unexpected"}),policy],
 ["unknown_service_status",ctx({...identity,service_token_status:undefined}),policy],
 ["revoked",ctx(),{...policy,bindings:[{...binding,revoked:true}]}],
 ["not_synthetic",ctx(),{...policy,synthetic:false}],
 ["duplicate_binding",ctx(),{...policy,bindings:[binding,binding]}],
 ["real_email",ctx({...identity,email:"user@gmail.com"}),policy],
 ["runtime_error",{access:{aud,getIdentity:async()=>{throw Error("PRIVATE");}}},policy]
])await assert.rejects(fixtureActor(c,p),{message:"access_denied"},label);
assert.deepEqual(await fixtureActor(ctx({...identity,role:"OWNER",subject:"fixture-b"}),policy),
 {subject:"fixture-a",role:"CONTRIBUTOR"});
console.log("synthetic Access context checks passed");
