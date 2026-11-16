// REMURA Contributors v0.19 LAB — 16/11/2026 01:16 CET
// Synthetic owner-only adapter. NO fetch handler, real identity, network or deploy.
// Trusted fixture caller supplies clock and principal; never use request JSON as actor.
const SQL=Object.freeze({
 ownerGate:"SELECT id FROM lab_owner WHERE id=1 AND subject=? AND revoked=0 AND EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND enabled=1)",
 queue:"SELECT e.id,e.subject,e.market,e.provider,e.ticker,e.product,e.contract,e.period,e.kind,e.price,e.anchor_utc,e.observed_utc,e.received_utc,e.note,e.source_group,COALESCE((SELECT r.action FROM lab_reviews r WHERE r.entry_id=e.id ORDER BY r.id DESC LIMIT 1),'UNREVIEWED') AS status,(SELECT r.at_utc FROM lab_reviews r WHERE r.entry_id=e.id ORDER BY r.id DESC LIMIT 1) AS reviewed_utc FROM lab_entries e WHERE e.id>? AND EXISTS(SELECT 1 FROM lab_owner WHERE id=1 AND subject=? AND revoked=0) AND EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND enabled=1) ORDER BY e.id LIMIT 20",
 history:"SELECT r.action,r.at_utc,r.reason FROM lab_reviews r WHERE r.entry_id=? AND EXISTS(SELECT 1 FROM lab_owner WHERE id=1 AND subject=? AND revoked=0) AND EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND enabled=1) ORDER BY r.id LIMIT 2",
 decision:"INSERT INTO lab_reviews(entry_id,owner,action,at_utc,reason) VALUES(?,?,?,?,?)"
});
function owner(actor,synthetic){
 if(synthetic!==true||!actor||Object.getPrototypeOf(actor)!==Object.prototype||actor.role!=="OWNER"||actor.subject!=="fixture-owner")throw Error("synthetic_owner_only");
 return actor.subject;
}
function entryId(v){if(!Number.isSafeInteger(v)||v<1)throw Error("entry_id");return v;}
function stamp(v){
 if(typeof v!=="string"||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(v)||!Number.isFinite(Date.parse(v))||new Date(v).toISOString().replace(".000Z","Z")!==v)throw Error("utc");
 return v;
}
async function authorized(db,s){const x=await db.prepare(SQL.ownerGate).bind(s).first();if(!x||x.id!==1)throw Error("denied");}
async function bounded(db,sql,args,limit){const x=await db.prepare(sql).bind(...args).all();if(x.success!==true||!Array.isArray(x.results)||x.results.length>limit)throw Error("read_unknown");return x.results;}
async function queue(db,actor,{after=0,synthetic=false}={}){
 const s=owner(actor,synthetic);if(!Number.isSafeInteger(after)||after<0)throw Error("cursor");
 await authorized(db,s);return bounded(db,SQL.queue,[after,s],20);
}
async function history(db,actor,id,{synthetic=false}={}){
 const s=owner(actor,synthetic);entryId(id);await authorized(db,s);return bounded(db,SQL.history,[id,s],2);
}
async function review(db,actor,id,action,{now,reason,synthetic=false}={}){
 const s=owner(actor,synthetic);entryId(id);stamp(now);
 if(!["APPROVED","REJECTED","REVOKED"].includes(action))throw Error("action");
 if(typeof reason!=="string"||!reason.trim()||[...reason].length>280||/[\u0000-\u001f\u007f-\u009f\uD800-\uDFFF]/u.test(reason))throw Error("reason");
 await authorized(db,s);
 // SQL trigger atomically rechecks state, owner, source, chronology, and transition.
 // No retry on ambiguous write; inspect history to reconcile.
 const x=await db.prepare(SQL.decision).bind(id,s,action,now,reason.trim()).run();
 if(x.success!==true||x.meta?.changes!==1)throw Error("write_unknown");
 return {id,action,at_utc:now};
}
export {SQL,queue,history,review};
