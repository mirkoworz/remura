// REMURA Contributors v0.98 LAB — 23/11/2026, 13:28 CET (Europe/Rome).
// Inert, private-Worker candidate. No default fetch, deploy, live identities or D1 calls here.
// v0.96 regression defense: OWNER can_read without can_recover MUST NOT see owner assets
// or reach *any* protected POST route (including /api/profile and /owner/queue).
import {createPrivateWorkerRouterV096} from './private_worker_router_v096_lab.mjs';
import {accessBinding} from './access_binding_candidate.mjs';
import {profile} from './d1_access_candidate.mjs';
import {protectedReadCandidateV069} from './protected_read_composition_v069_lab.mjs';
import {protectedLevelApiV096,ownerLevelAuditHandlerV078} from './private_levels_composition_v096_lab.mjs';
import {privateAssetFilesV096} from './private_assets_v096_lab.mjs';

const OWNER=new Set(['/owner/queue','/owner/history','/owner/review',
  '/owner/amendment/reconcile-queue','/owner/new-level/pending',
  '/owner/new-level/history','/owner/new-level/audit-intent',
  '/owner/new-level/attest','/owner/new-level/integrity']);
const C_READ=new Set(['/api/catalog','/api/receipts','/api/level-attempt/status',
  '/api/amendment/reconcile','/api/amendment/mine']);
const C_WRITE=new Set(['/api/submit']);
const BOTH=new Set(['/api/profile','/api/intent']);
const ALL=new Set([...OWNER,...C_READ,...C_WRITE,...BOTH]);
const DENY_HEADERS=Object.freeze({
  'Content-Type':'application/json; charset=utf-8',
  'Cache-Control':'no-store, max-age=0','X-Content-Type-Options':'nosniff',
  'Referrer-Policy':'no-referrer','Cross-Origin-Resource-Policy':'same-origin',
  'X-Frame-Options':'DENY'
});
const deny=()=>new Response('{"error":"denied"}',{status:403,headers:DENY_HEADERS});
const fail=()=>{throw Error('REMURA_V098_PILOT_CLOSED')};
const roleHeaders=['X-Remura-Role','X-Remura-Subject','X-Remura-Actor','X-Remura-Admin'];
function originOf(raw){
  if(typeof raw!=='string'||raw.length>250)fail();
  let u;try{u=new URL(raw)}catch{fail()}
  if(u.protocol!=='https:'||u.origin!==raw||u.pathname!=='/'||u.search||
    u.hash||u.username||u.password)fail();
  return raw;
}
function guardEnvelope(req,env,ctx){
  if(!(req instanceof Request)||req.method!=='POST'||
    env?.PRIVATE_WORKER_V078!=='OFFLINE_FIXTURE_ONLY'||
    env?.STAGING_ENABLED!=='D1_CANDIDATE')fail();
  const origin=originOf(env.STAGING_ORIGIN);
  if(!ctx?.access||ctx.access.aud!==env.ACCESS_AUD||
    typeof ctx.access.getIdentity!=='function')fail();
  const u=new URL(req.url);
  if(u.origin!==origin||req.url!==origin+u.pathname||!ALL.has(u.pathname))fail();
  if(req.headers.get('Origin')!==origin||
    req.headers.get('Sec-Fetch-Site')!=='same-origin'||
    req.headers.get('X-Remura-CSRF')!=='1'||
    !/^application\/json(?:;\s*charset=utf-8)?$/i.test(req.headers.get('Content-Type')??'')||
    (req.headers.has('Content-Encoding')&&req.headers.get('Content-Encoding')!=='identity')||
    roleHeaders.some(k=>req.headers.has(k)))fail();
  const n=req.headers.get('Content-Length');
  if(n!==null&&(!/^[1-9][0-9]{0,3}$/.test(n)||Number(n)<2||Number(n)>4096))fail();
  if(req.body===null)fail();
  return {path:u.pathname,declared:n};
}
async function validBoundedObject(req,declared){
  const reader=req.clone().body.getReader(),buf=new Uint8Array(4096);
  let n=0,done=false;
  try{
    for(;;){
      const part=await reader.read();
      if(part.done){done=true;break}
      if(!(part.value instanceof Uint8Array)||part.value.length+n>4096)fail();
      buf.set(part.value,n);n+=part.value.length;
    }
    if(n<2||(declared!==null&&Number(declared)!==n))fail();
    const parsed=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(buf.subarray(0,n)));
    if(!parsed||Array.isArray(parsed)||Object.getPrototypeOf(parsed)!==Object.prototype||
      Object.keys(parsed).length>40||
      ['__proto__','constructor','prototype'].some(k=>Object.hasOwn(parsed,k)))fail();
  }catch{fail()}finally{
    if(!done){try{const p=reader.cancel();if(p?.catch)void p.catch(()=>{})}catch{}}
    try{reader.releaseLock()}catch{}
  }
}
function allowedPost(path,p){
  if(!p||!['OWNER','CONTRIBUTOR'].includes(p.role)||p.can_read!==true||
    typeof p.can_write!=='boolean'||typeof p.can_recover!=='boolean')return false;
  if(p.role==='OWNER'&&p.can_recover!==true)return false;
  if(p.role==='CONTRIBUTOR'&&p.can_recover!==false)return false;
  if(OWNER.has(path))return p.role==='OWNER'&&p.can_recover===true;
  if(C_READ.has(path))return p.role==='CONTRIBUTOR'&&
    (path!=='/api/catalog'||p.can_write===true);
  if(C_WRITE.has(path))return p.role==='CONTRIBUTOR'&&p.can_write===true;
  if(BOTH.has(path))return path==='/api/profile'||
    (p.role==='OWNER'?p.can_recover:p.can_write);
  return false;
}

