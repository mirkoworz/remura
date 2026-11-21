// REMURA Contributors v0.90 LAB — 21/11/2026 Europe/Rome
// Additional server-side POST gate around frozen v0.78 router; NOT deployed.
// Deliberately no Worker default export. All downstream authorizations remain mandatory.
import {createPrivateWorkerRouterV078} from './private_worker_router_v078_lab.mjs';
const OWNER=new Set(['/owner/queue','/owner/history','/owner/review',
 '/owner/amendment/reconcile-queue','/owner/new-level/pending','/owner/new-level/history',
 '/owner/new-level/audit-intent','/owner/new-level/attest','/owner/new-level/integrity']);
const C_READ=new Set(['/api/catalog','/api/receipts','/api/level-attempt/status',
 '/api/amendment/reconcile','/api/amendment/mine']);
const C_WRITE=new Set(['/api/submit']);
const BOTH=new Set(['/api/profile','/api/intent']);
const ALL=new Set([...OWNER,...C_READ,...C_WRITE,...BOTH]);
const FORGED=['X-Remura-Role','X-Remura-Subject','X-Remura-Actor','X-Remura-Admin'];
const MAX_BODY=4096, HASH=/^[a-f0-9]{64}$/;
const HEAD=Object.freeze({'Content-Type':'application/json; charset=utf-8',
 'Cache-Control':'no-store, max-age=0','X-Content-Type-Options':'nosniff',
 'Referrer-Policy':'no-referrer','Cross-Origin-Resource-Policy':'same-origin',
 'X-Frame-Options':'DENY',
 'Content-Security-Policy':"default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'; object-src 'none'"});
const deny=()=>new Response('{"error":"denied"}',{status:403,headers:HEAD});
const fail=()=>{throw Error('REMURA_V090_POST_DENIED')};
function expectedOrigin(raw){
 if(typeof raw!=='string'||raw.length>250)fail();
 let u;try{u=new URL(raw)}catch{fail()}
 if(u.protocol!=='https:'||u.origin!==raw||u.username||u.password||
    u.pathname!=='/'||u.search||u.hash)fail();
 return raw;
}
function envelope(req,env,ctx){
 if(!(req instanceof Request)||req.method!=='POST'||
    env?.PRIVATE_WORKER_V078!=='OFFLINE_FIXTURE_ONLY'||
    env?.STAGING_ENABLED!=='D1_CANDIDATE')fail();
 const origin=expectedOrigin(env.STAGING_ORIGIN);
 if(!ctx?.access||ctx.access.aud!==env.ACCESS_AUD||
    typeof ctx.access.getIdentity!=='function')fail();
 let url;try{url=new URL(req.url)}catch{fail()}
 if(url.origin!==origin||req.url!==origin+url.pathname||!ALL.has(url.pathname))fail();
 if(req.headers.get('Origin')!==origin||
    req.headers.get('Sec-Fetch-Site')!=='same-origin'||
    req.headers.get('X-Remura-CSRF')!=='1')fail();
 if(!/^application\/json(?:;\s*charset=utf-8)?$/i.test(req.headers.get('Content-Type')??''))fail();
 const encoding=req.headers.get('Content-Encoding');
 if(encoding!==null&&encoding!=='identity')fail();
 if(FORGED.some(h=>req.headers.has(h)))fail();
 const n=req.headers.get('Content-Length');
 if(n!==null&&(!/^[1-9][0-9]{0,3}$/.test(n)||Number(n)<2||Number(n)>MAX_BODY))fail();
 if(req.body===null)fail();
 return {path:url.pathname,declared:n};
}
async function boundedJSON(req,declared){
 const cloned=req.clone(),stream=cloned.body;
 if(!stream)fail();
 const reader=stream.getReader(),buffer=new Uint8Array(MAX_BODY);
 let count=0,done=false;
 try{
  for(;;){
   const chunk=await reader.read();
   if(chunk.done){done=true;break}
   if(!(chunk.value instanceof Uint8Array)||count+chunk.value.byteLength>MAX_BODY)fail();
   buffer.set(chunk.value,count);count+=chunk.value.byteLength;
  }
  if(count<2||(declared!==null&&Number(declared)!==count))fail();
  const text=new TextDecoder('utf-8',{fatal:true}).decode(buffer.subarray(0,count));
  const data=JSON.parse(text);
  if(data===null||Array.isArray(data)||Object.getPrototypeOf(data)!==Object.prototype||
     Object.keys(data).length>40)fail();
  if(['__proto__','constructor','prototype'].some(k=>Object.hasOwn(data,k)))fail();
 }catch{fail()}finally{
  if(!done){try{const cancel=reader.cancel();if(cancel?.catch)void cancel.catch(()=>{})}catch{}}
  try{reader.releaseLock()}catch{}
 }
}
function allowed(path,p){
 if(!p||!['OWNER','CONTRIBUTOR'].includes(p.role)||p.can_read!==true||
    typeof p.can_write!=='boolean'||typeof p.can_recover!=='boolean')return false;
 if(p.role==='CONTRIBUTOR'&&p.can_recover)return false;
 if(path==='/api/profile')return true;
 if(OWNER.has(path))return p.role==='OWNER'&&p.can_recover===true;
 if(C_READ.has(path))return p.role==='CONTRIBUTOR'&&
   (path!=='/api/catalog'||p.can_write===true);
 if(C_WRITE.has(path))return p.role==='CONTRIBUTOR'&&p.can_write===true;
 if(path==='/api/intent')return p.role==='OWNER'?p.can_recover:p.can_write;
 return false;
}
export function createPostGuardedPrivateWorkerV090({authenticate,profileRead,protectedRead,levelApi,ownerAudit,assetFiles}){
 if([authenticate,profileRead,protectedRead,levelApi,ownerAudit].some(fn=>typeof fn!=='function'))fail();
 const base=createPrivateWorkerRouterV078({authenticate,profileRead,protectedRead,levelApi,ownerAudit,assetFiles});
 return async function guardedWorker(req,env,ctx){
  // Static GET handling remains owned by exact v0.78 source (no duplicated logic).
  if(!(req instanceof Request)||req.method!=='POST')return base(req,env,ctx);
  try{
   const {path,declared}=envelope(req,env,ctx);
   await boundedJSON(req,declared);
   const actor=await authenticate(ctx,env);
   if(!actor||!HASH.test(actor.subject??'')||!HASH.test(actor.email_tag??''))fail();
   const profile=await profileRead(ctx,env,actor);
   if(!allowed(path,profile))fail();
   // Route-specific D1 ownership, intent, rate limiting, RESERVED and owner audit
   // are STILL checked by delegated handlers. This gate cannot replace them.
   return await base(req,env,ctx);
  }catch{return deny();}
 };
}
export const V090_CONTRACT=Object.freeze({version:'0.90',maxPostBody:MAX_BODY,
 defaultDeployment:'NO_GO_LAB',roleClaimFromRequest:false,
 ownershipAttestedByWrapper:false});
