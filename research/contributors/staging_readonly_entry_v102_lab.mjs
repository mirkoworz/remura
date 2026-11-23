// REMURA Contributors v1.02 LAB · 23/11/2026 Europe/Rome.
// A real Workers module entrypoint candidate for an independently approved,
// Access-protected direct Worker (no Static Assets router, no service binding).
// INERT until separately configured and deployed by the OWNER. No POST permitted.
// v1.04: deny all scripts and client connections by CSP after v1.03 role gate.
import {privateStagingCspV104} from './private_worker_staging_csp_v104_lab.mjs';
const CLOSED_HEADERS=Object.freeze({
 'Content-Type':'application/json; charset=utf-8',
 'Cache-Control':'no-store, max-age=0','X-Content-Type-Options':'nosniff'
});
const deny=()=>new Response('{"error":"staging_not_authorized"}',{status:403,headers:CLOSED_HEADERS});
function stagingReady(env,ctx){
 return env?.PRIVATE_WORKER_V078==='STAGING_AUTHENTICATED_READONLY'&&
   env?.CONTRIBUTORS_STAGE_READONLY==='EXPLICIT_STAGING_ONLY'&&
   env?.STAGING_ENABLED==='D1_CANDIDATE'&&
   typeof env?.ACCESS_AUD==='string'&&/^[a-f0-9]{64}$/.test(env.ACCESS_AUD)&&
   typeof env?.ACCESS_ACCOUNT==='string'&&/^[a-f0-9]{32}$/.test(env.ACCESS_ACCOUNT)&&
   typeof env?.IDENTITY_HMAC_KEY==='string'&&/^[a-f0-9]{64}$/.test(env.IDENTITY_HMAC_KEY)&&
   !/^0+$/.test(env.IDENTITY_HMAC_KEY)&&
   typeof env?.CONTRIBUTORS_DB?.prepare==='function'&&
   ctx?.access?.aud===env.ACCESS_AUD&&
   typeof ctx?.access?.getIdentity==='function';
}
export default {
 async fetch(req,env,ctx){
  try{
   if(!(req instanceof Request)||req.method!=='GET'||!stagingReady(env,ctx))return deny();
   return await privateStagingCspV104(req,env,ctx);
  }catch{return deny()}
 }
};
export const V102_ENTRY=Object.freeze({
 version:'1.04',mode:'INERT_DEPLOYMENT_CANDIDATE',onlyGet:true,
 directAccessRequired:true,stagingUrlConfigured:false,
 providerVerified:false,authorized:false,deployed:false,readOnlyPresentation:true,strictCsp:true
});
