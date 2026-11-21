// REMURA Contributors v0.78 LAB — 21/11/2026 16:56 CET.
// No Worker entrypoint. OWNER evidence actions are append-only and do not unlock levels.
import {ownerIntegritySnapshotV078} from './owner_level_integrity_v078_lab.mjs';
import {verifyOwnerAuditAccessV077,ownerPendingLevelsV077,ownerLevelAuditHistoryV077,
 issueOwnerLevelAuditIntentV077,appendOwnerLevelAuditV077,validateOwnerLevelAuditV077} from './owner_level_audit_v077_lab.mjs';
const DENY=()=>new Response('{"error":"denied"}',{status:403,headers:HEAD});
const UNKNOWN=()=>new Response('{"error":"not_confirmed","retry":false}',{status:409,headers:HEAD});
const HEAD=Object.freeze({'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store, max-age=0',
 'X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer',
 'Cross-Origin-Resource-Policy':'same-origin','X-Frame-Options':'DENY'});
const PENDING='/owner/new-level/pending',HISTORY='/owner/new-level/history',
 INTENT='/owner/new-level/audit-intent',ATTEST='/owner/new-level/attest';
const INTEGRITY='/owner/new-level/integrity';
const ACTIONS=new Set([PENDING,HISTORY,INTENT,ATTEST,INTEGRITY]);
const bad=()=>{throw Error('REMURA_V077_AUDIT_HTTP_DENIED')};
const exact=(o,ks)=>o!==null&&typeof o==='object'&&!Array.isArray(o)&&Object.getPrototypeOf(o)===Object.prototype&&Object.keys(o).length===ks.length&&ks.every(k=>Object.hasOwn(o,k));
function preflight(req,env,ctx){
 if(env?.OWNER_LEVEL_AUDIT_V077!=='OFFLINE_FIXTURE_ONLY'||env.STAGING_ENABLED!=='D1_CANDIDATE'||
    env.HTTP_CANDIDATE_ENABLED!=='LAB_ONLY'||!ctx?.access||ctx.access.aud!==env.ACCESS_AUD||
    typeof ctx.access.getIdentity!=='function'||!(req instanceof Request)||req.method!=='POST')bad();
 let u,origin;try{u=new URL(req.url);origin=new URL(env.STAGING_ORIGIN)}catch{bad()}
 if(origin.protocol!=='https:'||origin.origin!==env.STAGING_ORIGIN||origin.pathname!=='/'||
    origin.username||origin.password||u.origin!==origin.origin||req.url!==origin.origin+u.pathname||
    !ACTIONS.has(u.pathname))bad();
 if(req.headers.get('Origin')!==origin.origin||req.headers.get('Sec-Fetch-Site')!=='same-origin'||
    req.headers.get('X-Remura-CSRF')!=='1'||
    !/^application\/json(?:;\s*charset=utf-8)?$/i.test(req.headers.get('Content-Type')??''))bad();
 if(req.headers.has('Content-Encoding')&&req.headers.get('Content-Encoding')!=='identity')bad();
 for(const name of ['X-Remura-Role','X-Remura-Subject','X-Remura-Actor'])if(req.headers.has(name))bad();
 return u.pathname;
}
async function body(req){
 const size=req.headers.get('Content-Length');
 if(size!==null&&(!/^\d{1,4}$/.test(size)||Number(size)<2||Number(size)>4096))bad();
 if(!req.body)bad();
 const reader=req.clone().body.getReader(),buf=new Uint8Array(4096);let done=false,n=0;
 try{
  for(;;){const a=await reader.read();if(a.done){done=true;break}
   if(!(a.value instanceof Uint8Array)||n+a.value.byteLength>4096)bad();
   buf.set(a.value,n);n+=a.value.byteLength;
  }
  if(size!==null&&n!==Number(size))bad();
  const value=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(buf.subarray(0,n)));
  if(value===null||Object.getPrototypeOf(value)!==Object.prototype)bad();
  return value;
 }finally{
  if(!done){try{const c=reader.cancel();if(c&&typeof c.catch==='function')void c.catch(()=>{});}catch{}}
  reader.releaseLock();
 }
}
const respond=(body,status=200)=>new Response(JSON.stringify({data:body}),{status,headers:HEAD});
const utcNow=()=>new Date().toISOString().slice(0,19)+'Z';
export function createOwnerLevelAuditHttpV078({authenticate,profileRead}){
 if([authenticate,profileRead].some(x=>typeof x!=='function'))bad();
 return async function ownerLevelAuditHttpV078(req,env,ctx){
  let route;
  try{route=preflight(req,env,ctx)}catch{return DENY()}
  try{
   const p=await body(req);
   const actor=await authenticate(ctx,env);
   const profile=await profileRead(ctx,env,actor);
   if(!profile||profile.role!=='OWNER'||profile.can_read!==true||profile.can_recover!==true)bad();
   if(typeof env.CONTRIBUTORS_RATE_LIMITER?.limit!=='function')bad();
   const limiter=await env.CONTRIBUTORS_RATE_LIMITER.limit({key:actor.subject});
   if(limiter?.success!==true)bad();
   await verifyOwnerAuditAccessV077(env,actor);
   if(route===INTEGRITY){
    if(!exact(p,['after'])||!Number.isSafeInteger(p.after)||p.after<0||p.after>1_000_000)bad();
    return respond(await ownerIntegritySnapshotV078(env,actor,p.after));
   }
   if(route===PENDING||route===HISTORY){
    if(!exact(p,['after'])||!Number.isSafeInteger(p.after)||p.after<0||p.after>1_000_000)bad();
    return respond(route===PENDING?await ownerPendingLevelsV077(env,actor,p.after):await ownerLevelAuditHistoryV077(env,actor,p.after));
   }
   if(route===INTENT){
    if(!exact(p,['body']))bad();
    return respond(await issueOwnerLevelAuditIntentV077(env,actor,validateOwnerLevelAuditV077(p.body)));
   }
   if(!exact(p,['subject','request_id','classification','receipt_id','reason']))bad();
   const x=validateOwnerLevelAuditV077(p);
   const token=req.headers.get('X-Remura-Intent');
   return respond(await appendOwnerLevelAuditV077(env,actor,x,token,utcNow()));
  }catch{
   // Mutation outcome can be ambiguous; never retry the HMAC token.
   return route===ATTEST?UNKNOWN():DENY();
  }
 };
}
export const REMURA_V078_OWNER_ROUTES=Object.freeze([PENDING,HISTORY,INTENT,ATTEST,INTEGRITY]);
