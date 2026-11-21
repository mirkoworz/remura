// REMURA Contributors v0.78 LAB — 21/11/2026 16:56 CET.
// Read-only OWNER diagnostic on the original-level, append-only v0.77 evidence.
// It can only observe changes; it NEVER confirms a reservation or unlocks a submit.
// No default Worker export, no migrations, no external calls.
import {verifyOwnerAuditAccessV077} from './owner_level_audit_v077_lab.mjs';
const DENIED=()=>{throw Error('REMURA_V078_OWNER_INTEGRITY_DENIED')};
const HEX=/^[0-9a-f]{64}$/,UUID=/^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/;
const ACTIONS=new Set(['RECEIPT_FOUND','RECEIPT_NOT_OBSERVED']);
export const OWNER_LEVEL_INTEGRITY_SQL_V078=[
 'SELECT a.rowid AS attempt_id,a.subject,a.request_id,a.state,e.id AS entry_id,',
 '(SELECT h.id FROM lab_new_level_owner_audit_v077 h WHERE h.subject=a.subject AND h.request_id=a.request_id ORDER BY h.id DESC LIMIT 1) AS audit_id,',
 '(SELECT h.classification FROM lab_new_level_owner_audit_v077 h WHERE h.subject=a.subject AND h.request_id=a.request_id ORDER BY h.id DESC LIMIT 1) AS audit_classification,',
 '(SELECT h.receipt_id FROM lab_new_level_owner_audit_v077 h WHERE h.subject=a.subject AND h.request_id=a.request_id ORDER BY h.id DESC LIMIT 1) AS audited_receipt',
 'FROM lab_new_level_attempts a LEFT JOIN lab_entries e ON e.subject=a.subject AND e.request_id=a.request_id',
 "WHERE a.rowid>? AND a.state='RESERVED' AND EXISTS(",
 'SELECT 1 FROM lab_owner o CROSS JOIN lab_state s CROSS JOIN lab_generation g',
 'WHERE o.id=1 AND o.subject=? AND o.email_tag=? AND o.revoked=0',
 'AND s.id=1 AND s.read_enabled=1 AND s.recovery_enabled=1',
 'AND g.id=1 AND g.generation=? AND g.journal_pin=?)',
 'ORDER BY a.rowid LIMIT 21'
].join(' ');
function classify(r){
 if(!Number.isSafeInteger(r.attempt_id)||r.attempt_id<1||!HEX.test(r.subject??'')||
    !UUID.test(r.request_id??'')||r.state!=='RESERVED')DENIED();
 const hasEntry=r.entry_id!==null;
 if(hasEntry&&(!Number.isSafeInteger(r.entry_id)||r.entry_id<1))DENIED();
 const hasAudit=r.audit_id!==null;
 if(hasAudit&&(!Number.isSafeInteger(r.audit_id)||r.audit_id<1||!ACTIONS.has(r.audit_classification)))DENIED();
 if(!hasAudit&&(r.audit_classification!==null||r.audited_receipt!==null))DENIED();
 if(hasAudit&&r.audit_classification==='RECEIPT_FOUND'&&(!Number.isSafeInteger(r.audited_receipt)||r.audited_receipt<1))DENIED();
 if(hasAudit&&r.audit_classification==='RECEIPT_NOT_OBSERVED'&&r.audited_receipt!==null)DENIED();
 let condition;
 if(hasEntry&&r.audit_classification==='RECEIPT_NOT_OBSERVED')condition='EVIDENCE_CHANGED_NEEDS_OWNER';
 else if(hasEntry&&r.audit_classification==='RECEIPT_FOUND'){
  condition=r.entry_id===r.audited_receipt?'RECEIPT_ATTESTED_LOCKED':'INCONSISTENT_EVIDENCE';
 }else if(hasEntry)condition='RECEIPT_FOUND_UNATTESTED';
 else if(r.audit_classification==='RECEIPT_FOUND')condition='INCONSISTENT_EVIDENCE';
 else if(r.audit_classification==='RECEIPT_NOT_OBSERVED')condition='ABSENCE_SNAPSHOT_ONLY';
 else condition='NOT_OBSERVED_UNATTESTED';
 return Object.freeze({
  attempt_id:r.attempt_id,subject:r.subject,request_id:r.request_id,
  observed_receipt:hasEntry?r.entry_id:null,
  last_audit_id:hasAudit?r.audit_id:null,
  condition,
  needs_owner:true,attempt_locked:true
 });
}
export async function ownerIntegritySnapshotV078(env,actor,after=0){
 if(env?.OWNER_INTEGRITY_V078!=='OFFLINE_FIXTURE_ONLY'||
    !Number.isSafeInteger(after)||after<0||after>1_000_000)DENIED();
 // Verify BEFORE and AFTER the scan; live permissions also appear inside the SELECT.
 await verifyOwnerAuditAccessV077(env,actor);
 const db=env.CONTRIBUTORS_DB?.withSession?.('first-primary');
 const query=db?.prepare?.(OWNER_LEVEL_INTEGRITY_SQL_V078)?.bind?.(
  after,actor.subject,actor.email_tag,env.CONTRIBUTORS_GENERATION,env.CONTRIBUTORS_JOURNAL_PIN
 );
 if(!query)DENIED();
 const r=await query.all();
 if(r?.success!==true||r.meta?.served_by_primary!==true||!Array.isArray(r.results)||r.results.length>21)DENIED();
 await verifyOwnerAuditAccessV077(env,actor);
 const items=r.results.slice(0,20).map(classify);
 if(new Set(items.map(x=>x.attempt_id)).size!==items.length)DENIED();
 return Object.freeze({rows:items,has_more:r.results.length>20,automatic_release:false});
}
