// REMURA Contributors v0.31 LAB — 16/11/2026 09:08 CET
// Offline request contract; NOT a Worker entrypoint. No wrangler binding or deployment.
import {accessBinding} from "./access_binding_candidate.mjs";
import {verifyGeneration,issueIntent,consumeIntent} from "./operation_intent_candidate.mjs";
import {submit,receipts,queue,history,review,profile,catalog} from "./d1_access_candidate.mjs";
const CAP=4096;
const routes=Object.freeze({
 "/api/profile":{fields:[],fn:(c,e,p,b)=>profile(c,e,b)},
 "/api/catalog":{fields:[],fn:(c,e,p,b)=>catalog(c,e,b)},
 "/api/intent":{fields:["path","body"],issue:true},
 "/api/submit":{fields:null,fn:(c,e,p,b)=>submit(c,e,p,b),mutation:true},
 "/api/receipts":{fields:["after"],fn:(c,e,p,b)=>receipts(c,e,p.after,b)},
 "/owner/queue":{fields:["after"],fn:(c,e,p,b)=>queue(c,e,p.after,b)},
 "/owner/history":{fields:["id"],fn:(c,e,p,b)=>history(c,e,p.id,b)},
 "/owner/review":{fields:["id","action","reason"],fn:(c,e,p,b)=>review(c,e,p.id,p.action,p.reason,b),mutation:true}
});
const headers=Object.freeze({
 "Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store, max-age=0",
 "X-Content-Type-Options":"nosniff","Referrer-Policy":"no-referrer",
 "Content-Security-Policy":"default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
 "X-Frame-Options":"DENY","Cross-Origin-Resource-Policy":"same-origin"
});
const reply=(status,body)=>new Response(JSON.stringify(body),{status,headers});
const closed=()=>reply(403,{error:"denied"});
function select(req,env){
 if(env?.HTTP_CANDIDATE_ENABLED!=="LAB_ONLY"||env.STAGING_ENABLED!=="D1_CANDIDATE"||typeof env.STAGING_ORIGIN!=="string")return null;
 const o=new URL(env.STAGING_ORIGIN),u=new URL(req.url);
 if(o.protocol!=="https:"||o.origin!==env.STAGING_ORIGIN||o.username||o.password||u.origin!==o.origin||
    req.url!==o.origin+u.pathname||req.method!=="POST"||!Object.hasOwn(routes,u.pathname))return null;
 const h=req.headers;
 // Require browser-controlled same-origin evidence AND a non-simple custom request header.
 // No CORS, no preflight, no app session cookie. Access is independently validated every call.
 if(h.get("Origin")!==o.origin||h.get("Sec-Fetch-Site")!=="same-origin"||h.get("X-Remura-CSRF")!=="1"||
    !/^application\/json(?:;\s*charset=utf-8)?$/i.test(h.get("Content-Type")??"")||
    (h.has("Content-Encoding")&&h.get("Content-Encoding")!=="identity"))return null;
 return routes[u.pathname];
}
async function objectBody(req,fields){
 const size=req.headers.get("Content-Length");
 if(size!==null&&(!/^\d{1,4}$/.test(size)||Number(size)>CAP||Number(size)<2))throw Error("body");
 if(!req.body)throw Error("body");
 const reader=req.body.getReader(),bytes=new Uint8Array(CAP);let n=0,done=false;
 try{
  while(true){
   const chunk=await reader.read();
   if(chunk.done){done=true;break;}
   if(!(chunk.value instanceof Uint8Array)||n+chunk.value.byteLength>CAP)throw Error("body");
   bytes.set(chunk.value,n);n+=chunk.value.byteLength;
  }
 }finally{
  if(!done){try{await reader.cancel();}catch{}}
  reader.releaseLock();
 }
 if(size!==null&&Number(size)!==n)throw Error("body");
 const p=JSON.parse(new TextDecoder("utf-8",{fatal:true}).decode(bytes.subarray(0,n)));
 if(!p||Object.getPrototypeOf(p)!==Object.prototype)throw Error("body");
 if(fields&&(Object.keys(p).length!==fields.length||fields.some(k=>!Object.hasOwn(p,k))))throw Error("body");
 return p;
}
async function candidateRequest(req,env,ctx){
 let route,b;
 try{
  route=select(req,env);if(!route)return closed();
  b=await accessBinding(ctx,env);
  // Stable pseudonymous UUID key, not browser/IP/role. Missing or malformed limiter denies.
  const r=await env.CONTRIBUTORS_RATE_LIMITER.limit({key:b.subject});
  if(r?.success===false)return reply(429,{error:"rate_limited"});
  if(r?.success!==true)return closed();
  await verifyGeneration(env);
 }catch{return closed();}
 let body;
 try{body=await objectBody(req,route.fields);}catch{return reply(400,{error:"invalid_body"});}
 try{
  if(route.issue){await accessBinding(ctx,env,b);return reply(200,{data:await issueIntent(env,b,body.path,body.body)});}
  if(route.mutation){await accessBinding(ctx,env,b);await consumeIntent(env,b,new URL(req.url).pathname,body,req.headers.get("X-Remura-Intent"));}
  // Expected actor originates only from the initial trusted Access binding. Adapter revalidates and compares both tags.
  return reply(200,{data:await route.fn(ctx,env,body,b)});
 }catch{
  // A mutation may already be committed. No exception, identifier, SQL or automatic retry exposed.
  // Deliberately do not disclose whether a target receipt/review exists.
  return route.mutation?reply(409,{error:"not_confirmed",retry:false}):closed();
 }
}
export {candidateRequest};
