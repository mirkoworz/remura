// REMURA TradingView v0.8.186 LAB — 21/11/2026 Europe/Rome.
// Pure, offline-only per-decision COT / retail / CVD candidate admission.
// No provider calls, persistence, historical repair, or publishable Worker.
// An asserted timestamp is NOT a verified first-seen receipt or external anchor.
const SCHEMA='remura.tv.decision_evidence_contract.v0186.lab';
const IDENT_FIELDS=['market','provider','ticker','product','contract'];
const HEX=/^[A-Z0-9_.!-]{1,32}$/;
const ISO=/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$/;
const KNOWN=new Set(['SPOT','CFD','FUTURE','INDEX']);

function plain(obj,fields){
 if(!obj||typeof obj!=='object'||Array.isArray(obj)||
    Object.getPrototypeOf(obj)!==Object.prototype)return false;
 const descriptors=Object.getOwnPropertyDescriptors(obj);
 return Object.keys(descriptors).length===fields.length&&
   fields.every(k=>Object.hasOwn(descriptors,k)&&'value' in descriptors[k]);
}
function instant(value){
 if(typeof value!=='string'||!ISO.test(value))return null;
 const n=Date.parse(value);
 return Number.isFinite(n)&&new Date(n).toISOString().slice(0,19)+'Z'===value?n:null;
}
function instrument(obj){
 return plain(obj,IDENT_FIELDS)&&
   ['market','provider','ticker'].every(k=>typeof obj[k]==='string'&&HEX.test(obj[k]))&&
   KNOWN.has(obj.product)&&typeof obj.contract==='string'&&
   (obj.product==='FUTURE'?HEX.test(obj.contract):obj.contract==='');
}
function equalInstrument(a,b){
 return IDENT_FIELDS.every(k=>a[k]===b[k]);
}
function candidate(item,fields,decision){
 if(item===null||item===undefined)return 'UNKNOWN';
 if(!plain(item,[...fields,'instrument'])||!instrument(item.instrument))return 'INVALID_CLAIM';
 if(!equalInstrument(decision.instrument,item.instrument))return 'EXACT_INSTRUMENT_OR_MAPPING_UNVERIFIED';
 return null;
}
function cot(item,decision,at){
 const issue=candidate(item,['report_as_of','published_at','first_seen_at'],decision);
 if(issue)return issue;
 const report=instant(item.report_as_of),pub=instant(item.published_at),seen=instant(item.first_seen_at);
 return report===null||pub===null||seen===null||!(report<=pub&&pub<=seen&&seen<=at)
   ?'LATE_OR_UNVERIFIABLE_TIME_ORDER':'CLAIMED_TIME_ORDER_ONLY';
}
function retail(item,decision,at){
 const issue=candidate(item,['snapshot_at','first_seen_at'],decision);
 if(issue)return issue;
 const snapshot=instant(item.snapshot_at),seen=instant(item.first_seen_at);
 return snapshot===null||seen===null||!(snapshot<=seen&&seen<=at)
   ?'LATE_OR_UNVERIFIABLE_TIME_ORDER':'CLAIMED_TIME_ORDER_ONLY';
}
function cvd(item,decision,at){
 const issue=candidate(item,['bar_close_at','first_seen_at','kind','timeframe'],decision);
 if(issue)return issue;
 const closed=instant(item.bar_close_at),seen=instant(item.first_seen_at);
 if(closed===null||seen===null||!(closed<=seen&&seen<=at))return 'LATE_OR_UNVERIFIABLE_TIME_ORDER';
 if(item.kind==='TRADINGVIEW_CVD'&&item.timeframe==='M5'){
  // Frozen V2: receipt by close+120s and before the NEXT M5 close.
  if(closed%300000!==0||seen>closed+120000||seen>=closed+300000)
   return 'M5_RECEIPT_NOT_ADMISSIBLE';
  return 'CLAIMED_TIME_ORDER_ONLY';
 }
 if(item.kind==='CTRADER_TICK_PROXY'&&item.timeframe==='M15')
  return 'TICK_VOLUME_PROXY_NOT_AGGRESSOR_CVD';
 return 'INCOMPARABLE_CVD_SOURCE_OR_TIMEFRAME';
}
export function reviewDecisionEvidenceV0186(input){
 const out={schema:SCHEMA,version:'0.8.186',mode:'OFFLINE_STRUCTURAL_LAB',
  status:'DECISION_INVALID',cot:'UNKNOWN',retail:'UNKNOWN',cvd:'UNKNOWN',
  data_available_at_decision_verified:false,first_seen_independently_attested:false,
  cross_product_mapping_verified:false,execution_volume_verified:false,
  oracle_or_cloudflare_calls:0,backfill_performed:false,
  protocol_modified:false,scientific_admission:false,edge_established:false,
  live_activation_allowed:false};
 if(!plain(input,['decision','cot','retail','cvd']))return out;
 const d=input.decision;
 if(!plain(d,['at','instrument'])||!instrument(d.instrument))return out;
 const at=instant(d.at);
 if(at===null)return out;
 out.cot=cot(input.cot,d,at);
 out.retail=retail(input.retail,d,at);
 out.cvd=cvd(input.cvd,d,at);
 out.status=[out.cot,out.retail,out.cvd].every(s=>s==='CLAIMED_TIME_ORDER_ONLY')
  ?'THREE_SOURCE_CLAIMS_COMPATIBLE_UNATTESTED':'INCOMPLETE_OR_INCOMPARABLE';
 return out;
}
export const V0186_EVIDENCE_CONTRACT=Object.freeze({schema:SCHEMA,
 comparator:'SAME_EXACT_MARKET_PROVIDER_TICKER_PRODUCT_CONTRACT',
 mappingAcrossProducts:'UNKNOWN_UNTIL_INDEPENDENT_MAPPING_PROOF',
 firstSeenProof:'UNVERIFIED_BY_THIS_MODULE',
 noDefaultExport:true,liveAllowed:false});
