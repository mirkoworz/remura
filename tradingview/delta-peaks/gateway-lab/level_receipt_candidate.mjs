// REMURA v0.8.118 LAB — 17/11/2026 CET
// Synthetic D1-shaped receipt candidate only. NOT connected to any Worker.
import {RESERVE_SQL} from "./level_admission_candidate.mjs";
import {validatePinnedLevel} from "./level_structure_candidate.mjs";
export const RESERVE_ID_SQL=RESERVE_SQL.replace("RETURNING enabled,allowed","RETURNING enabled,allowed,attempts");
export const INSERT_SQL = `INSERT INTO level_receipts_v1(close_ms,first_received_ms,sender_ms,attempt,body_digest,body,present_levels)
 SELECT ?2,?3,?4,?5,?6,?7,?8
 FROM level_admission_v1 a JOIN level_receipt_session_v1 s ON s.id=a.id AND s.pin=a.pin
 WHERE a.id=1 AND a.pin=?1 AND s.config_digest=?9 AND s.chart_type=?10 AND s.timezone=?11
 AND s.session_name=?12 AND s.cutoff_ms=?13 AND a.enabled=1 AND a.allowed=1
 AND a.attempts=?5 AND a.last_ms<=?3 AND ?2>s.cutoff_ms
 AND (SELECT count(*) FROM level_receipts_v1)<12
 AND NOT EXISTS(SELECT 1 FROM level_receipts_v1 WHERE close_ms>=?2 OR first_received_ms>?3 OR attempt=?5)
 RETURNING close_ms`;
export const EXISTING_SQL = `SELECT r.body_digest,r.first_received_ms FROM level_receipts_v1 r
 JOIN level_admission_v1 a ON a.id=1 JOIN level_receipt_session_v1 s ON s.id=a.id AND s.pin=a.pin
 WHERE a.pin=?1 AND r.close_ms=?2 AND a.enabled=1 AND a.allowed=1 AND a.attempts=?3
 AND s.config_digest=?4 AND s.chart_type=?5 AND s.timezone=?6 AND s.session_name=?7 AND s.cutoff_ms=?8
 AND a.last_ms<=?9 AND NOT EXISTS(SELECT 1 FROM level_receipts_v1 WHERE attempt=?3 AND close_ms<>?2)`;
const hex=x=>typeof x==="string"&&/^[a-f0-9]{64}$/.test(x);
const time=x=>Number.isSafeInteger(x)&&x>0&&x<4102444800000;
const response=status=>({status,synthetic:true,receipt_authenticated:false,scientific_admission:false,operational_signal:false});
export async function reserveFixture(db,pin,now,{synthetic=false}={}){
 if(synthetic!==true||!hex(pin)||!time(now))return {status:"UNAVAILABLE"};
 try{
  const row=await db.prepare(RESERVE_ID_SQL).bind(pin,now).first();
  if(row?.enabled===1&&row.allowed===1&&Number.isInteger(row.attempts)&&row.attempts>=1&&row.attempts<=48)
   return {status:"RESERVED",attempt:row.attempts};
  return {status:"DENIED"};
 }catch{return {status:"UNAVAILABLE"};}
}
export async function storeFixture(db,raw,{synthetic=false,pin,attempt,expected,receivedMs,afterCloseMs}={}){
 if(synthetic!==true||!hex(pin)||!Number.isInteger(attempt)||attempt<1||attempt>48)return response("DENIED");
 let report,p,digest;
 try{
  report=await validatePinnedLevel(raw,expected,{receivedMs,afterCloseMs,synthetic:true});
  p=JSON.parse(raw).snapshot; // strict parser already rejected duplicate keys and unsafe clocks.
  const bytes=new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(raw)));
  digest=Array.from(bytes,b=>b.toString(16).padStart(2,"0")).join("");
 }catch{return response("INVALID");}
 try{
  const cfg=[expected.configuration_digest,expected.chart_type,expected.timezone,expected.session,afterCloseMs];
  const row=await db.prepare(INSERT_SQL).bind(pin,p.snapshot_close_ms,receivedMs,p.sender_clock_ms,attempt,digest,raw,report.present_levels,...cfg).first();
  if(row?.close_ms===p.snapshot_close_ms)return response("STORED_SYNTHETIC");
  if(row!==null)return response("UNAVAILABLE");
  // Diagnostic classification only; separate read, no change to first receipt.
  const old=await db.prepare(EXISTING_SQL).bind(pin,p.snapshot_close_ms,attempt,...cfg,receivedMs).first();
  if(old===null)return response("CLOSED_STALE_OR_CAPACITY");
  if(!hex(old?.body_digest)||!time(old?.first_received_ms))return response("UNAVAILABLE");
  return response(old.body_digest===digest?"DUPLICATE":"CONFLICT");
 }catch{return response("UNAVAILABLE");}
}
