// REMURA Contributors v0.19 LAB — 16/11/2026 01:16 CET
// Synthetic D1 adapter only. NO fetch handler, no routes, no real identity.
// The trusted test caller supplies a fixture actor and server clock.
// Not a deployable service or verification of Cloudflare Access claims.
const FIELDS=["request_id","market","provider","ticker","product","contract","period","kind","price","anchor_utc","observed_utc","note"];
const periods=new Set(["DAY","WEEK","CURRENT_MONTH","PREVIOUS_MONTH"]);
const kinds=new Set(["DELTA_PEAK","EFFORT_RESULT","OTHER_VOLUME_LEVEL"]);
const SQL=Object.freeze({
 gate:"SELECT slot FROM lab_identities WHERE subject=? AND revoked=0 AND EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND enabled=1)",
 existing:"SELECT e.id,e.request_id,e.market,e.provider,e.ticker,e.product,e.contract,e.period,e.kind,e.price,e.anchor_utc,e.observed_utc,e.note FROM lab_entries e JOIN lab_identities i ON i.subject=e.subject AND i.revoked=0 WHERE e.subject=? AND e.request_id=? AND EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND enabled=1)",
 insert:"INSERT INTO lab_entries(subject,request_id,market,provider,ticker,product,contract,period,kind,price,anchor_utc,observed_utc,received_utc,note,source_group) SELECT ?,?,?,?,?,?,?,?,?,?,?,?,?,?,source_group FROM lab_catalog WHERE market=? AND provider=? AND ticker=? AND product=? AND contract=? AND active=1 ON CONFLICT(subject,request_id) DO NOTHING",
 receipts:"SELECT e.id,e.market,e.provider,e.ticker,e.product,e.contract,e.period,e.kind,e.price,e.anchor_utc,e.observed_utc,e.received_utc,e.note,COALESCE((SELECT r.action FROM lab_reviews r WHERE r.entry_id=e.id ORDER BY r.id DESC LIMIT 1),'UNREVIEWED') AS status,(SELECT r.at_utc FROM lab_reviews r WHERE r.entry_id=e.id ORDER BY r.id DESC LIMIT 1) AS reviewed_utc FROM lab_entries e JOIN lab_identities i ON i.subject=e.subject AND i.revoked=0 WHERE e.subject=? AND e.id>? AND EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND enabled=1) ORDER BY e.id LIMIT 20"
});
function validateStamp(s){
 if(typeof s!=="string"||!/^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$/.test(s)||!Number.isFinite(Date.parse(s))||new Date(s).toISOString().replace(".000Z","Z")!==s)throw Error("utc");
 return s;
}
function normalize(p,now){
 if(!p||Object.getPrototypeOf(p)!==Object.prototype||Object.keys(p).length!==FIELDS.length||FIELDS.some(k=>!Object.hasOwn(p,k)||typeof p[k]!=="string"))throw Error("fields");
 if(!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(p.request_id))throw Error("request_id");
 if(!/^[A-Z0-9_]{1,24}$/.test(p.market)||!/^[A-Z0-9_]{1,16}$/.test(p.provider)||!/^[A-Z0-9_.!-]{1,24}$/.test(p.ticker))throw Error("mapping");
 if(!["SPOT","CFD","INDEX","FUTURE"].includes(p.product)||(p.product==="FUTURE"?(!/^[A-Z0-9_.-]{1,24}$/.test(p.contract)||p.ticker.includes("!")):p.contract!==""))throw Error("contract");
 if(!periods.has(p.period)||!kinds.has(p.kind))throw Error("classification");
 let price=p.price.replace(",",".");
 if(!/^(?:0|[1-9][0-9]{0,7})(?:\.[0-9]{1,8})?$/.test(price)||!/[1-9]/.test(price))throw Error("price");
 if(price.includes("."))price=price.replace(/0+$/,"").replace(/\.$/,"");
 if([...p.note].length>280||/[\u0000-\u001f\u007f-\u009f\uD800-\uDFFF]/u.test(p.note))throw Error("note");
 if(validateStamp(p.anchor_utc)>validateStamp(p.observed_utc)||p.observed_utc>validateStamp(now))throw Error("chronology");
 return {...p,price};
}
function subject(actor,synthetic){
 if(synthetic!==true||!actor||Object.getPrototypeOf(actor)!==Object.prototype||actor.role!=="CONTRIBUTOR"||typeof actor.subject!=="string"||!/^fixture-[a-z0-9-]{1,48}$/.test(actor.subject))throw Error("synthetic_actor_only");
 return actor.subject;
}
async function authorized(db,s){
 const row=await db.prepare(SQL.gate).bind(s).first();
 if(!row||!["friend-a","friend-b"].includes(row.slot))throw Error("denied");
}
async function submit(db,actor,p,{now,synthetic=false}={}){
 const s=subject(actor,synthetic),data=normalize(p,now);
 await authorized(db,s);
 const existing=()=>db.prepare(SQL.existing).bind(s,data.request_id).first();
 const check=(row,duplicate)=>{
  if(!row||FIELDS.some(k=>row[k]!==data[k]))throw Error("conflict_or_denied");
  // Acceptance receipt describes original intake; current review state is in receipts().
  return {id:row.id,status:"UNREVIEWED",duplicate};
 };
 const prior=await existing();
 if(prior)return check(prior,true);
 // Guard trigger rechecks live authorization, catalog and caps in the write.
 const w=await db.prepare(SQL.insert).bind(s,data.request_id,data.market,data.provider,data.ticker,data.product,data.contract,data.period,data.kind,data.price,data.anchor_utc,data.observed_utc,now,data.note,data.market,data.provider,data.ticker,data.product,data.contract).run();
 if(w.success!==true||![0,1].includes(w.meta?.changes))throw Error("write_unknown");
 // 0 changes can be a concurrent idempotent replay or inactive mapping.
 return check(await existing(),w.meta.changes===0);
}
async function receipts(db,actor,{after=0,synthetic=false}={}){
 const s=subject(actor,synthetic);
 if(!Number.isSafeInteger(after)||after<0)throw Error("cursor");
 await authorized(db,s);
 const result=await db.prepare(SQL.receipts).bind(s,after).all();
 if(result.success!==true||!Array.isArray(result.results)||result.results.length>20)throw Error("read_unknown");
 return result.results;
}
export {SQL,normalize,submit,receipts};
