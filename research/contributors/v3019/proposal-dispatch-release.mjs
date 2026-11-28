// V30.19 RELEASE CANDIDATE. Separate from simulated transport. No calls at import.
import {createReleaseStore,dispatchGroupedRelease} from "./proposal-store.mjs";
import {RECOVERY_SQL,normalizeRecovery} from "./proposal-dispatch-lab.mjs";
import {isReleaseRealm} from "./proposal-realm.mjs";
import {releaseMode,createGroupedTelegramTransport} from "./proposal-telegram-transport.mjs";
export {normalizeRecovery};
const positive=x=>Number.isSafeInteger(x)&&x>0;
export function createReleaseDispatcher(env,fetchImpl=globalThis.fetch){
 if(!releaseMode(env))return null;
 const db=env.CONTRIBUTORS_DB,store=createReleaseStore(db,"STAGING_CANDIDATE_ONLY");
 const dispatch=async id=>{
  if(!positive(id)||!await isReleaseRealm(db))return {state:"OFF"};
  const send=createGroupedTelegramTransport(env,fetchImpl);
  if(!send)return {state:"OFF"};
  return dispatchGroupedRelease({store,proposalId:id,send,permit:"STAGING_CANDIDATE_ONLY"});
 };
 async function ownerRecovery(actor,raw){
  const b=normalizeRecovery(raw);
  if(!/^[a-f0-9]{64}$/.test(actor?.subject??"")||!/^[a-f0-9]{64}$/.test(actor?.email_tag??""))throw Error("denied");
  if(!await isReleaseRealm(db))return {state:"OFF"};
  if(b.action==="PENDING"&&!createGroupedTelegramTransport(env,fetchImpl))return {state:"OFF"};
  const r=await db.withSession("first-primary").prepare(RECOVERY_SQL[b.action==="PENDING"?"pending":"abandon"]).bind(actor.subject,actor.email_tag,b.id,b.epoch).all();
  if(r?.success!==true||r.meta?.served_by_primary!==true||!Array.isArray(r.results)||r.results.length>1)throw Error("recovery_unknown");
  if(!r.results.length)return {state:"EMPTY"};
  if(b.action==="MARK_UNKNOWN")return {state:"UNKNOWN",proposalId:b.id};
  return dispatch(b.id);
 }
 return Object.freeze({dispatch,ownerRecovery});
}
export function scheduleProposalRelease(ctx,env,id){
 if(!positive(id)||typeof ctx?.waitUntil!=="function")return false;
 try{
  if(!createGroupedTelegramTransport(env))return false;
  const d=createReleaseDispatcher(env);if(!d)return false;
  ctx.waitUntil(d.dispatch(id).catch(()=>{}));return true;
 }catch{return false;}
}
