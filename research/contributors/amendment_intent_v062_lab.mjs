// REMURA Contributors v0.62 LAB — 21/11/2026 CET
// HMAC-bound one-use intents for amendment mutations; no HTTP entrypoint or provisioning.
import {accessBinding} from './access_binding_candidate.mjs';
import {SQL as baseSQL} from './operation_intent_candidate.mjs';
const hex = x=>Array.from(new Uint8Array(x),v=>v.toString(16).padStart(2,'0')).join('');
const rawhex = x=>Uint8Array.from(x.match(/../g),h=>parseInt(h,16));
const HEX=/^[0-9a-f]{64}$/;
const TOKEN=/^([a-f0-9]{32})\.([0-9]{10})\.([a-f0-9]{64})$/;
const exact=(p,keys)=>p!==null&&typeof p==='object'&&!Array.isArray(p)&&Object.getPrototypeOf(p)===Object.prototype&&Object.keys(p).length===keys.length&&keys.every(k=>Object.hasOwn(p,k));
const no=()=>{throw Error('AMENDMENT_INTENT_DENIED')};
const ENC=new TextEncoder();
const mutateRoutes=Object.freeze({'/api/amendment/submit':'CONTRIBUTOR','/owner/amendment/review':'OWNER'});
function operation(path,p){
 if(!Object.hasOwn(mutateRoutes,path))no();
 if(path==='/api/amendment/submit'){
  if(!exact(p,['source_entry_id','request_id','price','observed_utc','note'])||!Number.isSafeInteger(p.source_entry_id)||p.source_entry_id<1||typeof p.request_id!=='string'||typeof p.price!=='string'||typeof p.observed_utc!=='string'||typeof p.note!=='string')no();
 }else{
  if(!exact(p,['id','action','reason'])||!Number.isSafeInteger(p.id)||p.id<1||!['APPROVED','REJECTED','REVOKED'].includes(p.action)||typeof p.reason!=='string')no();
 }
 const role=mutateRoutes[path],mode=p.action==='REVOKED'?'RECOVERY':'WRITE';
 const body=JSON.stringify(Object.keys(p).sort().map(k=>[k,p[k]]));
 if(ENC.encode(body).length>2048)no();
 return {role,mode,body};
}
function config(env){
 if(env?.STAGING_ENABLED!=='D1_CANDIDATE'||env?.AMENDMENT_V062_ENABLED!=='OFFLINE_FIXTURE_ONLY'||env?.AMENDMENT_V061_ENABLED!=='OFFLINE_FIXTURE_ONLY'||
   typeof env.INTENT_HMAC_KEY!=='string'||!HEX.test(env.INTENT_HMAC_KEY)||/^0+$/.test(env.INTENT_HMAC_KEY)||env.INTENT_HMAC_KEY===env.IDENTITY_HMAC_KEY||
   typeof env.CONTRIBUTORS_GENERATION!=='string'||!/^[a-f0-9]{32}$/.test(env.CONTRIBUTORS_GENERATION)||
   typeof env.CONTRIBUTORS_JOURNAL_PIN!=='string'||!HEX.test(env.CONTRIBUTORS_JOURNAL_PIN)||!env.CONTRIBUTORS_DB?.withSession)no();
}
async function secretKey(env){return crypto.subtle.importKey('raw',rawhex(env.INTENT_HMAC_KEY),{name:'HMAC',hash:'SHA-256'},false,['sign','verify'])}
function signBytes(env,actor,path,op,nonce,exp){return ENC.encode(JSON.stringify(['remura-amendment-v062-fixture',env.CONTRIBUTORS_GENERATION,env.CONTRIBUTORS_JOURNAL_PIN,actor.subject,actor.email_tag,path,op.role,op.mode,op.body,nonce,exp]));}
function permissionArgs(env,a,op){return [env.CONTRIBUTORS_GENERATION,env.CONTRIBUTORS_JOURNAL_PIN,op.mode,op.role,a.subject,a.email_tag,op.role,a.subject,a.email_tag];}
async function primary(env,sql,args,write=false){
 try{
  const stmt=env.CONTRIBUTORS_DB.withSession('first-primary').prepare(sql).bind(...args);
  const r=await(write?stmt.run():stmt.all());
  if(r?.success!==true||r.meta?.served_by_primary!==true)no();
  if(write ? r.meta.changes!==1 : !Array.isArray(r.results)||r.results.length!==1)no();
  return write?r:r.results[0];
 }catch{no()}
}
async function authenticate(env,ctx){
 config(env);const actor=await accessBinding(ctx,env);
 const limit=await env.CONTRIBUTORS_RATE_LIMITER?.limit({key:actor.subject});
 if(limit?.success!==true)no();
 return actor;
}
export async function issueAmendmentIntentLab(ctx,env,path,p){
 const op=operation(path,p),actor=await authenticate(env,ctx);
 const permission=await primary(env,baseSQL.permission,permissionArgs(env,actor,op));
 if(permission.allowed!==1)no();
 const exp=Math.floor(Date.now()/1000)+90;
 const nonce=hex(crypto.getRandomValues(new Uint8Array(16)));
 const signature=hex(await crypto.subtle.sign('HMAC',await secretKey(env),signBytes(env,actor,path,op,nonce,exp)));
 return Object.freeze({intent:nonce+'.'+exp+'.'+signature,expires_unix:exp});
}
export async function burnAmendmentIntentLab(ctx,env,path,p,token){
 const op=operation(path,p),actor=await authenticate(env,ctx);
 if(typeof token!=='string'||!TOKEN.test(token))no();
 const [nonce,expiry,sig]=token.split('.'),exp=Number(expiry),now=Math.floor(Date.now()/1000);
 if(exp<now||exp>now+90)no();
 const valid=await crypto.subtle.verify('HMAC',await secretKey(env),rawhex(sig),signBytes(env,actor,path,op,nonce,exp));
 if(!valid)no();
 const a=permissionArgs(env,actor,op);
 await primary(env,baseSQL.burn,[nonce,actor.subject,op.mode,op.role,exp,a[0],a[1],exp,...a.slice(2)],true);
 if(Math.floor(Date.now()/1000)>exp)no();
 return Object.freeze({actor});
}
