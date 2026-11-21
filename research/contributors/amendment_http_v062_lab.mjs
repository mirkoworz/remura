// REMURA Contributors v0.62 LAB — 21/11/2026 CET
// Direct offline HTTP candidate only; never wired to Worker/routes or deployed.
import {issueAmendmentIntentLab,burnAmendmentIntentLab} from './amendment_intent_v062_lab.mjs';
import {submitAmendmentLab,ownAmendmentsLab,ownerAmendmentQueueLab,ownerAmendmentDecisionLab,approvedLevelsLab} from './amendment_adapter_v061_lab.mjs';
const CAP=4096;
const security=Object.freeze({
 'Cache-Control':'no-store, max-age=0','Content-Type':'application/json; charset=utf-8',
 'X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Referrer-Policy':'no-referrer',
 'Cross-Origin-Resource-Policy':'same-origin','Content-Security-Policy':"default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
});
const respond=(code,body)=>new Response(JSON.stringify(body),{status:code,headers:security});
const fail=()=>respond(403,{error:'denied'});
const paths=new Set(['/api/amendment/intent','/api/amendment/submit','/api/amendment/mine','/api/amendment/approved','/owner/amendment/queue','/owner/amendment/review']);
const mutations=new Set(['/api/amendment/submit','/owner/amendment/review']);
const exact=(p,keys)=>p!==null&&typeof p==='object'&&!Array.isArray(p)&&Object.getPrototypeOf(p)===Object.prototype&&Object.keys(p).length===keys.length&&keys.every(k=>Object.hasOwn(p,k));
function authorizeRequest(req,env){
 try{
  if(env?.AMENDMENT_V062_ENABLED!=='OFFLINE_FIXTURE_ONLY'||env?.AMENDMENT_V061_ENABLED!=='OFFLINE_FIXTURE_ONLY'||typeof env.STAGING_ORIGIN!=='string')return null;
  const original=new URL(env.STAGING_ORIGIN),url=new URL(req.url);
  if(original.protocol!=='https:'||original.origin!==env.STAGING_ORIGIN||original.username||original.password||
    url.origin!==original.origin||req.url!==original.origin+url.pathname||!paths.has(url.pathname)||req.method!=='POST')return null;
  const h=req.headers;
  if(h.get('Origin')!==original.origin||h.get('Sec-Fetch-Site')!=='same-origin'||h.get('X-Remura-CSRF')!=='1'||
    !/^application\/json(?:;\s*charset=utf-8)?$/i.test(h.get('Content-Type')??'')||
    (h.has('Content-Encoding')&&h.get('Content-Encoding')!=='identity'))return null;
  return url.pathname;
 }catch{return null}
}
async function bodyJson(req){
 let reader,complete=false;
 try{
  const length=req.headers.get('Content-Length');
  if(length!==null&&(!/^[0-9]{1,4}$/.test(length)||Number(length)<2||Number(length)>CAP))throw Error('length');
  if(!req.body)throw Error('missing');
  reader=req.body.getReader();let total=0;const bytes=new Uint8Array(CAP);
  for(;;){const part=await reader.read();if(part.done){complete=true;break}
   if(!(part.value instanceof Uint8Array)||total+part.value.length>CAP)throw Error('too_large');
   bytes.set(part.value,total);total+=part.value.length;
  }
  if(length!==null&&Number(length)!==total)throw Error('length');
  const o=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes.subarray(0,total)));
  if(!o||Object.getPrototypeOf(o)!==Object.prototype)throw Error('json');
  return o;
 }finally{if(reader){if(!complete)try{await reader.cancel()}catch{}reader.releaseLock()}
}
export async function amendmentHttpCandidateV062(req,env,ctx){
 const path=authorizeRequest(req,env);if(!path)return fail();
 let body;try{body=await bodyJson(req)}catch{return respond(400,{error:'invalid_body'})}
 try{
  if(path==='/api/amendment/intent'){
   if(!exact(body,['path','body']))return respond(400,{error:'invalid_body'});
   return respond(200,{data:await issueAmendmentIntentLab(ctx,env,body.path,body.body)});
  }
  if(path==='/api/amendment/mine'||path==='/owner/amendment/queue'){
   if(!exact(body,['after'])||!Number.isSafeInteger(body.after)||body.after<0)return respond(400,{error:'invalid_body'});
   const data=path==='/api/amendment/mine'?await ownAmendmentsLab(ctx,env,body.after):await ownerAmendmentQueueLab(ctx,env,body.after);
   return respond(200,{data});
  }
  if(path==='/api/amendment/approved'){
   if(!exact(body,[]))return respond(400,{error:'invalid_body'});
   return respond(200,{data:await approvedLevelsLab(ctx,env)});
  }
  if(!mutations.has(path))return fail();
  // An issued HMAC intent must be consumed and burned BEFORE a mutation. No retry on uncertainty.
  await burnAmendmentIntentLab(ctx,env,path,body,req.headers.get('X-Remura-Intent'));
  const data=path==='/api/amendment/submit'?await submitAmendmentLab(ctx,env,body):await ownerAmendmentDecisionLab(ctx,env,body);
  return respond(200,{data});
 }catch{
  return mutations.has(path)?respond(409,{error:'not_confirmed',retry:false}):fail();
 }
}
