// REMURA Contributors v0.17 LAB — 14/11/2026 23:59 CET
// Synthetic ctx.access contract adapter ONLY. Never accept ctx from HTTP bodies.
// The runtime supplies authenticated context; this module does not verify JWTs.
// Real deployment, Google IdP policy and identity semantics are NOT proven.
const UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const EMAIL=/^[a-z0-9][a-z0-9._+-]{0,62}@example\.invalid$/;
const AUD=/^[0-9a-f]{64}$/;
const ACCOUNT=/^[0-9a-f]{32}$/;
const denial=()=>new Error("access_denied");
function config(policy){
 if(!policy||policy.synthetic!==true||!AUD.test(policy.aud)||!ACCOUNT.test(policy.account)||
    !Array.isArray(policy.bindings)||policy.bindings.length>2)throw denial();
 const ids=new Set(),emails=new Set(),subjects=new Set();
 for(const b of policy.bindings){
  if(!b||!UUID.test(b.uuid)||!EMAIL.test(b.email)||!/^fixture-[a-z0-9-]{1,48}$/.test(b.subject)||
     typeof b.revoked!=="boolean"||ids.has(b.uuid)||emails.has(b.email)||subjects.has(b.subject))throw denial();
  ids.add(b.uuid);emails.add(b.email);subjects.add(b.subject);
 }
 return policy;
}
async function fixtureActor(ctx,policy){
 try{
  const p=config(policy);
  const access=ctx?.access;
  if(!access||typeof access.aud!=="string"||access.aud!==p.aud||typeof access.getIdentity!=="function")throw denial();
  const identity=await access.getIdentity();
  // Refuse unknown/missing/service-token identity. Never fall back to email.
  if(!identity||typeof identity.user_uuid!=="string"||!UUID.test(identity.user_uuid)||
     typeof identity.email!=="string"||!EMAIL.test(identity.email)||
     identity.account_id!==p.account||identity.service_token_status!==false||
     (identity.service_token_id!==undefined&&identity.service_token_id!==null&&identity.service_token_id!==""))throw denial();
  const binding=p.bindings.find(b=>b.uuid===identity.user_uuid&&b.email===identity.email&&!b.revoked);
  if(!binding)throw denial();
  return Object.freeze({subject:binding.subject,role:"CONTRIBUTOR"});
 }catch{throw denial();}
}
export {fixtureActor};