// The existing v0.96 router performs the GET authentication and D1 role lookup;
// this strict read enforces the v0.92 OWNER recovery revocation within that SAME lookup.
// No global or cross-request cache: revocation must be checked fresh for each request.
export function createPilotOwnerGuardV098({
  authenticate,profileRead,protectedRead,levelApi,ownerAudit,assetFiles
}){
  if([authenticate,profileRead,protectedRead,levelApi,ownerAudit].some(f=>typeof f!=='function'))fail();
  const strictProfile=async(ctx,env,actor)=>{
    const p=await profileRead(ctx,env,actor);
    if(p?.role==='OWNER'&&p.can_recover!==true)fail();
    return p;
  };
  const base=createPrivateWorkerRouterV096({
    authenticate,profileRead:strictProfile,protectedRead,levelApi,ownerAudit,assetFiles
  });
  return async function pilotGuardV098(req,env,ctx){
    if(!(req instanceof Request)||req.method!=='POST')return base(req,env,ctx);
    try{
      const {path,declared}=guardEnvelope(req,env,ctx);
      await validBoundedObject(req,declared);
      const actor=await authenticate(ctx,env);
      if(!actor||!/^[a-f0-9]{64}$/.test(actor.subject??'')||
        !/^[a-f0-9]{64}$/.test(actor.email_tag??''))fail();
      if(!allowedPost(path,await strictProfile(ctx,env,actor)))fail();
      // The existing downstream v0.96 endpoints still own D1 identity/ownership,
      // durable journal, HMAC intent, rate limiting, audit and no-retry semantics.
      return await base(req,env,ctx);
    }catch{return deny();}
  };
}

// Actual existing LAB dependencies, NOT an active Worker export.
export const privateWorkerPilotV098=createPilotOwnerGuardV098({
  authenticate:accessBinding,profileRead:profile,
  protectedRead:protectedReadCandidateV069,levelApi:protectedLevelApiV096,
  ownerAudit:ownerLevelAuditHandlerV078,assetFiles:privateAssetFilesV096
});
export const V098_PILOT=Object.freeze({
  version:'0.98',mode:'INERT_LAB',ownerGetRecoveryRequired:true,
  ownerAllPostRecoveryRequired:true,contributorCrossRoleDenied:true,
  postExtraPrimaryProfileReads:1,realD1UsageMeasured:false,
  accessSeatsVerified:false,billingVerified:false,safariAuthenticated:false,
  deployAuthorized:false,realPilotAllowed:false
});
