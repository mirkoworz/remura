// REMURA Contributors v0.31 LAB — 16/11/2026 09:08 CET
// Offline candidate only. All calls derive identity from trusted Access context, never a client actor.
// No HTTP export, binding configuration or automatic enrollment.
import {accessBinding} from "./access_binding_candidate.mjs";
import {SQL as intake,normalize} from "./d1_lab_adapter.mjs";
import {SQL as reviews} from "./d1_lab_review.mjs";
const SQL=Object.freeze({
 profile:"SELECT 'OWNER' AS role,'owner' AS slot,s.write_enabled,s.read_enabled,s.recovery_enabled FROM lab_owner i CROSS JOIN lab_state s WHERE i.id=1 AND i.subject=? AND i.email_tag=? AND i.revoked=0 AND s.id=1 AND (s.write_enabled=1 OR s.read_enabled=1 OR s.recovery_enabled=1) UNION ALL SELECT 'CONTRIBUTOR',i.slot,s.write_enabled,s.read_enabled,0 FROM lab_identities i CROSS JOIN lab_state s WHERE i.subject=? AND i.email_tag=? AND i.revoked=0 AND s.id=1 AND (s.write_enabled=1 OR s.read_enabled=1)",
 catalog:"SELECT m.market,m.provider,m.ticker,m.product,m.contract FROM lab_catalog m WHERE m.active=1 AND EXISTS(SELECT 1 FROM lab_identities i CROSS JOIN lab_state s WHERE i.subject=? AND i.email_tag=? AND i.revoked=0 AND s.id=1 AND s.write_enabled=1) ORDER BY m.market,m.provider,m.ticker,m.product,m.contract LIMIT 257",
 contributor:"SELECT slot FROM lab_identities WHERE subject=? AND email_tag=? AND revoked=0 AND EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND CASE ? WHEN 'READ' THEN read_enabled WHEN 'WRITE' THEN write_enabled ELSE 0 END=1)",
 owner:"SELECT id FROM lab_owner WHERE id=1 AND subject=? AND email_tag=? AND revoked=0 AND EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND CASE ? WHEN 'READ' THEN read_enabled WHEN 'WRITE' THEN write_enabled WHEN 'RECOVERY' THEN recovery_enabled ELSE 0 END=1)",
 existing:"SELECT e.id,e.request_id,e.market,e.provider,e.ticker,e.product,e.contract,e.period,e.kind,e.price,e.anchor_utc,e.observed_utc,e.note FROM lab_entries e JOIN lab_identities i ON i.subject=e.subject AND i.revoked=0 WHERE e.subject=? AND i.email_tag=? AND e.request_id=? AND EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND write_enabled=1)",
 receipts:"SELECT e.id,e.market,e.provider,e.ticker,e.product,e.contract,e.period,e.kind,e.price,e.anchor_utc,e.observed_utc,e.received_utc,e.note,COALESCE((SELECT r.action FROM lab_reviews r WHERE r.entry_id=e.id ORDER BY r.id DESC LIMIT 1),'UNREVIEWED') AS status,(SELECT r.at_utc FROM lab_reviews r WHERE r.entry_id=e.id ORDER BY r.id DESC LIMIT 1) AS reviewed_utc FROM lab_entries e JOIN lab_identities i ON i.subject=e.subject AND i.revoked=0 WHERE e.subject=? AND i.email_tag=? AND e.id>? AND EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND read_enabled=1) ORDER BY e.id LIMIT 20",
 queue:"SELECT e.id,e.subject,e.market,e.provider,e.ticker,e.product,e.contract,e.period,e.kind,e.price,e.anchor_utc,e.observed_utc,e.received_utc,e.note,e.source_group,COALESCE((SELECT r.action FROM lab_reviews r WHERE r.entry_id=e.id ORDER BY r.id DESC LIMIT 1),'UNREVIEWED') AS status,(SELECT r.at_utc FROM lab_reviews r WHERE r.entry_id=e.id ORDER BY r.id DESC LIMIT 1) AS reviewed_utc FROM lab_entries e WHERE e.id>? AND EXISTS(SELECT 1 FROM lab_owner WHERE id=1 AND subject=? AND email_tag=? AND revoked=0) AND EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND read_enabled=1) ORDER BY e.id LIMIT 20",
 history:"SELECT r.action,r.at_utc,r.reason FROM lab_reviews r WHERE r.entry_id=? AND EXISTS(SELECT 1 FROM lab_owner WHERE id=1 AND subject=? AND email_tag=? AND revoked=0) AND EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND recovery_enabled=1) ORDER BY r.id LIMIT 2",
 revoke:"INSERT INTO lab_identity_revocations(subject,owner,at_utc) SELECT subject,?,? FROM lab_identities WHERE slot=? AND revoked=0 AND EXISTS(SELECT 1 FROM lab_owner WHERE id=1 AND subject=? AND email_tag=? AND revoked=0)"
});
const deny=()=>Error("denied");
function cursor(n,min=0){if(!Number.isSafeInteger(n)||n<min)throw deny();return n;}
function clock(){return new Date().toISOString().replace(/\.\d{3}Z$/,"Z");}
function reasonText(v){if(typeof v!=="string"||!v.trim()||[...v].length>280||/[\u0000-\u001f\u007f-\u009f\uD800-\uDFFF]/u.test(v))throw deny();return v.trim();}
function statement(db,sql,args){
 // Each statement begins a NEW primary-bound session; never accept client bookmarks.
 // No session reuse after auth or mutation; sequential consistency alone is not fresh revocation.
 return db.withSession("first-primary").prepare(sql).bind(...args);
}
async function result(db,sql,args,write=false){
 try{
  const stmt=statement(db,sql,args);
  const x=await (write?stmt.run():stmt.all());
  if(x?.success!==true||x.meta?.served_by_primary!==true)throw deny();
  return x;
 }catch{throw Error(write?"write_unknown_or_denied":"read_unknown_or_denied");}
}
async function rows(db,sql,args,max){
 const x=await result(db,sql,args);
 if(!Array.isArray(x.results)||x.results.length>max)throw deny();
 return x.results;
}
async function gate(ctx,env,owner,mode,expected){
 const a=await accessBinding(ctx,env,expected),db=env.CONTRIBUTORS_DB;
 const found=await rows(db,owner?SQL.owner:SQL.contributor,[a.subject,a.email_tag,mode],1);
 if(found.length!==1||(owner?found[0].id!==1:!["friend-a","friend-b"].includes(found[0].slot)))throw deny();
 return {db,a};
}
async function submit(ctx,env,p,expected){
 const now=clock(),data=normalize(p,now),{db,a}=await gate(ctx,env,false,"WRITE",expected);
 const existing=()=>rows(db,SQL.existing,[a.subject,a.email_tag,data.request_id],1);
 const receipt=(rr,duplicate)=>{
  if(rr.length!==1||Object.keys(data).some(k=>rr[0][k]!==data[k])||!Number.isSafeInteger(rr[0].id)||rr[0].id<1)throw deny();
  return {id:rr[0].id,status:"UNREVIEWED",duplicate};
 };
 const prior=await existing();if(prior.length)return receipt(prior,true);
 const x=await result(db,intake.insert,[a.subject,data.request_id,data.market,data.provider,data.ticker,data.product,data.contract,data.period,data.kind,data.price,data.anchor_utc,data.observed_utc,now,data.note,data.market,data.provider,data.ticker,data.product,data.contract],true);
 if(![0,1].includes(x.meta.changes))throw Error("write_unknown_or_denied");
 // Fresh guarded lookup for idempotent reconciliation, never automatic write retry.
 return receipt(await existing(),x.meta.changes===0);
}
async function receipts(ctx,env,after=0,expected){
 cursor(after);const {db,a}=await gate(ctx,env,false,"READ",expected);
 return rows(db,SQL.receipts,[a.subject,a.email_tag,after],20);
}
async function queue(ctx,env,after=0,expected){
 cursor(after);const {db,a}=await gate(ctx,env,true,"READ",expected);
 return rows(db,SQL.queue,[after,a.subject,a.email_tag],20);
}
async function history(ctx,env,id,expected){
 cursor(id,1);const {db,a}=await gate(ctx,env,true,"RECOVERY",expected);
 return rows(db,SQL.history,[id,a.subject,a.email_tag],2);
}
async function review(ctx,env,id,action,reason,expected){
 cursor(id,1);if(!["APPROVED","REJECTED","REVOKED"].includes(action))throw deny();
 const reasonSafe=reasonText(reason),now=clock(),{db,a}=await gate(ctx,env,true,action==="REVOKED"?"RECOVERY":"WRITE",expected);
 const x=await result(db,reviews.decision,[id,a.subject,action,now,reasonSafe],true);
 if(x.meta.changes!==1)throw Error("write_unknown_or_denied");
 return {id,action,at_utc:now};
}
async function revokeContributor(ctx,env,slot,expected){
 if(!["friend-a","friend-b"].includes(slot))throw deny();
 const now=clock(),{db,a}=await gate(ctx,env,true,"RECOVERY",expected);
 const x=await result(db,SQL.revoke,[a.subject,now,slot,a.subject,a.email_tag],true);
 if(x.meta.changes!==1)throw Error("write_unknown_or_denied");
 return {slot,status:"REVOKED",at_utc:now};
}
async function profile(ctx,env,expected){
 const a=await accessBinding(ctx,env,expected),db=env.CONTRIBUTORS_DB;
 const x=await rows(db,SQL.profile,[a.subject,a.email_tag,a.subject,a.email_tag],1);
 if(x.length!==1)throw deny();
 const r=x[0];
 if(!((r.role==="OWNER"&&r.slot==="owner")||(r.role==="CONTRIBUTOR"&&["friend-a","friend-b"].includes(r.slot)&&r.recovery_enabled===0))||
   ![r.write_enabled,r.read_enabled,r.recovery_enabled].every(v=>v===0||v===1))throw deny();
 return {role:r.role,can_write:r.write_enabled===1,can_read:r.read_enabled===1,can_recover:r.recovery_enabled===1};
}
async function catalog(ctx,env,expected){
 const {db,a}=await gate(ctx,env,false,"WRITE",expected);
 const list=await rows(db,SQL.catalog,[a.subject,a.email_tag],256);
 for(const r of list){
  if(typeof r.market!=="string"||typeof r.provider!=="string"||typeof r.ticker!=="string"||
    !/^[A-Z0-9_]{1,24}$/.test(r.market)||!/^[A-Z0-9_]{1,16}$/.test(r.provider)||!/^[A-Z0-9_.!-]{1,24}$/.test(r.ticker)||
    !["SPOT","CFD","INDEX","FUTURE"].includes(r.product)||typeof r.contract!=="string"||
    (r.product==="FUTURE"?(!/^[A-Z0-9_.-]{1,24}$/.test(r.contract)||r.ticker.includes("!")):r.contract!==""))throw deny();
 }
 return list.map(({market,provider,ticker,product,contract})=>({market,provider,ticker,product,contract}));
}
export {SQL,submit,receipts,queue,history,review,revokeContributor,profile,catalog};
