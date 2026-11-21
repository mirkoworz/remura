// REMURA Contributors v0.76 LAB — 21/11/2026 15:57 CET.
// Bridges original HMAC intent + original submit into a conservative durable-attempt
// reservation. On any uncertainty, NO automatic retry and NO release of the slot.
// NO default fetch, no real Worker binding or Cloudflare environment.
import {normalizeNewLevelV076,newLevelFingerprintV076,claimNewLevelV076,confirmNewLevelV076,inspectNewLevelV076} from './level_attempt_journal_v076_lab.mjs';
const RESP_HEADERS=Object.freeze({'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store, max-age=0','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Cross-Origin-Resource-Policy':'same-origin'});
const deny=()=>new Response('{"error":"denied"}',{status:403,headers:RESP_HEADERS});
const uncertain=()=>new Response('{"error":"not_confirmed","retry":false}',{status:409,headers:RESP_HEADERS});
const bad=()=>{throw Error('REMURA_V076_CLOSED')};
const exact=(v,ks)=>v!==null&&typeof v==='object'&&!Array.isArray(v)&&Object.getPrototypeOf(v)===Object.prototype&&Object.keys(v).length===ks.length&&ks.every(k=>Object.hasOwn(v,k));
const stamp=()=>new Date().toISOString().slice(0,19)+'Z';
function preflight(req,env,ctx){
 if(env?.LEVEL_JOURNAL_V076!=='OFFLINE_FIXTURE_ONLY'||env.STAGING_ENABLED!=='D1_CANDIDATE'||env.HTTP_CANDIDATE_ENABLED!=='LAB_ONLY'||typeof env.STAGING_ORIGIN!=='string')bad();
 let url,origin;try{url=new URL(req.url);origin=new URL(env.STAGING_ORIGIN)}catch{bad()}
 if(!(req instanceof Request)||req.method!=='POST'||origin.protocol!=='https:'||origin.origin!==env.STAGING_ORIGIN||origin.pathname!=='/'||origin.username||origin.password||url.origin!==origin.origin||req.url!==origin.origin+url.pathname)bad();
 if(!ctx?.access||ctx.access.aud!==env.ACCESS_AUD||typeof ctx.access.getIdentity!=='function')bad();
 if(req.headers.get('Origin')!==origin.origin||req.headers.get('Sec-Fetch-Site')!=='same-origin'||req.headers.get('X-Remura-CSRF')!=='1'||!/^application\/json(?:;\s*charset=utf-8)?$/i.test(req.headers.get('Content-Type')??''))bad();
 if(req.headers.has('Content-Encoding')&&req.headers.get('Content-Encoding')!=='identity')bad();
 for(const name of ['X-Remura-Actor','X-Remura-Role','X-Remura-Subject'])if(req.headers.has(name))bad();
 return url.pathname;
}
async function boundedBody(req){
 const size=req.headers.get('Content-Length');if(size!==null&&(!/^[0-9]{1,4}$/.test(size)||Number(size)<2||Number(size)>4096))bad();
 if(!req.body)bad();
 const clone=req.clone(),reader=clone.body.getReader(),buffer=new Uint8Array(4096);let done=false,n=0;
 try{
  while(true){const part=await reader.read();if(part.done){done=true;break}
   if(!(part.value instanceof Uint8Array)||n+part.value.length>4096)bad();
   buffer.set(part.value,n);n+=part.value.length;
  }
  if(size!==null&&Number(size)!==n)bad();
  const data=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(buffer.subarray(0,n)));
  if(!data||Object.getPrototypeOf(data)!==Object.prototype||Array.isArray(data))bad();
  return data;
 }finally{
  if(!done){try{const pending=reader.cancel();if(pending&&typeof pending.catch==='function')void pending.catch(()=>{});}catch{}}
  reader.releaseLock();
 }
}
async function readProfile(ctx,env,authenticate,profileRead,mode){
 const actor=await authenticate(ctx,env),p=await profileRead(ctx,env,actor);
 if(!p||p.role!=='CONTRIBUTOR'||p[mode]!=='boolean'||p[mode]!==true)bad();
 return actor;
}
async function applyLimit(env,subject){
 const limiter=env.CONTRIBUTORS_RATE_LIMITER;
 if(!limiter||typeof limiter.limit!=='function')bad();
 const x=await limiter.limit({key:subject});
 if(x?.success!==true)bad();
}
export function createDurableLevelApiV076({authenticate,profileRead,originalHandler}){
 if([authenticate,profileRead,originalHandler].some(x=>typeof x!=='function'))bad();
 return async function durableLevelApiV076(req,env,ctx){
  let path;
  try{path=preflight(req,env,ctx)}catch{return deny()}
  if(path==='/api/level-attempt/status'){
   try{
    if(!exact(await boundedBody(req),[]))bad();
    const actor=await readProfile(ctx,env,authenticate,profileRead,'can_read');
    await applyLimit(env,actor.subject);
    return new Response(JSON.stringify({data:await inspectNewLevelV076(env,actor)}),{status:200,headers:RESP_HEADERS});
   }catch{return deny()}
  }
  if(path!=='/api/submit'){
   try{return await originalHandler(req,env,ctx)}catch{return deny()}
  }
  try{
   const raw=await boundedBody(req),now=stamp(),level=normalizeNewLevelV076(raw,now);
   const actor=await readProfile(ctx,env,authenticate,profileRead,'can_write');
   await applyLimit(env,actor.subject); // Before acquiring the durable lock.
   const fingerprint=await newLevelFingerprintV076(level);
   // Cross-tab, cross-device and restart barrier: DB UNIQUE(subject WHERE RESERVED).
   // NO automatic retries if this INSERT is ambiguous, fails or conflicts.
   await claimNewLevelV076(env,actor,level,fingerprint,now);
   const r=await originalHandler(req,env,ctx); // original HMAC burn then D1 INSERT
   if(!(r instanceof Response)||r.status!==200||r.redirected||!/^application\/json\b/i.test(r.headers.get('Content-Type')??'')||!/\bno-store\b/i.test(r.headers.get('Cache-Control')??''))bad();
   const body=await r.clone().json();
   if(!exact(body,['data'])||!exact(body.data,['id','status','duplicate'])||!Number.isSafeInteger(body.data.id)||body.data.id<1||body.data.status!=='UNREVIEWED'||body.data.duplicate!==false)bad();
   // The same persisted receipt must match every original-level field in SQL.
   await confirmNewLevelV076(env,actor,level,fingerprint,body.data.id,stamp());
   return r;
  }catch{
   // A reservation or actual D1 insert might already exist. No second write or
   // token replay. On reload: use /api/level-attempt/status; OWNER reviews ambiguity.
   return uncertain();
  }
 };
}
