// V30.19.1 LAB route candidate; explicit synthetic-only gate, NO live Telegram dispatch.
import {createProposalApi,normalizeProposalAction} from "./proposal-api.mjs";
import {PROPOSAL_HTML,PROPOSAL_CSS,PROPOSAL_FORM,PROPOSAL_CORE} from "./proposal-ui-assets.mjs";
import {createLabDispatcher,normalizeRecovery,scheduleProposalLab} from "./proposal-dispatch-lab.mjs";
import {isSyntheticRealm} from "./proposal-realm.mjs";
// REMURA V30.18 staging-only bundle, pinned source 4dc5dd59acac87c1bb9a763dc82a1b15d5b4b6ed
// d1_lab_adapter.mjs git blob d004c3d3177e3e085394209285a44afa011f149c
const __remura_d1_lab_adapter_mjs = (() => {
"use strict";
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


return Object.freeze({SQL:SQL,normalize:normalize,submit:submit,receipts:receipts});
})();
// level_attempt_journal_v076_lab.mjs git blob ea905642f82c752e47ef6b714c2e4a63324e651b
const __remura_level_attempt_journal_v076_lab_mjs = (() => {
"use strict";
// REMURA Contributors v0.76 LAB — 21/11/2026 15:57 CET.
// Original-level durable-attempt candidate: D1-compatible SQL + primary-only sessions.
// NO fetch export, NO migration, NO retries, NO live account usage.
const {normalize : normalizeOriginalLevel} = __remura_d1_lab_adapter_mjs;
const BAD=()=>{throw Error('REMURA_V076_ATTEMPT_DENIED')};
const HEX=/^[a-f0-9]{64}$/;
const UUID=/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/;
const STAMP=/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/;
const DAY=new Set(['DAY','WEEK','CURRENT_MONTH','PREVIOUS_MONTH']);
const FIELDS=['request_id','market','provider','ticker','product','contract','period','kind','price','anchor_utc','observed_utc','note'];
const SQL=Object.freeze({
 permission:"SELECT 1 AS allowed FROM lab_identities i CROSS JOIN lab_state s CROSS JOIN lab_generation g WHERE i.subject=? AND i.email_tag=? AND i.revoked=0 AND s.id=1 AND s.read_enabled=1 AND g.id=1 AND g.generation=? AND g.journal_pin=? LIMIT 1",
 claim:"INSERT INTO lab_new_level_attempts(subject,email_tag,request_id,fingerprint,state,claimed_utc) SELECT ?,?,?,?,'RESERVED',? WHERE EXISTS(SELECT 1 FROM lab_identities i CROSS JOIN lab_state s CROSS JOIN lab_generation g WHERE i.subject=? AND i.email_tag=? AND i.revoked=0 AND s.id=1 AND s.write_enabled=1 AND g.id=1 AND g.generation=? AND g.journal_pin=?)",
 confirm:"UPDATE lab_new_level_attempts SET state='COMMITTED',receipt_id=?,confirmed_utc=? WHERE subject=? AND email_tag=? AND request_id=? AND fingerprint=? AND state='RESERVED' AND EXISTS(SELECT 1 FROM lab_entries e WHERE e.id=? AND e.subject=? AND e.request_id=? AND e.market=? AND e.provider=? AND e.ticker=? AND e.product=? AND e.contract=? AND e.period=? AND e.kind=? AND e.price=? AND e.anchor_utc=? AND e.observed_utc=? AND e.note=?) AND EXISTS(SELECT 1 FROM lab_identities i CROSS JOIN lab_state s CROSS JOIN lab_generation g WHERE i.subject=? AND i.email_tag=? AND i.revoked=0 AND s.id=1 AND s.write_enabled=1 AND g.id=1 AND g.generation=? AND g.journal_pin=?)",
 status:"SELECT a.state,a.request_id,a.receipt_id,e.id AS observed_receipt FROM lab_new_level_attempts a LEFT JOIN lab_entries e ON e.subject=a.subject AND e.request_id=a.request_id JOIN lab_identities i ON i.subject=a.subject AND i.email_tag=a.email_tag AND i.revoked=0 CROSS JOIN lab_state s CROSS JOIN lab_generation g WHERE a.subject=? AND a.email_tag=? AND s.id=1 AND s.read_enabled=1 AND g.id=1 AND g.generation=? AND g.journal_pin=? ORDER BY CASE WHEN a.state='RESERVED' THEN 0 ELSE 1 END,a.rowid DESC LIMIT 1"
});
function strictActor(a){
 if(!a||typeof a!=='object'||!HEX.test(a.subject??'')||!HEX.test(a.email_tag??''))BAD();
}
function primary(env){
 if(!env||env.LEVEL_JOURNAL_V076!=='OFFLINE_FIXTURE_ONLY'||env.STAGING_ENABLED!=='D1_CANDIDATE'||typeof env.CONTRIBUTORS_GENERATION!=='string'||!(/^[a-f0-9]{32}$/).test(env.CONTRIBUTORS_GENERATION)||!HEX.test(env.CONTRIBUTORS_JOURNAL_PIN??''))BAD();
 if(typeof env.CONTRIBUTORS_DB?.withSession!=='function')BAD();
 return env.CONTRIBUTORS_DB.withSession('first-primary');
}
async function exec(env,sql,args,mode){
 const db=primary(env);
 const q=db?.prepare?.(sql)?.bind?.(...args);
 if(!q)BAD();
 const r=mode==='run'?await q.run():await q.all();
 if(!r||r.success!==true||r.meta?.served_by_primary!==true)BAD();
 if(mode==='run'){
  if(!Number.isSafeInteger(r.meta?.changes)||r.meta.changes!==1)BAD();
  return true;
 }
 if(!Array.isArray(r.results)||r.results.length>1)BAD();
 return r.results;
}
function normalizeNewLevelV076(input,now){
 if(!input||Object.getPrototypeOf(input)!==Object.prototype||Object.keys(input).length!==FIELDS.length||FIELDS.some(k=>!Object.hasOwn(input,k)||typeof input[k]!=='string')||!UUID.test(input.request_id))BAD();
 if(!STAMP.test(now??'')||!Number.isFinite(Date.parse(now))||new Date(now).toISOString().slice(0,19)+'Z'!==now)BAD();
 // Reuse the ORIGINAL catalog/price/timestamp contract, not a new permissive validator.
 const output=normalizeOriginalLevel(input,now);
 if(!DAY.has(output.period))BAD();
 return Object.freeze(output);
}
async function newLevelFingerprintV076(level){
 const obj=Object.keys(level).sort().map(k=>[k,level[k]]);
 if(typeof globalThis.crypto?.subtle?.digest!=='function')BAD();
 const raw=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(obj)));
 return Array.from(new Uint8Array(raw),x=>x.toString(16).padStart(2,'0')).join('');
}
async function claimNewLevelV076(env,actor,level,fingerprint,now){
 strictActor(actor);if(!HEX.test(fingerprint??''))BAD();
 await exec(env,SQL.claim,[actor.subject,actor.email_tag,level.request_id,fingerprint,now,actor.subject,actor.email_tag,env.CONTRIBUTORS_GENERATION,env.CONTRIBUTORS_JOURNAL_PIN],'run');
 return Object.freeze({state:'RESERVED',request_id:level.request_id});
}
async function confirmNewLevelV076(env,actor,level,fingerprint,receiptId,now){
 strictActor(actor);if(!HEX.test(fingerprint??'')||!Number.isSafeInteger(receiptId)||receiptId<1)BAD();
 const args=[receiptId,now,actor.subject,actor.email_tag,level.request_id,fingerprint,
  receiptId,actor.subject,level.request_id,
  level.market,level.provider,level.ticker,level.product,level.contract,level.period,level.kind,level.price,level.anchor_utc,level.observed_utc,level.note,
  actor.subject,actor.email_tag,env.CONTRIBUTORS_GENERATION,env.CONTRIBUTORS_JOURNAL_PIN];
 await exec(env,SQL.confirm,args,'run');
 return Object.freeze({state:'COMMITTED',request_id:level.request_id,receipt_id:receiptId});
}
async function inspectNewLevelV076(env,actor){
 strictActor(actor);
 // Empty attempt rows and disabled read access MUST never be conflated.
 const bind=[actor.subject,actor.email_tag,env.CONTRIBUTORS_GENERATION,env.CONTRIBUTORS_JOURNAL_PIN];
 const permit=await exec(env,SQL.permission,bind,'all');
 if(permit.length!==1||permit[0].allowed!==1)BAD();
 const rows=await exec(env,SQL.status,bind,'all');
 if(!rows.length)return Object.freeze({state:'NO_ATTEMPT',request_id:null,receipt_id:null,can_submit:true});
 const x=rows[0];if(typeof x.request_id!=='string'||!UUID.test(x.request_id))BAD();
 if(x.state==='RESERVED'){
  if(x.receipt_id!==null)BAD();
  if(x.observed_receipt===null)return Object.freeze({state:'UNRESOLVED',request_id:x.request_id,receipt_id:null,can_submit:false});
  if(!Number.isSafeInteger(x.observed_receipt)||x.observed_receipt<1)BAD();
  return Object.freeze({state:'COMMITTED_NEEDS_OWNER',request_id:x.request_id,receipt_id:x.observed_receipt,can_submit:false});
 }
 if(x.state==='COMMITTED'&&Number.isSafeInteger(x.receipt_id)&&x.receipt_id>0&&x.receipt_id===x.observed_receipt){
  return Object.freeze({state:'COMMITTED',request_id:x.request_id,receipt_id:x.receipt_id,can_submit:true});
 }
 BAD();
}
const LEVEL_ATTEMPT_SQL_V076=SQL;
const LEVEL_ATTEMPT_V076_INPUT_FIELDS=Object.freeze([...FIELDS]);

