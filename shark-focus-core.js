/* REMURA Shark Focus v1.71 LAB — 23/11/2026 20:20 CET (Europe/Rome).
 * Browser-only watchlist view over the CFTC card objects already loaded.
 * No fetch, new market metrics, predictive rank, storage or institution identities.
 */
(function(root,factory){
  const contracts=(typeof module==="object"&&module.exports)?
    require("./shark-cockpit-core.js"):(root&&root.REMURA_SHARK_CORE);
  const api=factory(contracts);
  if(typeof module==="object"&&module.exports)module.exports=api;
  if(root)root.REMURA_SHARK_FOCUS=api;
})(typeof window!=="undefined"?window:null,function(core){
  "use strict";
  const round=n=>Math.round(n*100)/100;
  const QUALITY={CONFRONTABILE:0,SOLO_REPORT:1,DATATO:2,CONFLITTO:3,NON_DISPONIBILE:4};
  function classify(card){
    if(!card)return "NON_DISPONIBILE";
    if(card.status==="QUARANTINE_CONFLICT")return "CONFLITTO";
    if(card.status==="STALE_REPORT")return "DATATO";
    if(card.status==="CURRENT_REPORT_DATE"&&
       card.deltas&&Number.isFinite(card.deltas.first)&&Number.isFinite(card.deltas.second))
      return "CONFRONTABILE";
    if(card.status==="CURRENT_REPORT_DATE"||card.status==="UNKNOWN_WEEKLY_COMPARISON")
      return "SOLO_REPORT";
    return "NON_DISPONIBILE";
  }
  function build(cards=[],favorites=[]){
    const legal=core&&typeof core.parseFavorites==="function"?
      core.parseFavorites(JSON.stringify(Array.isArray(favorites)?favorites:[])):[];
    const known=new Map((Array.isArray(cards)?cards:[]).filter(x=>x&&typeof x.code==="string")
      .map(x=>[x.code,x]));
    const items=legal.map(code=>{
      const c=known.get(code)||null;
      const quality=classify(c),ready=quality==="CONFRONTABILE";
      const deltas=ready?{first:round(c.deltas.first),second:round(c.deltas.second)}:null;
      return {code,name:c?.name||core.CONTRACTS.find(x=>x.code===code)?.name||code,
        family:c?.family||null,dataset:c?.dataset||null,
        labels:Array.isArray(c?.labels)?c.labels.slice(0,2):[],
        reportDate:c?.reportDate||null,quality,deltas,
        comparison:ready?c.comparison:null,
        ageDays:Number.isFinite(c?.ageDays)?c.ageDays:null,
        magnitudePp:ready?Math.max(Math.abs(deltas.first),Math.abs(deltas.second)):null,
        institutionIdentitiesKnown:false,priceDirectionKnown:false,
        tradingSignal:false};
    });
    items.sort((a,b)=>QUALITY[a.quality]-QUALITY[b.quality]||
      (b.reportDate||"").localeCompare(a.reportDate||"")||
      ((b.magnitudePp||0)-(a.magnitudePp||0))||
      a.code.localeCompare(b.code));
    const comparable=items.filter(x=>x.quality==="CONFRONTABILE").length;
    const onlyReport=items.filter(x=>x.quality==="SOLO_REPORT").length;
    const dates=[...new Set(items.filter(x=>x.quality==="CONFRONTABILE"&&x.reportDate)
      .map(x=>x.reportDate))].sort();
    return {state:!items.length?"EMPTY":comparable?"PARTIAL_OR_READY":"UNVERIFIED",
      count:items.length,comparable,onlyReport,
      unavailable:items.length-comparable-onlyReport,
      distinctComparableReportDates:dates,
      differentReportWeeks:dates.length>1,
      items,rankingMeaning:"DISPLAY_ORDER_ONLY",source:"CFTC_PUBLIC_WEEKLY_SNAPSHOTS",
      measuredLiveOrders:false,tradingSignal:false,
      disclaimer:"L'ordine raggruppa qualità e date, poi ampiezza in pp nello stesso martedì. Non è una classifica di opportunità o probabilità."};
  }
  return Object.freeze({build,classify});
});