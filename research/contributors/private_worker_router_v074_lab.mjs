// REMURA Contributors v0.74 LAB — 21/11/2026, 15:36 CET.
// Private direct-Worker asset/API router candidate. No default Worker export, no deploy.
const DENIAL = JSON.stringify({error:'denied'});
const ROUTE_CANDIDATES = Object.freeze({
 '/contributors/': {file:'contributors_recovery_v072_private_lab.html',role:'CONTRIBUTOR'},
 '/owner/': {file:'contributors_owner_recovery_v072_private_lab.html',role:'OWNER'},
 '/contributors/levels/': {file:'contributors_levels_v074_lab.html',role:'CONTRIBUTOR'},
 '/owner/levels/': {file:'owner_levels_v074_lab.html',role:'OWNER'}
});
const ASSET_FILES = Object.freeze([
 'contributors_recovery_v067_lab.css',
 'recovery_portal_v072_lab.mjs',
 'secure_exit_v072_lab.mjs',
 'recovery_transport_v070_lab.mjs',
 'reconciliation_client_v065_lab.mjs',
 'amendment_client_v063_lab.mjs',
 'contributors_levels_v074_lab.css',
 'contributors_levels_ui_v074_lab.mjs',
 'contributors_candidate_client.mjs'
]);
const LEVEL_PATHS=new Set(['/api/profile','/api/catalog','/api/receipts','/owner/queue','/owner/history','/api/intent','/api/submit','/owner/review']);
const READ_PATHS = new Set(['/api/amendment/reconcile','/api/amendment/mine','/owner/amendment/reconcile-queue']);
const baseHeaders=Object.freeze({
 'Cache-Control':'no-store, max-age=0',
 'X-Content-Type-Options':'nosniff',
 'Referrer-Policy':'no-referrer',
 'Cross-Origin-Resource-Policy':'same-origin',
 'X-Frame-Options':'DENY',
 'Permissions-Policy':'camera=(), microphone=(), geolocation=()',
 'Content-Security-Policy':"default-src 'none'; base-uri 'none'; object-src 'none'; frame-ancestors 'none'; form-action 'none'; style-src 'self'; script-src 'self'; connect-src 'self'"
});
const denial=()=>new Response(DENIAL,{status:403,headers:{...baseHeaders,'Content-Type':'application/json; charset=utf-8'}});
const fail=()=>{throw Error('REMURA_V074_PRIVATE_CLOSED')};
const assetType=path=>path.endsWith('.html')?'text/html; charset=utf-8':path.endsWith('.css')?'text/css; charset=utf-8':'text/javascript; charset=utf-8';
function verifiedOrigin(raw){
 if(typeof raw!=='string')fail();
 let url;try{url=new URL(raw)}catch{fail()}
 if(url.protocol!=='https:'||url.origin!==raw||url.pathname!=='/'||url.search||url.hash||url.username||url.password)fail();
 return url.origin;
}
function validateFiles(files){
 const required=[...Object.values(ROUTE_CANDIDATES).map(x=>x.file),...ASSET_FILES];
 if(files===null||typeof files!=='object'||Array.isArray(files)||Object.getPrototypeOf(files)!==Object.prototype||Object.keys(files).length!==required.length)fail();
 for(const name of required){if(!Object.hasOwn(files,name)||typeof files[name]!=='string'||files[name].length===0||files[name].length>120000)fail();}
 return Object.freeze(Object.fromEntries(required.map(name=>[name,files[name]])));
}
// The assetFiles map is supplied by a FUTURE build step; no static-assets router is used.
// Access authentication and D1 role checks are always executed server-side on GET.
export function createPrivateWorkerRouterV074({authenticate,profileRead,protectedRead,levelApi,assetFiles}){
 if([authenticate,profileRead,protectedRead,levelApi].some(f=>typeof f!=='function'))fail();
 const files=validateFiles(assetFiles);
 return async function privateWorkerRouterV074(request,env,ctx){
  try{
   if(env?.PRIVATE_WORKER_V074!=='OFFLINE_FIXTURE_ONLY'||env?.STAGING_ENABLED!=='D1_CANDIDATE')fail();
   const origin=verifiedOrigin(env.STAGING_ORIGIN);
   if(!ctx?.access||ctx.access.aud!==env.ACCESS_AUD||typeof ctx.access.getIdentity!=='function')fail();
   if(!(request instanceof Request)||!['GET','POST'].includes(request.method))fail();
   const url=new URL(request.url);
   if(url.origin!==origin||request.url!==origin+url.pathname)fail();
   if(request.method==='POST'){
    if(READ_PATHS.has(url.pathname))return await protectedRead(request,env,ctx);
    if(LEVEL_PATHS.has(url.pathname))return await levelApi(request,env,ctx);
    fail();
   }
   if(request.body!==null)fail();
   const route=ROUTE_CANDIDATES[url.pathname];
   let file, zone=null;
   if(route)file=route.file;
   else {
    const match=/^\/(contributors|owner)\/(?:levels\/)?([a-z0-9_.-]+)$/.exec(url.pathname);
    if(!match||!ASSET_FILES.includes(match[2]))fail();
    file=match[2]; zone=match[1]==='contributors'?'CONTRIBUTOR':'OWNER';
   }
   const actor=await authenticate(ctx,env);
   if(!actor||typeof actor.subject!=='string'||!/^[a-f0-9]{64}$/.test(actor.subject)||typeof actor.email_tag!=='string'||!/^[a-f0-9]{64}$/.test(actor.email_tag))fail();
   const profile=await profileRead(ctx,env,actor);
   if(!profile||profile.can_read!==true||!['OWNER','CONTRIBUTOR'].includes(profile.role)||(route&&profile.role!==route.role)||(zone!==null&&profile.role!==zone))fail();
   const headers={...baseHeaders,'Content-Type':assetType(file)};
   return new Response(files[file],{status:200,headers});
  }catch{return denial();}
 };
}
export const REMURA_V074_ALLOWED_STATIC=Object.freeze({pages:Object.freeze(Object.keys(ROUTE_CANDIDATES)),files:ASSET_FILES});
