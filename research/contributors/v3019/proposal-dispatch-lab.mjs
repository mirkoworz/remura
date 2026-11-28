// REMURA V30.19 LAB — synthetic transport, no network, no credentials.
import {createFixtureStore,dispatchGroupedFixture} from "./proposal-store.mjs";
import {isSyntheticRealm} from "./proposal-realm.mjs";
const owner="EXISTS(SELECT 1 FROM lab_owner i CROSS JOIN lab_state s WHERE i.id=1 AND i.subject=?1 AND i.email_tag=?2 AND i.revoked=0 AND s.id=1 AND s.read_enabled=1 AND s.write_enabled=1 AND s.recovery_enabled=0)";
export const RECOVERY_SQL=Object.freeze({
 pending:"SELECT o.proposal_id FROM lab_proposal_outbox_v3019 o JOIN lab_telegram_policy_v3012 p ON p.id=1 AND p.enabled=1 AND p.epoch=o.epoch JOIN lab_proposal_decision_v3019 d ON d.proposal_id=o.proposal_id AND d.action='APPROVED' WHERE o.proposal_id=?3 AND o.epoch=?4 AND o.state='PENDING' AND o.queued_utc>=strftime('%Y-%m-%dT%H:%M:%SZ','now','-15 minutes') AND "+owner,
 abandon:"UPDATE lab_proposal_outbox_v3019 SET state='UNKNOWN',finished_utc=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE proposal_id=?3 AND epoch=?4 AND state='SENDING' AND claimed_utc<=strftime('%Y-%m-%dT%H:%M:%SZ','now','-5 minutes') AND "+owner+" RETURNING proposal_id"
});
const positive=x=>Number.isSafeInteger(x)&&x>0;
function enabled(env){return env?.REMURA_V3019_LAB_MODE==="SYNTHETIC_ONLY"&&env?.REMURA_V3019_TRANSPORT==="SYNTHETIC_TRANSPORT_ONLY";}
export function normalizeRecovery(body){
 if(!body||Object.getPrototypeOf(body)!==Object.prototype||Object.keys(body).length!==3||!positive(body.id)||!positive(body.epoch)||!["PENDING","MARK_UNKNOWN"].includes(body.action))throw Error("invalid_recovery");
 return {id:body.id,epoch:body.epoch,action:body.action};
}
export function createLabDispatcher(env){
 if(!enabled(env))return null;
 const db=env.CONTRIBUTORS_DB,store=createFixtureStore(db,"OFFLINE_FIXTURE_ONLY");
 const dispatch=async id=>{
 if(!await isSyntheticRealm(db))return {state:"OFF"};
 return dispatchGroupedFixture({store,proposalId:id,permit:"OFFLINE_FIXTURE_ONLY",send:async message=>{
  if(typeof message!=="string"||!message.includes("Rif. P"+id+" ·"))throw Error("message_invalid");
  // This deliberately fabricates only a synthetic acknowledgement. Never real Telegram delivery.
  return {ok:true,messageId:id};
 }});};
 async function ownerRecovery(actor,raw){
  const b=normalizeRecovery(raw);
  if(!await isSyntheticRealm(db))return {state:"OFF",simulated:true};
  if(!/^[a-f0-9]{64}$/.test(actor?.subject??"")||!/^[a-f0-9]{64}$/.test(actor?.email_tag??""))throw Error("denied");
  const sql=RECOVERY_SQL[b.action==="PENDING"?"pending":"abandon"];
  const r=await db.withSession("first-primary").prepare(sql).bind(actor.subject,actor.email_tag,b.id,b.epoch).all();
  if(r?.success!==true||r.meta?.served_by_primary!==true||!Array.isArray(r.results)||r.results.length>1)throw Error("recovery_unknown");
  if(!r.results.length)return {state:"EMPTY",simulated:true};
  if(b.action==="MARK_UNKNOWN")return {state:"UNKNOWN",proposalId:b.id,simulated:true};
  return {...await dispatch(b.id),simulated:true};
 }
 return Object.freeze({dispatch,ownerRecovery});
}
export function scheduleProposalLab(ctx,env,id){
 if(!positive(id)||typeof ctx?.waitUntil!=="function")return false;
 try{const d=createLabDispatcher(env);if(!d)return false;ctx.waitUntil(d.dispatch(id).catch(()=>{}));return true;}catch{return false;}
}
