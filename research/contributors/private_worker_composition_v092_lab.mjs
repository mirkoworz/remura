// REMURA Contributors v0.92 LAB — 21/11/2026, Europe/Rome.
// Real dependency composition of prior LAB candidates; inert without a Worker entrypoint.
// No default fetch export, deploy config, secrets, enrollment or provider requests.
import {accessBinding} from './access_binding_candidate.mjs';
import {profile} from './d1_access_candidate.mjs';
import {protectedReadCandidateV069} from './protected_read_composition_v069_lab.mjs';
import {protectedLevelApiV078,ownerLevelAuditHandlerV078} from './private_levels_composition_v078_lab.mjs';
import {privateAssetFilesV078} from './private_assets_v078_lab.mjs';
import {createPostGuardedPrivateWorkerV090} from './private_post_guard_v090_lab.mjs';

// v0.90's central POST guard was previously exercised with mock delegates only.
// This candidate deliberately wires it to the actual pre-existing LAB handlers.
const guarded=createPostGuardedPrivateWorkerV090({
 authenticate:accessBinding,profileRead:profile,
 protectedRead:protectedReadCandidateV069,
 levelApi:protectedLevelApiV078,
 ownerAudit:ownerLevelAuditHandlerV078,
 assetFiles:privateAssetFilesV078
});

const HEAD=Object.freeze({'Content-Type':'application/json; charset=utf-8',
 'Cache-Control':'no-store, max-age=0','X-Content-Type-Options':'nosniff',
 'Referrer-Policy':'no-referrer','X-Frame-Options':'DENY',
 'Content-Security-Policy':"default-src 'none'; frame-ancestors 'none'; base-uri 'none'"});
const denied=()=>new Response('{"error":"denied"}',{status:403,headers:HEAD});
const bad=()=>{throw Error('REMURA_V092_GET_OWNER_DENIED')};

// v0.78 already checked GET role/read. ADDITIONAL Owner-only GET requirement:
// a revoked administrative permission must not expose OWNER HTML or JS, even if
// general read permission remains true. A fresh D1 primary role read is required;
// real Worker/Access execution and its quota cost remain UNTESTED.
export async function privateWorkerCandidateV092(req,env,ctx){
 if(!(req instanceof Request)||req.method!=='GET')return guarded(req,env,ctx);
 let url;
 try{url=new URL(req.url)}catch{return denied()}
 if(!url.pathname.startsWith('/owner/'))return guarded(req,env,ctx);
 try{
  if(env?.PRIVATE_WORKER_V078!=='OFFLINE_FIXTURE_ONLY'||
     env.STAGING_ENABLED!=='D1_CANDIDATE'||
     typeof env.STAGING_ORIGIN!=='string'||env.STAGING_ORIGIN.length>250)bad();
  const origin=new URL(env.STAGING_ORIGIN);
  if(origin.protocol!=='https:'||origin.origin!==env.STAGING_ORIGIN||
     url.origin!==origin.origin||req.url!==origin.origin+url.pathname||
     req.body!==null)bad();
  const actor=await accessBinding(ctx,env);
  const p=await profile(ctx,env,actor);
  if(!p||p.role!=='OWNER'||p.can_read!==true||p.can_recover!==true)bad();
 }catch{return denied()}
 return guarded(req,env,ctx);
}
export const V092_COMPOSITION=Object.freeze({
 version:'0.92',type:'INERT_LAB_CANDIDATE',ownerGetRecoveryGate:true,
 postV090RealDelegatesWired:true,workflowsMayDeploy:false,
 liveAccessJwtVerified:false,realD1Tested:false,realSafariTested:false,
 freeQuotaAttested:false,pilotAllowed:false
});
