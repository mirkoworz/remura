// REMURA V30.19 LAB — offline fixture only, never attach to deployed Worker.
// Requires D1-like primary session; caller must supply a trusted authenticated actor.
// No HTTP route and no access to credentials.
import {payloadForStorage, classify, formatGrouped} from "./proposal-core.mjs";
const identityGate="EXISTS(SELECT 1 FROM lab_identities i CROSS JOIN lab_state s WHERE i.subject=?1 AND i.email_tag=?2 AND i.revoked=0 AND s.id=1 AND s.read_enabled=1)";
export const SQL=Object.freeze({
 lookup:"SELECT id,request_id,mapping_id,kind,period,prices_json,note,payload,received_utc,publication_mode FROM lab_proposals_v3019 WHERE subject=?1 AND email_tag=?2 AND request_id=?3 AND "+identityGate,
 insert:"INSERT INTO lab_proposals_v3019(subject,email_tag,request_id,mapping_id,market,provider,ticker,product,contract,source_group,kind,period,prices_json,note,payload,received_utc,publication_mode) SELECT ?1,?2,?3,?4,c.market,c.provider,c.ticker,c.product,c.contract,c.source_group,?10,?11,?12,?13,?14,strftime('%Y-%m-%dT%H:%M:%SZ','now'),CASE WHEN i.slot='friend-a' OR ?15='TEST' THEN 'TEST' ELSE 'TELEGRAM' END FROM lab_level_catalog_v110 c JOIN lab_identities i ON i.subject=?1 AND i.email_tag=?2 AND i.revoked=0 JOIN lab_state s ON s.id=1 AND s.read_enabled=1 AND s.write_enabled=1 AND s.recovery_enabled=0 WHERE (c.market,c.provider,c.ticker,c.product,c.contract)=(?5,?6,?7,?8,?9) AND c.active=1 AND NOT EXISTS(SELECT 1 FROM lab_proposals_v3019 WHERE subject=?1 AND request_id=?3) RETURNING id",
 claim:"UPDATE lab_proposal_outbox_v3019 SET state='SENDING',claimed_utc=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE proposal_id=?1 AND state='PENDING' AND queued_utc>=strftime('%Y-%m-%dT%H:%M:%SZ','now','-15 minutes') AND EXISTS(SELECT 1 FROM lab_proposal_decision_v3019 d WHERE d.proposal_id=lab_proposal_outbox_v3019.proposal_id AND d.action='APPROVED') AND EXISTS(SELECT 1 FROM lab_telegram_policy_v3012 p JOIN lab_state s ON s.id=1 AND s.read_enabled=1 AND s.write_enabled=1 AND s.recovery_enabled=0 WHERE p.id=1 AND p.enabled=1 AND p.epoch=lab_proposal_outbox_v3019.epoch) RETURNING proposal_id,epoch",
 load:"SELECT e.id,e.request_id,e.mapping_id,e.kind,e.period,e.prices_json,e.note,e.received_utc,e.publication_mode,i.slot,d.action AS decision,d.origin AS decision_origin FROM lab_proposal_outbox_v3019 o JOIN lab_proposals_v3019 e ON e.id=o.proposal_id JOIN lab_proposal_decision_v3019 d ON d.proposal_id=e.id AND d.action='APPROVED' JOIN lab_identities i ON i.subject=e.subject AND i.email_tag=e.email_tag AND i.revoked=0 JOIN lab_telegram_policy_v3012 p ON p.id=1 AND p.enabled=1 AND p.epoch=o.epoch JOIN lab_state s ON s.id=1 AND s.read_enabled=1 AND s.write_enabled=1 AND s.recovery_enabled=0 JOIN lab_telegram_sources_v3012 a ON (a.market,a.provider,a.ticker,a.product,a.contract)=(e.market,e.provider,e.ticker,e.product,e.contract) JOIN lab_level_catalog_v110 c ON (c.market,c.provider,c.ticker,c.product,c.contract,c.source_group)=(e.market,e.provider,e.ticker,e.product,e.contract,e.source_group) AND c.active=1 WHERE o.proposal_id=?1 AND o.epoch=?2 AND o.state='SENDING' AND e.publication_mode='TELEGRAM' AND i.slot IN('friend-b','friend-c')",
 finish:"UPDATE lab_proposal_outbox_v3019 SET state=?2,finished_utc=strftime('%Y-%m-%dT%H:%M:%SZ','now'),message_id=?3 WHERE proposal_id=?1 AND state='SENDING' RETURNING proposal_id",
});
function actorArgs(actor){
 if(!/^[a-f0-9]{64}$/.test(actor?.subject??"")||!/^[a-f0-9]{64}$/.test(actor?.email_tag??""))throw Error("denied");
 return [actor.subject,actor.email_tag];
}
function view(row){
 const prices=JSON.parse(row.prices_json);
 return {state:"COMMITTED",id:row.id,received_utc:row.received_utc,publication_mode:row.publication_mode,
 proposal:{request_id:row.request_id,mapping_id:row.mapping_id,kind:row.kind,period:row.period,prices:prices.join("\n"),note:row.note}};
}
function makeStore(db){
 if(typeof db?.withSession!=="function")throw Error("DB_REQUIRED");
 const session=db.withSession("first-primary");
 async function one(key,args){
  const r=await session.prepare(SQL[key]).bind(...args).all();
  if(r?.success!==true||r.meta?.served_by_primary!==true||!Array.isArray(r.results)||r.results.length>1)throw Error("storage_unknown");
  return r.results[0]??null;
 }
 return Object.freeze({
 async submit(actor,body){
  const ids=actorArgs(actor),{proposal:p,mapping:m,prices,payload}=payloadForStorage(body);
  const args=[...ids,p.request_id];
  const lookup=()=>one("lookup",args);
  let prior=await lookup();
  if(prior){if(prior.payload!==payload)throw Error("conflict");return {...view(prior),replay:true};}
  // Publication mode is based on trusted D1 slot + conservative server note filter.
  const hint=classify("friend-b",p.note);
  const inserted=await one("insert",[...args,m.id,m.market,m.provider,m.ticker,m.product,m.contract,p.kind,p.period,JSON.stringify(prices),p.note,payload,hint]);
  prior=await lookup();
  if(!prior)throw Error("denied_or_unknown");
  if(prior.payload!==payload)throw Error("conflict");
  return {...view(prior),replay:!inserted};
 },
 async lookup(actor,requestId){
  if(!/^[a-f0-9-]{36}$/.test(requestId??""))throw Error("invalid_request");
  const row=await one("lookup",[...actorArgs(actor),requestId]);return row?view(row):null;
 },
 claim:id=>one("claim",[id]),
 load:async claim=>{const row=await one("load",[claim.proposal_id,claim.epoch]);return row?{...view(row),slot:row.slot,decision:row.decision,decision_origin:row.decision_origin}:null;},
 finish:async (id,state,messageId)=>{if(!await one("finish",[id,state,messageId]))throw Error("finish_unknown");}
 });
}
// Separate explicit adapters. The Worker must additionally attest the database realm.
export function createFixtureStore(db,permit){
 if(permit!=="OFFLINE_FIXTURE_ONLY")throw Error("LAB_ONLY");
 return makeStore(db);
}
export function createReleaseStore(db,permit){
 if(permit!=="STAGING_CANDIDATE_ONLY")throw Error("RELEASE_ONLY");
 return makeStore(db);
}
export async function dispatchGroupedFixture(opts){
 if(opts?.permit!=="OFFLINE_FIXTURE_ONLY")return {state:"OFF"};
 return dispatchGrouped(opts);
}
export async function dispatchGroupedRelease(opts){
 if(opts?.permit!=="STAGING_CANDIDATE_ONLY")return {state:"OFF"};
 return dispatchGrouped(opts);
}
// One claim, one attempt, one terminal outcome. No transport constructed here.
async function dispatchGrouped({store,proposalId,send}){
 if(typeof send!=="function")return {state:"OFF"};
 if(!Number.isSafeInteger(proposalId)||proposalId<1)return {state:"BLOCKED"};
 let claimed;
 try{claimed=await store.claim(proposalId);}catch{return {state:"CLAIM_UNKNOWN"};}
 if(!claimed)return {state:"EMPTY"};
 let state="UNKNOWN",messageId=null;
 try{
  const row=await store.load(claimed),message=row&&formatGrouped(row);
  if(!message)state="BLOCKED";
  else{const reply=await send(message);if(reply?.ok===true&&Number.isSafeInteger(reply.messageId)&&reply.messageId>0){state="SENT";messageId=reply.messageId;}}
 }catch{}
 try{await store.finish(proposalId,state,messageId);}catch{return {state:"FINALIZATION_UNKNOWN",proposalId};}
 return {state,proposalId};
}