return Object.freeze({normalizeNewLevelV076,newLevelFingerprintV076,claimNewLevelV076,confirmNewLevelV076,inspectNewLevelV076,LEVEL_ATTEMPT_SQL_V076,LEVEL_ATTEMPT_V076_INPUT_FIELDS});
})();
// volumetric_catalog_v3013_lab.mjs git blob ec13b30f92b29a0269c6dfd3c02036e8302aacb5
const __remura_volumetric_catalog_v3013_lab_mjs = (() => {
"use strict";
// REMURA V30.13 LAB — offline candidate catalog. Never writes D1 or enables Telegram.
const PLATFORMS = Object.freeze(["ATAS","MOTIVEWAVE"]);
const FEEDS = Object.freeze(["RITHMIC","DXFEED"]);
// Reference roots only, not verified feed-specific tickers or active contracts.
// Currency markets use the native futures quotation, not its reciprocal.
const ROOTS = Object.freeze({
 "6E":Object.freeze({market:"EURUSD",exchange:"CME",forexReference:"EURUSD",inverse:false}),
 "6B":Object.freeze({market:"GBPUSD",exchange:"CME",forexReference:"GBPUSD",inverse:false}),
 "6J":Object.freeze({market:"JPYUSD",exchange:"CME",forexReference:"USDJPY",inverse:true}),
 "6A":Object.freeze({market:"AUDUSD",exchange:"CME",forexReference:"AUDUSD",inverse:false}),
 "6C":Object.freeze({market:"CADUSD",exchange:"CME",forexReference:"USDCAD",inverse:true}),
 "6S":Object.freeze({market:"CHFUSD",exchange:"CME",forexReference:"USDCHF",inverse:true}),
 "6N":Object.freeze({market:"NZDUSD",exchange:"CME",forexReference:"NZDUSD",inverse:false}),
 "GC":Object.freeze({market:"GC",exchange:"COMEX",forexReference:null,inverse:false}),
 "SI":Object.freeze({market:"SI",exchange:"COMEX",forexReference:null,inverse:false}),
 "NQ":Object.freeze({market:"NQ",exchange:"CME",forexReference:null,inverse:false}),
 "ES":Object.freeze({market:"ES",exchange:"CME",forexReference:null,inverse:false}),
 "CL":Object.freeze({market:"CL",exchange:"NYMEX",forexReference:null,inverse:false})
});
function buildCatalogCandidate(input){
 if(!input||!PLATFORMS.includes(input.platform)||!FEEDS.includes(input.feed)||
    !Object.hasOwn(ROOTS,input.root))throw Error("unsupported_source_or_root");
 if(typeof input.ticker!=="string"||!/^[A-Z0-9_.-]{1,24}$/.test(input.ticker)||
    input.ticker===input.root||typeof input.contract!=="string"||
    !/^20[2-9][0-9]-(0[1-9]|1[0-2])$/.test(input.contract))
    throw Error("explicit_contract_and_compatible_ticker_required");
 const ref=ROOTS[input.root];
 // Platform is metadata, not a feed. Do not create two rows for the same feed contract.
 const row=Object.freeze({market:ref.market,provider:input.feed,ticker:input.ticker,
    product:"FUTURE",contract:input.contract,source_group:ref.exchange+"_"+input.root,active:0});
 return Object.freeze({row,platform:input.platform,root:input.root,
    quote:"ORIGINAL_FUTURES",forexReference:ref.forexReference,inverse:ref.inverse,
    status:"NEEDS_OWNER_VERIFICATION",telegramEligible:false});
}

return Object.freeze({PLATFORMS,FEEDS,ROOTS,buildCatalogCandidate});
})();
// continuous_catalog_v3017_lab.mjs git blob 9e8391a6a2face0c209afb418e947b9bf25077e8
const __remura_continuous_catalog_v3017_lab_mjs = (() => {
"use strict";
// REMURA V30.17 LAB — continuous chart selection, not a live data adapter.
// Symbols below are REMURA internal aliases, never feed API symbols.
const {ROOTS,PLATFORMS,FEEDS} = __remura_volumetric_catalog_v3013_lab_mjs;
const CONTINUOUS_CHOICES=Object.freeze(Object.entries(ROOTS).flatMap(([root,ref])=>
 FEEDS.map(feed=>Object.freeze({id:feed+"_"+root+"_CONT",root,feed,
 market:ref.market,exchange:ref.exchange,forexReference:ref.forexReference,
 inverse:ref.inverse,platforms:PLATFORMS,series:"CONTINUOUS",
 sourceTicker:null,adjustment:null,rollMethod:null,activeContract:null,
 enabled:false,telegramEligible:false,scienceEligible:false}))));
function describeContinuous(id){
 const row=CONTINUOUS_CHOICES.find(x=>x.id===id);
 if(!row)throw Error("unknown_continuous_choice");
 return row;
}
// Metadata is not inferred from current calendar, feed, or root.
// A continuous observation is a chart reference, not an executable contract quote.
// Preserve original reported price; no reciprocal conversion or rollover adjustment.
// Before live use, persist a versioned platform/feed profile (actual ticker,
// roll method and adjustment); permit an unknown underlying contract only with
// explicit CONTINUOUS label and keep it excluded from contract-specific science.
// Existing V30.16 intake schema/formatter do not encode this distinction;
// this module intentionally does not generate insert SQL or modify active mappings.

return Object.freeze({CONTINUOUS_CHOICES,describeContinuous});
})();
// continuous_intake_v3018_lab.mjs git blob 44ad3d6a994fc7e0842549156218ad074047b50f
const __remura_continuous_intake_v3018_lab_mjs = (() => {
"use strict";
// V30.18 LAB: explicit chart-observation sentinel within existing additive schema.
// Alias is internal; neither a vendor ticker nor an expiring contract.
const {CONTINUOUS_CHOICES} = __remura_continuous_catalog_v3017_lab_mjs;
const CONTINUOUS_MARKER="CONTINUOUS";
const CONTINUOUS_ROWS=Object.freeze(CONTINUOUS_CHOICES.map(x=>Object.freeze({
 market:x.market,provider:x.feed,ticker:x.root+"_CONT",product:"FUTURE",contract:CONTINUOUS_MARKER,
 source_group:"CHART_ONLY_"+x.exchange+"_"+x.root,active:0
})));
function continuousMapping(row){
 return CONTINUOUS_ROWS.find(x=>["market","provider","ticker","product","contract"].every(k=>x[k]===row?.[k]))??null;
}
function checkContinuousMapping(row){
 const reserved=row?.contract===CONTINUOUS_MARKER||String(row?.ticker??"").endsWith("_CONT");
 if(reserved&&!continuousMapping(row))throw Error("invalid_continuous_mapping");
 return row;
}
function describeChartSeries(row){
 const c=continuousMapping(row);
 if(!c)return null;
 return Object.freeze({root:c.ticker.slice(0,-5),feed:c.provider,
 sourceTicker:null,activeContract:null,adjustment:"UNKNOWN",rollMethod:"UNKNOWN",
 quote:"MANUAL_CHART_OBSERVATION",scienceEligible:false});
}

return Object.freeze({CONTINUOUS_MARKER,CONTINUOUS_ROWS,continuousMapping,checkContinuousMapping,describeChartSeries});
})();
// telegram_message_v3011_lab.mjs git blob 40f3e3619aca8e5f8d8c902afcbeefa3d2abf909
const __remura_telegram_message_v3011_lab_mjs = (() => {
"use strict";
// REMURA V30.11 Telegram Bridge LAB. Pure message builder, no network.
const {checkContinuousMapping,describeChartSeries} = __remura_continuous_intake_v3018_lab_mjs;
const periods = Object.freeze({DAY:"Giornaliero",WEEK:"Settimanale",CURRENT_MONTH:"Mese corrente",PREVIOUS_MONTH:"Mese precedente"});
const kinds = Object.freeze({DELTA_PEAK:"Picco Delta",EFFORT_RESULT:"Effort / Result",OTHER_VOLUME_LEVEL:"Altro livello volumetrico"});
const flags = Object.freeze({EUR:"🇪🇺",USD:"🇺🇸",GBP:"🇬🇧",JPY:"🇯🇵",CHF:"🇨🇭",CAD:"🇨🇦",AUD:"🇦🇺",NZD:"🇳🇿"});
const stamp = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/;
function prepareTelegramMessage(event, policy = {}) {
  // Server-internal input only; never derive identity or test status from client.
  // A persistent, unique receipt outbox must enforce deduplication before any send.
  if (policy.enabled !== true || event?.state !== "COMMITTED" ||
      event.newCanonical !== true || event.test !== false ||
      !["friend-b","friend-c"].includes(event.slot)) return null;
  const r=event.receipt;
  if (!r || !Number.isSafeInteger(r.id) || r.id < 1 ||
      !Number.isSafeInteger(policy.startAfterReceipt) || policy.startAfterReceipt < 0 ||
      r.id <= policy.startAfterReceipt || typeof r.note !== "string" ||
      /\b(?:TEST|COLLAUDO|NON[ -]OPERATIVO)\b/i.test(r.note)) return null;
  if (typeof r.market !== "string" || !/^[A-Z0-9_]{1,24}$/.test(r.market) ||
      typeof r.provider !== "string" || !/^[A-Z0-9_]{1,16}$/.test(r.provider) ||
      typeof r.ticker !== "string" || !/^[A-Z0-9_.!-]{1,24}$/.test(r.ticker) ||
      typeof r.contract !== "string" || !/^[A-Z0-9_.-]{0,24}$/.test(r.contract) ||
      !["SPOT","CFD","FUTURE","INDEX"].includes(r.product) ||
      (r.product === "FUTURE" ? !r.contract || r.ticker.includes("!") : r.contract !== "") ||
      r.provider === "ECB") return null;
  // Explicit OWNER-reviewed authentic volumetric mappings; empty by default.
  const mapping=[r.market,r.provider,r.ticker,r.product,r.contract];
  if (!Array.isArray(policy.allowedMappings) || !policy.allowedMappings.some(x =>
      Array.isArray(x) && x.length===5 && x.every((v,i)=>v===mapping[i]))) return null;
  if (!Object.hasOwn(periods,r.period) || !Object.hasOwn(kinds,r.kind) ||
      typeof r.price !== "string" || !/^(?:0|[1-9][0-9]{0,7})(?:\.[0-9]{1,8})?$/.test(r.price) ||
      !/[1-9]/.test(r.price) || typeof r.received_utc !== "string" ||
      !stamp.test(r.received_utc) || !Number.isFinite(Date.parse(r.received_utc)) ||
      new Date(r.received_utc).toISOString().replace(".000Z","Z") !== r.received_utc) return null;
  let chart;
  try{checkContinuousMapping(r);chart=describeChartSeries(r);}catch{return null;}
  const a=r.market.slice(0,3),b=r.market.slice(3);
  const market=flags[a] && flags[b] ? flags[a]+" "+flags[b]+" "+a+"/"+b : "📊 "+r.market;
  const time=new Intl.DateTimeFormat("it-IT",{timeZone:"Europe/Rome",dateStyle:"short",timeStyle:"medium"}).format(new Date(r.received_utc));
  return Object.freeze({receiptId:r.id,text:[
    "🦈 REMURA | NUOVO LIVELLO", "",market,(chart?"🎯 Prezzo originale del grafico: ":"🎯 Livello: ")+r.price,
    "📊 Metodologia: "+kinds[r.kind],"⏳ Periodo: "+periods[r.period],
    chart?"📡 Feed dichiarato: "+chart.feed+" · "+chart.root:"📡 Fonte dati: "+r.provider+" · "+r.ticker+(r.contract?" · "+r.contract:""),
    ...(chart?["🔄 Grafico continuativo · contratto e adeguamento non verificati","⚠️ Riferimento grafico, non prezzo di un contratto eseguibile"]:[]),
    "🕒 Ricevuto: "+time+" (Roma)","👤 REMURA Contributor",
    "📌 Rif. #"+r.id+" · Non ancora esaminato dall’OWNER"
  ].join("\n")});
}

return Object.freeze({prepareTelegramMessage});
})();
// telegram_dispatch_v3012_lab.mjs git blob ea5b993a67ac846da95ace09f6cd61557255fa7b
const __remura_telegram_dispatch_v3012_lab_mjs = (() => {
"use strict";
// REMURA V30.12 LAB. One bounded dispatch. No live fetch by default.
const {prepareTelegramMessage} = __remura_telegram_message_v3011_lab_mjs;
const SQL=Object.freeze({
 claim:`UPDATE lab_telegram_outbox_v3012 SET state='SENDING',claimed_utc=?1
 WHERE receipt_id=(
 SELECT o.receipt_id FROM lab_telegram_outbox_v3012 o
 JOIN lab_telegram_policy_v3012 p ON p.id=1 AND p.enabled=1 AND p.epoch=o.epoch
 JOIN lab_state s ON s.id=1 AND s.read_enabled=1 AND s.write_enabled=1 AND s.recovery_enabled=0
 WHERE o.state='PENDING' AND (?2 IS NULL OR o.receipt_id=?2)
 AND (?3 IS NULL OR o.epoch=?3) AND (?4 IS NULL OR o.queued_utc>=?4)
 AND (?5 IS NULL OR EXISTS(SELECT 1 FROM lab_owner i WHERE i.id=1 AND i.subject=?5 AND i.email_tag=?6 AND i.revoked=0))
 ORDER BY o.receipt_id LIMIT 1)
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
 AND e.publication_mode='TELEGRAM' AND i.slot IN('friend-b','friend-c')`,
 finish:`UPDATE lab_telegram_outbox_v3012 SET state=?2,finished_utc=?3,telegram_message_id=?4
 WHERE receipt_id=?1 AND state='SENDING' RETURNING receipt_id`
});
const utc=()=>new Date().toISOString().slice(0,19)+"Z";
async function one(db,sql,args){
 const result=await db.withSession("first-primary").prepare(sql).bind(...args).all();
 if(result?.success!==true||result.meta?.served_by_primary!==true||!Array.isArray(result.results)||result.results.length>1)
 throw Error("telegram_storage_unavailable");
 return result.results[0]??null;
}
function createTelegramOutbox(db){
 return Object.freeze({
 claim:(now,receiptId=null,recovery=null)=>one(db,SQL.claim,[now,receiptId,recovery?.epoch??null,recovery?.cutoff??null,recovery?.actor?.subject??null,recovery?.actor?.email_tag??null]),
 load:claim=>one(db,SQL.load,[claim.receipt_id,claim.epoch]),
 async finish(id,state,now,messageId=null){
  if(!await one(db,SQL.finish,[id,state,now,messageId]))throw Error("telegram_finish_unavailable");
 }
 });
}
// Only an explicitly provided transport can send; synthetic tests inject a fake.
// A claimed receipt is never automatically requeued, including on timeout/crash.
async function dispatchOne({store,send,enabled=false,clock=utc,receiptId=null,recovery=null}={}){
 if(enabled!==true||typeof send!=="function")return {state:"OFF"};
 if(receiptId!==null&&(!Number.isSafeInteger(receiptId)||receiptId<1))return {state:"BLOCKED"};
 if(receiptId===null&&(!recovery||!Number.isSafeInteger(recovery.epoch)||recovery.epoch<1||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(recovery.cutoff??'')||!/^[a-f0-9]{64}$/.test(recovery.actor?.subject??'')||!/^[a-f0-9]{64}$/.test(recovery.actor?.email_tag??'')))return {state:'BLOCKED'};
 let claim;
 try{claim=await store.claim(clock(),receiptId,recovery);}catch{return {state:"CLAIM_UNKNOWN"};}
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


return Object.freeze({TELEGRAM_OUTBOX_SQL:SQL,createTelegramOutbox,dispatchOne});
})();
// telegram_transport_v3012_lab.mjs git blob bb1d1b3b5f9433d0a635da3d2ff10a7d332e9f73
const __remura_telegram_transport_v3012_lab_mjs = (() => {
"use strict";
// REMURA V30.12 LAB. Outbound-only Telegram API; no polling or inbound webhook.
const {createTelegramOutbox,dispatchOne} = __remura_telegram_dispatch_v3012_lab_mjs;
function createTelegramTransport(env, fetchImpl=globalThis.fetch){
 const token=env?.TELEGRAM_BOT_TOKEN, chat=env?.TELEGRAM_CHAT_ID;
 if(env?.TELEGRAM_BRIDGE_V3012!=="EXPLICIT_STAGING_ONLY" ||
    typeof token!=="string" || !/^[0-9]{5,20}:[A-Za-z0-9_-]{20,100}$/.test(token) ||
    typeof chat!=="string" || !/^-[1-9][0-9]{0,15}$/.test(chat) ||
    !Number.isSafeInteger(Number(chat)) || typeof fetchImpl!=="function")return null;
 return async text=>{
  if(typeof text!=="string"||!text||text.length>3500)return {ok:false};
  const controller=new AbortController();
  const timeout=setTimeout(()=>controller.abort(),8000);
  try{
   const res=await fetchImpl("https://api.telegram.org/bot"+token+"/sendMessage",{
    method:"POST",redirect:"error",signal:controller.signal,
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({chat_id:chat,text,link_preview_options:{is_disabled:true}})
   });
   if(!res.ok)return {ok:false};
   const reply=await res.json();
   if(reply?.ok!==true||String(reply.result?.chat?.id)!==chat||
      !Number.isSafeInteger(reply.result?.message_id)||reply.result.message_id<1)return {ok:false};
   return {ok:true,messageId:reply.result.message_id};
  }catch{return {ok:false};}
  finally{clearTimeout(timeout);}
 };
}
function scheduleTelegramAfterSubmit(ctx,env,result,profile){
 // COMMITTED can also be a replay: durable outbox claim, not this hook, prevents duplicate sends.
 if(!["friend-b","friend-c"].includes(profile?.slot)||result?.state!=="COMMITTED"||
    !Number.isSafeInteger(result.receipt?.id)||result.receipt.id<1||
    typeof ctx?.waitUntil!=="function")return;
 const send=createTelegramTransport(env);
 if(!send)return;
 // Never alter the contributor's response because Telegram failed.
 try{ctx.waitUntil(dispatchOne({store:createTelegramOutbox(env.CONTRIBUTORS_DB),send,enabled:true,
    receiptId:result.receipt.id}).catch(()=>{}));}catch{}
}

return Object.freeze({createTelegramTransport,scheduleTelegramAfterSubmit});
})();
// telegram_owner_v3015_lab.mjs git blob e698e81afba0fe9a15e5ff573c737463351010c5
const __remura_telegram_owner_v3015_lab_mjs = (() => {
"use strict";
// REMURA V30.15 LAB. OWNER-only Telegram policy, no credentials in responses.
const ownerRead=`EXISTS(SELECT 1 FROM lab_owner i CROSS JOIN lab_state s
 WHERE i.id=1 AND i.subject=?1 AND i.email_tag=?2 AND i.revoked=0
 AND s.id=1 AND s.read_enabled=1)`;
const ownerWrite=`EXISTS(SELECT 1 FROM lab_owner i CROSS JOIN lab_state s
 WHERE i.id=1 AND i.subject=?1 AND i.email_tag=?2 AND i.revoked=0
 AND s.id=1 AND s.read_enabled=1 AND s.write_enabled=1 AND s.recovery_enabled=0)`;
const TELEGRAM_OWNER_SQL=Object.freeze({
 read:`SELECT enabled,epoch,start_after_receipt FROM lab_telegram_policy_v3012 WHERE id=1 AND ${ownerRead}`,
 change:`UPDATE lab_telegram_policy_v3012
 SET enabled=?3,epoch=epoch+CASE WHEN ?3=1 THEN 1 ELSE 0 END,
 start_after_receipt=CASE WHEN ?3=1 THEN (SELECT COALESCE(MAX(id),0) FROM lab_level_attempts_v110) ELSE start_after_receipt END
 WHERE id=1 AND enabled=1-?3 AND epoch=?4 AND ${ownerWrite}
 AND (?3=0 OR EXISTS(SELECT 1 FROM lab_telegram_sources_v3012 m JOIN lab_level_catalog_v110 c
 USING(market,provider,ticker,product,contract) WHERE c.active=1))
 RETURNING enabled,epoch,start_after_receipt`
});
async function query(db,sql,actor,extra=[]){
 if(!/^[a-f0-9]{64}$/.test(actor?.subject??'')||!/^[a-f0-9]{64}$/.test(actor?.email_tag??''))throw Error('telegram_denied');
 const r=await db.withSession('first-primary').prepare(sql).bind(actor.subject,actor.email_tag,...extra).all();
 if(r?.success!==true||r.meta?.served_by_primary!==true||!Array.isArray(r.results)||r.results.length>1)throw Error('telegram_unavailable');
 const row=r.results[0];
 if(!row)return null;
 if(![0,1].includes(row.enabled)||!Number.isSafeInteger(row.epoch)||row.epoch<1||
 !Number.isSafeInteger(row.start_after_receipt)||row.start_after_receipt<0)throw Error('telegram_unavailable');
 return row;
}
function readTelegramPolicy(db,actor){return query(db,TELEGRAM_OWNER_SQL.read,actor);}
function changeTelegramPolicy(db,actor,body){
 if(typeof body?.enabled!=='boolean'||!Number.isSafeInteger(body.epoch)||body.epoch<1)throw Error('telegram_invalid');
 return query(db,TELEGRAM_OWNER_SQL.change,actor,[Number(body.enabled),body.epoch]);
}

return Object.freeze({TELEGRAM_OWNER_SQL,readTelegramPolicy,changeTelegramPolicy});
})();
// telegram_recovery_v3016_lab.mjs git blob b340e18b522babd532abbf156574d7b661789e8b
const __remura_telegram_recovery_v3016_lab_mjs = (() => {
"use strict";
// REMURA V30.16 LAB: one OWNER-requested recovery, never retry an ambiguous send.
const {createTelegramTransport} = __remura_telegram_transport_v3012_lab_mjs;
const {createTelegramOutbox,dispatchOne} = __remura_telegram_dispatch_v3012_lab_mjs;
async function recoverTelegramPending({env,actor,epoch,now=Date.now(),sendFactory=createTelegramTransport,storeFactory=createTelegramOutbox}){
 if(!Number.isSafeInteger(epoch)||epoch<1||!Number.isFinite(now)||
 !/^[a-f0-9]{64}$/.test(actor?.subject??"")||!/^[a-f0-9]{64}$/.test(actor?.email_tag??""))return {state:"BLOCKED"};
 const send=sendFactory(env);
 if(!send)return {state:"OFF"};
 const cutoff=new Date(now-15*60*1000).toISOString().slice(0,19)+"Z";
 return dispatchOne({store:storeFactory(env.CONTRIBUTORS_DB),send,enabled:true,recovery:{epoch,cutoff,actor}});
}

return Object.freeze({recoverTelegramPending});
})();
// staging_levels_store_v110_lab.mjs git blob 842382b932ce3336da4b94ae05efc16bfd36fe22
const __remura_staging_levels_store_v110_lab_mjs = (() => {
"use strict";
// REMURA Contributors v1.10 LAB. Every statement starts on D1 primary.
// The Worker supplies freshly verified Access HMAC tags, never client identity fields.
const { normalizeNewLevelV076, newLevelFingerprintV076 } = __remura_level_attempt_journal_v076_lab_mjs;

const normalizeLevelV110 = normalizeNewLevelV076;
const pageSize = 20;
const hash = /^[a-f0-9]{64}$/;
const requestKey = /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/;
const contributorSlots = ['friend-a', 'friend-b', 'friend-c'];

class LevelsStoreError extends Error {
  constructor(code) {
    super(code);
    this.code = code;
  }
}

const contributorRead = `SELECT 1 FROM lab_identities i CROSS JOIN lab_state s
  WHERE i.subject=?1 AND i.email_tag=?2 AND i.revoked=0 AND s.id=1 AND s.read_enabled=1`;
const contributorWrite = `${contributorRead} AND s.write_enabled=1`;
const ownerRead = `SELECT 1 FROM lab_owner i CROSS JOIN lab_state s
  WHERE i.id=1 AND i.subject=?1 AND i.email_tag=?2 AND i.revoked=0 AND s.id=1 AND s.read_enabled=1`;
const ownerWrite = `${ownerRead} AND s.write_enabled=1`;
const unenrolled = `NOT EXISTS(SELECT 1 FROM lab_owner WHERE subject=?1 OR email_tag=?2)
  AND NOT EXISTS(SELECT 1 FROM lab_identities WHERE subject=?1 OR email_tag=?2)`;
const joinEnabled = `EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND read_enabled=1 AND write_enabled=1)`;
const receiptFields = `e.id,e.market,e.provider,e.ticker,e.product,e.contract,e.period,e.kind,e.price,
  e.anchor_utc,e.observed_utc,e.received_utc,e.note,e.publication_mode,COALESCE(d.action,'UNREVIEWED') AS status,d.at_utc AS reviewed_utc`;
const intakeCandidate = `SELECT ?3 AS request_id,?4 AS fingerprint,?5 AS market,?6 AS provider,
  ?7 AS ticker,?8 AS product,?9 AS contract,?10 AS period,?11 AS kind,?12 AS price,
  ?13 AS anchor_utc,?14 AS observed_utc,?15 AS received_utc,?16 AS note,?17 AS publication_mode`;

const SQL = Object.freeze({
  profile: `
    SELECT 'OWNER' AS role,'owner' AS slot,s.read_enabled,s.write_enabled,s.recovery_enabled
    FROM lab_owner i CROSS JOIN lab_state s
    WHERE i.id=1 AND i.subject=?1 AND i.email_tag=?2 AND i.revoked=0 AND s.id=1
    UNION ALL
    SELECT 'CONTRIBUTOR',i.slot,s.read_enabled,s.write_enabled,0
    FROM lab_identities i CROSS JOIN lab_state s
    WHERE i.subject=?1 AND i.email_tag=?2 AND i.revoked=0 AND s.id=1`,
  catalog: `
    SELECT market,provider,ticker,product,contract FROM lab_level_catalog_v110
    WHERE active=1 AND EXISTS(${contributorRead})
    ORDER BY market,provider,ticker,product,contract LIMIT 257`,
  receipts: `
    SELECT ${receiptFields}
    FROM lab_level_attempts_v110 e
    LEFT JOIN lab_activity_v110 d ON d.entry_id=e.id
    WHERE e.subject=?1 AND e.email_tag=?2 AND e.duplicate_of IS NULL AND e.id>?3
     AND EXISTS(${contributorRead}) ORDER BY e.id LIMIT 20`,
  lookup: `
    WITH permit AS (${contributorRead})
    SELECT ${receiptFields},a.fingerprint,(a.duplicate_of IS NOT NULL) AS is_duplicate
    FROM permit
    LEFT JOIN lab_level_attempts_v110 a ON a.subject=?1 AND a.email_tag=?2 AND a.request_id=?3
    LEFT JOIN lab_level_attempts_v110 e ON e.id=COALESCE(a.duplicate_of,a.id)
     AND e.subject=?1 AND e.email_tag=?2 AND e.duplicate_of IS NULL
    LEFT JOIN lab_activity_v110 d ON d.entry_id=e.id`,
  submit: `
    WITH candidate AS (${intakeCandidate})
    INSERT INTO lab_level_attempts_v110(
     subject,email_tag,request_id,fingerprint,market,provider,ticker,product,contract,
     period,kind,price,anchor_utc,observed_utc,received_utc,note,source_group,duplicate_of,publication_mode)
    SELECT ?1,?2,n.request_id,n.fingerprint,n.market,n.provider,n.ticker,n.product,n.contract,
     n.period,n.kind,n.price,n.anchor_utc,n.observed_utc,n.received_utc,n.note,c.source_group,p.id,n.publication_mode
    FROM candidate n JOIN lab_level_catalog_v110 c USING(market,provider,ticker,product,contract)
    LEFT JOIN lab_level_attempts_v110 p
     ON p.subject=?1 AND p.email_tag=?2 AND p.duplicate_of IS NULL
     AND (p.market,p.provider,p.ticker,p.product,p.contract,p.period,p.kind,p.price,p.anchor_utc)=
         (n.market,n.provider,n.ticker,n.product,n.contract,n.period,n.kind,n.price,n.anchor_utc)
    WHERE c.active=1 AND EXISTS(${contributorWrite})
     AND NOT EXISTS(SELECT 1 FROM lab_level_attempts_v110 WHERE subject=?1 AND request_id=n.request_id)
     AND (p.id IS NOT NULL OR NOT EXISTS(
      SELECT 1 FROM lab_level_attempts_v110 e WHERE e.subject=?1 AND e.duplicate_of IS NULL
      AND e.received_utc BETWEEN substr(n.received_utc,1,10)||'T00:00:00Z'
                             AND substr(n.received_utc,1,10)||'T23:59:59Z'
      LIMIT 1 OFFSET 19
     ))
     AND NOT EXISTS(
      SELECT 1 FROM lab_level_attempts_v110 e WHERE e.subject=?1
      AND e.received_utc BETWEEN substr(n.received_utc,1,10)||'T00:00:00Z'
                             AND substr(n.received_utc,1,10)||'T23:59:59Z'
      LIMIT 1 OFFSET 59
     )
    RETURNING id`,
  submitUnavailable: `
    SELECT CASE WHEN NOT EXISTS(${contributorWrite}) THEN 'denied'
     WHEN NOT EXISTS(SELECT 1 FROM lab_level_catalog_v110
      WHERE market=?3 AND provider=?4 AND ticker=?5 AND product=?6 AND contract=?7 AND active=1)
     THEN 'invalid_mapping' ELSE 'capacity' END AS code`,
  pending: `
    SELECT ${receiptFields},i.slot FROM lab_level_pending_v110 p
    JOIN lab_level_attempts_v110 e ON e.id=p.entry_id
    JOIN lab_identities i ON i.subject=e.subject AND i.email_tag=e.email_tag
    LEFT JOIN lab_activity_v110 d ON d.entry_id=e.id
    WHERE p.entry_id>?3 AND e.duplicate_of IS NULL AND d.id IS NULL AND EXISTS(${ownerRead})
    ORDER BY p.entry_id LIMIT 20`,
  history: `
    SELECT ${receiptFields},i.slot FROM lab_activity_v110 d
    JOIN lab_level_attempts_v110 e ON e.id=d.entry_id
    JOIN lab_identities i ON i.subject=e.subject AND i.email_tag=e.email_tag
    WHERE d.entry_id>?3 AND e.duplicate_of IS NULL AND EXISTS(${ownerRead})
    ORDER BY d.entry_id LIMIT 20`,
  audit: `
    SELECT id,entry_id,slot,action,at_utc,reason FROM lab_activity_v110
    WHERE id>?3 AND EXISTS(${ownerRead}) ORDER BY id LIMIT 20`,
  review: `
    INSERT INTO lab_activity_v110(entry_id,action,at_utc,reason)
    SELECT e.id,?4,?5,?6 FROM lab_level_attempts_v110 e
    WHERE e.id=?3 AND e.duplicate_of IS NULL AND e.received_utc<=?5 AND EXISTS(${ownerWrite})
     AND NOT EXISTS(SELECT 1 FROM lab_activity_v110 d WHERE d.entry_id=e.id)
     AND (?4='REJECTED' OR EXISTS(
      SELECT 1 FROM lab_identities i JOIN lab_level_catalog_v110 c
      ON (c.market,c.provider,c.ticker,c.product,c.contract)=(e.market,e.provider,e.ticker,e.product,e.contract)
      WHERE i.subject=e.subject AND i.email_tag=e.email_tag AND i.revoked=0
       AND c.active=1 AND c.source_group=e.source_group
     ))
    RETURNING entry_id AS id,action,at_utc`,
  slots: `
    SELECT slot,status FROM lab_slot_status_v110 WHERE EXISTS(${ownerRead}) ORDER BY slot`,
  slotRevision: `
    SELECT revision FROM lab_slot_status_v110 WHERE slot=?3 AND EXISTS(${ownerRead})`,
  getInvite: `
    SELECT slot,revision FROM lab_slot_status_v110
    WHERE status='INVITED' AND invite_email_tag=?2 AND ${unenrolled} AND ${joinEnabled}`,
  invite: `
    INSERT INTO lab_activity_v110(slot,action,at_utc,invite_email_tag)
    SELECT slot,'INVITED',?5,?4 FROM lab_slot_status_v110
    WHERE slot=?3 AND status='VACANT' AND revision=?6 AND EXISTS(${ownerWrite})
     AND NOT EXISTS(SELECT 1 FROM lab_slot_status_v110 WHERE invite_email_tag=?4)
     AND NOT EXISTS(SELECT 1 FROM lab_owner WHERE email_tag=?4)
     AND NOT EXISTS(SELECT 1 FROM lab_identities WHERE email_tag=?4)
    RETURNING slot,'INVITED' AS status,at_utc`,
  withdraw: `
    INSERT INTO lab_activity_v110(slot,action,at_utc)
    SELECT slot,'WITHDRAWN',?4 FROM lab_slot_status_v110
    WHERE slot=?3 AND status='INVITED' AND revision=?5 AND EXISTS(${ownerWrite})
    RETURNING slot,'VACANT' AS status,at_utc`,
  enroll: `
    INSERT INTO lab_activity_v110(slot,action,at_utc,invite_email_tag,enrollment_subject)
    SELECT slot,'ENROLLED',?3,?2,?1 FROM lab_slot_status_v110
    WHERE status='INVITED' AND invite_email_tag=?2 AND revision=?4
     AND ${unenrolled} AND ${joinEnabled}
    RETURNING slot,'ACTIVE' AS status,at_utc`,
  revoke: `
    INSERT INTO lab_activity_v110(slot,action,at_utc)
    SELECT slot,'REVOKED',?4 FROM lab_slot_status_v110
    WHERE slot=?3 AND status='ACTIVE' AND revision=?5 AND EXISTS(${ownerWrite})
    RETURNING slot,'REVOKED' AS status,at_utc`
});

function tags(actor) {
  if (!hash.test(actor?.subject ?? '') || !hash.test(actor?.email_tag ?? '')) {
    throw new LevelsStoreError('denied');
  }
  return [actor.subject, actor.email_tag];
}

function cursor(value, min = 0) {
  if (!Number.isSafeInteger(value) || value < min) throw new LevelsStoreError('invalid_input');
  return value;
}

function slot(value, allowPermanent = true) {
  if (!contributorSlots.includes(value) || (!allowPermanent && value === 'friend-a')) {
    throw new LevelsStoreError('invalid_input');
  }
  return value;
}

function reasonText(value) {
  if (typeof value !== 'string' || !value.trim() || [...value].length > 280 ||
    /[\u0000-\u001f\u007f-\u009f\uD800-\uDFFF]/u.test(value)) {
    throw new LevelsStoreError('invalid_input');
  }
  return value.trim();
}

function outcome(row) {
  const { fingerprint, is_duplicate, ...receipt } = row;
  if (receipt.id === null) return { state: 'NOT_FOUND' };
  if (!Number.isSafeInteger(receipt.id) || receipt.id < 1 ||
    !hash.test(fingerprint ?? '') || ![0, 1].includes(is_duplicate)) {
    throw new Error('levels_store_unavailable');
  }
  return { state: is_duplicate === 1 ? 'DUPLICATE' : 'COMMITTED', receipt };
}

function createLevelsStoreV110(db) {
  async function rows(key, args, max = 1) {
    const result = await db.withSession('first-primary').prepare(SQL[key]).bind(...args).all();
    if (result?.success !== true || result.meta?.served_by_primary !== true ||
      !Array.isArray(result.results) || result.results.length > max) {
      throw new Error('levels_store_unavailable');
    }
    return result.results;
  }

  async function single(key, args) {
    return (await rows(key, args))[0] ?? null;
  }

  async function lookupRecord(actor, requestId) {
    if (!requestKey.test(requestId ?? '')) throw new LevelsStoreError('invalid_input');
    const row = await single('lookup', [...tags(actor), requestId]);
    if (!row) throw new LevelsStoreError('denied');
    return row;
  }

  function listPage(key, actor, after) {
    return rows(key, [...tags(actor), cursor(after)], pageSize);
  }

  return Object.freeze({
    async profile(actor) {
      const row = await single('profile', tags(actor));
      if (!row) return null;
      const validRole = row.role === 'OWNER' && row.slot === 'owner' ||
        row.role === 'CONTRIBUTOR' && contributorSlots.includes(row.slot) && row.recovery_enabled === 0;
      if (!validRole || ![row.read_enabled, row.write_enabled, row.recovery_enabled].every(bit => bit === 0 || bit === 1)) {
        throw new Error('levels_store_unavailable');
      }
      return {
        role: row.role,
        slot: row.slot,
        can_read: row.read_enabled === 1,
        can_write: row.write_enabled === 1,
        can_recover: row.recovery_enabled === 1
      };
    },
    catalog: actor => rows('catalog', tags(actor), 256),
    receipts: (actor, after = 0) => listPage('receipts', actor, after),
    queue: (actor, after = 0) => listPage('pending', actor, after),
    history: (actor, after = 0) => listPage('history', actor, after),
    audit: (actor, after = 0) => listPage('audit', actor, after),
    slots: actor => rows('slots', tags(actor), 3),
    async slotRevision(actor, targetSlot) {
      const row = await single('slotRevision', [...tags(actor), slot(targetSlot)]);
      if (!row) throw new LevelsStoreError('denied');
      return cursor(row.revision);
    },
    getInvite: actor => single('getInvite', tags(actor)),
    invite(actor, targetSlot, emailTag, now, revision) {
      if (!hash.test(emailTag ?? '')) throw new LevelsStoreError('invalid_input');
      return single('invite', [...tags(actor), slot(targetSlot, false), emailTag, now, cursor(revision)]);
    },
    withdraw: (actor, targetSlot, now, revision) =>
      single('withdraw', [...tags(actor), slot(targetSlot, false), now, cursor(revision)]),
    enroll: (actor, now, revision) => single('enroll', [...tags(actor), now, cursor(revision)]),
    revoke: (actor, { slot: targetSlot }, now, revision) =>
      single('revoke', [...tags(actor), slot(targetSlot), now, cursor(revision)]),
    review(actor, { id, action, reason }, now) {
      if (!['APPROVED', 'REJECTED'].includes(action)) throw new LevelsStoreError('invalid_input');
      return single('review', [...tags(actor), cursor(id, 1), action, now, reasonText(reason)]);
    },
    async lookup(actor, requestId) {
      return outcome(await lookupRecord(actor, requestId));
    },
    async submit(actor, level, now, publication_mode='PRIVATE') {
      if(!['PRIVATE','TEST','TELEGRAM'].includes(publication_mode))throw new LevelsStoreError('invalid_input');
      const identity = tags(actor);
      const { request_id, market, provider, ticker, product, contract, period, kind, price, anchor_utc, observed_utc, note } = level;
      const fingerprint = await newLevelFingerprintV076(level);
      const inserted = await single('submit', [
        ...identity, request_id, fingerprint, market, provider, ticker, product, contract,
        period, kind, price, anchor_utc, observed_utc, now, note, publication_mode
      ]);
      let record;
      try {
        record = await lookupRecord(actor, request_id);
      } catch (error) {
        // The write succeeded before a later access/storage failure.
        if (inserted) throw new Error('levels_store_unavailable');
        throw error;
      }
      const result = outcome(record);
      if (result.state !== 'NOT_FOUND') {
        if (record.fingerprint !== fingerprint) throw new LevelsStoreError('conflict');
        return result;
      }
      if (inserted) throw new Error('levels_store_unavailable');
      const status = await single('submitUnavailable', [...identity, market, provider, ticker, product, contract]);
      if (!status) throw new Error('levels_store_unavailable');
      throw new LevelsStoreError(status.code);
    }
  });
}

return Object.freeze({normalizeLevelV110,LevelsStoreError,createLevelsStoreV110});
})();
// cot_archive_v110_lab.mjs git blob cbefc64afed63fdaaa3369ff50dd16490574630b
const __remura_cot_archive_v110_lab_mjs = (() => {
"use strict";
// Public CFTC snapshot markup carried forward from the two v1.08 dashboards.
// Source: staging_readonly_bundle_v108_lab.mjs at d34a3a71fc1e32c7244b7f7a5a65f80528abdf21.
const COT_ARCHIVE_V110 = `
<section class="panel" id="cot"><div class="eyebrow">Shark Cockpit</div><h2>Shark Cockpit · COT</h2><p class="tag">ARCHIVIO AUTENTICO · SOLO DESCRITTIVO</p><p>Report CFTC 17/11/2026 e 10/11/2026. Acquisiti il 24/11/2026 alle 10:05 CET. Snapshot B V22.3; commit 3ddf1f93. Non rappresentano ordini live, segnali di trading o un vantaggio statistico dimostrato. Parità privata, primo avvistamento storico e indice COT 52 settimane non verificati.</p><div class="metrics"><div class="metric"><small>Fattori valutari</small><strong>7</strong></div><div class="metric"><small>Cross sintetici</small><strong>28</strong></div><div class="metric"><small>Futures</small><strong>7</strong></div></div><p class="hint">Apri le sezioni per leggere i valori. Le tabelle scorrono orizzontalmente su iPhone.</p>
</section>
<details class="panel market-group" id="valute">
<summary>7 fattori valutari<span class="chevron" aria-hidden="true"></span></summary><div class="scroll" tabindex="0">
<table>
<thead>
<tr><th scope="col">Valuta</th><th scope="col">AM net % OI</th><th scope="col">LF net % OI</th><th scope="col">Δ AM pp</th><th scope="col">Δ LF pp</th></tr>
</thead>
<tbody>
<tr><th scope="row">AUD</th><td data-exact="-48.820271400364966">-48.82</td><td data-exact="10.147456055744215">10.15</td><td data-exact="-4.267914793334967">-4.27</td><td data-exact="-4.254613892875488">-4.25</td></tr>
<tr><th scope="row">NZD</th><td data-exact="-34.65136457429511">-34.65</td><td data-exact="-17.2039169078885">-17.20</td><td data-exact="-3.552111962982707">-3.55</td><td data-exact="1.618756408970949">1.62</td></tr>
<tr><th scope="row">GBP</th><td data-exact="-44.803189735287944">-44.80</td><td data-exact="12.329817258318023">12.33</td><td data-exact="3.3891429719149784">3.39</td><td data-exact="-3.3590702155868932">-3.36</td></tr>
<tr><th scope="row">CAD</th><td data-exact="1.4978251522951762">1.50</td><td data-exact="-20.134231935363193">-20.13</td><td data-exact="-2.7277283572779787">-2.73</td><td data-exact="-0.23064926129986318">-0.23</td></tr>
<tr><th scope="row">EUR</th><td data-exact="17.00098841613243">17.00</td><td data-exact="-8.843437655883385">-8.84</td><td data-exact="-2.3597266843993303">-2.36</td><td data-exact="-0.4573863282323245">-0.46</td></tr>
<tr><th scope="row">CHF</th><td data-exact="-8.863222846293805">-8.86</td><td data-exact="-15.634047939245313">-15.63</td><td data-exact="1.5571034763256382">1.56</td><td data-exact="-2.918227147651839">-2.92</td></tr>
<tr><th scope="row">JPY</th><td data-exact="21.69299699508916">21.69</td><td data-exact="-6.094358811459136">-6.09</td><td data-exact="-1.539147010053881">-1.54</td><td data-exact="-1.7600611579715117">-1.76</td></tr>
</tbody>
</table></div>
</details>
<details class="panel market-group" id="forex">
<summary>28 cross sintetici — non spot diretto<span class="chevron" aria-hidden="true"></span></summary><div class="scroll" tabindex="0">
<table>
<thead>
<tr><th scope="col">Cross</th><th scope="col">Δ AM pp</th><th scope="col">Δ LF pp</th></tr>
</thead>
<tbody>
<tr><th scope="row">EURUSD</th><td data-exact="-2.3597266843993303">-2.36</td><td data-exact="-0.4573863282323245">-0.46</td></tr>
<tr><th scope="row">GBPUSD</th><td data-exact="3.3891429719149784">3.39</td><td data-exact="-3.3590702155868932">-3.36</td></tr>
<tr><th scope="row">AUDUSD</th><td data-exact="-4.267914793334967">-4.27</td><td data-exact="-4.254613892875488">-4.25</td></tr>
<tr><th scope="row">NZDUSD</th><td data-exact="-3.552111962982707">-3.55</td><td data-exact="1.618756408970949">1.62</td></tr>
<tr><th scope="row">USDJPY</th><td data-exact="1.539147010053881">1.54</td><td data-exact="1.7600611579715117">1.76</td></tr>
<tr><th scope="row">USDCAD</th><td data-exact="2.7277283572779787">2.73</td><td data-exact="0.23064926129986318">0.23</td></tr>
<tr><th scope="row">USDCHF</th><td data-exact="-1.5571034763256382">-1.56</td><td data-exact="2.918227147651839">2.92</td></tr>
<tr><th scope="row">EURGBP</th><td data-exact="-5.748869656314309">-5.75</td><td data-exact="2.9016838873545687">2.90</td></tr>
<tr><th scope="row">EURJPY</th><td data-exact="-0.8205796743454492">-0.82</td><td data-exact="1.3026748297391872">1.30</td></tr>
<tr><th scope="row">EURCHF</th><td data-exact="-3.9168301607249685">-3.92</td><td data-exact="2.4608408194195146">2.46</td></tr>
<tr><th scope="row">EURCAD</th><td data-exact="0.3680016728786484">0.37</td><td data-exact="-0.22673706693246132">-0.23</td></tr>
<tr><th scope="row">EURAUD</th><td data-exact="1.9081881089356365">1.91</td><td data-exact="3.7972275646431637">3.80</td></tr>
<tr><th scope="row">EURNZD</th><td data-exact="1.1923852785833766">1.19</td><td data-exact="-2.0761427372032735">-2.08</td></tr>
<tr><th scope="row">GBPJPY</th><td data-exact="4.9282899819688595">4.93</td><td data-exact="-1.5990090576153815">-1.60</td></tr>
<tr><th scope="row">GBPCHF</th><td data-exact="1.8320394955893402">1.83</td><td data-exact="-0.4408430679350541">-0.44</td></tr>
<tr><th scope="row">GBPCAD</th><td data-exact="6.116871329192957">6.12</td><td data-exact="-3.12842095428703">-3.13</td></tr>
<tr><th scope="row">GBPAUD</th><td data-exact="7.657057765249945">7.66</td><td data-exact="0.895543677288595">0.90</td></tr>
<tr><th scope="row">GBPNZD</th><td data-exact="6.941254934897685">6.94</td><td data-exact="-4.977826624557842">-4.98</td></tr>
<tr><th scope="row">AUDJPY</th><td data-exact="-2.7287677832810857">-2.73</td><td data-exact="-2.4945527349039764">-2.49</td></tr>
<tr><th scope="row">AUDCAD</th><td data-exact="-1.5401864360569881">-1.54</td><td data-exact="-4.023964631575625">-4.02</td></tr>
<tr><th scope="row">AUDCHF</th><td data-exact="-5.825018269660605">-5.83</td><td data-exact="-1.336386745223649">-1.34</td></tr>
<tr><th scope="row">AUDNZD</th><td data-exact="-0.7158028303522599">-0.72</td><td data-exact="-5.873370301846437">-5.87</td></tr>
<tr><th scope="row">NZDJPY</th><td data-exact="-2.012964952928826">-2.01</td><td data-exact="3.3788175669424607">3.38</td></tr>
<tr><th scope="row">NZDCAD</th><td data-exact="-0.8243836057047282">-0.82</td><td data-exact="1.8494056702708122">1.85</td></tr>
<tr><th scope="row">NZDCHF</th><td data-exact="-5.109215439308345">-5.11</td><td data-exact="4.536983556622788">4.54</td></tr>
<tr><th scope="row">CADJPY</th><td data-exact="-1.1885813472240976">-1.19</td><td data-exact="1.5294118966716486">1.53</td></tr>
<tr><th scope="row">CADCHF</th><td data-exact="-4.284831833603617">-4.28</td><td data-exact="2.687577886351976">2.69</td></tr>
<tr><th scope="row">CHFJPY</th><td data-exact="3.0962504863795193">3.10</td><td data-exact="-1.1581659896803274">-1.16</td></tr>
</tbody>
</table></div>
</details>
<details class="panel market-group" id="futures-finanziari">
<summary>Futures finanziari<span class="chevron" aria-hidden="true"></span></summary><div class="scroll" tabindex="0">
<table>
<thead>
<tr><th scope="col">Riferimento</th><th scope="col">Asset Manager/Institutional net % OI</th><th scope="col">Leveraged Funds net % OI</th><th scope="col">Δ A pp</th><th scope="col">Δ B pp</th></tr>
</thead>
<tbody>
<tr><th scope="row">US30</th><td data-exact="-9.238772159029619">-9.24</td><td data-exact="4.133955004734451">4.13</td><td data-exact="-11.740335636202852">-11.74</td><td data-exact="2.5524377102715663">2.55</td></tr>
<tr><th scope="row">NAS100</th><td data-exact="27.96679070112643">27.97</td><td data-exact="-3.686623507622553">-3.69</td><td data-exact="2.756983173339705">2.76</td><td data-exact="-8.524232654295592">-8.52</td></tr>
<tr><th scope="row">US500</th><td data-exact="42.68321063178185">42.68</td><td data-exact="-11.205660771460373">-11.21</td><td data-exact="-2.6226271914285917">-2.62</td><td data-exact="3.8145083628007868">3.81</td></tr>
<tr><th scope="row">DXY</th><td data-exact="33.75705961452263">33.76</td><td data-exact="-2.2429403854773646">-2.24</td><td data-exact="1.789719023542851">1.79</td><td data-exact="-7.783375844264301">-7.78</td></tr>
</tbody>
</table></div>
</details>
<details class="panel market-group" id="futures-fisici">
<summary>Futures fisici<span class="chevron" aria-hidden="true"></span></summary><div class="scroll" tabindex="0">
<table>
<thead>
<tr><th scope="col">Riferimento</th><th scope="col">Managed Money net % OI</th><th scope="col">Producer/Merchant net % OI</th><th scope="col">Δ A pp</th><th scope="col">Δ B pp</th></tr>
</thead>
<tbody>
<tr><th scope="row">XAUUSD</th><td data-exact="25.24115203734853">25.24</td><td data-exact="-1.1257031046945571">-1.13</td><td data-exact="-2.516214075444104">-2.52</td><td data-exact="1.5627890813577006">1.56</td></tr>
<tr><th scope="row">XAGUSD</th><td data-exact="1.0411159461547848">1.04</td><td data-exact="-10.47378909268372">-10.47</td><td data-exact="-2.0846406339302983">-2.08</td><td data-exact="-0.045089199901926946">-0.05</td></tr>
<tr><th scope="row">USOIL</th><td data-exact="0.8457638803094895">0.85</td><td data-exact="20.602699021119495">20.60</td><td data-exact="-0.49527195174655503">-0.50</td><td data-exact="1.3801076208755276">1.38</td></tr>
</tbody>
</table></div>
</details>
<section class="panel" id="moduli"><h2>Altri moduli</h2><p>Myfxbook privato, CVD, Ampere e Squalincome: non collegati a questo portale. Nessun dato simulato.</p><p>AM = Asset Manager/Institutional; LF = Leveraged Funds; OI = open interest; pp = punti percentuali.</p>
</section>
`;

return Object.freeze({COT_ARCHIVE_V110});
})();
// contributors_style_v110_lab.mjs git blob 7bc8e15b892d8dc7d67a44ed6e1bf5395bf31342
const __remura_contributors_style_v110_lab_mjs = (() => {
"use strict";
// Shared v1.10 theme based on the v1.08 cockpit palette and navigation.
const CONTRIBUTORS_CSS_V110 = `
:root{color-scheme:dark;--bg:#07121a;--panel:#102833;--line:#2d4f58;--aqua:#69edca;--ink:#edf9f5;--muted:#a0bac0;--blue:#91baff;--gold:#f4c890;--red:#f5909c;--radius:19px;--control:12px;--focus:var(--aqua)}
*{box-sizing:border-box}html{scroll-padding-top:16px}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
a,summary,button,input,select{font:inherit}a{color:var(--aqua);text-decoration:none}a:focus-visible,summary:focus-visible,button:focus-visible,.scroll:focus-visible{outline:2px solid var(--focus);outline-offset:3px}
.version{padding:calc(8px + env(safe-area-inset-top,0px)) 12px 8px;background:#102c35;border-bottom:1px solid #39655d;color:#b9f8df;text-align:center;font-size:11px;font-weight:700;overflow-wrap:anywhere}
.shell{max-width:1230px;margin:auto;padding:20px max(16px,env(safe-area-inset-right,0px)) calc(40px + env(safe-area-inset-bottom,0px)) max(16px,env(safe-area-inset-left,0px))}
.masthead{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:12px;margin-bottom:16px}.brand{font-size:23px;font-weight:890;letter-spacing:.15em;color:var(--aqua)}.brand small{display:block;color:var(--muted);font-size:10px;letter-spacing:.06em;font-weight:700}
.tag,.eyebrow{font-size:11px;font-weight:850;letter-spacing:.09em;color:var(--aqua)}.tag{border:1px solid #4c8579;border-radius:999px;padding:5px 9px;display:inline-block}
.navigation{display:grid;gap:10px;margin:0 0 20px}.primary-nav{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.nav-link,.action{min-height:46px;display:flex;align-items:center;justify-content:center;border:1px solid #355762;border-radius:var(--control);padding:10px 12px;background:#18323e;color:var(--ink);font-weight:750;font-size:14px;text-align:center}.nav-link.active,.action{background:var(--aqua);color:#0a2929;border-color:var(--aqua)}.menu{border:1px solid var(--line);background:#0d2731;border-radius:var(--control)}.menu-body{padding:8px;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.menu-body .nav-link{justify-content:flex-start;text-align:left}
summary{list-style:none;cursor:pointer;min-height:46px;display:flex;justify-content:space-between;align-items:center;gap:10px;color:var(--aqua);font-weight:850;padding:10px 14px}summary::-webkit-details-marker{display:none}.chevron{flex:none;width:9px;height:9px;border-right:2px solid currentColor;border-bottom:2px solid currentColor;transform:rotate(45deg);margin:0 5px 4px}details[open]>summary .chevron{transform:rotate(225deg)}
.hero{padding:clamp(20px,4vw,45px);background:radial-gradient(ellipse at 95% 0%,#18635785,transparent 70%),linear-gradient(130deg,#13323d,#0b202c 68%);border:1px solid #2c585d;border-radius:24px;min-width:0}.hero h1{font-size:clamp(30px,5vw,54px);line-height:1.08;letter-spacing:-.04em;margin:8px 0 14px;overflow-wrap:anywhere}.hero p{margin:0;color:#c1d9d8}
h2{font-size:clamp(19px,3vw,25px);line-height:1.25;letter-spacing:-.02em;margin:0 0 12px}p{color:var(--muted);margin:8px 0 12px;overflow-wrap:anywhere}.panel{min-width:0;margin:16px 0;border:1px solid var(--line);border-radius:var(--radius);padding:20px;background:linear-gradient(155deg,#102b36,#0c1e29)}.market-group{padding:4px 12px 8px}.market-group[open]{padding-bottom:14px}.metrics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:16px 0}.metric{min-width:0;border:1px solid var(--line);border-radius:12px;background:#102c35;padding:12px 8px}.metric small{display:block;color:var(--muted);font-size:11px;overflow-wrap:anywhere}.metric strong{display:block;color:var(--aqua);font-size:27px;font-variant-numeric:tabular-nums}.hint{font-size:13px}.notice{border:1px solid #64543e;background:#2c2a21;color:var(--gold);padding:12px;border-radius:var(--control)}
.scroll{overflow-x:auto;max-width:100%;overscroll-behavior-inline:contain;border:1px solid #355a61;border-radius:10px}table{width:100%;border-collapse:collapse;white-space:nowrap;font-size:13px;font-variant-numeric:tabular-nums}th,td{padding:11px 10px;border-bottom:1px solid #284a55;text-align:right}th:first-child{text-align:left}thead th{color:var(--aqua);background:#143743}tbody th{position:sticky;left:0;background:#102833;z-index:1}tbody tr:last-child>*{border-bottom:0}.action{width:fit-content}footer{font-size:12px;color:var(--muted);margin-top:24px;padding-top:16px;border-top:1px solid var(--line)}
@media(max-width:540px){.shell{padding-top:14px}.panel{padding:15px}.market-group{padding:3px 8px 8px}.menu-body{grid-template-columns:1fr}.hero{padding:20px}.metric strong{font-size:24px}.metric small{font-size:10px}.action{width:100%}}
@media(max-width:340px){.primary-nav{grid-template-columns:1fr}.metrics{grid-template-columns:1fr}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{scroll-behavior:auto!important;transition:none!important}}
`;

const CONTRIBUTORS_FORMS_CSS_V110 = `
[hidden] { display: none !important; }
.brand { display: inline-flex; min-height: 46px; flex-direction: column; justify-content: center; }
.panel { background: var(--panel); }
.work-grid, .access-forms { display: grid; gap: 16px; margin: 16px 0; }
.work-grid { grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr); align-items: start; }
.work-grid > .panel { margin: 0; }
.access-forms { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.access-forms .panel { margin: 0; }
.fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.field { min-width: 0; }
.field.wide { grid-column: 1 / -1; }
label { display: block; font-weight: 700; margin: 0 0 4px; }
input, select, textarea, button { font: inherit; }
input, select, textarea {
  min-height: 46px;
  width: 100%;
  color: var(--ink);
  background: #0b202c;
  padding: 9px 11px;
  border: 1px solid #4a6c75;
  border-radius: var(--control);
  font-size: 16px;
}
textarea { min-height: 85px; resize: vertical; }
input::placeholder, textarea::placeholder { color: var(--muted); }
input:focus-visible, select:focus-visible, textarea:focus-visible {
  outline: 2px solid var(--focus);
  outline-offset: 3px;
}
button {
  min-height: 46px;
  border: 1px solid var(--aqua);
  border-radius: var(--control);
  padding: 9px 14px;
  background: var(--aqua);
  color: #0a2929;
  font-size: 14px;
  font-weight: 750;
  cursor: pointer;
}
button.secondary { border-color: #4a6c75; color: var(--ink); background: #18323e; }
button.danger { border-color: var(--red); color: var(--red); background: transparent; }
button:disabled { opacity: .58; cursor: not-allowed; }
button:focus-visible { outline: 2px solid var(--focus); outline-offset: 3px; }
.actions { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0 0; }
.status { color: var(--muted); overflow-wrap: anywhere; }
.status:empty { margin: 0; }
.status[data-tone="success"] { color: var(--aqua); }
.status[data-tone="warning"] { color: var(--gold); }
.status[data-tone="error"] { color: var(--red); }
.receipt { padding: 3px 0; margin: 8px 0; border: 1px solid var(--line); border-radius: var(--control); }
.receipt summary { flex-wrap: wrap; justify-content: flex-start; gap: 5px 12px; }
.receipt .chevron { margin-left: auto; }
.receipt-actions { padding: 0 14px 12px; }
.receipt dl { display: grid; grid-template-columns: fit-content(40%) 1fr; gap: 4px 12px; padding: 0 14px; }
.receipt dt, .receipt dd { min-width: 0; margin: 0; overflow-wrap: anywhere; }
.receipt dt { color: var(--muted); }
.state { color: var(--blue); }
.state[data-state="UNREVIEWED"], .state[data-state="INVITED"] { color: var(--gold); }
.state[data-state="APPROVED"], .state[data-state="ACTIVE"] { color: var(--aqua); }
.state[data-state="REJECTED"], .state[data-state="REVOKED"] { color: var(--red); }
.work-table { white-space: normal; }
.work-table th, .work-table td { text-align: left; vertical-align: middle; }
.work-table tbody th { position: static; }
.work-table td > button { white-space: nowrap; }
.work-table td { overflow-wrap: anywhere; }

@media (max-width: 840px) {
  .work-grid, .access-forms { grid-template-columns: minmax(0, 1fr); }
}
@media (max-width: 540px) {
  .fields { grid-template-columns: minmax(0, 1fr); }
  .actions button { flex: 1 1 auto; }
}
`;

return Object.freeze({CONTRIBUTORS_CSS_V110,CONTRIBUTORS_FORMS_CSS_V110});
})();
// contributors_browser_v110_lab.mjs git blob 1f47497c01b3e545b8adf7dbac634e768e96b055
const __remura_contributors_browser_v110_lab_mjs = (() => {
"use strict";
function browserTools() {
  const find = id => document.getElementById(id);
  const observedUtc = () => new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
  // Fixed Europe/Rome timezone even if the device is abroad. Reject DST gaps/folds.
  const romeFormat = new Intl.DateTimeFormat('en-CA', {timeZone:'Europe/Rome',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'});
  function romeLocal(date) {
    const parts=Object.fromEntries(romeFormat.formatToParts(date).map(x=>[x.type,x.value]));
    return parts.year+'-'+parts.month+'-'+parts.day+'T'+parts.hour+':'+parts.minute+':'+parts.second;
  }
  function romeToUtc(value) {
    if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value)) value+=':00';
    if (!/^20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(value)) throw Error('rome_date');
    const nominal=Date.parse(value+'Z');
    if(!Number.isFinite(nominal)) throw Error('rome_date');
    const matches=[60,120].map(m=>new Date(nominal-m*60000)).filter(d=>romeLocal(d)===value);
    if(matches.length!==1)throw Error('rome_date_ambiguous_or_invalid');
    return matches[0].toISOString().replace('.000Z','Z');
  }
  const observedRome=()=>romeLocal(new Date());
  const oneLine = text => text.replace(/\r\n?|\n/g, ' ');
  const stateLabels = {
    UNREVIEWED: 'In attesa', APPROVED: 'Approvato', REJECTED: 'Rifiutato',
    ACTIVE: 'Attivo', REVOKED: 'Revocato', INVITED: 'Invito in attesa', AVAILABLE: 'Disponibile',
    WITHDRAWN: 'Invito ritirato', ENROLLED: 'Iscrizione completata',
  };

  function element(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  }

  function status(id, text, tone = '') {
    const el = find(id);
    el.textContent = text;
    el.dataset.tone = tone;
  }

  function state(value, label = stateLabels[value] ?? value) {
    const node = element('span', label, 'state');
    node.dataset.state = value;
    return node;
  }

  function choices(id, values, placeholder) {
    const select = find(id);
    const previous = select.value;
    const option = ([value, label]) => {
      const node = element('option', label);
      node.value = value;
      return node;
    };
    select.replaceChildren(option(['', placeholder]), ...values.map(option));
    if (values.some(([value]) => value === previous)) select.value = previous;
  }

  function displayDate(value) {
    const date = new Date(value);
    if (!Number.isFinite(date.getTime())) return value;
    return new Intl.DateTimeFormat('it-IT', {
      timeZone: 'Europe/Rome', dateStyle: 'short', timeStyle: 'medium',
    }).format(date);
  }

  async function request(path, options = {}) {
    const { body, intent, requestId } = options;
    const headers = new Headers({ Accept: 'application/json' });
    if (body !== undefined) {
      headers.set('Content-Type', 'application/json');
      headers.set('X-Remura-CSRF', '1');
    }
    if (intent) headers.set('X-Remura-Intent', intent);
    if (requestId) headers.set('X-Remura-Request-ID', requestId);
    const timeout = new AbortController();
    const timer = setTimeout(() => timeout.abort(), 15000);
    try {
      const response = await fetch(path, {
        method: body === undefined ? 'GET' : 'POST', body: body === undefined ? undefined : JSON.stringify(body),
        headers, credentials: 'same-origin', cache: 'no-store', redirect: 'error', signal: timeout.signal,
      });
      if (!/^application\/json\b/i.test(response.headers.get('Content-Type') ?? '')) {
        throw Object.assign(new Error('non_json'), { status: response.status });
      }
      const data = await response.json();
      if (!response.ok) throw Object.assign(new Error('request_failed'), { code: data.error, status: response.status });
      return data;
    } finally {
      clearTimeout(timer);
    }
  }

  async function mutation(path, body) {
    const { intent } = await request('/api/intent', { body: { path, body } });
    if (typeof intent !== 'string' || !intent) throw new Error('intent_missing');
    try {
      return await request(path, { body, intent });
    } catch (error) {
      throw Object.assign(error, { dispatched: true });
    }
  }

  function paginator({ prefix, endpoint, empty, render }) {
    const loadButton = find(`${prefix}Load`);
    const nextButton = find(`${prefix}Next`);
    let cursor = null;
    async function load(after = 0) {
      if (loadButton.disabled) return;
      loadButton.disabled = nextButton.disabled = true;
      try {
        const { items, next } = await request(`${endpoint}?after=${after}`);
        if (!Array.isArray(items) || (next !== null && (!Number.isSafeInteger(next) || next <= after))) {
          throw new Error('invalid_page');
        }
        render(find(`${prefix}Rows`), items);
        cursor = next;
        nextButton.hidden = cursor === null;
        status(`${prefix}Status`, items.length ? '' : empty);
      } catch (error) {
        if ([401, 403].includes(error.status)) {
          find(`${prefix}Rows`).replaceChildren();
          cursor = null;
          nextButton.hidden = true;
        }
        status(`${prefix}Status`, 'Lettura non disponibile. Aggiorna per riprovare.', 'error');
      } finally {
        loadButton.disabled = nextButton.disabled = false;
      }
    }
    loadButton.addEventListener('click', () => load());
    nextButton.addEventListener('click', () => { if (cursor !== null) void load(cursor); });
    return { load };
  }

  function table(container, caption, headers, rows) {
    container.replaceChildren();
    if (!rows.length) return;
    const scroll = element('div', undefined, 'scroll');
    scroll.tabIndex = 0;
    scroll.setAttribute('role', 'region');
    scroll.setAttribute('aria-label', caption);
    const grid = element('table', undefined, 'work-table');
    const thead = grid.createTHead();
    const labels = thead.insertRow();
    for (const header of headers) {
      const cell = element('th', header);
      cell.scope = 'col';
      labels.append(cell);
    }
    const tbody = grid.createTBody();
    for (const values of rows) {
      const row = tbody.insertRow();
      for (const [index, value] of values.entries()) {
        const cell = element(index ? 'td' : 'th');
        if (!index) cell.scope = 'row';
        cell.append(value instanceof Node ? value : document.createTextNode(String(value ?? '—')));
        row.append(cell);
      }
    }
    scroll.append(grid);
    container.append(scroll);
  }

  function receipt(row, forOwner = false) {
    const details = element('details', undefined, 'receipt');
    const summary = element('summary');
    const marker = element('span', undefined, 'chevron');
    marker.setAttribute('aria-hidden', 'true');
    summary.append(element('span', `#${row.id} · ${row.market} · ${row.price}`), state(row.status), marker);
    const mapping = row.contract==='CONTINUOUS' ? `${row.provider} · ${row.ticker.replace(/_CONT$/,'')} · Grafico continuativo (scadenza/adeguamento non verificati)` : [row.provider, row.ticker, row.product, row.contract].filter(Boolean).join(' · ');
    const periods = { DAY: 'Giorno', WEEK: 'Settimana', CURRENT_MONTH: 'Mese corrente', PREVIOUS_MONTH: 'Mese precedente' };
    const methods = { DELTA_PEAK: 'Picco delta', EFFORT_RESULT: 'Effort / result', OTHER_VOLUME_LEVEL: 'Altro livello volumetrico' };
    const values = [
      ['Strumento e fonte', mapping], ['Periodo', periods[row.period] ?? row.period],
      ['Metodologia', methods[row.kind] ?? row.kind], ['Riferimento (Roma)', displayDate(row.anchor_utc)],
      ['Osservato (Roma)', displayDate(row.observed_utc)], ['Ricevuto (Roma)', displayDate(row.received_utc)],
      ['Decisione (Roma)', row.reviewed_utc && displayDate(row.reviewed_utc)], ['Osservazioni', row.note],
    ];
    if (forOwner) values.unshift(['Slot', row.slot]);
    const fields = element('dl');
    for (const [label, value] of values) {
      if (value) fields.append(element('dt', label), element('dd', value));
    }
    details.append(summary, fields);
    return details;
  }

  function protectPage() {
    window.addEventListener('pageshow', event => {
      if (event.persisted) window.location.reload();
    });
  }

  return { find, observedUtc, observedRome, romeToUtc, oneLine, element, status, state, choices, displayDate, request, mutation, paginator, table, receipt, protectPage };
}

function startContributor({ find, observedRome, romeToUtc, oneLine, status, choices, request, mutation, paginator, receipt, protectPage }) {
  protectPage();
  const write = document.body.dataset.write === 'true';
  const storageKey = `remura.contributors.v110.pending.${document.body.dataset.slot}`;
  const idPattern = /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/;
  const digestPattern = /^[a-f0-9]{64}$/;
  const form = find('intake');
  const catalogButton = find('catalogLoad');
  const intakeLabel = find('send').textContent;
  const receiptPager = paginator({
    prefix: 'my', endpoint: '/api/receipts', empty: 'Nessuna ricevuta in questa pagina.',
    render: (container, rows) => container.replaceChildren(...rows.map(row => receipt(row))),
  });
  let catalog = [];
  let busy = false;
  let pending = readPending();
  let original = null;
  let absent = false;

  function readPending() {
    try {
      const saved = JSON.parse(sessionStorage.getItem(storageKey));
      if (saved && idPattern.test(saved.id) && digestPattern.test(saved.digest)) return saved;
    } catch {
      // A new dispatch will validate tab storage before contacting the server.
    }
    return null;
  }

  function clearPending() {
    pending = null;
    original = null;
    absent = false;
    try { sessionStorage.removeItem(storageKey); } catch {
      // The server result is authoritative if the stored reference reappears.
    }
  }

  async function draftDigest(data) {
    const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(JSON.stringify(data)));
    return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
  }

  function decisions() {
    const reenter = pending && absent && !original;
    form.hidden = !write || !catalog.length || Boolean(pending && !reenter);
    find('send').textContent = reenter ? 'Reinvia lo stesso livello' : intakeLabel;
    find('send').disabled = busy || form.hidden;
    find('pendingAttempt').hidden = !pending;
    find('checkAttempt').disabled = busy;
    find('retryAttempt').hidden = !write || !pending || !absent || !original;
    find('retryAttempt').disabled = busy;
    find('clearAttempt').hidden = !pending || !absent;
    find('clearAttempt').disabled = busy;
    if (pending) {
      find('pendingMessage').textContent = absent
        ? 'La ricevuta non è ancora presente. Puoi riprovare con gli stessi dati e la stessa richiesta. L’invio iniziale potrebbe ancora arrivare.'
        : 'La proposta potrebbe essere già stata registrata. Verifica la ricevuta prima di riprovare.';
    }
  }

  function updateMappings() {
    const market = find('market').value;
    const provider = find('provider').value;
    choices('mapping', catalog.flatMap((row, index) => row.market === market && row.provider === provider
      ? [[String(index), row.contract==='CONTINUOUS' ? `${row.ticker.replace(/_CONT$/,'')} · Grafico continuativo` : [row.ticker, row.product, row.contract].filter(Boolean).join(' · ')]] : []), 'Seleziona serie');
  }

  function updateProviders() {
    const providers = new Set(catalog.filter(row => row.market === find('market').value).map(row => row.provider));
    choices('provider', [...providers].map(value => [value, value]), 'Seleziona fonte');
    updateMappings();
  }

  async function loadCatalog() {
    catalogButton.hidden = true;
    status('catalogStatus', 'Caricamento catalogo…');
    try {
      const { items } = await request('/api/catalog');
      const fields = ['market', 'provider', 'ticker', 'product', 'contract'];
      if (!Array.isArray(items) || !items.every(row => row && fields.every(field => typeof row[field] === 'string'))) {
        throw new Error('invalid_catalog');
      }
      catalog = items;
      find('mapping').value = '';
      choices('market', [...new Set(catalog.map(row => row.market))].map(value => [value, value]), 'Seleziona strumento');
      updateProviders();
      status('catalogStatus', catalog.length ? '' : 'Nessuna fonte abilitata per l’invio.', catalog.length ? '' : 'warning');
      catalogButton.hidden = catalog.length > 0;
    } catch {
      status('catalogStatus', 'Catalogo non disponibile. Ricarica per riprovare.', 'error');
      catalogButton.hidden = false;
    } finally {
      decisions();
    }
  }

  function draft(id) {
    const selection = find('mapping').value;
    const row = selection === '' ? null : catalog[Number(selection)];
    if (!row || row.market !== find('market').value || row.provider !== find('provider').value) throw new Error('mapping');
    let price = find('price').value.trim().replace(',', '.');
    if (price.includes('.')) price = price.replace(/0+$/, '').replace(/\.$/, '');
    return {
      request_id: id, market: row.market, provider: row.provider, ticker: row.ticker, product: row.product,
      contract: row.contract, period: find('period').value, kind: find('kind').value, price,
      anchor_utc: romeToUtc(find('anchor').value), observed_utc: romeToUtc(find('observed').value), note: oneLine(find('note').value),
    };
  }

  function confirmReceipt(result) {
    if (!['COMMITTED', 'DUPLICATE'].includes(result.state) || !Number.isSafeInteger(result.receipt?.id) || result.receipt.id < 1) {
      return false;
    }
    const label = result.state === 'DUPLICATE' ? 'Livello già registrato (nessuna nuova pubblicazione)' : 'Proposta registrata';
    status('intakeStatus', `${label} · Ricevuta #${result.receipt.id}.`, 'success');
    clearPending();
    form.reset();
    updateProviders();
    find('observed').value = observedRome();
    if (!find('myRead').hidden) void receiptPager.load();
    return true;
  }

  async function dispatch(data, existing) {
    absent = false;
    decisions();
    status('intakeStatus', 'Invio della proposta…');
    try {
      const result = await mutation('/api/submit', data);
      if (!confirmReceipt(result)) throw Object.assign(new Error('invalid_receipt'), { dispatched: true });
    } catch (error) {
      const known = ['invalid', 'invalid_mapping', 'conflict', 'denied', 'capacity'].includes(error.code);
      if ((!error.dispatched || known) && !existing) {
        clearPending();
        const messages = {
          invalid: 'Dati rifiutati. Controlla i campi e la cronologia UTC.',
          invalid_mapping: 'Strumento e fonte non disponibili. Ricarica il catalogo.',
          conflict: 'Proposta in conflitto con un tentativo registrato. Aggiorna le ricevute.',
          denied: 'Invio rifiutato. Verifica i permessi e ricarica la pagina.',
          capacity: 'Limite di invii raggiunto.',
        };
        if (error.code === 'invalid_mapping') {
          catalog = [];
          catalogButton.hidden = false;
        }
        const message = messages[error.code] ?? 'Invio non avviato. Riprova quando la connessione è disponibile.';
        status('intakeStatus', message, 'error');
      } else {
        status('intakeStatus', 'Esito dell’invio incerto.', 'warning');
      }
    }
  }

  async function exclusive(fn) {
    if (busy) return;
    busy = true;
    decisions();
    try { await fn(); } finally {
      busy = false;
      decisions();
    }
  }

  form.addEventListener('submit', event => {
    event.preventDefault();
    if (!write || form.hidden || busy) return;
    void exclusive(async () => {
      const existing = Boolean(pending);
      let data;
      let digest;
      try {
        data = draft(pending?.id ?? crypto.randomUUID());
        digest = await draftDigest(data);
      } catch {
        status('intakeStatus', 'Impossibile preparare la richiesta. Controlla i campi e l’ora di Roma (evita ore ambigue del cambio legale).', 'error');
        return;
      }
      if (pending && digest !== pending.digest) {
        status('intakeStatus', 'I dati differiscono dalla proposta da verificare. Ricontrolla anche le due date UTC e le osservazioni.', 'error');
        return;
      }
      if (!pending) {
        try {
          const reference = { id: data.request_id, digest };
          sessionStorage.setItem(storageKey, JSON.stringify(reference));
          pending = reference;
        } catch {
          status('intakeStatus', 'La scheda non può salvare il riferimento per verificare l’invio.', 'error');
          return;
        }
      }
      original = Object.freeze(data);
      await dispatch(original, existing);
    });
  });

  find('checkAttempt').addEventListener('click', () => void exclusive(async () => {
    if (!pending) return;
    status('intakeStatus', 'Verifica in corso…');
    try {
      const result = await request('/api/level-attempt/status', { requestId: pending.id });
      if (confirmReceipt(result)) return;
      if (result.state !== 'NOT_FOUND') throw new Error('invalid_attempt');
      absent = true;
      status('intakeStatus', original || !write ? '' : 'Ricompila la proposta precedente con gli stessi valori prima di reinviarla.', 'warning');
    } catch {
      absent = false;
      status('intakeStatus', 'Impossibile verificare il tentativo. Riprova quando la connessione è disponibile.', 'error');
    }
  }));
  find('retryAttempt').addEventListener('click', () => {
    if (pending && absent && original && write) void exclusive(() => dispatch(original, true));
  });
  find('clearAttempt').addEventListener('click', () => {
    if (!pending || !absent || busy) return;
    if (!window.confirm('La proposta iniziale potrebbe ancora arrivare. Vuoi chiudere la verifica e preparare una nuova proposta?')) return;
    clearPending();
    form.reset();
    updateProviders();
    find('observed').value = observedRome();
    status('intakeStatus', 'Verifica chiusa. Aggiorna le ricevute per controllare eventuali registrazioni successive.', 'warning');
    decisions();
  });
  find('market').addEventListener('change', updateProviders);
  find('provider').addEventListener('change', updateMappings);
  catalogButton.addEventListener('click', () => void loadCatalog());
  find('observed').value = observedRome();
  decisions();
  if (write) void loadCatalog();
  if (!find('myRead').hidden) void receiptPager.load();
}

function startOwner({ find, oneLine, element, status, state, choices, displayDate, request, mutation, paginator, table, receipt, protectPage }) {
  protectPage();
  const write = document.body.dataset.write === 'true';
  const slotButtons = ['inviteSend', 'withdrawSend', 'revokeSend'];
  const slotsLoad = find('slotsLoad');
  const inviteEmail = find('inviteEmail');
  const reviewForm = find('review');
  let mutating = false;
  let slots = [];
  const approvalAuto=find('approvalAuto'),approvalManual=find('approvalManual'),approvalLoad=find('approvalLoad');
  let approval=null,approvalBusy=false,batchBusy=false;
  function renderApproval(){for(const [btn,mode] of [[approvalAuto,'AUTOMATIC'],[approvalManual,'MANUAL']]){btn.disabled=approvalBusy||!write||!approval||approval.mode===mode;btn.setAttribute('aria-pressed',String(approval?.mode===mode));}approvalLoad.disabled=approvalBusy;}
  async function loadApproval(){approval=null;renderApproval();try{const r=await request('/owner/approval/status');if(!['AUTOMATIC','MANUAL'].includes(r.mode)||!Number.isSafeInteger(r.revision))throw Error('mode');approval=r;status('approvalStatus',r.mode==='AUTOMATIC'?'AUTOMATICA · le nuove proposte valide sono approvate all’inserimento.':'MANUALE · le nuove proposte attendono la tua decisione.','success');}catch{status('approvalStatus','Modalità non disponibile.','warning');}renderApproval();}
  async function setApproval(mode){if(!write||approvalBusy||!approval||approval.mode===mode)return;approvalBusy=true;renderApproval();let uncertain=false;try{await mutation('/owner/approval/mode',{mode,revision:approval.revision});}catch{uncertain=true;}finally{await loadApproval();approvalBusy=false;renderApproval();await policyAudit.load();if(uncertain)status('approvalStatus','Esito della richiesta non confermato. Modalità riletta: '+(approval?.mode??'non disponibile')+'. Consulta il registro.','warning');}}
  approvalAuto.onclick=()=>setApproval('AUTOMATIC');approvalManual.onclick=()=>setApproval('MANUAL');approvalLoad.onclick=loadApproval;
  const batch=paginator({prefix:'batch',endpoint:'/owner/proposals',empty:'Nessuna proposta multipla.',render(container,rows){container.replaceChildren(...rows.map(row=>{const card=element('section',undefined,'receipt');card.append(element('h3',row.reference+' · '+row.slot+' · '+row.mapping_id),element('p',row.prices.join(' / ')),element('p',row.kind+' · '+row.period+' · '+displayDate(row.received_utc)),element('p',row.decision+' · Telegram LAB '+row.telegram_state+(row.publication_mode==='TEST'?' · TEST':'')));if(write&&['PENDING','SENDING'].includes(row.telegram_state)&&Number.isSafeInteger(row.telegram_epoch)){const recover=element('button',row.telegram_state==='PENDING'?'Simula recupero mai tentato':'Segna esito incerto (LAB)','secondary');recover.type='button';recover.onclick=async()=>{if(batchBusy||!window.confirm('Operazione esclusivamente LAB, nessun invio reale.'))return;batchBusy=true;recover.disabled=true;try{const r=await mutation('/owner/proposals/recover',{id:row.id,epoch:row.telegram_epoch,action:row.telegram_state==='PENDING'?'PENDING':'MARK_UNKNOWN'});await batch.load();status('batchStatus','Esito LAB: '+r.state,'warning');}catch{status('batchStatus','Esito non confermato. Aggiorna il registro.','warning');}finally{batchBusy=false;recover.disabled=false;}};card.append(recover);}if(row.note)card.append(element('p',row.note));if(row.decision_reason)card.append(element('p',row.decision_reason));if(write&&row.decision==='PENDING'){const reason=element('textarea');reason.maxLength=280;reason.placeholder='Motivazione';reason.setAttribute('aria-label','Motivazione per '+row.reference);const actions=element('div',undefined,'actions');for(const [action,label] of [['APPROVED','Approva'],['REJECTED','Rifiuta']]){const b=element('button',label,'secondary');b.type='button';b.onclick=async()=>{if(batchBusy)return;const text=reason.value.trim();if(!text){status('batchStatus','Inserisci la motivazione.','warning');return;}batchBusy=true;for(const x of actions.querySelectorAll('button'))x.disabled=true;let uncertain=false;try{await mutation('/owner/proposals/review',{id:row.id,action,reason:text});}catch{uncertain=true;}finally{batchBusy=false;await batch.load();if(uncertain)status('batchStatus','Esito da verificare: consulta il registro.','warning');}};actions.append(b);}card.append(reason,actions);}return card;}));}});
  const policyAudit=paginator({prefix:'policyAudit',endpoint:'/owner/approval/audit',empty:'Nessun cambio registrato.',render(container,rows){container.replaceChildren(...rows.map(r=>element('p',r.setting+' · '+r.old_value+' → '+r.new_value+' · '+displayDate(r.changed_utc))));}});
  void loadApproval();void batch.load();void policyAudit.load();
  const telegramToggle=find('telegramToggle');
  const telegramReload=find('telegramReload');
  const telegramRecover=find('telegramRecover');
  let telegramPolicy=null,telegramBusy=false;
  function renderTelegram(){
    telegramToggle.disabled=telegramBusy||!write||!telegramPolicy;
    telegramReload.disabled=telegramBusy;
    telegramRecover.disabled=true;telegramRecover.hidden=true; // legacy recovery permanently hidden
    telegramToggle.textContent=!telegramPolicy?'Stato non disponibile':telegramPolicy.enabled?'Disabilita invio livelli Telegram':'Abilita invio livelli Telegram';
    telegramToggle.setAttribute('aria-pressed',String(telegramPolicy?.enabled===1));
  }
  async function loadTelegram(){
    telegramPolicy=null;
    renderTelegram();
    try{
      const p=await request('/owner/telegram/status');
      if(![0,1].includes(p.enabled)||!Number.isSafeInteger(p.epoch)||p.epoch<1||typeof p.configured!=='boolean')throw Error('telegram');
      telegramPolicy=p;
      status('telegramStatus',p.enabled?'Politica ON · LAB, nessun invio reale':'Politica OFF · nessun invio',p.enabled?'success':'warning');
    }catch{status('telegramStatus','Stato Telegram non disponibile. Aggiorna per riprovare.','warning');}
    renderTelegram();
  }
  telegramReload.addEventListener('click',async()=>{
    if(telegramBusy)return;telegramBusy=true;renderTelegram();
    try{await loadTelegram();}finally{telegramBusy=false;renderTelegram();}
  });
  telegramToggle.addEventListener('click',async()=>{
    if(telegramToggle.disabled||telegramBusy||!telegramPolicy)return;
    const body={enabled:telegramPolicy.enabled===0,epoch:telegramPolicy.epoch};
    if(body.enabled&&!window.confirm('Abilitare la politica Telegram nel LAB? Nessun invio reale.'))return;
    telegramBusy=true;renderTelegram();
    try{await mutation('/owner/telegram/toggle',body);}
    catch{status('telegramStatus','Modifica non confermata. Verifica lo stato prima di riprovare.','warning');}
    finally{await loadTelegram();telegramBusy=false;renderTelegram();}
  });
  telegramRecover.addEventListener('click',async()=>{
    if(telegramRecover.disabled||telegramBusy||!telegramPolicy)return;
    if(!window.confirm('Recuperare un livello recente mai inviato a SMF PLUS?'))return;
    const body={epoch:telegramPolicy.epoch};
    telegramBusy=true;renderTelegram();
    try{
      const r=await mutation('/owner/telegram/recover',body);
      const labels={SENT:'Consegna Telegram confermata.',EMPTY:'Nessun invio recente da recuperare.',BLOCKED:'Invio bloccato dalle protezioni.',OFF:'Telegram non configurato.'};
      status('telegramRecoveryStatus',labels[r.state]??'Esito incerto: non ripetere il medesimo invio.',r.state==='SENT'?'success':'warning');
    }catch{status('telegramRecoveryStatus','Esito non confermato. Controlla il gruppo prima di proseguire.','warning');}
    finally{await loadTelegram();telegramBusy=false;renderTelegram();}
  });
  telegramBusy=true;
  void loadTelegram().finally(()=>{telegramBusy=false;renderTelegram();});

  const queue = paginator({
    prefix: 'queue', endpoint: '/owner/queue', empty: 'Nessuna proposta da esaminare in questa pagina.',
    render(container, rows) {
      container.replaceChildren(...rows.map(row => {
        const card = receipt(row, true);
        if (write && row.status === 'UNREVIEWED') {
          const actions = element('div', undefined, 'actions receipt-actions');
          const select = element('button', `Esamina #${row.id}`, 'secondary');
          select.type = 'button';
          select.addEventListener('click', () => {
            if (mutating) return;
            find('entry').value = row.id;
            find('decision').focus();
          });
          actions.append(select);
          card.append(actions);
        }
        return card;
      }));
    },
  });

  function renderAudit(container, rows) {
    const actionLabels = { INVITED: 'Invito registrato', REVOKED: 'Accesso revocato' };
    table(container, 'Eventi del registro OWNER', ['Evento', 'Riferimento', 'Ora (Roma)', 'Motivazione'], rows.map(row => [
      state(row.action, actionLabels[row.action]), row.entry_id == null ? row.slot : `Ricevuta #${row.entry_id}`, displayDate(row.at_utc), row.reason || '—',
    ]));
  }

  const history = paginator({
    prefix: 'history', endpoint: '/owner/history', empty: 'Nessuna decisione in questa pagina.',
    render: (container, rows) => container.replaceChildren(...rows.map(row => receipt(row, true))),
  });
  const audit = paginator({ prefix: 'audit', endpoint: '/owner/audit', empty: 'Nessun evento in questa pagina.', render: renderAudit });
  const slotTypes = { invite: 'AVAILABLE', withdraw: 'INVITED', revoke: 'ACTIVE' };

  function refreshButtons() {
    find('reviewSend').disabled = !write || mutating;
    for (const id of slotButtons) {
      const control = find(id);
      if (!control) continue;
      const type = id.slice(0, -4);
      control.disabled = mutating || !slots.some(row => row.status === slotTypes[type] && (type !== 'invite' || row.slot !== 'friend-a'));
    }
  }

  function renderSlots() {
    table(find('slotsRows'), 'Stato degli slot', ['Slot', 'Stato'], slots.map(({ slot, status: current }) => [slot, state(current)]));
    if (write) {
      for (const [type, current] of Object.entries(slotTypes)) {
        const eligible = slots.filter(row => row.status === current && (type !== 'invite' || row.slot !== 'friend-a'));
        choices(`${type}Slot`, eligible.map(row => [row.slot, row.slot]), 'Seleziona slot');
      }
    }
    refreshButtons();
  }

  async function loadSlots() {
    if (slotsLoad.disabled) return;
    slotsLoad.disabled = true;
    try {
      const { items } = await request('/owner/collaborators');
      const allowed = ['friend-a', 'friend-b', 'friend-c'];
      const states = ['AVAILABLE', 'INVITED', 'ACTIVE', 'REVOKED'];
      if (!Array.isArray(items) || items.length !== allowed.length ||
          !allowed.every(slot => items.some(row => row?.slot === slot && states.includes(row.status)))) {
        throw new Error('invalid_slots');
      }
      slots = items;
      status('slotsStatus', '');
    } catch {
      slots = [];
      status('slotsStatus', 'Stato degli slot non disponibile. Aggiorna per riprovare.', 'error');
    } finally {
      renderSlots();
      slotsLoad.disabled = false;
    }
  }

  function logResult(prefix, error) {
    if (error.code === 'conflict') {
      status(`${prefix}Status`, 'Lo stato è cambiato. Aggiorna il registro prima di procedere.', 'error');
    } else if (error.code === 'invalid') {
      status(`${prefix}Status`, 'Verifica i dati della richiesta.', 'error');
    } else if (error.code === 'denied') {
      status(`${prefix}Status`, 'Operazione rifiutata. Verifica i permessi.', 'error');
    } else if (error.dispatched) {
      status(`${prefix}Status`, 'Esito incerto. Consulta il registro e l’audit prima di ripetere l’operazione.', 'warning');
    } else {
      status(`${prefix}Status`, 'Operazione non avviata. Riprova quando è disponibile la connessione.', 'error');
    }
  }

  async function run(prefix, path, body, success, refresh) {
    if (!write || mutating) return;
    mutating = true;
    refreshButtons();
    status(`${prefix}Status`, 'Registrazione in corso…');
    try {
      await mutation(path, body);
      status(`${prefix}Status`, success, 'success');
      find(prefix).reset();
    } catch (error) {
      logResult(prefix, error);
    } finally {
      if (prefix === 'invite') inviteEmail.value = '';
      await refresh();
      mutating = false;
      refreshButtons();
    }
  }

  reviewForm.addEventListener('submit', event => {
    event.preventDefault();
    const id = Number(find('entry').value);
    const action = find('decision').value;
    const reason = oneLine(find('reason').value).trim();
    if (!Number.isSafeInteger(id) || id < 1 || !['APPROVED', 'REJECTED'].includes(action) || !reason) {
      status('reviewStatus', 'Compila numero ricevuta, decisione e motivazione.', 'error');
      return;
    }
    void run('review', '/owner/review', { id, action, reason },
      `${action === 'APPROVED' ? 'Approvazione registrata' : 'Rifiuto registrato'} · Ricevuta #${id}.`,
      () => Promise.all([queue.load(), history.load()]));
  });

  if (write) {
    const confirmations = { invite: 'Invito registrato.', withdraw: 'Invito ritirato.', revoke: 'Accesso revocato.' };
    for (const [type, current] of Object.entries(slotTypes)) {
      find(type).addEventListener('submit', event => {
        event.preventDefault();
        const slot = find(`${type}Slot`).value;
        if (mutating || !slots.some(row => row.slot === slot && row.status === current)) return;
        if (type === 'revoke' && !window.confirm(`Revocare l’accesso Contributors per ${slot}?`)) return;
        const body = type === 'invite' ? { slot, email: inviteEmail.value.trim() } : { slot };
        void run(type, `/owner/${type}`, body, confirmations[type], loadSlots);
      });
    }
    window.addEventListener('pagehide', () => { inviteEmail.value = ''; });
  }
  slotsLoad.addEventListener('click', () => void loadSlots());
  refreshButtons();
  if (!find('ownerRead').hidden) void queue.load();
  if (!find('slotsPanel').hidden) void loadSlots();
}

function startInvited({ find, status, request, mutation, protectPage }) {
  protectPage();
  const button = find('enrollSend');
  const write = document.body.dataset.write === 'true';
  button.disabled = !write;
  button.addEventListener('click', async () => {
    if (!write || button.disabled) return;
    button.disabled = true;
    status('enrollStatus', 'Registrazione in corso…');
    let activated = false;
    try {
      await mutation('/api/enroll', {});
      activated = true;
    } catch (error) {
      if (error.dispatched || error.code === 'denied') {
        try {
          const profile = await request('/api/profile');
          activated = profile.role === 'CONTRIBUTOR' && profile.slot === document.body.dataset.slot;
        } catch {
          // Activation remains unconfirmed until another allowed profile check.
        }
      }
    } finally {
      button.disabled = activated;
      if (activated) {
        button.hidden = true;
        find('enrollDashboard').hidden = false;
        status('enrollStatus', 'Slot attivato.', 'success');
      } else {
        status('enrollStatus', 'Attivazione non confermata. Verifica l’invito con l’OWNER o riprova.', 'warning');
      }
    }
  });
}

function standalone(start) {
  return `(${start.toString()})((${browserTools.toString()})());\n`;
}

const CONTRIBUTORS_BROWSER_V110 = Object.freeze({
  CONTRIBUTOR: standalone(startContributor),
  OWNER: standalone(startOwner),
  INVITED: standalone(startInvited),
});

return Object.freeze({CONTRIBUTORS_BROWSER_V110});
})();
// contributors_ui_v110_lab.mjs git blob 1a6ce863f41c6e862e0534fe659dbc069583e405
const __remura_contributors_ui_v110_lab_mjs = (() => {
"use strict";
const { COT_ARCHIVE_V110 } = __remura_cot_archive_v110_lab_mjs;
const { CONTRIBUTORS_CSS_V110 : theme, CONTRIBUTORS_FORMS_CSS_V110 } = __remura_contributors_style_v110_lab_mjs;


const CONTRIBUTORS_CSS_V110 = theme + CONTRIBUTORS_FORMS_CSS_V110;
const VERSION = 'REMURA Contributors V30.19.1 LAB';
const UPDATED = '28/11/2026 09:36 CET (Europe/Rome)';
const SLOTS = ['friend-a', 'friend-b', 'friend-c'];
const NAV_SECTIONS = [
  ['cot', 'Shark Cockpit · COT'],
  ['valute', 'Fattori valutari'],
  ['forex', 'Forex · 28 cross'],
  ['futures-finanziari', 'Futures finanziari'],
  ['futures-fisici', 'Metalli ed energia'],
  ['moduli', 'Disponibilità moduli'],
];
const CHEVRON = '<span class="chevron" aria-hidden="true"></span>';

function shell({ role, home, slot, caption, navigation, body, script, write }) {
  return `<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <meta name="theme-color" content="#07121a">
  <meta name="robots" content="noindex,nofollow,noarchive">
  <title>${caption} · ${VERSION}</title>
  <link rel="stylesheet" href="${home}contributors-v110.css">
  ${script ? `<script type="module" src="${home}contributors-v110.js"></script>` : ''}
</head>
<body data-slot="${slot}" data-write="${write}">
  <div class="version">${VERSION} · <time datetime="2026-11-28T09:36:00+01:00">${UPDATED}</time></div>
  <main class="shell">
    <header class="masthead">
      ${role === 'INVITED'
        ? '<span class="brand">REMURA<small>Segui le tracce istituzionali</small></span>'
        : `<a class="brand" href="${home}" aria-label="REMURA, torna alla dashboard">REMURA<small>Segui le tracce istituzionali</small></a>`}
      <span class="tag">${role === 'INVITED' ? 'INVITO CONTRIBUTORS' : role}</span>
    </header>
    ${navigation}
    ${body}
    <footer>${VERSION}</footer>
  </main>
</body>
</html>`;
}

function navLink(path, name, active = false) {
  return `<a class="nav-link${active ? ' active' : ''}" href="${path}"${active ? ' aria-current="page"' : ''}>${name}</a>`;
}

function navigation(home, label, levels) {
  return `<nav aria-label="Menu REMURA" class="navigation">
    <div class="primary-nav">${navLink(home, 'Dashboard', !levels)}${navLink(`${home}levels/`, label, levels)}</div>
    <details class="menu">
      <summary>Esplora REMURA${CHEVRON}</summary>
      <div class="menu-body">${NAV_SECTIONS.map(([id, name]) => navLink(`${home}#${id}`, name)).join('')}</div>
    </details>
  </nav>`;
}

function hero(title, description) {
  return `<section class="hero"><h1>${title}</h1><p>${description}</p></section>`;
}

function status(id, text = '') {
  return `<p class="status" id="${id}" role="status" aria-live="polite">${text}</p>`;
}

function field(id, label, input, wide = false) {
  return `<div class="field${wide ? ' wide' : ''}"><label for="${id}">${label}</label>${input}</div>`;
}

function controls(id, label, data, { wide = false, placeholder = '' } = {}) {
  const options = data.map(([value, text]) => `<option value="${value}">${text}</option>`).join('');
  return field(id, label, `<select id="${id}" required>${placeholder ? `<option value="">${placeholder}</option>` : ''}${options}</select>`, wide);
}

function button(id, label, { type = 'button', modifier = 'secondary', hidden = false, disabled = false } = {}) {
  return `<button id="${id}" type="${type}" class="${modifier}"${hidden ? ' hidden' : ''}${disabled ? ' disabled' : ''}>${label}</button>`;
}

function dataPanel({ title, name, prefix, heading, hidden = false }) {
  return `<section class="panel" id="${name}"${hidden ? ' hidden' : ''} aria-labelledby="${name}Heading">
    <h2 id="${name}Heading">${title}</h2>
    ${status(`${prefix}Status`, heading)}
    <div id="${prefix}Rows"></div>
    <div class="actions">
      ${button(`${prefix}Load`, 'Aggiorna')}
      ${button(`${prefix}Next`, 'Pagina successiva', { hidden: true })}
    </div>
  </section>`;
}

const PERIODS = [['DAY', 'Giorno'], ['WEEK', 'Settimana'], ['CURRENT_MONTH', 'Mese corrente'], ['PREVIOUS_MONTH', 'Mese precedente']];
const KINDS = [['DELTA_PEAK', 'Picco delta'], ['EFFORT_RESULT', 'Effort / result'], ['OTHER_VOLUME_LEVEL', 'Altro livello volumetrico']];

function contributorLevels(write, read) {
  const unavailable = write ? 'Caricamento catalogo…' : 'Invio dei livelli disattivato.';
  return `${hero('I miei livelli', 'Proponi livelli volumetrici e segui le decisioni nelle tue ricevute.')}
  <section class="panel" id="pendingAttempt" hidden aria-labelledby="pendingHeading">
    <h2 id="pendingHeading">Verifica dell’invio</h2>
    <p id="pendingMessage" class="notice"></p>
    <div class="actions">
      ${button('checkAttempt', 'Verifica la ricevuta')}
      ${button('retryAttempt', 'Reinvia lo stesso livello', { hidden: true, modifier: '' })}
      ${button('clearAttempt', 'Chiudi il tentativo', { hidden: true })}
    </div>
  </section>
  ${status('intakeStatus')}
  <div class="work-grid">
    <section class="panel" aria-labelledby="intakeHeading">
      <h2 id="intakeHeading">Nuova proposta</h2>
      ${status('catalogStatus', unavailable)}
      ${button('catalogLoad', 'Ricarica catalogo', { hidden: true })}
      <form id="intake" autocomplete="off" hidden>
        <div class="fields">
          ${controls('market', 'Strumento', [], { placeholder: 'Seleziona strumento' })}
          ${controls('provider', 'Fonte', [], { placeholder: 'Seleziona fonte' })}
          ${controls('mapping', 'Serie / contratto', [], { wide: true, placeholder: 'Seleziona serie' })}
          ${controls('period', 'Periodo', PERIODS)}
          ${controls('kind', 'Metodologia', KINDS)}
          ${field('price', 'Prezzo originale del grafico', '<input id="price" inputmode="decimal" maxlength="17" required>')}
          ${field('anchor', 'Riferimento (ora Roma)', '<input id="anchor" type="datetime-local" step="1" required>')}
          ${field('observed', 'Osservato (ora Roma)', '<input id="observed" type="datetime-local" step="1" required>')}
          ${field('note', 'Osservazioni tecniche', '<textarea id="note" maxlength="280" rows="2"></textarea>', true)}
        </div>
        <p class="notice">Per le serie continue riporta il prezzo esatto del grafico: il contratto effettivo e l’eventuale adeguamento possono non essere noti.</p>
        <div class="actions">${button('send', 'Registra livello', { type: 'submit', modifier: '', disabled: true })}</div>
      </form>
    </section>
    ${dataPanel({ title: 'Le mie ricevute', name: 'myRead', prefix: 'my', heading: 'Caricamento ricevute…', hidden: !read })}
  </div>`;
}

function ownerAccessForm(id, title, label, text = '') {
  return `<form class="panel" id="${id}" autocomplete="off" aria-labelledby="${id}Heading">
    <h2 id="${id}Heading">${title}</h2>
    <div class="fields">
      ${controls(`${id}Slot`, 'Slot', [], { wide: true, placeholder: 'Seleziona slot' })}
      ${text}
    </div>
    ${status(`${id}Status`)}
    <div class="actions">${button(`${id}Send`, label, { type: 'submit', modifier: id === 'revoke' ? 'danger' : '', disabled: true })}</div>
  </form>`;
}

function ownerLevels(write, read) {
  return `${hero('Desk livelli', 'Esamina le proposte, registra le decisioni e gestisci gli accessi dei collaboratori.')}
  ${write ? '' : '<p class="notice">Registro in sola lettura.</p>'}
  <section class="panel" aria-labelledby="approvalHeading"><h2 id="approvalHeading">Approvazione delle proposte</h2><p>Impostazione indipendente da Telegram. Le proposte già in attesa restano manuali.</p><div class="actions"><button type="button" id="approvalAuto" disabled aria-pressed="false">Automatica</button><button type="button" id="approvalManual" disabled aria-pressed="false">Manuale</button><button type="button" id="approvalLoad">Aggiorna</button></div>${status('approvalStatus','Verifica modalità…')}</section>
  <section class="panel" aria-labelledby="telegramHeading">
    <h2 id="telegramHeading">Invio livelli Telegram</h2>
    <p>SMF PLUS · Pubblicazione indipendente dalla modalità di approvazione. LAB: nessun invio reale.</p>
    ${status('telegramStatus','Verifica stato…')}
    <div class="actions">
      ${button('telegramToggle','Caricamento…',{disabled:true})}
      ${button('telegramReload','Aggiorna stato')}
      ${button('telegramRecover','Recupera un invio recente',{disabled:true})}
    </div>
    ${status('telegramRecoveryStatus','Recupero reale disabilitato nel LAB. Gli stati SENT sono solo simulati.')}
    <p class="notice">La riattivazione non pubblica lo storico. Un invio già in corso può concludersi dopo lo stop.</p>
  </section>
  <div class="work-grid">
    ${dataPanel({ title: 'Proposte da esaminare', name: 'ownerRead', prefix: 'queue', heading: 'Caricamento proposte…', hidden: !read })}
    <form class="panel" id="review" autocomplete="off" ${write ? '' : 'hidden'} aria-labelledby="reviewHeading">
      <h2 id="reviewHeading">Decisione OWNER</h2>
      <div class="fields">
        ${field('entry', 'Numero ricevuta', '<input id="entry" type="number" min="1" step="1" required>')}
        ${controls('decision', 'Decisione', [['APPROVED', 'Approva'], ['REJECTED', 'Rifiuta']], { placeholder: 'Seleziona decisione' })}
        ${field('reason', 'Motivazione per il registro OWNER', '<textarea id="reason" maxlength="280" rows="2" required></textarea>', true)}
      </div>
      ${status('reviewStatus')}
      <div class="actions">${button('reviewSend', 'Registra decisione', { type: 'submit', modifier: '', disabled: true })}</div>
    </form>
  </div>
  ${dataPanel({ title: 'Nuove proposte multiple', name: 'batchPanel', prefix: 'batch', heading: 'Consulta approvazioni e stato Telegram.', hidden: !read })}
  ${dataPanel({ title: 'Audit impostazioni', name: 'policyAuditPanel', prefix: 'policyAudit', heading: 'Modifiche dei due selettori.', hidden: !read })}
  ${dataPanel({ title: 'Cronologia decisioni precedenti', name: 'historyPanel', prefix: 'history', heading: 'Consulta le decisioni archiviate.', hidden: !read })}
  ${dataPanel({ title: 'Collaboratori', name: 'slotsPanel', prefix: 'slots', heading: 'Caricamento slot…', hidden: !read })}
  ${write ? `<div class="access-forms">
    ${ownerAccessForm('invite', 'Invita collaboratore', 'Registra invito', field('inviteEmail', 'Email usata con Google Access', '<input id="inviteEmail" type="email" inputmode="email" maxlength="254" autocomplete="off" required>', true))}
    ${ownerAccessForm('withdraw', 'Ritira invito', 'Ritira invito')}
    ${ownerAccessForm('revoke', 'Revoca accesso', 'Revoca accesso')}
  </div>` : ''}
  ${dataPanel({ title: 'Audit OWNER', name: 'auditPanel', prefix: 'audit', heading: 'Consulta gli eventi registrati.', hidden: !read })}`;
}

function renderContributorsPageV110(path, profile) {
  const { role, slot, can_read: read, can_write: write } = profile ?? {};
  if (path === '/join/' && role === 'INVITED' && ['friend-b', 'friend-c'].includes(slot)) {
    return shell({ role, slot, home: '/join/', caption: 'Invito Contributors', navigation: '', script: true, write: write === true,
      body: `${hero('Completa l’accesso Contributors', `Account Google verificato. Invito riservato allo slot ${slot}.`)}
      <section class="panel" aria-labelledby="enrollHeading">
        <h2 id="enrollHeading">Attiva il tuo slot</h2>
        ${status('enrollStatus', write ? '' : 'La registrazione è temporaneamente in sola lettura.')}
        <div class="actions">${button('enrollSend', 'Accetta invito', { modifier: '', disabled: true })}</div>
        <p><a id="enrollDashboard" class="nav-link" href="/contributors/" hidden>Apri la dashboard</a></p>
      </section>` });
  }
  const owner = role === 'OWNER' && slot === 'owner';
  if (!owner && (role !== 'CONTRIBUTOR' || !SLOTS.includes(slot))) return null;
  const home = owner ? '/owner/' : '/contributors/';
  const levels = path === `${home}levels/`;
  if (path !== home && !levels) return null;
  const label = owner ? 'Desk livelli' : 'I miei livelli';
  const caption = levels ? label : owner ? 'Centro di controllo' : 'Segui le tracce istituzionali';
  return shell({ role, home, slot, caption, write: write === true, navigation: navigation(home, label, levels), script: levels,
    body: levels ? (owner ? ownerLevels(write === true, read === true) : contributorLevels(write === true, read === true))
      : `${hero(caption, 'Consulta il posizionamento aggregato CFTC.')}${COT_ARCHIVE_V110}` });
}

return Object.freeze({CONTRIBUTORS_BROWSER_V110:__remura_contributors_browser_v110_lab_mjs.CONTRIBUTORS_BROWSER_V110,CONTRIBUTORS_CSS_V110,renderContributorsPageV110});
})();
// staging_contributors_v110_lab.mjs git blob 7bb18f8442027b201dc67994530414bfffd46b41
const __remura_staging_contributors_v110_lab_mjs = (() => {
"use strict";
// Direct Cloudflare Access Worker for the dedicated REMURA Contributors staging origin.
const {normalizeNewLevelV076} = __remura_level_attempt_journal_v076_lab_mjs;
const {checkContinuousMapping} = __remura_continuous_intake_v3018_lab_mjs;
const {scheduleTelegramAfterSubmit,createTelegramTransport} = __remura_telegram_transport_v3012_lab_mjs;
const {readTelegramPolicy,changeTelegramPolicy} = __remura_telegram_owner_v3015_lab_mjs;
const {recoverTelegramPending} = __remura_telegram_recovery_v3016_lab_mjs;
const {createLevelsStoreV110, LevelsStoreError} = __remura_staging_levels_store_v110_lab_mjs;
const {
  CONTRIBUTORS_BROWSER_V110, CONTRIBUTORS_CSS_V110, renderContributorsPageV110,
} = __remura_contributors_ui_v110_lab_mjs;

const HEX = /^[a-f0-9]{64}$/;
const UUID = /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/;
const EMAIL = /^[^\s@\u0000-\u001f\u007f-\u009f]{1,64}@[^\s@\u0000-\u001f\u007f-\u009f]{1,189}$/u;
const SLOTS = new Set(['friend-a', 'friend-b', 'friend-c']);
const INVITE_SLOTS = new Set(['friend-b', 'friend-c']);
const ROLE_DIRECTORY = {OWNER: '/owner/', CONTRIBUTOR: '/contributors/', INVITED: '/join/'};
const READS = new Map([
  ['/api/proposals/catalog','CONTRIBUTOR'],
  ['/api/proposals','CONTRIBUTOR'],
  ['/api/proposals/status','CONTRIBUTOR'],
  ['/owner/proposals','OWNER'],
  ['/owner/approval/status','OWNER'],
  ['/owner/approval/audit','OWNER'],
  ['/api/catalog', 'CONTRIBUTOR'],
  ['/api/receipts', 'CONTRIBUTOR'],
  ['/api/level-attempt/status', 'CONTRIBUTOR'],
  ['/owner/queue', 'OWNER'],
  ['/owner/history', 'OWNER'],
  ['/owner/audit', 'OWNER'],
  ['/owner/collaborators', 'OWNER'],
  ['/owner/telegram/status', 'OWNER'],
]);
const PAGED = new Set(['/api/receipts', '/owner/queue', '/owner/history', '/owner/audit','/api/proposals','/owner/proposals','/owner/approval/audit']);
const ACTIONS = new Map([
  ['/api/proposals/submit','CONTRIBUTOR'],
  ['/owner/approval/mode','OWNER'],
  ['/owner/proposals/review','OWNER'],
  ['/owner/proposals/recover','OWNER'],
  ['/owner/review', 'OWNER'],
  ['/owner/telegram/toggle', 'OWNER'],
  // legacy recovery disabled in V30.19 route candidate; no historical dispatch.
  ['/owner/invite', 'OWNER'],
  ['/owner/withdraw', 'OWNER'],
  ['/owner/revoke', 'OWNER'],
  ['/api/enroll', 'INVITED'],
]);
const SLOT_ACTIONS = new Set(['/owner/invite', '/owner/withdraw', '/owner/revoke']);
const SENSITIVE_HEADERS = ['x-remura-role', 'x-remura-subject', 'x-remura-actor', 'x-remura-admin'];
const LIMIT_BYTES = 4096;
const PAGE_SIZE = 20;
const INTENT_TTL = 90;
const ENCODER = new TextEncoder();
const HEADERS = {
  'Cache-Control': 'private, no-store, max-age=0',
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'X-Robots-Tag': 'noindex, nofollow, noarchive',
  'Referrer-Policy': 'no-referrer',
  'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
  'Cross-Origin-Resource-Policy': 'same-origin',
  'Content-Security-Policy': "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; object-src 'none'; form-action 'none'; frame-ancestors 'none'",
};
const REQUEST_ERRORS = {
  denied: 403, invalid: 400, conflict: 409, invalid_mapping: 409,
  capacity: 429,
};

function response(body, type, status = 200) {
  return new Response(body, {status, headers: {...HEADERS, 'Content-Type': type}});
}

function json(body, status = 200) {
  return response(JSON.stringify(body), 'application/json; charset=utf-8', status);
}

function reject(code = 'denied') {
  return json({error: code}, REQUEST_ERRORS[code]);
}

function unavailable(write) {
  return json({error: write ? 'outcome_unknown' : 'temporarily_unavailable'}, 503);
}

function hasKey(value) {
  return typeof value === 'string' && HEX.test(value) && !/^0+$/.test(value);
}

function bytes(value) {
  return Uint8Array.from(value.match(/../g), part => parseInt(part, 16));
}

function hex(value) {
  return Array.from(new Uint8Array(value), part => part.toString(16).padStart(2, '0')).join('');
}

function hmac(secret, usages) {
  return crypto.subtle.importKey('raw', bytes(secret), {name: 'HMAC', hash: 'SHA-256'}, false, usages);
}

function ready(env, url) {
  return env?.REMURA_V3019_LAB_MODE === 'SYNTHETIC_ONLY' && url.protocol === 'https:' && url.origin === env?.STAGING_ORIGIN &&
    !url.username && !url.password &&
    env.PRIVATE_WORKER_V078 === 'STAGING_AUTHENTICATED_READONLY' &&
    env.CONTRIBUTORS_STAGE_READONLY === 'EXPLICIT_STAGING_ONLY' &&
    env.STAGING_ENABLED === 'D1_CANDIDATE' &&
    typeof env.ACCESS_AUD === 'string' && HEX.test(env.ACCESS_AUD) &&
    typeof env.ACCESS_ACCOUNT === 'string' && /^[a-f0-9]{32}$/.test(env.ACCESS_ACCOUNT) &&
    hasKey(env.IDENTITY_HMAC_KEY) && typeof env.CONTRIBUTORS_DB?.withSession === 'function';
}

// Keep the exact v1.08 HMAC namespace and values so existing D1 bindings survive.
async function identityTag(key, env, domain, value) {
  const data = JSON.stringify(['remura-contributors-v1', env.ACCESS_ACCOUNT, env.ACCESS_AUD, domain, value]);
  return hex(await crypto.subtle.sign('HMAC', key, ENCODER.encode(data)));
}

async function authenticate(ctx, env) {
  const access = ctx?.access;
  if (access?.aud !== env.ACCESS_AUD || typeof access.getIdentity !== 'function') return null;
  const identity = await access.getIdentity();
  if (identity?.account_id !== env.ACCESS_ACCOUNT || typeof identity.user_uuid !== 'string' ||
      !UUID.test(identity.user_uuid) || typeof identity.email !== 'string' || !EMAIL.test(identity.email) ||
      identity.service_token_status !== false ||
      (identity.service_token_id != null && identity.service_token_id !== '')) return null;
  const key = await hmac(env.IDENTITY_HMAC_KEY, ['sign']);
  const [subject, email_tag] = await Promise.all([
    identityTag(key, env, 'uuid', identity.user_uuid),
    identityTag(key, env, 'email', identity.email),
  ]);
  return {actor: Object.freeze({subject, email_tag}), key};
}

function writesEnabled(env) {
  return env.CONTRIBUTORS_V110_WRITE === 'EXPLICIT_STAGING_ONLY' &&
    hasKey(env.INTENT_HMAC_KEY) && env.INTENT_HMAC_KEY !== env.IDENTITY_HMAC_KEY;
}

async function resolvedProfile(store, actor, allowWrite, mayBeInvited) {
  const profile = await store.profile(actor);
  if (profile?.can_read === true) {
    return {data: {...profile, can_write: allowWrite && profile.can_write === true}};
  }
  if (profile === null && allowWrite && mayBeInvited) {
    const invited = await store.getInvite(actor);
    if (INVITE_SLOTS.has(invited?.slot) && Number.isSafeInteger(invited.revision) && invited.revision > 0) {
      return {
        data: {role: 'INVITED', slot: invited.slot, can_read: true, can_write: true, can_recover: false},
        revision: invited.revision,
      };
    }
  }
  return null;
}

function originAllowed(req, origin) {
  const site = req.headers.get('Sec-Fetch-Site');
  const contentType = req.headers.get('Content-Type')?.toLowerCase().trim();
  return req.headers.get('Origin') === origin &&
    (site === null || site === 'same-origin') &&
    req.headers.get('X-Remura-CSRF') === '1' &&
    (contentType === 'application/json' || contentType === 'application/json; charset=utf-8') &&
    !req.headers.has('Content-Encoding');
}

function shape(value, fields) {
  return !!value && Object.getPrototypeOf(value) === Object.prototype &&
    Object.keys(value).length === fields.length && fields.every(field => Object.hasOwn(value, field));
}

async function requestBody(req) {
  const declaration = req.headers.get('Content-Length');
  if (declaration !== null && (!/^[1-9]\d{0,3}$/.test(declaration) || Number(declaration) > LIMIT_BYTES)) {
    throw Error('length');
  }
  const reader = req.body?.getReader();
  if (!reader) throw Error('body');
  const data = new Uint8Array(LIMIT_BYTES);
  let length = 0;
  try {
    for (;;) {
      const {value, done} = await reader.read();
      if (done) break;
      if (length + value.byteLength > LIMIT_BYTES) {
        void reader.cancel().catch(() => {});
        throw Error('length');
      }
      data.set(value, length);
      length += value.byteLength;
    }
  } finally {
    reader.releaseLock();
  }
  if (declaration !== null && Number(declaration) !== length) throw Error('length');
  return JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(data.subarray(0, length)));
}

function normalizeAction(path, body, now) {
  if(path==='/owner/proposals/recover')return normalizeRecovery(body);
  if (['/api/proposals/submit','/owner/approval/mode','/owner/proposals/review'].includes(path)) return normalizeProposalAction(path,body);
  if (path === '/api/submit') return checkContinuousMapping(normalizeNewLevelV076(body,now));
  if (path === '/owner/telegram/recover' && shape(body,['epoch']) && Number.isSafeInteger(body.epoch) && body.epoch>0) return body;
  if (path === '/owner/telegram/toggle' && shape(body,['enabled','epoch']) &&
      typeof body.enabled==='boolean' && Number.isSafeInteger(body.epoch) && body.epoch>0) return body;
  if (path === '/owner/review' && shape(body, ['id', 'action', 'reason']) &&
      Number.isSafeInteger(body.id) && body.id > 0 &&
      ['APPROVED', 'REJECTED'].includes(body.action) && typeof body.reason === 'string') {
    const reason = body.reason.trim();
    if (reason && [...reason].length <= 280 && !/[\u0000-\u001f\u007f-\u009f\uD800-\uDFFF]/u.test(reason)) {
      return {id: body.id, action: body.action, reason};
    }
  }
  if (path === '/owner/invite' && shape(body, ['slot', 'email']) && INVITE_SLOTS.has(body.slot) &&
      typeof body.email === 'string' && EMAIL.test(body.email)) return body;
  if (path === '/owner/withdraw' && shape(body, ['slot']) && INVITE_SLOTS.has(body.slot)) return body;
  if (path === '/owner/revoke' && shape(body, ['slot']) && SLOTS.has(body.slot)) return body;
  if (path === '/api/enroll' && shape(body, [])) return body;
  throw Error('fields');
}

function intentMessage(env, actor, profile, path, body, expiry, revision, nonce) {
  const fields = Object.keys(body).sort().map(name => [name, body[name]]);
  return ENCODER.encode(JSON.stringify([
    'remura-contributors-v110-mutation', env.STAGING_ORIGIN, env.ACCESS_ACCOUNT, env.ACCESS_AUD,
    actor.subject, actor.email_tag, profile.role, profile.slot, path, fields, expiry, revision, nonce,
  ]));
}

async function issueIntent(env, actor, profile, path, body, revision, time) {
  const nonce = hex(crypto.getRandomValues(new Uint8Array(16)));
  const expiry = time + INTENT_TTL;
  const key = await hmac(env.INTENT_HMAC_KEY, ['sign']);
  const mac = await crypto.subtle.sign('HMAC', key, intentMessage(env, actor, profile, path, body, expiry, revision, nonce));
  return [nonce, expiry, revision, hex(mac)].join('.');
}

async function verifyIntent(env, actor, profile, path, body, token, time) {
  if (!token || !/^[a-f0-9]{32}\.\d{10}\.(0|[1-9]\d{0,15})\.[a-f0-9]{64}$/.test(token)) return null;
  const [nonce, expires, version, mac] = token.split('.');
  const expiry = Number(expires);
  const revision = Number(version);
  if (expiry <= time || expiry > time + INTENT_TTL || !Number.isSafeInteger(revision)) return null;
  const key = await hmac(env.INTENT_HMAC_KEY, ['verify']);
  const valid = await crypto.subtle.verify(
    'HMAC', key, bytes(mac), intentMessage(env, actor, profile, path, body, expiry, revision, nonce),
  );
  return valid ? revision : null;
}

function cursor(url) {
  if (!url.search) return 0;
  if (!/^\?after=(0|[1-9]\d{0,15})$/.test(url.search)) return null;
  const after = Number(url.search.slice('?after='.length));
  return Number.isSafeInteger(after) ? after : null;
}

function page(items) {
  return json({items, next: items.length === PAGE_SIZE ? items.at(-1).id : null});
}

async function get(req, url, store, actor, profile, env) {
  const path = url.pathname;
  if (path === '/api/profile' || READS.has(path)) {
    const origin = req.headers.get('Origin');
    const site = req.headers.get('Sec-Fetch-Site');
    if ((origin !== null && origin !== url.origin) ||
        (site !== null && site !== 'same-origin' && site !== 'none')) return reject();
  }
  if (url.search && !PAGED.has(path)) return reject('invalid');
  if (path === '/api/profile') return json(profile);
  if (READS.has(path)) {
    if (READS.get(path) !== profile.role) return reject();
    const after = cursor(url);
    if (after === null) return reject('invalid');
    const proposals=()=>createProposalApi(env.CONTRIBUTORS_DB,env.REMURA_V3019_LAB_MODE);
    switch (path) {
      case '/api/proposals/catalog': return json({items:await proposals().catalog(actor)});
      case '/api/proposals': return page(await proposals().history(actor,after));
      case '/api/proposals/status': {
        const id=req.headers.get('X-Remura-Request-ID');
        if(!id||!UUID.test(id)) return reject('invalid');
        const receipt=await proposals().status(actor,id);
        return receipt?json(receipt):json({state:'NOT_FOUND'});
      }
      case '/owner/proposals': return page(await proposals().history(actor,after,true));
      case '/owner/approval/status': {const policy=await proposals().approval(actor);return policy?json(policy):reject();}
      case '/owner/approval/audit': return page(await proposals().audit(actor,after));
      case '/api/catalog':
        return json({items: await store.catalog(actor)});
      case '/api/receipts':
        return page(await store.receipts(actor, after));
      case '/api/level-attempt/status': {
        const requestId = req.headers.get('X-Remura-Request-ID');
        if (!requestId || !UUID.test(requestId)) return reject('invalid');
        return json(await store.lookup(actor, requestId));
      }
      case '/owner/telegram/status': {
        const policy=await readTelegramPolicy(env.CONTRIBUTORS_DB,actor);
        return policy ? json({...policy,configured:false,labOnly:true,simulationEnabled:env.REMURA_V3019_TRANSPORT==='SYNTHETIC_TRANSPORT_ONLY'}) : reject();
      }
      case '/owner/queue':
        return page(await store.queue(actor, after));
      case '/owner/history':
        return page(await store.history(actor, after));
      case '/owner/audit':
        return page(await store.audit(actor, after));
      case '/owner/collaborators': {
        const items = await store.slots(actor);
        return json({items: items.map(({slot, status}) => ({slot, status: status === 'VACANT' ? 'AVAILABLE' : status}))});
      }
    }
  }
  if(profile.role==='CONTRIBUTOR'){
    if(path==='/contributors/levels/')return response(PROPOSAL_HTML.replace('__WRITE__',String(profile.can_write===true)).replace('__SLOT__',profile.slot),'text/html; charset=utf-8');
    if(path==='/contributors/levels/proposal-preview.css')return response(PROPOSAL_CSS,'text/css; charset=utf-8');
    if(path==='/contributors/levels/proposal-form.mjs')return response(PROPOSAL_FORM,'text/javascript; charset=utf-8');
    if(path==='/contributors/levels/proposal-core.mjs')return response(PROPOSAL_CORE,'text/javascript; charset=utf-8');
    if(path==='/contributors/legacy/')return response(renderContributorsPageV110('/contributors/levels/',{...profile,can_write:false}),'text/html; charset=utf-8');
  }
  const directory = ROLE_DIRECTORY[profile.role];
  if (path === '/') return new Response(null, {status: 303, headers: {...HEADERS, Location: directory}});
  if (path === directory + 'contributors-v110.css') {
    return response(CONTRIBUTORS_CSS_V110, 'text/css; charset=utf-8');
  }
  if (path === directory + 'contributors-v110.js') {
    return response(CONTRIBUTORS_BROWSER_V110[profile.role], 'text/javascript; charset=utf-8');
  }
  if (path !== directory && (profile.role === 'INVITED' || path !== directory + 'levels/')) return reject();
  const html = renderContributorsPageV110(path, profile);
  return typeof html === 'string' ? response(html, 'text/html; charset=utf-8') : reject();
}

async function mutate(path, body, revision, {store, actor, key, env, now, ctx, profile}) {
  let result;
  switch (path) {
    case '/api/proposals/submit': {
      const receipt=await createProposalApi(env.CONTRIBUTORS_DB,env.REMURA_V3019_LAB_MODE).submit(actor,body);
      if(!receipt.replay&&receipt.decision==='APPROVED'&&receipt.telegram_state==='PENDING'&&receipt.publication_mode==='TELEGRAM')scheduleProposalLab(ctx,env,receipt.id);
      return json(receipt);
    }
    case '/owner/approval/mode': result=await createProposalApi(env.CONTRIBUTORS_DB,env.REMURA_V3019_LAB_MODE).change(actor,body); break;
    case '/owner/proposals/review':
      result=await createProposalApi(env.CONTRIBUTORS_DB,env.REMURA_V3019_LAB_MODE).review(actor,body);
      if(result?.action==='APPROVED')scheduleProposalLab(ctx,env,result.proposal_id);
      break;
    case '/owner/proposals/recover': {
      const d=createLabDispatcher(env);
      if(!d)return reject('conflict');
      return json(await d.ownerRecovery(actor,body));
    }
    case '/owner/telegram/toggle':
      // LAB permits testing policy transitions only. No transport called.
      if(body.enabled && env.REMURA_V3019_LAB_MODE!=='SYNTHETIC_ONLY') return reject('conflict');
      result=await changeTelegramPolicy(env.CONTRIBUTORS_DB,actor,body);
      break;
    case '/owner/review':
      result = await store.review(actor, body, now);
      break;
    case '/owner/invite': {
      const emailTag = await identityTag(key, env, 'email', body.email);
      if (emailTag === actor.email_tag) return reject('conflict');
      result = await store.invite(actor, body.slot, emailTag, now, revision);
      break;
    }
    case '/owner/withdraw':
      result = await store.withdraw(actor, body.slot, now, revision);
      break;
    case '/owner/revoke':
      result = await store.revoke(actor, body, now, revision);
      break;
    case '/api/enroll':
      result = await store.enroll(actor, now, revision);
      break;
  }
  return result ? json(result) : reject('conflict');
}

async function post(req, url, opts) {
  const {store, actor, profile, env} = opts;
  if (!profile.can_write || url.search || !originAllowed(req, url.origin)) return reject();
  const issuing = url.pathname === '/api/intent';
  if (!issuing && ACTIONS.get(url.pathname) !== profile.role) return reject();
  let path, body;
  const time = Math.floor(Date.now() / 1000);
  const now = new Date(time * 1000).toISOString().replace('.000Z', 'Z');
  try {
    const parsed = await requestBody(req);
    if (issuing && !shape(parsed, ['path', 'body'])) return reject('invalid');
    path = issuing ? parsed.path : url.pathname;
    if (ACTIONS.get(path) !== profile.role) return reject();
    body = normalizeAction(path, issuing ? parsed.body : parsed, now);
  } catch {
    return reject('invalid');
  }
  if (issuing) {
    let revision = 0;
    if (SLOT_ACTIONS.has(path)) revision = await store.slotRevision(actor, body.slot);
    if (path === '/api/enroll') revision = opts.inviteRevision;
    if (!Number.isSafeInteger(revision) || revision < 0) return reject();
    return json({intent: await issueIntent(env, actor, profile, path, body, revision, time)});
  }
  const revision = await verifyIntent(env, actor, profile, path, body, req.headers.get('X-Remura-Intent'), time);
  if (revision === null || (path === '/api/enroll' && revision !== opts.inviteRevision)) return reject();
  try {
    return await mutate(path, body, revision, {...opts, now});
  } catch (error) {
    if (error instanceof LevelsStoreError && Object.hasOwn(REQUEST_ERRORS, error.code)) return reject(error.code);
    return unavailable(true);
  }
}

function knownRoute(path, method) {
  if (method === 'POST') return path === '/api/intent' || ACTIONS.has(path);
  if (method !== 'GET') return false;
  if (path === '/' || path === '/api/profile' || READS.has(path)) return true;
  if (['/contributors/legacy/','/contributors/levels/proposal-preview.css','/contributors/levels/proposal-form.mjs','/contributors/levels/proposal-core.mjs'].includes(path))return true;
  return /^\/(?:owner|contributors)\/(?:levels\/|contributors-v110\.(?:css|js))?$/.test(path) ||
    /^\/join\/(?:contributors-v110\.(?:css|js))?$/.test(path);
}

const __default = {
  async fetch(req, env, ctx) {
    let url, identity;
    try {
      url = new URL(req.url);
      if (!ready(env, url) || !knownRoute(url.pathname, req.method) ||
          SENSITIVE_HEADERS.some(name => req.headers.has(name))) return reject();
      identity = await authenticate(ctx, env);
      if (!identity) return reject();
    } catch {
      return reject();
    }
    try {
      if(!await isSyntheticRealm(env.CONTRIBUTORS_DB)) return reject();
      const store = createLevelsStoreV110(env.CONTRIBUTORS_DB);
      const {actor, key} = identity;
      const mayBeInvited = ['/api/profile', '/api/intent', '/api/enroll', '/'].includes(url.pathname) ||
        url.pathname.startsWith('/join/');
      const access = await resolvedProfile(store, actor, writesEnabled(env), mayBeInvited);
      if (!access) return reject();
      if (req.method === 'GET') return await get(req, url, store, actor, access.data, env);
      return await post(req, url, {store, actor, key, env, ctx, profile: access.data, inviteRevision: access.revision});
    } catch (error) {
      if (error instanceof LevelsStoreError && Object.hasOwn(REQUEST_ERRORS, error.code)) return reject(error.code);
      return unavailable(false);
    }
  },
};

return Object.freeze({default:__default});
})();
export default __remura_staging_contributors_v110_lab_mjs.default;
