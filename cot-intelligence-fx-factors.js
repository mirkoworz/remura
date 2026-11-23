/* REMURA Filone B v21.0 LAB — 23/11/2026 Europe/Rome
 * Seven unique FX futures vs 28 overlapping synthetic cross views.
 * Pure/offline; no price engine, no market fetch, no BUY/SELL.
 */
(function(root){"use strict";
const core=typeof module!=="undefined"&&module.exports?require("./cot-intelligence-core.js"):root.REMURA_COT_INTELLIGENCE;
const watch=typeof module!=="undefined"&&module.exports?require("./cot-intelligence-watchlist.js"):root.REMURA_COT_WATCHLIST;
function build(snapshot,options={}){
 const w=watch.build(snapshot,options);
 const meta={schema:"remura-cot-fx-factors-v1",mode:w.mode,source:w.source,
  observedAt:w.observedAt??null,publicReadAtUtc:w.publicReadAtUtc??null,
  reportDate:w.periods?.tff?.latest??null,previousReportDate:w.periods?.tff?.previous??null,
  basis:"7 distinct currency futures versus USD; 28 overlapping synthetic FX pairs",
  disclaimer:"Net%/OI futures positioning, not spot Forex, live flows, independent signals or forecast"};
 const blocked=reason=>({...meta,state:"blocked",reason,factors:[],pairs:[]});
 if(w.periods?.tff?.state!=="complete")return blocked(w.periods?.tff?.state??"no_tff_data");
 const pairGroup=w.groups.find(x=>x.id==="fx_relative");
 if(!pairGroup||pairGroup.state==="blocked"||pairGroup.entries.length!==core.PAIRS.length)
  return blocked("incomplete_fx_crosses");
 const parsed=core.parseRows(snapshot.rows,options.observedAt?Date.parse(options.observedAt):null);
 if(parsed.rejected)throw Error("INVALID_FX_FACTOR_INPUT");
 const percent=(r,cat)=>100*((cat==="A"?r.aLong-r.aShort:r.bLong-r.bShort)/r.oi);
 const factors=[];
 for(const [currency,code] of Object.entries(core.FX)){
  const rows=parsed.indexed.get("tff|"+code);
  if(!rows)return blocked("missing_futures_"+currency);
  const current=rows.get(meta.reportDate),previous=rows.get(meta.previousReportDate);
  if(!current||!previous)return blocked("missing_comparison_"+currency);
  const history=[...rows.values()].sort((a,b)=>a.date.localeCompare(b.date));
  const tail=history.slice(-52);
  const validHistory=tail.length===52&&tail.at(-1).date===meta.reportDate&&
   tail.slice(1).every((r,i)=>{
    const gap=(Date.parse(r.date+"T00:00:00Z")-Date.parse(tail[i].date+"T00:00:00Z"))/86400000;
    return gap>=5&&gap<=9;
   });
  factors.push({
   currency,code,reportDate:meta.reportDate,previousReportDate:meta.previousReportDate,
   netAssetManagersPp:percent(current,"A"),netLeveragedFundsPp:percent(current,"B"),
   weeklyAssetManagersPp:percent(current,"A")-percent(previous,"A"),
   weeklyLeveragedFundsPp:percent(current,"B")-percent(previous,"B"),
   openInterestContracts:current.oi,openInterestDeltaContracts:current.oi-previous.oi,
   cotIndex52AssetManagers:validHistory?core.cotIndex(tail.map(r=>percent(r,"A"))):null,
   historicalStatus:validHistory?"ok":tail.length<52?"insufficient":"gapped_history",
   localFirstSeenAtUtc:current.seen===null?null:new Date(current.seen).toISOString(),
   previousLocalFirstSeenAtUtc:previous.seen===null?null:new Date(previous.seen).toISOString()
  });
 }
 const by=Object.fromEntries(factors.map(f=>[f.currency,f]));
 const factor=(c,k)=>c==="USD"?0:by[c][k];
 const pairs=[];
 for(const symbol of core.PAIRS){
  const base=symbol.slice(0,3),quote=symbol.slice(3);
  const reference=pairGroup.entries.find(e=>e.symbol===symbol);
  if(!reference)throw Error("MISSING_SYNTHETIC_CROSS:"+symbol);
  const a=factor(base,"weeklyAssetManagersPp")-factor(quote,"weeklyAssetManagersPp");
  const b=factor(base,"weeklyLeveragedFundsPp")-factor(quote,"weeklyLeveragedFundsPp");
  if(Math.abs(reference.deltaA_Pp-a)>1e-8||Math.abs(reference.deltaB_Pp-b)>1e-8)
   throw Error("CROSS_FACTOR_DECOMPOSITION_MISMATCH:"+symbol);
  pairs.push({symbol,reportDate:meta.reportDate,
   underlyingCurrencies:[base,quote].filter(c=>c!=="USD"),
   componentSigns:[base,quote].filter(c=>c!=="USD").map(c=>({currency:c,weight:c===base?1:-1})),
   weeklyAssetManagersPp:a,weeklyLeveragedFundsPp:b,
   derivation:"base_futures_change_minus_quote_futures_change; USD zero is a mathematical reference"
  });
 }
 factors.sort((a,b)=>Math.abs(b.weeklyAssetManagersPp)-Math.abs(a.weeklyAssetManagersPp)||a.currency.localeCompare(b.currency));
 const occurrence=Object.fromEntries(Object.keys(core.FX).map(currency=>[
  currency,pairs.filter(p=>p.underlyingCurrencies.includes(currency)).length
 ]));
 return {...meta,state:"descriptive_ready",uniqueUnderlyingCount:7,syntheticPairCount:pairs.length,
  factors,pairs,occurrence,
  notes:["Seven separate CFTC contract codes; economic factors may still be correlated",
   "Every synthetic cross is exactly reconstructible from two component futures versus USD",
   "Cross reuse must never count as 28 statistically independent positioning movements",
   "First local capture, when present, does not prove official CFTC publication or unchanged historical values",
   "No price direction, leverage guidance, win probability or alpha claim"]};
}
const api={build};
if(typeof module!=="undefined"&&module.exports)module.exports=api;
if(root)root.REMURA_COT_FX_FACTORS=api;
})(typeof window!=="undefined"?window:null);
