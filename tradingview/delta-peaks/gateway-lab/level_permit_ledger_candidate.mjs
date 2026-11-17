// REMURA v0.8.120 LAB — 17/11/2026 07:04 CET (session start)
// Only for a NEW disposable fixture, no Worker binding.
import {reserveFixture} from "./level_receipt_candidate.mjs";
import {validatePinnedLevel} from "./level_structure_candidate.mjs";
export {reserveFixture};
export const FINALIZE_SQL = `WITH eligible AS (
 SELECT p.attempt,CASE
 WHEN EXISTS(SELECT 1 FROM level_receipts_v2 WHERE close_ms=?2 AND body_digest=?6) THEN 'DUPLICATE'
 WHEN EXISTS(SELECT 1 FROM level_receipts_v2 WHERE close_ms=?2) THEN 'CONFLICT'
 WHEN (SELECT count(*) FROM level_receipts_v2)>=12 OR EXISTS(SELECT 1 FROM level_receipts_v2 WHERE close_ms>=?2 OR first_received_ms>?3) THEN 'CAPACITY_OR_ORDER'
 ELSE 'STORED_SYNTHETIC' END AS outcome
 FROM level_permits_v2 p JOIN level_admission_v1 a ON a.id=1 AND a.pin=p.pin
 JOIN level_receipt_session_v1 s ON s.id=a.id AND s.pin=a.pin
 WHERE a.enabled=1 AND a.pin=?1 AND p.attempt=?5 AND p.received_ms=?3
 AND ?14 BETWEEN p.received_ms AND p.received_ms+5000
 AND s.config_digest=?9 AND s.chart_type=?10 AND s.timezone=?11 AND s.session_name=?12
 AND s.cutoff_ms=?13 AND ?2>s.cutoff_ms
 AND NOT EXISTS(SELECT 1 FROM level_finalizations_v2 f WHERE f.attempt=p.attempt)
 )
 INSERT INTO level_finalizations_v2(attempt,completed_ms,outcome,close_ms,received_ms,sender_ms,digest,body,present_levels)
 SELECT attempt,?14,outcome,?2,?3,?4,?6,CASE WHEN outcome='STORED_SYNTHETIC' THEN ?7 ELSE NULL END,?8 FROM eligible
 RETURNING outcome`;
const hex=x=>typeof x==="string"&&/^[a-f0-9]{64}$/.test(x);
const time=x=>Number.isSafeInteger(x)&&x>0&&x<4102444800000;
const result=status=>({status,synthetic:true,receipt_authenticated:false,scientific_admission:false,operational_signal:false});
export async function finalizeFixture(db,raw,{synthetic=false,pin,attempt,expected,receivedMs,afterCloseMs,completedMs}={}){
 if(synthetic!==true||!hex(pin)||!Number.isInteger(attempt)||attempt<1||attempt>48||!time(receivedMs)||!time(completedMs)||completedMs<receivedMs||completedMs-receivedMs>5000)return result("DENIED");
 let report,p,digest;
 try{
  report=await validatePinnedLevel(raw,expected,{receivedMs,afterCloseMs,synthetic:true});
  p=JSON.parse(raw).snapshot;
  const bytes=new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(raw)));
  digest=Array.from(bytes,b=>b.toString(16).padStart(2,"0")).join("");
 }catch{return result("INVALID");}
 try{
  const row=await db.prepare(FINALIZE_SQL).bind(pin,p.snapshot_close_ms,receivedMs,p.sender_clock_ms,attempt,digest,raw,report.present_levels,expected.configuration_digest,expected.chart_type,expected.timezone,expected.session,afterCloseMs,completedMs).first();
  if(row===null)return result("CLOSED_USED_OR_EXPIRED");
  if(["STORED_SYNTHETIC","DUPLICATE","CONFLICT","CAPACITY_OR_ORDER"].includes(row?.outcome))return result(row.outcome);
  return result("UNAVAILABLE");
 }catch{return result("UNAVAILABLE");}
}
