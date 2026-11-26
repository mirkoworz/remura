// REMURA V30.12 LAB. One bounded dispatch. No live fetch by default.
import {prepareTelegramMessage} from "./telegram_message_v3011_lab.mjs";
const SQL=Object.freeze({
 claim:`UPDATE lab_telegram_outbox_v3012 SET state='SENDING',claimed_utc=?1
 WHERE receipt_id=(
 SELECT o.receipt_id FROM lab_telegram_outbox_v3012 o
 JOIN lab_telegram_policy_v3012 p ON p.id=1 AND p.enabled=1 AND p.epoch=o.epoch
 JOIN lab_state s ON s.id=1 AND s.read_enabled=1 AND s.write_enabled=1 AND s.recovery_enabled=0
 WHERE o.state='PENDING' ORDER BY o.receipt_id LIMIT 1)
 AND state='PENDING' RETURNING receipt_id,epoch`,
 load:`SELECT e.id,e.market,e.provider,e.ticker,e.product,e.contract,e.period,e.kind,e.price,
 e.received_utc,e.note,i.slot,p.start_after_receipt
 FROM lab_telegram_outbox_v3012 o JOIN lab_level_attempts_v110 e ON e.id=o.receipt_id AND e.duplicate_of IS NULL
 JOIN lab_identities i ON i.subject=e.subject AND i.email_tag=e.email_tag AND i.revoked=0
 JOIN lab_telegram_policy_v3012 p ON p.id=1 AND p.enabled=1 AND p.epoch=o.epoch
 JOIN lab_state s ON s.id=1 AND s.read_enabled=1 AND s.write_enabled=1 AND s.recovery_enabled=0
 JOIN lab_telegram_sources_v3012 m ON (m.market,m.provider,m.ticker,m.product,m.contract)=(e.market,e.provider,e.ticker,e.product,e.contract)
 JOIN lab_level_catalog_v110 c ON (c.market,c.provider,c.ticker,c.product,c.contract)=(e.market,e.provider,e.ticker,e.product,e.contract)
 AND c.active=1 AND c.source_group=e.source_group
 WHERE o.receipt_id=?1 AND o.epoch=?2 AND o.state='SENDING'
 AND i.slot IN('friend-b','friend-c')`,
 finish:`UPDATE lab_telegram_outbox_v3012 SET state=?2,finished_utc=?3,telegram_message_id=?4
 WHERE receipt_id=?1 AND state='SENDING' RETURNING receipt_id`
});
const utc=()=>new Date().toISOString().slice(0,19)+"Z";
async function one(db,sql,args){
 const result=await db.withSession("first-primary").prepare(sql).bind(...args).all();
 if(result?.success!==true||!Array.isArray(result.results)||result.results.length>1)
 throw Error("telegram_storage_unavailable");
 return result.results[0]??null;
}
export function createTelegramOutbox(db){
 return Object.freeze({
 claim:now=>one(db,SQL.claim,[now]),
 load:claim=>one(db,SQL.load,[claim.receipt_id,claim.epoch]),
 async finish(id,state,now,messageId=null){
  if(!await one(db,SQL.finish,[id,state,now,messageId]))throw Error("telegram_finish_unavailable");
 }
 });
}
// Only an explicitly provided transport can send; synthetic tests inject a fake.
// A claimed receipt is never automatically requeued, including on timeout/crash.
export async function dispatchOne({store,send,enabled=false,clock=utc}={}){
 if(enabled!==true||typeof send!=="function")return {state:"OFF"};
 let claim;
 try{claim=await store.claim(clock());}catch{return {state:"CLAIM_UNKNOWN"};}
 if(!claim)return {state:"EMPTY"};
 const id=claim.receipt_id;
 let state="UNKNOWN",messageId=null;
 try{
  const r=await store.load(claim);
  const prepared=r&&prepareTelegramMessage({state:"COMMITTED",newCanonical:true,test:false,slot:r.slot,receipt:r},
    {enabled:true,startAfterReceipt:r.start_after_receipt,allowedMappings:[[r.market,r.provider,r.ticker,r.product,r.contract]]});
  if(!prepared)state="BLOCKED";
  else{
   const reply=await send(prepared.text);
   if(reply?.ok===true&&Number.isSafeInteger(reply.messageId)&&reply.messageId>0){
    state="SENT";messageId=reply.messageId;
   }
  }
 }catch{state="UNKNOWN";messageId=null;}
 try{await store.finish(id,state,clock(),messageId);}
 catch{return {state:"FINALIZATION_UNKNOWN",receiptId:id};}
 return {state,receiptId:id};
}
export {SQL as TELEGRAM_OUTBOX_SQL};
