// V30.19 LAB, authenticated route adapter. Never deploy this candidate.
import {CATALOG,normalizeProposal} from "./proposal-core.mjs";
import {createFixtureStore} from "./proposal-store.mjs";
const HEX=/^[a-f0-9]{64}$/;
const UUID=/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/;
const ownerRead="EXISTS(SELECT 1 FROM lab_owner o CROSS JOIN lab_state s WHERE o.id=1 AND o.subject=?1 AND o.email_tag=?2 AND o.revoked=0 AND s.id=1 AND s.read_enabled=1)";
const ownerWrite=ownerRead.replace("s.read_enabled=1","s.read_enabled=1 AND s.write_enabled=1 AND s.recovery_enabled=0");
const contributorRead="EXISTS(SELECT 1 FROM lab_identities i CROSS JOIN lab_state s WHERE i.subject=?1 AND i.email_tag=?2 AND i.revoked=0 AND s.id=1 AND s.read_enabled=1 AND s.recovery_enabled=0)";
const fields="e.id,e.request_id,e.mapping_id,e.kind,e.period,e.prices_json,e.note,e.received_utc,e.publication_mode,a.mode AS approval_mode,COALESCE(d.action,'PENDING') AS decision,d.origin AS decision_origin,d.reason AS decision_reason,d.decided_utc,COALESCE(q.state,'NOT_QUEUED') AS telegram_state,q.epoch AS telegram_epoch";
const joins=" FROM lab_proposals_v3019 e JOIN lab_proposal_admission_v3019 a ON a.proposal_id=e.id LEFT JOIN lab_proposal_decision_v3019 d ON d.proposal_id=e.id LEFT JOIN lab_proposal_outbox_v3019 q ON q.proposal_id=e.id";
const ownerList="SELECT "+fields+",i.slot"+joins+" JOIN lab_identities i ON i.subject=e.subject AND i.email_tag=e.email_tag WHERE e.id>?3 AND "+ownerRead+" ORDER BY e.id LIMIT 20";
const userList="SELECT "+fields+joins+" WHERE e.subject=?1 AND e.email_tag=?2 AND e.id>?3 AND "+contributorRead+" ORDER BY e.id LIMIT 20";
const userStatus="SELECT "+fields+joins+" WHERE e.subject=?1 AND e.email_tag=?2 AND e.request_id=?3 AND "+contributorRead;
export const PROPOSAL_API_SQL=Object.freeze({
 catalog:"SELECT market,provider,ticker,product,contract FROM lab_level_catalog_v110 WHERE active=1 AND "+contributorRead+" LIMIT 105",
 userList,userStatus,ownerList,
 approval:"SELECT mode,revision FROM lab_approval_policy_v3019 WHERE id=1 AND "+ownerRead,
 change:"UPDATE lab_approval_policy_v3019 SET mode=?3,revision=revision+1 WHERE id=1 AND revision=?4 AND mode<>?3 AND "+ownerWrite+" RETURNING mode,revision",
 review:"INSERT INTO lab_proposal_decision_v3019(proposal_id,action,origin,actor_subject,actor_email_tag,reason) SELECT a.proposal_id,?4,'OWNER',?1,?2,?5 FROM lab_proposal_admission_v3019 a WHERE a.proposal_id=?3 AND a.mode='MANUAL' AND NOT EXISTS(SELECT 1 FROM lab_proposal_decision_v3019 d WHERE d.proposal_id=a.proposal_id) AND "+ownerWrite+" RETURNING proposal_id,action,origin,decided_utc",
 audit:"SELECT id,setting,old_value,new_value,revision,changed_utc FROM lab_policy_audit_v3019 WHERE id>?3 AND "+ownerRead+" ORDER BY id LIMIT 20"
});
function exact(b,fields){return !!b&&Object.getPrototypeOf(b)===Object.prototype&&Object.keys(b).length===fields.length&&fields.every(k=>Object.hasOwn(b,k));}
const existing=CATALOG.filter(x=>x.availability==="V3018_EXISTING");
export function normalizeProposalAction(path,b){
 if(path==="/api/proposals/submit"){
  const p=normalizeProposal(b);
  if(!existing.some(x=>x.id===p.mapping_id))throw Error("mapping_not_verified");
  return p;
 }
 if(path==="/owner/approval/mode"&&exact(b,["mode","revision"])&&["AUTOMATIC","MANUAL"].includes(b.mode)&&Number.isSafeInteger(b.revision)&&b.revision>0)return {mode:b.mode,revision:b.revision};
 if(path==="/owner/proposals/review"&&exact(b,["id","action","reason"])&&Number.isSafeInteger(b.id)&&b.id>0&&["APPROVED","REJECTED"].includes(b.action)&&typeof b.reason==="string"){
  const reason=b.reason.trim();
  if(reason&&[...reason].length<=280&&!/[\u0000-\u001f\u007f-\u009f\uD800-\uDFFF]/u.test(reason))return {id:b.id,action:b.action,reason};
 }
 throw Error("invalid_fields");
}
function tags(actor){if(!HEX.test(actor?.subject??"")||!HEX.test(actor?.email_tag??""))throw Error("denied");return [actor.subject,actor.email_tag];}
function afterId(after){if(!Number.isSafeInteger(after)||after<0)throw Error("invalid_cursor");return after;}
function receipt(row){
 if(!row)return null;
 const {prices_json,...rest}=row,prices=JSON.parse(prices_json);
 if(!Array.isArray(prices)||prices.length<1||prices.length>20||!["APPROVED","REJECTED","PENDING"].includes(rest.decision))throw Error("invalid_receipt");
 return {...rest,reference:"P"+rest.id,prices};
}
export function createProposalApi(db,permit){
 if(permit!=="SYNTHETIC_ONLY"||typeof db?.withSession!=="function")throw Error("LAB_ONLY");
 async function query(key,actor,args=[],max=1){
  const res=await db.withSession("first-primary").prepare(PROPOSAL_API_SQL[key]).bind(...tags(actor),...args).all();
  if(res?.success!==true||res.meta?.served_by_primary!==true||!Array.isArray(res.results)||res.results.length>max)throw Error("storage_unknown");
  return res.results;
 }
 const one=async(k,a,args)=> (await query(k,a,args))[0]??null;
 const status=async(a,id)=>{if(!UUID.test(id??""))throw Error("invalid_request");return receipt(await one("userStatus",a,[id]));};
 return Object.freeze({
  async catalog(actor){
   const active=await query("catalog",actor,[],105);
   if(active.length>=105)throw Error("catalog_bound");
   return existing.filter(m=>active.some(x=>["market","provider","ticker","product","contract"].every(k=>x[k]===m[k]))).map(({id,mode,category,asset,provider})=>({id,mode,category,asset,provider}));
  },
  status,
  async submit(actor,body){
   const p=normalizeProposalAction("/api/proposals/submit",body);
   const saved=await createFixtureStore(db,"OFFLINE_FIXTURE_ONLY").submit(actor,p);
   const row=await status(actor,p.request_id);
   if(!row||row.id!==saved.id)throw Error("outcome_unknown");
   return {...row,replay:saved.replay};
  },
  async history(actor,after=0,owner=false){return (await query(owner?"ownerList":"userList",actor,[afterId(after)],20)).map(receipt);},
  approval:actor=>one("approval",actor),
  change(actor,body){const b=normalizeProposalAction("/owner/approval/mode",body);return one("change",actor,[b.mode,b.revision]);},
  review(actor,body){const b=normalizeProposalAction("/owner/proposals/review",body);return one("review",actor,[b.id,b.action,b.reason]);},
  audit:(actor,after=0)=>query("audit",actor,[afterId(after)],20)
 });
}
