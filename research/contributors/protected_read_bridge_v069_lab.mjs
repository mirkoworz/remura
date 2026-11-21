// REMURA Contributors v0.69 LAB — 21/11/2026 12:25 CET.
// Pure, explicitly composed read-only Worker candidate. NO default fetch export, NO deploy.
import {inspectStagingRequestV068} from './staging_admission_v068_lab.mjs';
const DENIED=()=>new Response('{"error":"denied"}',{status:403,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store, max-age=0','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Cross-Origin-Resource-Policy':'same-origin','Content-Security-Policy':"default-src 'none'; frame-ancestors 'none'"}});
const HEX64=/^[a-f0-9]{64}$/;
const PATHS=new Set(['/api/amendment/reconcile','/api/amendment/mine','/owner/amendment/reconcile-queue']);
const CAP=4096;
const deny=()=>{throw Error('REMURA_V069_DENIED')};
function basic(req,env,ctx){
 if(env?.READ_BRIDGE_V069!=='OFFLINE_FIXTURE_ONLY'||env?.STAGING_ENABLED!=='D1_CANDIDATE'||env?.AMENDMENT_V061_ENABLED!=='OFFLINE_FIXTURE_ONLY'||env?.AMENDMENT_V062_ENABLED!=='OFFLINE_FIXTURE_ONLY'||env?.AMENDMENT_V064_ENABLED!=='OFFLINE_FIXTURE_ONLY'||env?.AMENDMENT_V065_ENABLED!=='OFFLINE_FIXTURE_ONLY'||env?.RECONCILIATION_V064_ENABLED!=='OFFLINE_FIXTURE_ONLY')deny();
 if(!ctx?.access||ctx.access.aud!==env.ACCESS_AUD||typeof ctx.access.getIdentity!=='function'||typeof req?.url!=='string'||req.method!=='POST'||!req.headers?.get||typeof env?.STAGING_ORIGIN!=='string')deny();
 let u;try{u=new URL(req.url)}catch{deny()}
 if(u.protocol!=='https:'||u.origin!==env.STAGING_ORIGIN||req.url!==u.origin+u.pathname||!PATHS.has(u.pathname))deny();
 if(req.headers.get('Origin')!==env.STAGING_ORIGIN||req.headers.get('Sec-Fetch-Site')!=='same-origin'||req.headers.get('X-Remura-CSRF')!=='1'||!/^application\/json(?:;\s*charset=utf-8)?$/i.test(req.headers.get('Content-Type')??''))deny();
 if(req.headers.has('Content-Encoding')&&req.headers.get('Content-Encoding')!=='identity')deny();
 for(const h of ['X-Remura-Actor','X-Remura-Role','X-Remura-Subject'])if(req.headers.has(h))deny();
 return u.pathname;
}
async function boundedBody(req){
 const length=req.headers.get('Content-Length');
 if(length!==null&&(!/^[0-9]{1,4}$/.test(length)||Number(length)<2||Number(length)>CAP))deny();
 if(!req.body||typeof req.body.getReader!=='function')deny();
 const reader=req.body.getReader();const buf=new Uint8Array(CAP);let total=0,done=false;
 try{for(;;){const p=await reader.read();if(p.done){done=true;break;}if(!(p.value instanceof Uint8Array)||total+p.value.length>CAP)deny();buf.set(p.value,total);total+=p.value.length;}
  if(length!==null&&Number(length)!==total)deny();
  const obj=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(buf.subarray(0,total)));
  if(obj===null||Array.isArray(obj)||typeof obj!=='object'||Object.getPrototypeOf(obj)!==Object.prototype)deny();
  return obj;
 }finally{if(!done)try{await reader.cancel()}catch{}reader.releaseLock();}
}
// Dependencies MUST be built server-side from the authenticated Access runtime and D1.
// Never supply them from a request, user input, or a browser bundle.
export function createProtectedReadBridgeV069({actor,profileRead,handle}){
 if([actor,profileRead,handle].some(f=>typeof f!=='function'))deny();
 return async function protectedReadBridgeV069(req,env,ctx){
  try{
   const path=basic(req,env,ctx);
   const payload=await boundedBody(req);
   const principal=await actor(ctx,env);
   if(!principal||!HEX64.test(principal.subject)||!HEX64.test(principal.email_tag))deny();
   const role=await profileRead(ctx,env,principal);
   if(!role||role.can_read!==true||!['OWNER','CONTRIBUTOR'].includes(role.role))deny();
   const verdict=inspectStagingRequestV068({url:req.url,method:req.method,headers:{origin:req.headers.get('Origin'),csrf:req.headers.get('X-Remura-CSRF'),contentType:'application/json'},body:payload},{role:role.role,trusted:true,active:true,audienceVerified:true,emailVerified:true,serviceToken:false},{origin:env.STAGING_ORIGIN,stage:'PRIVATE_STAGING',enabled:true});
   if(verdict.path!==path||verdict.kind!=='READ'||verdict.readOnly!==true)deny();
   if(typeof env.CONTRIBUTORS_RATE_LIMITER?.limit!=='function')deny();
   const limit=await env.CONTRIBUTORS_RATE_LIMITER.limit({key:principal.subject});if(limit?.success!==true)deny();
   // Canonicalization changes byte length: remove untrusted original Content-Length.
   const forwarded=new Headers(req.headers);forwarded.delete('Content-Length');
   const request=new Request(req.url,{method:'POST',headers:forwarded,body:JSON.stringify(payload)});
   const response=await handle(request,env,ctx);
   if(!(response instanceof Response)||response.redirected||!/^application\/json\b/i.test(response.headers.get('Content-Type')??'')||!/(?:^|,)\s*no-store\b/i.test(response.headers.get('Cache-Control')??''))deny();
   return response;
  }catch{return DENIED();}
 };
}
