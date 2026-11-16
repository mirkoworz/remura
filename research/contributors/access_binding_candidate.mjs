// REMURA Contributors v0.20 LAB — 16/11/2026 07:02 CET
// Offline candidate; no fetch handler, no env binding/config change, no enrollment endpoint.
// Direct Access-authenticated Worker context only. An env secret must be independently provisioned.
const AUD=/^[a-f0-9]{64}$/, ACCOUNT=/^[a-f0-9]{32}$/;
const UUID=/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/;
const EMAIL=/^[^\s@\u0000-\u001f\u007f-\u009f]{1,64}@[^\s@\u0000-\u001f\u007f-\u009f]{1,189}$/;
const HEX=/^[a-f0-9]{64}$/;
const deny=()=>Error("access_denied");
const hex=b=>Array.from(new Uint8Array(b),x=>x.toString(16).padStart(2,"0")).join("");
async function accessBinding(ctx,env){
 try{
  if(env?.STAGING_ENABLED!=="D1_CANDIDATE"||typeof env.ACCESS_AUD!=="string"||!AUD.test(env.ACCESS_AUD)||
     typeof env.ACCESS_ACCOUNT!=="string"||!ACCOUNT.test(env.ACCESS_ACCOUNT)||
     typeof env.IDENTITY_HMAC_KEY!=="string"||!HEX.test(env.IDENTITY_HMAC_KEY)||/^0+$/.test(env.IDENTITY_HMAC_KEY))throw deny();
  const access=ctx?.access;
  if(!access||access.aud!==env.ACCESS_AUD||typeof access.getIdentity!=="function")throw deny();
  const i=await access.getIdentity();
  if(!i||i.account_id!==env.ACCESS_ACCOUNT||typeof i.user_uuid!=="string"||!UUID.test(i.user_uuid)||
     typeof i.email!=="string"||!EMAIL.test(i.email)||i.service_token_status!==false||
     (i.service_token_id!==undefined&&i.service_token_id!==null&&i.service_token_id!==""))throw deny();
  const key=await crypto.subtle.importKey("raw",Uint8Array.from(env.IDENTITY_HMAC_KEY.match(/../g),x=>parseInt(x,16)),{name:"HMAC",hash:"SHA-256"},false,["sign"]);
  const tag=async (domain,value)=>hex(await crypto.subtle.sign("HMAC",key,new TextEncoder().encode(JSON.stringify(["remura-contributors-v1",env.ACCESS_ACCOUNT,env.ACCESS_AUD,domain,value]))));
  return Object.freeze({subject:await tag("uuid",i.user_uuid),email_tag:await tag("email",i.email)});
 }catch{throw deny();}
}
export {accessBinding};
