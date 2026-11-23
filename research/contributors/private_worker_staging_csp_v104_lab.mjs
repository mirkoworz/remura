// REMURA Contributors v1.04 LAB — 24/11/2026 00:12 CET (Europe/Rome).
// Authenticated read-only Worker hardening: inert until separately authorized.
// No new API or D1 operation: delegates to v1.03, which delegates to
// v1.01 Access/D1 fail-closed guard. NEVER attaches to the public Pages site.
import {privateStagingSafeReadV103} from './private_worker_staging_saferead_v103_lab.mjs';

const PAGE_PATHS=new Set(['/owner/','/owner/levels/','/contributors/','/contributors/levels/']);
const OLD_VERSION='REMURA Contributors v1.03 LAB';
const NEW_VERSION='REMURA Contributors v1.04 LAB';
const OLD_AT='23/11/2026 23:05 CET';
const NEW_AT='24/11/2026 00:12 CET';
const STRICT_CSP="default-src 'none'; base-uri 'none'; object-src 'none'; "+
 "frame-ancestors 'none'; form-action 'none'; script-src 'none'; "+
 "connect-src 'none'; img-src 'none'; style-src 'self'; font-src 'none'";
const DENY_HEADERS=Object.freeze({
 'Content-Type':'application/json; charset=utf-8',
 'Cache-Control':'no-store, max-age=0',
 'X-Content-Type-Options':'nosniff',
 'X-Frame-Options':'DENY',
 'Content-Security-Policy':STRICT_CSP
});
const deny=()=>new Response('{"error":"denied"}',{status:403,headers:DENY_HEADERS});

export function createStagingCspV104({guardedRead}){
 if(typeof guardedRead!=='function')throw Error('V104_GUARDED_READER_REQUIRED');
 return async function cspRead(request,env,ctx){
  try{
   if(!(request instanceof Request)||request.method!=='GET'||request.body!==null)return deny();
   const path=new URL(request.url).pathname;
   const response=await guardedRead(request,env,ctx);
   if(response?.status!==200)return response??deny();
   if(!PAGE_PATHS.has(path))return response; // CSS remains Access/D1 gated.
   const type=response.headers.get('Content-Type')||'';
   if(!/^text\/html(?:;|$)/i.test(type))return deny();
   const oldHtml=await response.text();
   if(oldHtml.length>20000||!oldHtml.includes(OLD_VERSION)||
     !oldHtml.includes(OLD_AT)||!oldHtml.includes('SOLA LETTURA')||
     /<(?:form|script|iframe|object|embed|input|button|base)\b/i.test(oldHtml)||
     /\son(?:click|load|error|submit)\s*=/i.test(oldHtml))
       return deny();
   const html=oldHtml.replaceAll(OLD_VERSION,NEW_VERSION)
      .replaceAll('REMURA v1.03 LAB','REMURA v1.04 LAB')
      .replaceAll(OLD_AT,NEW_AT);
   const headers=new Headers(response.headers);
   headers.delete('Content-Length');
   headers.set('Content-Type','text/html; charset=utf-8');
   headers.set('Content-Security-Policy',STRICT_CSP);
   headers.set('Cache-Control','no-store, max-age=0');
   headers.set('X-Content-Type-Options','nosniff');
   headers.set('X-Frame-Options','DENY');
   headers.set('X-Robots-Tag','noindex, nofollow, noarchive');
   headers.set('Referrer-Policy','no-referrer');
   headers.set('Cross-Origin-Resource-Policy','same-origin');
   return new Response(html,{status:200,headers});
  }catch{return deny();}
 };
}

export const privateStagingCspV104=createStagingCspV104({
 guardedRead:privateStagingSafeReadV103
});
export const V104_READONLY=Object.freeze({
 version:'1.04',mode:'INERT_LAB',noScripts:true,noConnections:true,
 noForms:true,cssSameOriginOnly:true,ownerContributorRoleSeparation:true,
 additionalD1Reads:0,accessRuntimeVerified:false,
 workersDeployed:false,usersCreated:false,realPilotAllowed:false
});
