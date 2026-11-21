// REMURA Contributors v0.64 LAB — 21/11/2026 CET.
// Read-only recovery status; no HTTP handler, release, mutation or live D1 binding.
import {accessBinding} from './access_binding_candidate.mjs';
const no=()=>{throw Error('RECONCILIATION_BLOCKED')};
const HEX32=/^[a-f0-9]{32}$/,HEX64=/^[a-f0-9]{64}$/;
const STATES=new Set(['UNRESOLVED','COMMITTED_UNREVIEWED','COMMITTED_REVIEWED','CLOSED']);
export const RECOVERY_SQL=Object.freeze({
 generation:'SELECT id FROM lab_generation WHERE id=1 AND generation=? AND journal_pin=?',
 contributor:"SELECT slot FROM lab_identities WHERE subject=? AND email_tag=? AND revoked=0 AND EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND read_enabled=1)",
 owner:"SELECT id FROM lab_owner WHERE id=1 AND subject=? AND email_tag=? AND revoked=0 AND EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND read_enabled=1)",
 mine:"SELECT a.id AS attempt_id,a.request_id,CASE WHEN x.attempt_id IS NOT NULL THEN 'CLOSED' WHEN e.id IS NULL THEN 'UNRESOLVED' WHEN (SELECT r.action FROM lab_level_amendment_reviews_v059 r WHERE r.amendment_id=e.id ORDER BY r.id DESC LIMIT 1) IS NULL THEN 'COMMITTED_UNREVIEWED' ELSE 'COMMITTED_REVIEWED' END AS state FROM lab_amend_attempts_v064 a JOIN lab_identities i ON i.subject=a.subject AND i.email_tag=? AND i.revoked=0 LEFT JOIN lab_amend_releases_v064 x ON x.attempt_id=a.id LEFT JOIN lab_level_amendments_v059 e ON e.subject=a.subject AND e.request_id=a.request_id WHERE a.subject=? AND EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND read_enabled=1) ORDER BY a.id DESC LIMIT 1",
 ownerQueue:"SELECT a.id AS attempt_id,a.subject,a.request_id,CASE WHEN e.id IS NULL THEN 'UNRESOLVED' WHEN (SELECT r.action FROM lab_level_amendment_reviews_v059 r WHERE r.amendment_id=e.id ORDER BY r.id DESC LIMIT 1) IS NULL THEN 'COMMITTED_UNREVIEWED' ELSE 'COMMITTED_REVIEWED' END AS state FROM lab_amend_attempts_v064 a LEFT JOIN lab_amend_releases_v064 x ON x.attempt_id=a.id LEFT JOIN lab_level_amendments_v059 e ON e.subject=a.subject AND e.request_id=a.request_id WHERE x.attempt_id IS NULL AND a.id>? AND EXISTS(SELECT 1 FROM lab_owner o WHERE o.id=1 AND o.subject=? AND o.email_tag=? AND o.revoked=0) AND EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND read_enabled=1) ORDER BY a.id LIMIT 20"
});
async function query(db,sql,params,max){
 try{
  const response=await db.withSession('first-primary').prepare(sql).bind(...params).all();
  if(response?.success!==true||response.meta?.served_by_primary!==true||!Array.isArray(response.results)||response.results.length>max)no();
  return response.results;
 }catch{no()}
}
async function context(ctx,env,owner=false){
 if(env?.RECONCILIATION_V064_ENABLED!=='OFFLINE_FIXTURE_ONLY'||env?.STAGING_ENABLED!=='D1_CANDIDATE'||
  !HEX32.test(env?.CONTRIBUTORS_GENERATION)||!HEX64.test(env?.CONTRIBUTORS_JOURNAL_PIN)||
  !env?.CONTRIBUTORS_DB?.withSession||typeof env?.CONTRIBUTORS_RATE_LIMITER?.limit!=='function')no();
 let actor;try{actor=await accessBinding(ctx,env)}catch{no()}
 try{const lim=await env.CONTRIBUTORS_RATE_LIMITER.limit({key:actor.subject});if(lim?.success!==true)no()}catch{no()}
 const g=await query(env.CONTRIBUTORS_DB,RECOVERY_SQL.generation,[env.CONTRIBUTORS_GENERATION,env.CONTRIBUTORS_JOURNAL_PIN],1);
 if(g.length!==1||g[0].id!==1)no();
 const rows=await query(env.CONTRIBUTORS_DB,owner?RECOVERY_SQL.owner:RECOVERY_SQL.contributor,[actor.subject,actor.email_tag],1);
 if(rows.length!==1||(owner?rows[0].id!==1:!['friend-a','friend-b'].includes(rows[0].slot)))no();
 return actor;
}
function valid(r,owner=false){
 if(!Number.isSafeInteger(r.attempt_id)||r.attempt_id<1||!(/^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/).test(r.request_id)||!STATES.has(r.state))no();
 if(owner&&!/^[a-f0-9]{64}$/.test(r.subject))no();
}
export async function inspectMyAmendmentRecoveryV064(ctx,env){
 const a=await context(ctx,env);
 const rows=await query(env.CONTRIBUTORS_DB,RECOVERY_SQL.mine,[a.email_tag,a.subject],1);
 // A new trusted identity check is mandatory before any returned state.
 try{await accessBinding(ctx,env,a)}catch{no()}
 if(!rows.length)return Object.freeze({status:'NO_ATTEMPT',mayResubmit:false,manualApprovalRequired:true});
 const r=rows[0];valid(r);
 return Object.freeze({status:r.state,attempt_id:r.attempt_id,request_id:r.request_id,mayResubmit:false,manualApprovalRequired:true});
}
export async function inspectOwnerRecoveryQueueV064(ctx,env,after=0){
 if(!Number.isSafeInteger(after)||after<0)no();
 const a=await context(ctx,env,true);
 const rows=await query(env.CONTRIBUTORS_DB,RECOVERY_SQL.ownerQueue,[after,a.subject,a.email_tag],20);
 try{await accessBinding(ctx,env,a)}catch{no()}
 return Object.freeze(rows.map(r=>{valid(r,true);return Object.freeze({attempt_id:r.attempt_id,subject:r.subject,request_id:r.request_id,status:r.state,manualApprovalRequired:true})}));
}
