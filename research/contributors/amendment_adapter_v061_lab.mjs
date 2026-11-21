// REMURA Contributors v0.61 LAB — 21/11/2026 CET
// Offline candidate: NO HTTP handler, Worker deployment, real Access identity, Secrets or D1 binding.
// Direct calls are ONLY valid when ctx.access comes from a trusted platform runtime.
import {accessBinding} from './access_binding_candidate.mjs';
import {SQL as amend} from './d1_amendment_queries_v059_lab.mjs';

const deny=()=>{throw Error('AMENDMENT_NOT_CONFIRMED_OR_DENIED');};
const exact=(v,fields)=>v!==null&&typeof v==='object'&&!Array.isArray(v)&&Object.getPrototypeOf(v)===Object.prototype&&Object.keys(v).length===fields.length&&fields.every(k=>Object.hasOwn(v,k));
const HEX32=/^[a-f0-9]{32}$/,HEX64=/^[a-f0-9]{64}$/;
const UUID=/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/;
const UTC=/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/;
const PRICE=/^(?:0|[1-9][0-9]{0,7})(?:\.[0-9]{1,8})?$/;
const STATE=new Set(['UNREVIEWED','APPROVED','REJECTED','REVOKED']);
function positiveId(v,min=1){if(!Number.isSafeInteger(v)||v<min)deny();return v;}
function stamp(v){if(typeof v!=='string'||!UTC.test(v)||!Number.isFinite(Date.parse(v))||new Date(v).toISOString().slice(0,19)+'Z'!==v)deny();return v;}
function note(v,{required=false}={}){if(typeof v!=='string'||[...v].length>280||/[\u0000-\u001f\u007f-\u009f\uD800-\uDFFF]/u.test(v)||(required&&!v.trim()))deny();return v;}
function price(v){if(typeof v!=='string')deny();let p=v.replace(',','.');if(!PRICE.test(p)||!/[1-9]/.test(p)||p.length>17)deny();if(p.includes('.'))p=p.replace(/0+$/,'').replace(/\.$/,'');return p;}
function config(env){
 if(env?.AMENDMENT_V061_ENABLED!=='OFFLINE_FIXTURE_ONLY'||env.STAGING_ENABLED!=='D1_CANDIDATE'||!env.CONTRIBUTORS_DB?.withSession||
 !env.CONTRIBUTORS_RATE_LIMITER?.limit||typeof env.CONTRIBUTORS_GENERATION!=='string'||!HEX32.test(env.CONTRIBUTORS_GENERATION)||
 typeof env.CONTRIBUTORS_JOURNAL_PIN!=='string'||!HEX64.test(env.CONTRIBUTORS_JOURNAL_PIN))deny();
}
async function dbCall(db,sql,args,write=false,max=20){
 try{
  // Every operation uses a fresh primary-bound D1 session; primary metadata is mandatory.
  const stmt=db.withSession('first-primary').prepare(sql).bind(...args);
  const r=await (write?stmt.run():stmt.all());
  if(r?.success!==true||r.meta?.served_by_primary!==true)deny();
  if(write){if(r.meta.changes!==1)deny();}
  else if(!Array.isArray(r.results)||r.results.length>max)deny();
  return write?r:r.results;
 }catch{deny();}
}
const gateSQL=Object.freeze({
 generation:'SELECT id FROM lab_generation WHERE id=1 AND generation=? AND journal_pin=?',
 contributor:"SELECT slot FROM lab_identities WHERE subject=? AND email_tag=? AND revoked=0 AND EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND CASE ? WHEN 'READ' THEN read_enabled WHEN 'WRITE' THEN write_enabled ELSE 0 END=1)",
 owner:"SELECT id FROM lab_owner WHERE id=1 AND subject=? AND email_tag=? AND revoked=0 AND EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND CASE ? WHEN 'READ' THEN read_enabled WHEN 'WRITE' THEN write_enabled WHEN 'RECOVERY' THEN recovery_enabled ELSE 0 END=1)",
 existing:"SELECT a.id,a.source_entry_id,a.price,a.observed_utc,a.note,COALESCE((SELECT r.action FROM lab_level_amendment_reviews_v059 r WHERE r.amendment_id=a.id ORDER BY r.id DESC LIMIT 1),'UNREVIEWED') AS status FROM lab_level_amendments_v059 a JOIN lab_identities i ON i.subject=a.subject AND i.revoked=0 WHERE a.subject=? AND i.email_tag=? AND a.request_id=? AND EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND write_enabled=1)"
});
async function authorize(ctx,env,{role,mode,expected}={}){
 config(env);
 const actor=await accessBinding(ctx,env,expected);
 try{const limit=await env.CONTRIBUTORS_RATE_LIMITER.limit({key:actor.subject});if(limit?.success!==true)deny();}catch{deny();}
 const db=env.CONTRIBUTORS_DB;
 const g=await dbCall(db,gateSQL.generation,[env.CONTRIBUTORS_GENERATION,env.CONTRIBUTORS_JOURNAL_PIN],false,1);
 if(g.length!==1||g[0].id!==1)deny();
 const rows=await dbCall(db,role==='OWNER'?gateSQL.owner:gateSQL.contributor,[actor.subject,actor.email_tag,mode],false,1);
 if(rows.length!==1||(role==='OWNER'?rows[0].id!==1:!['friend-a','friend-b'].includes(rows[0].slot)))deny();
 return actor;
}
async function stillCurrent(ctx,env,actor){await accessBinding(ctx,env,actor);}
function newPayload(v){
 if(!exact(v,['source_entry_id','request_id','price','observed_utc','note']))deny();
 positiveId(v.source_entry_id);
 if(typeof v.request_id!=='string'||!UUID.test(v.request_id))deny();
 const observed_utc=stamp(v.observed_utc),now=stamp(new Date().toISOString().slice(0,19)+'Z');
 if(observed_utc>now)deny();
 return Object.freeze({source_entry_id:v.source_entry_id,request_id:v.request_id,price:price(v.price),observed_utc,note:note(v.note),received_utc:now});
}
function matched(row,p){return row&&Number.isSafeInteger(row.id)&&row.id>=1&&row.source_entry_id===p.source_entry_id&&row.price===p.price&&row.observed_utc===p.observed_utc&&row.note===p.note&&STATE.has(row.status);}
export async function submitAmendmentLab(ctx,env,input,expected){
 const p=newPayload(input);
 const actor=await authorize(ctx,env,{role:'CONTRIBUTOR',mode:'WRITE',expected});
 const existing=()=>dbCall(env.CONTRIBUTORS_DB,gateSQL.existing,[actor.subject,actor.email_tag,p.request_id],false,1);
 const old=await existing();
 if(old.length){if(!matched(old[0],p))deny();await stillCurrent(ctx,env,actor);return Object.freeze({id:old[0].id,status:old[0].status,duplicate:true});}
 await stillCurrent(ctx,env,actor);
 await dbCall(env.CONTRIBUTORS_DB,amend.submit,[actor.subject,p.request_id,p.price,p.observed_utc,p.received_utc,p.note,p.source_entry_id,actor.subject,actor.email_tag],true);
 // Do not retry a write if confirmation is missing. Reconcile only with a fresh read.
 const found=await existing();
 if(found.length!==1||!matched(found[0],p))deny();
 await stillCurrent(ctx,env,actor);
 return Object.freeze({id:found[0].id,status:found[0].status,duplicate:false});
}
export async function ownAmendmentsLab(ctx,env,after=0,expected){
 positiveId(after,0);
 const actor=await authorize(ctx,env,{role:'CONTRIBUTOR',mode:'READ',expected});
 const list=await dbCall(env.CONTRIBUTORS_DB,amend.own,[actor.subject,actor.email_tag,after]);
 await stillCurrent(ctx,env,actor);
 return list.map(r=>{if(!Number.isSafeInteger(r.id)||r.id<1||!Number.isSafeInteger(r.source_entry_id)||r.source_entry_id<1||!STATE.has(r.status))deny();return Object.freeze({id:r.id,source_entry_id:r.source_entry_id,price:r.price,observed_utc:r.observed_utc,received_utc:r.received_utc,note:r.note,status:r.status});});
}
export async function ownerAmendmentQueueLab(ctx,env,after=0,expected){
 positiveId(after,0);
 const actor=await authorize(ctx,env,{role:'OWNER',mode:'READ',expected});
 const list=await dbCall(env.CONTRIBUTORS_DB,amend.ownerQueue,[after,actor.subject,actor.email_tag]);
 await stillCurrent(ctx,env,actor);
 return list.map(r=>Object.freeze({id:r.id,source_entry_id:r.source_entry_id,subject:r.subject,price:r.price,observed_utc:r.observed_utc,received_utc:r.received_utc,note:r.note}));
}
export async function ownerAmendmentDecisionLab(ctx,env,input,expected){
 if(!exact(input,['id','action','reason']))deny();
 const id=positiveId(input.id),action=input.action;
 if(!['APPROVED','REJECTED','REVOKED'].includes(action))deny();
 const reason=note(input.reason,{required:true}),mode=action==='REVOKED'?'RECOVERY':'WRITE';
 const actor=await authorize(ctx,env,{role:'OWNER',mode,expected});
 const at_utc=stamp(new Date().toISOString().slice(0,19)+'Z');
 await stillCurrent(ctx,env,actor);
 await dbCall(env.CONTRIBUTORS_DB,amend.review,[id,action,at_utc,reason,actor.subject,actor.email_tag],true);
 await stillCurrent(ctx,env,actor);
 return Object.freeze({id,action,at_utc});
}
export async function approvedLevelsLab(ctx,env,expected){
 const actor=await authorize(ctx,env,{role:'CONTRIBUTOR',mode:'READ',expected});
 const list=await dbCall(env.CONTRIBUTORS_DB,amend.approved,[actor.subject,actor.email_tag],false,100);
 await stillCurrent(ctx,env,actor);
 return list.map(r=>Object.freeze({id:r.id,market:r.market,provider:r.provider,ticker:r.ticker,product:r.product,contract:r.contract,period:r.period,kind:r.kind,price:r.price,observed_utc:r.observed_utc}));
}
// Explicitly NO fetch() export or HTTP route. CSRF/one-time intent are NOT implemented here.
