// REMURA Contributors v0.74 LAB — 21/11/2026 15:36 CET.
// Explicitly OFFLINE-only role gate for ORIGINAL /api/submit, /owner/review and read APIs.
// No default Worker export, no direct D1 binding, no deployable production switch.
const DENY=()=>new Response('{"error":"denied"}',{status:403,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store, max-age=0','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Cross-Origin-Resource-Policy':'same-origin'}});
const BAD=()=>{throw Error('REMURA_V074_LEVEL_GATE_DENIED')};
const ROUTES=Object.freeze({
 '/api/profile':{role:'BOTH',type:'READ'},
 '/api/catalog':{role:'CONTRIBUTOR',type:'READ'},
 '/api/receipts':{role:'CONTRIBUTOR',type:'READ'},
 '/owner/queue':{role:'OWNER',type:'READ'},
 '/owner/history':{role:'OWNER',type:'READ'},
 '/api/intent':{role:'BOTH',type:'INTENT'},
 '/api/submit':{role:'CONTRIBUTOR',type:'WRITE'},
 '/owner/review':{role:'OWNER',type:'WRITE'}
});
const HASH=/^[a-f0-9]{64}$/;
const SAFE_ORIGIN=raw=>{let u;try{u=new URL(raw)}catch{BAD()}if(typeof raw!=='string'||u.protocol!=='https:'||u.origin!==raw||u.pathname!=='/'||u.username||u.password||u.search||u.hash)BAD();return u.origin;};
const EXACT=(v,ks)=>v!==null&&typeof v==='object'&&!Array.isArray(v)&&Object.getPrototypeOf(v)===Object.prototype&&Object.keys(v).length===ks.length&&ks.every(k=>Object.hasOwn(v,k));
async function targetFromIntent(req){
 const h=req.headers.get('Content-Length');if(h!==null&&(!/^[0-9]{1,4}$/.test(h)||Number(h)>4096||Number(h)<2))BAD();
 if(!req.body)BAD();
 const r=req.clone().body.getReader(),buf=new Uint8Array(4096);let n=0,done=false;
 try{for(;;){const p=await r.read();if(p.done){done=true;break}if(!(p.value instanceof Uint8Array)||n+p.value.byteLength>4096)BAD();buf.set(p.value,n);n+=p.value.byteLength}
 if(h!==null&&Number(h)!==n)BAD();
 const b=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(buf.subarray(0,n)));
 if(!EXACT(b,['path','body'])||typeof b.path!=='string'||!EXACT(b.body,b.path==='/api/submit'?['request_id','market','provider','ticker','product','contract','period','kind','price','anchor_utc','observed_utc','note']:['id','action','reason']))BAD();
 if(!['/api/submit','/owner/review'].includes(b.path))BAD();
 return b.path;
 }finally{if(!done)try{await r.cancel()}catch{}r.releaseLock();}
}
export function createLevelApiGateV074({authenticate,profileRead,handler}){
 if([authenticate,profileRead,handler].some(x=>typeof x!=='function'))BAD();
 return async function levelApiGateV074(req,env,ctx){
  try{
   if(env?.LEVEL_HTTP_V074!=='OFFLINE_FIXTURE_ONLY'||env?.HTTP_CANDIDATE_ENABLED!=='LAB_ONLY'||env?.STAGING_ENABLED!=='D1_CANDIDATE')BAD();
   const origin=SAFE_ORIGIN(env.STAGING_ORIGIN);
   if(!ctx?.access||ctx.access.aud!==env.ACCESS_AUD||typeof ctx.access.getIdentity!=='function'||!(req instanceof Request)||req.method!=='POST')BAD();
   const u=new URL(req.url);if(u.origin!==origin||req.url!==origin+u.pathname)BAD();
   const route=ROUTES[u.pathname];if(!route)BAD();
   if(req.headers.get('Origin')!==origin||req.headers.get('Sec-Fetch-Site')!=='same-origin'||req.headers.get('X-Remura-CSRF')!=='1'||!/^application\/json(?:;\s*charset=utf-8)?$/i.test(req.headers.get('Content-Type')??''))BAD();
   if(req.headers.has('Content-Encoding')&&req.headers.get('Content-Encoding')!=='identity')BAD();
   for(const h of ['X-Remura-Role','X-Remura-Actor','X-Remura-Subject'])if(req.headers.has(h))BAD();
   const effective=route.type==='INTENT'?ROUTES[await targetFromIntent(req)]:route;
   const actor=await authenticate(ctx,env);
   if(!actor||!HASH.test(actor.subject)||!HASH.test(actor.email_tag))BAD();
   const p=await profileRead(ctx,env,actor);
   if(!p||!['OWNER','CONTRIBUTOR'].includes(p.role)||!['boolean'].includes(typeof p.can_read)||typeof p.can_write!=='boolean'||typeof p.can_recover!=='boolean')BAD();
   if((effective.role!=='BOTH'&&p.role!==effective.role)||(effective.type==='READ'&&!p.can_read)||(effective.type==='WRITE'&&!p.can_write && !(p.role==='OWNER'&&p.can_recover)))BAD();
   if(route.type==='INTENT'&&effective.type!=='WRITE')BAD();
   // Original candidateRequest re-validates live Access identity, D1 roles, generation,
   // rate limit and burns one-use HMAC intent BEFORE any write.
   const r=await handler(req,env,ctx);
   if(!(r instanceof Response)||r.redirected===true||!/^application\/json\b/i.test(r.headers.get('Content-Type')??'')||!/\bno-store\b/i.test(r.headers.get('Cache-Control')??''))BAD();
   return r;
  }catch{return DENY();}
 };
}
export const REMURA_V074_LEVEL_ROUTES=ROUTES;
