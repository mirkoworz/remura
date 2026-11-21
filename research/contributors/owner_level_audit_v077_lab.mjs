// REMURA Contributors v0.77 LAB — 21/11/2026 16:44 CET.
// OWNER reconciliation for ORIGINAL-level attempts, independent of amendment journal.
// All operations require the trusted direct Access identity and D1 first-primary.
// Evidence audit appends ONLY; it NEVER releases a RESERVED attempt or approves a level.
const DENIED=()=>{throw Error('REMURA_V077_OWNER_AUDIT_DENIED')};
const HEX=/^[0-9a-f]{64}$/,GEN=/^[0-9a-f]{32}$/;
const UUID=/^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/;
const EXP=/^([0-9a-f]{32})\.([0-9]{10})\.([0-9a-f]{64})$/;
const ACTIONS=new Set(['RECEIPT_FOUND','RECEIPT_NOT_OBSERVED']);
const SQL=Object.freeze({
 permit:"SELECT 1 AS allowed FROM lab_owner o CROSS JOIN lab_state s CROSS JOIN lab_generation g WHERE o.id=1 AND o.subject=? AND o.email_tag=? AND o.revoked=0 AND s.id=1 AND s.read_enabled=1 AND s.recovery_enabled=1 AND g.id=1 AND g.generation=? AND g.journal_pin=?",
 pending:"SELECT a.rowid AS attempt_id,a.subject,a.request_id,a.state,a.claimed_utc,e.id AS observed_receipt,(SELECT max(z.id) FROM lab_new_level_owner_audit_v077 z WHERE z.subject=a.subject AND z.request_id=a.request_id) AS audit_id FROM lab_new_level_attempts a LEFT JOIN lab_entries e ON e.subject=a.subject AND e.request_id=a.request_id WHERE a.rowid>? AND a.state='RESERVED' ORDER BY a.rowid LIMIT 21",
 history:"SELECT id,subject,request_id,owner_subject,classification,receipt_id,reason,at_utc FROM lab_new_level_owner_audit_v077 WHERE id>? ORDER BY id LIMIT 21",
 burn:"INSERT INTO lab_intent_used(nonce,subject,mode,role,expires) SELECT ?,?,'RECOVERY','OWNER',? WHERE EXISTS(SELECT 1 FROM lab_owner o CROSS JOIN lab_state s CROSS JOIN lab_generation g WHERE o.id=1 AND o.subject=? AND o.email_tag=? AND o.revoked=0 AND s.id=1 AND s.recovery_enabled=1 AND s.read_enabled=1 AND g.id=1 AND g.generation=? AND g.journal_pin=?)",
 record:"INSERT INTO lab_new_level_owner_audit_v077(subject,request_id,owner_subject,classification,receipt_id,reason,at_utc) SELECT ?,?,?,?,?,?,? WHERE EXISTS(SELECT 1 FROM lab_owner o CROSS JOIN lab_state s CROSS JOIN lab_generation g WHERE o.id=1 AND o.subject=? AND o.email_tag=? AND o.revoked=0 AND s.id=1 AND s.read_enabled=1 AND s.recovery_enabled=1 AND g.id=1 AND g.generation=? AND g.journal_pin=?)"
});
function trusted(env,actor){
 if(env?.OWNER_LEVEL_AUDIT_V077!=='OFFLINE_FIXTURE_ONLY'||env.STAGING_ENABLED!=='D1_CANDIDATE'||
    !GEN.test(env.CONTRIBUTORS_GENERATION??'')||!HEX.test(env.CONTRIBUTORS_JOURNAL_PIN??'')||
    !HEX.test(actor?.subject??'')||!HEX.test(actor?.email_tag??'')||
    typeof env.CONTRIBUTORS_DB?.withSession!=='function')DENIED();
}
async function dbcall(env,actor,statement,args,write=false,max=20){
 trusted(env,actor);
 const session=env.CONTRIBUTORS_DB.withSession('first-primary');
 const query=session?.prepare?.(statement)?.bind?.(...args);
 if(!query)DENIED();
 const r=await (write?query.run():query.all());
 if(r?.success!==true||r.meta?.served_by_primary!==true)DENIED();
 if(write){if(r.meta?.changes!==1)DENIED();return true;}
 if(!Array.isArray(r.results)||r.results.length>max+1)DENIED();
 return r.results;
}
const bind=(env,a)=>[a.subject,a.email_tag,env.CONTRIBUTORS_GENERATION,env.CONTRIBUTORS_JOURNAL_PIN];
export async function verifyOwnerAuditAccessV077(env,actor){
 const rows=await dbcall(env,actor,SQL.permit,bind(env,actor),false,1);
 if(rows.length!==1||rows[0].allowed!==1)DENIED();
 return true;
}
const cursor=n=>{if(!Number.isSafeInteger(n)||n<0||n>1_000_000)DENIED();return n};
export async function ownerPendingLevelsV077(env,actor,after){
 await verifyOwnerAuditAccessV077(env,actor);
 const rows=await dbcall(env,actor,SQL.pending,[cursor(after)],false);
 return Object.freeze({
  rows:rows.slice(0,20).map(r=>{
   if(!Number.isSafeInteger(r.attempt_id)||r.attempt_id<1||!HEX.test(r.subject)||!UUID.test(r.request_id)||r.state!=='RESERVED'||
      (r.observed_receipt!==null&&(!Number.isSafeInteger(r.observed_receipt)||r.observed_receipt<1))||
      (r.audit_id!==null&&(!Number.isSafeInteger(r.audit_id)||r.audit_id<1)))DENIED();
   return {attempt_id:r.attempt_id,subject:r.subject,request_id:r.request_id,
     evidence:r.observed_receipt===null?'NOT_OBSERVED':'RECEIPT_FOUND',
     receipt_id:r.observed_receipt,audit_id:r.audit_id};
  }),has_more:rows.length>20
 });
}
export async function ownerLevelAuditHistoryV077(env,actor,after){
 await verifyOwnerAuditAccessV077(env,actor);
 const rows=await dbcall(env,actor,SQL.history,[cursor(after)],false);
 return Object.freeze({rows:rows.slice(0,20).map(r=>{
  if(!Number.isSafeInteger(r.id)||!HEX.test(r.subject)||!HEX.test(r.owner_subject)||!UUID.test(r.request_id)||!ACTIONS.has(r.classification))DENIED();
  return {id:r.id,subject:r.subject,request_id:r.request_id,classification:r.classification,
   receipt_id:r.receipt_id,at_utc:r.at_utc,reason:r.reason};
 }),has_more:rows.length>20});
}
export function validateOwnerLevelAuditV077(body){
 const fields=['subject','request_id','classification','receipt_id','reason'];
 if(!body||Object.getPrototypeOf(body)!==Object.prototype||Object.keys(body).length!==fields.length||fields.some(k=>!Object.hasOwn(body,k))||
  !HEX.test(body.subject??'')||!UUID.test(body.request_id??'')||!ACTIONS.has(body.classification)||
  !(body.classification==='RECEIPT_FOUND'?Number.isSafeInteger(body.receipt_id)&&body.receipt_id>0:body.receipt_id===null)||
  typeof body.reason!=='string'||body.reason.trim().length<1||body.reason.length>280||
  /[\u0000-\u001f\u007f-\u009f\uD800-\uDFFF]/u.test(body.reason))DENIED();
 return Object.freeze({...body});
}
const bytes=h=>Uint8Array.from(h.match(/../g),c=>parseInt(c,16));
const hex=b=>Array.from(new Uint8Array(b),v=>v.toString(16).padStart(2,'0')).join('');
const message=(env,a,p,n,expires)=>JSON.stringify([
 'remura-owner-new-level-audit-v077',env.CONTRIBUTORS_GENERATION,env.CONTRIBUTORS_JOURNAL_PIN,
 a.subject,a.email_tag,
 ...Object.keys(p).sort().map(k=>[k,p[k]]),n,expires
]);
async function key(env){
 if(!HEX.test(env.INTENT_HMAC_KEY??'')||/^0+$/.test(env.INTENT_HMAC_KEY)||env.INTENT_HMAC_KEY===env.IDENTITY_HMAC_KEY||
 typeof crypto?.subtle?.importKey!=='function')DENIED();
 return crypto.subtle.importKey('raw',bytes(env.INTENT_HMAC_KEY),{name:'HMAC',hash:'SHA-256'},false,['sign','verify']);
}
export async function issueOwnerLevelAuditIntentV077(env,actor,raw){
 const p=validateOwnerLevelAuditV077(raw);
 await verifyOwnerAuditAccessV077(env,actor);
 const expires=Math.floor(Date.now()/1000)+90;
 const nonce=hex(crypto.getRandomValues(new Uint8Array(16)));
 const h=await key(env);
 const sig=hex(await crypto.subtle.sign('HMAC',h,new TextEncoder().encode(message(env,actor,p,nonce,expires))));
 return {intent:nonce+'.'+expires+'.'+sig,expires_unix:expires};
}
export async function appendOwnerLevelAuditV077(env,actor,raw,token,now){
 const p=validateOwnerLevelAuditV077(raw);
 await verifyOwnerAuditAccessV077(env,actor);
 if(typeof token!=='string'||!EXP.test(token)||typeof now!=='string'||
    !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(now)||new Date(now).toISOString().slice(0,19)+'Z'!==now)DENIED();
 const [nonce,ex,sig]=token.split('.'),expires=Number(ex),epoch=Math.floor(Date.now()/1000);
 if(expires<epoch||expires>epoch+90)DENIED();
 const valid=await crypto.subtle.verify('HMAC',await key(env),bytes(sig),
    new TextEncoder().encode(message(env,actor,p,nonce,expires)));
 if(valid!==true)DENIED();
 // Burn the one-use HMAC before the audit append. A lost response may not be retried.
 await dbcall(env,actor,SQL.burn,[nonce,actor.subject,expires,...bind(env,actor)],true);
 await dbcall(env,actor,SQL.record,[p.subject,p.request_id,actor.subject,p.classification,p.receipt_id,p.reason,now,...bind(env,actor)],true);
 // This audit event records an observation; it NEVER unlocks a submission.
 return Object.freeze({recorded:true,retry:false,attempt_still_locked:true});
}
export const OWNER_LEVEL_AUDIT_SQL_V077=SQL;
