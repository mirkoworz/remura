// REMURA Contributors v1.01 LAB — 23/11/2026 Europe/Rome.
// NEW, read-only, direct Access Worker staging candidate. NEVER deployed.
// Purpose: authenticate GET pages/assets using real ctx.access + D1 profile;
// every POST/PUT/DELETE is denied. No default fetch export, no Worker setup.
import {accessBinding} from './access_binding_candidate.mjs';
import {profile} from './d1_access_candidate.mjs';
import {privateAssetFilesV096} from './private_assets_v096_lab.mjs';
import {REMURA_V096_ALLOWED_STATIC} from './private_worker_router_v096_lab.mjs';

const ROUTES=Object.freeze({
  '/contributors/':{role:'CONTRIBUTOR',area:'RECOVERY',file:'contributors_recovery_v078_private_lab.html'},
  '/contributors/levels/':{role:'CONTRIBUTOR',area:'LEVELS',file:'contributors_levels_v096_lab.html'},
  '/owner/':{role:'OWNER',area:'RECOVERY',file:'contributors_owner_recovery_v078_private_lab.html'},
  '/owner/levels/':{role:'OWNER',area:'LEVELS',file:'owner_levels_v078_lab.html'}
});
const HEADERS=Object.freeze({
  'Cache-Control':'no-store, max-age=0',
  'X-Content-Type-Options':'nosniff',
  'Referrer-Policy':'no-referrer',
  'X-Frame-Options':'DENY',
  'Cross-Origin-Resource-Policy':'same-origin',
  'Permissions-Policy':'camera=(), microphone=(), geolocation=()',
  'Content-Security-Policy':"default-src 'none'; base-uri 'none'; object-src 'none'; frame-ancestors 'none'; form-action 'none'; style-src 'self'; script-src 'self'; connect-src 'self'"
});
const denied=()=>new Response('{"error":"denied"}',{status:403,headers:{
  ...HEADERS,'Content-Type':'application/json; charset=utf-8'
}});
function goodOrigin(origin){
  if(typeof origin!=='string'||origin.length>250)return false;
  try{const u=new URL(origin);
    return u.protocol==='https:'&&u.origin===origin&&u.pathname==='/'&&!u.search&&!u.hash&&!u.username&&!u.password;
  }catch{return false}
}
function fileFor(path){
  const page=ROUTES[path];
  if(page)return page;
  const m=/^\/(owner|contributors)\/(levels\/)?([a-z0-9_.-]+)$/.exec(path);
  if(!m)return null;
  const role=m[1]==='owner'?'OWNER':'CONTRIBUTOR', area=m[2]?'LEVELS':'RECOVERY',file=m[3];
  if(!REMURA_V096_ALLOWED_STATIC.areas[area].includes(file))return null;
  if(['owner_level_audit_ui_v077_lab.mjs','owner_level_integrity_ui_v078_lab.mjs'].includes(file)
      &&!(role==='OWNER'&&area==='LEVELS'))return null;
  return {role,area,file};
}
function validProfile(p,expected){
  // Read-only pilot: neither role needs mutation or recovery capability.
  return p&&p.role===expected&&p.can_read===true&&p.can_write===false&&p.can_recover===false;
}
function mime(file){
  return file.endsWith('.html')?'text/html; charset=utf-8':
    file.endsWith('.css')?'text/css; charset=utf-8':'text/javascript; charset=utf-8';
}
export function createStagingReadOnlyV101({authenticate,profileRead,assetFiles}){
  if(typeof authenticate!=='function'||typeof profileRead!=='function'||
    !assetFiles||typeof assetFiles!=='object'||Array.isArray(assetFiles))throw Error('V101_BAD_DEPENDENCIES');
  return async function stagingReadOnly(req,env,ctx){
    try{
      if(env?.PRIVATE_WORKER_V078!=='STAGING_AUTHENTICATED_READONLY'||
        env?.STAGING_ENABLED!=='D1_CANDIDATE'||
        env?.CONTRIBUTORS_STAGE_READONLY!=='EXPLICIT_STAGING_ONLY'||
        !goodOrigin(env?.STAGING_ORIGIN)||typeof env?.CONTRIBUTORS_DB?.prepare!=='function')return denied();
      if(!(req instanceof Request)||req.method!=='GET'||req.body!==null)return denied();
      const u=new URL(req.url);
      if(u.origin!==env.STAGING_ORIGIN||req.url!==u.origin+u.pathname)return denied();
      if(!ctx?.access||ctx.access.aud!==env.ACCESS_AUD||
        typeof ctx.access.getIdentity!=='function')return denied();
      const route=fileFor(u.pathname);
      if(!route||!Object.hasOwn(assetFiles,route.file)||
        typeof assetFiles[route.file]!=='string'||assetFiles[route.file].length===0||
        assetFiles[route.file].length>120000)return denied();
      const actor=await authenticate(ctx,env);
      if(!actor||!/^[a-f0-9]{64}$/.test(actor.subject??'')||
        !/^[a-f0-9]{64}$/.test(actor.email_tag??''))return denied();
      // Always use a fresh D1 profile: a revoked contributor with an open Safari tab
      // must fail on the next GET. No request-shared cache or client role headers.
      const p=await profileRead(ctx,env,actor);
      if(!validProfile(p,route.role))return denied();
      return new Response(assetFiles[route.file],{status:200,headers:{
        ...HEADERS,'Content-Type':mime(route.file)
      }});
    }catch{return denied()}
  };
}
// This is NOT an active Worker entrypoint. Real Access/D1 data have not been
// verified, and no configuration or deploy is part of the v1.01 checkpoint.
export const privateReadOnlyStagingV101=createStagingReadOnlyV101({
  authenticate:accessBinding,profileRead:profile,assetFiles:privateAssetFilesV096
});
export const V101_STATE=Object.freeze({
  version:'1.01',mode:'INERT_LAB',getOnly:true,allWritesDenied:true,
  requiresDirectAccess:true,requiresFreshD1Profile:true,
  stagingAuthorized:false,accessRuntimeVerified:false,safariVerified:false,
  deployAuthorized:false,pilotAllowed:false
});
