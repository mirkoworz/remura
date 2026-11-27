// REMURA Contributors v0.18 LAB — 15/11/2026 08:34 CET
// Closed staging identity probe. No DB, external fetch, logs or write routes.
// Trust ONLY ctx.access from direct authenticated Worker runtime.
// Google-only policy, account plan and actual identity shape need live verification.
// Explicit owner-controlled test binding; never use email alone or auto-enroll.
const AUD=/^[a-f0-9]{64}$/;
const ACCOUNT=/^[a-f0-9]{32}$/;
const UUID=/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/;
const EMAIL=/^[^\s@]{1,64}@[^\s@]{1,189}$/;
const headers={
 "Content-Type":"text/plain; charset=utf-8",
 "Cache-Control":"no-store, max-age=0",
 "X-Content-Type-Options":"nosniff",
 "Referrer-Policy":"no-referrer",
 "Content-Security-Policy":"default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
 "Permissions-Policy":"camera=(), microphone=(), geolocation=()",
 "X-Frame-Options":"DENY"
};
const reply=(status,body)=>new Response(body,{status,headers});
const closed=()=>reply(403,"REMURA Contributors staging closed");
function policy(env){
 if(env?.STAGING_ENABLED!=="IDENTITY_ONLY"||!AUD.test(env.ACCESS_AUD??"")||!ACCOUNT.test(env.ACCESS_ACCOUNT??"")||
 typeof env.TEST_UUID!=="string"||!UUID.test(env.TEST_UUID)||typeof env.TEST_EMAIL!=="string"||
 !EMAIL.test(env.TEST_EMAIL)||typeof env.STAGING_ORIGIN!=="string")return null;
 const u=new URL(env.STAGING_ORIGIN);
 if(u.protocol!=="https:"||u.origin!==env.STAGING_ORIGIN||u.username||u.password)return null;
 return {aud:env.ACCESS_AUD,account:env.ACCESS_ACCOUNT,uuid:env.TEST_UUID,email:env.TEST_EMAIL,origin:u.origin};
}
export default {
 async fetch(request,env,ctx){
  try {
   const p=policy(env);
   if(!p)return closed();
   const url=new URL(request.url);
   if(url.origin!==p.origin||url.pathname!=="/"||url.search||request.method!=="GET"||request.body!==null)return closed();
   const access=ctx?.access;
   if(!access||access.aud!==p.aud||typeof access.getIdentity!=="function")return closed();
   const i=await access.getIdentity();
   if(!i||i.account_id!==p.account||i.user_uuid!==p.uuid||i.email!==p.email||
      i.service_token_status!==false||
      (i.service_token_id!==undefined&&i.service_token_id!==null&&i.service_token_id!==""))return closed();
   return reply(200,"REMURA Contributors v0.18 LAB | 15/11/2026 08:34 CET\nIdentity test passed. No data collection.");
  }catch{return closed();}
 }
};
