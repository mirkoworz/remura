// REMURA Contributors v0.76 LAB — 21/11/2026 15:57 CET.
// Original-level durable-attempt candidate: D1-compatible SQL + primary-only sessions.
// NO fetch export, NO migration, NO retries, NO live account usage.
import {normalize as normalizeOriginalLevel} from './d1_lab_adapter.mjs';
const BAD=()=>{throw Error('REMURA_V076_ATTEMPT_DENIED')};
const HEX=/^[a-f0-9]{64}$/;
const UUID=/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/;
const STAMP=/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/;
const DAY=new Set(['DAY','WEEK','CURRENT_MONTH','PREVIOUS_MONTH']);
const FIELDS=['request_id','market','provider','ticker','product','contract','period','kind','price','anchor_utc','observed_utc','note'];
const SQL=Object.freeze({
 permission:"SELECT 1 AS allowed FROM lab_identities i CROSS JOIN lab_state s CROSS JOIN lab_generation g WHERE i.subject=? AND i.email_tag=? AND i.revoked=0 AND s.id=1 AND s.read_enabled=1 AND g.id=1 AND g.generation=? AND g.journal_pin=? LIMIT 1",
 claim:"INSERT INTO lab_new_level_attempts(subject,email_tag,request_id,fingerprint,state,claimed_utc) SELECT ?,?,?,?,'RESERVED',? WHERE EXISTS(SELECT 1 FROM lab_identities i CROSS JOIN lab_state s CROSS JOIN lab_generation g WHERE i.subject=? AND i.email_tag=? AND i.revoked=0 AND s.id=1 AND s.write_enabled=1 AND g.id=1 AND g.generation=? AND g.journal_pin=?)",
 confirm:"UPDATE lab_new_level_attempts SET state='COMMITTED',receipt_id=?,confirmed_utc=? WHERE subject=? AND email_tag=? AND request_id=? AND fingerprint=? AND state='RESERVED' AND EXISTS(SELECT 1 FROM lab_entries e WHERE e.id=? AND e.subject=? AND e.request_id=? AND e.market=? AND e.provider=? AND e.ticker=? AND e.product=? AND e.contract=? AND e.period=? AND e.kind=? AND e.price=? AND e.anchor_utc=? AND e.observed_utc=? AND e.note=?) AND EXISTS(SELECT 1 FROM lab_identities i CROSS JOIN lab_state s CROSS JOIN lab_generation g WHERE i.subject=? AND i.email_tag=? AND i.revoked=0 AND s.id=1 AND s.write_enabled=1 AND g.id=1 AND g.generation=? AND g.journal_pin=?)",
 status:"SELECT a.state,a.request_id,a.receipt_id,e.id AS observed_receipt FROM lab_new_level_attempts a LEFT JOIN lab_entries e ON e.subject=a.subject AND e.request_id=a.request_id JOIN lab_identities i ON i.subject=a.subject AND i.email_tag=a.email_tag AND i.revoked=0 CROSS JOIN lab_state s CROSS JOIN lab_generation g WHERE a.subject=? AND a.email_tag=? AND s.id=1 AND s.read_enabled=1 AND g.id=1 AND g.generation=? AND g.journal_pin=? ORDER BY CASE WHEN a.state='RESERVED' THEN 0 ELSE 1 END,a.rowid DESC LIMIT 1"
});
function strictActor(a){
 if(!a||typeof a!=='object'||!HEX.test(a.subject??'')||!HEX.test(a.email_tag??''))BAD();
}
function primary(env){
 if(!env||env.LEVEL_JOURNAL_V076!=='OFFLINE_FIXTURE_ONLY'||env.STAGING_ENABLED!=='D1_CANDIDATE'||typeof env.CONTRIBUTORS_GENERATION!=='string'||!(/^[a-f0-9]{32}$/).test(env.CONTRIBUTORS_GENERATION)||!HEX.test(env.CONTRIBUTORS_JOURNAL_PIN??''))BAD();
 if(typeof env.CONTRIBUTORS_DB?.withSession!=='function')BAD();
 return env.CONTRIBUTORS_DB.withSession('first-primary');
}
async function exec(env,sql,args,mode){
 const db=primary(env);
 const q=db?.prepare?.(sql)?.bind?.(...args);
 if(!q)BAD();
 const r=mode==='run'?await q.run():await q.all();
 if(!r||r.success!==true||r.meta?.served_by_primary!==true)BAD();
 if(mode==='run'){
  if(!Number.isSafeInteger(r.meta?.changes)||r.meta.changes!==1)BAD();
  return true;
 }
 if(!Array.isArray(r.results)||r.results.length>1)BAD();
 return r.results;
}
export function normalizeNewLevelV076(input,now){
 if(!input||Object.getPrototypeOf(input)!==Object.prototype||Object.keys(input).length!==FIELDS.length||FIELDS.some(k=>!Object.hasOwn(input,k)||typeof input[k]!=='string')||!UUID.test(input.request_id))BAD();
 if(!STAMP.test(now??'')||!Number.isFinite(Date.parse(now))||new Date(now).toISOString().slice(0,19)+'Z'!==now)BAD();
 // Reuse the ORIGINAL catalog/price/timestamp contract, not a new permissive validator.
 const output=normalizeOriginalLevel(input,now);
 if(!DAY.has(output.period))BAD();
 return Object.freeze(output);
}
export async function newLevelFingerprintV076(level){
 const obj=Object.keys(level).sort().map(k=>[k,level[k]]);
 if(typeof globalThis.crypto?.subtle?.digest!=='function')BAD();
 const raw=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(obj)));
 return Array.from(new Uint8Array(raw),x=>x.toString(16).padStart(2,'0')).join('');
}
export async function claimNewLevelV076(env,actor,level,fingerprint,now){
 strictActor(actor);if(!HEX.test(fingerprint??''))BAD();
 await exec(env,SQL.claim,[actor.subject,actor.email_tag,level.request_id,fingerprint,now,actor.subject,actor.email_tag,env.CONTRIBUTORS_GENERATION,env.CONTRIBUTORS_JOURNAL_PIN],'run');
 return Object.freeze({state:'RESERVED',request_id:level.request_id});
}
export async function confirmNewLevelV076(env,actor,level,fingerprint,receiptId,now){
 strictActor(actor);if(!HEX.test(fingerprint??'')||!Number.isSafeInteger(receiptId)||receiptId<1)BAD();
 const args=[receiptId,now,actor.subject,actor.email_tag,level.request_id,fingerprint,
  receiptId,actor.subject,level.request_id,
  level.market,level.provider,level.ticker,level.product,level.contract,level.period,level.kind,level.price,level.anchor_utc,level.observed_utc,level.note,
  actor.subject,actor.email_tag,env.CONTRIBUTORS_GENERATION,env.CONTRIBUTORS_JOURNAL_PIN];
 await exec(env,SQL.confirm,args,'run');
 return Object.freeze({state:'COMMITTED',request_id:level.request_id,receipt_id:receiptId});
}
export async function inspectNewLevelV076(env,actor){
 strictActor(actor);
 // Empty attempt rows and disabled read access MUST never be conflated.
 const bind=[actor.subject,actor.email_tag,env.CONTRIBUTORS_GENERATION,env.CONTRIBUTORS_JOURNAL_PIN];
 const permit=await exec(env,SQL.permission,bind,'all');
 if(permit.length!==1||permit[0].allowed!==1)BAD();
 const rows=await exec(env,SQL.status,bind,'all');
 if(!rows.length)return Object.freeze({state:'NO_ATTEMPT',request_id:null,receipt_id:null,can_submit:true});
 const x=rows[0];if(typeof x.request_id!=='string'||!UUID.test(x.request_id))BAD();
 if(x.state==='RESERVED'){
  if(x.receipt_id!==null)BAD();
  if(x.observed_receipt===null)return Object.freeze({state:'UNRESOLVED',request_id:x.request_id,receipt_id:null,can_submit:false});
  if(!Number.isSafeInteger(x.observed_receipt)||x.observed_receipt<1)BAD();
  return Object.freeze({state:'COMMITTED_NEEDS_OWNER',request_id:x.request_id,receipt_id:x.observed_receipt,can_submit:false});
 }
 if(x.state==='COMMITTED'&&Number.isSafeInteger(x.receipt_id)&&x.receipt_id>0&&x.receipt_id===x.observed_receipt){
  return Object.freeze({state:'COMMITTED',request_id:x.request_id,receipt_id:x.receipt_id,can_submit:true});
 }
 BAD();
}
export const LEVEL_ATTEMPT_SQL_V076=SQL;
export const LEVEL_ATTEMPT_V076_INPUT_FIELDS=Object.freeze([...FIELDS]);
