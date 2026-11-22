/* REMURA Shark Movers v1.67 LAB — 22/11/2026 21:41 CET.
 * Instant browser-only summary of existing CFTC report cards. No fetch.
 * Readable grouped COT deltas are not order flow or trading signals.
 */
(function(root, factory) {
  "use strict";
  const api=factory();
  if(typeof module==="object"&&module.exports)module.exports=api;
  root.REMURA_SHARK_MOVERS=api;
})(typeof window!=="undefined"?window:globalThis,function(){
  "use strict";
  const ALLOWED=new Set(["CURRENT_REPORT_DATE"]);
  function validDate(s){
    if(typeof s!=="string"||!/^\d{4}-\d{2}-\d{2}$/.test(s))return false;
    const x=Date.parse(s+"T00:00:00Z");
    return Number.isFinite(x)&&new Date(x).toISOString().slice(0,10)===s;
  }
  function scan(cards,{favoritesOnly=false,favorites=[],limit=6}={}){
    if(!Array.isArray(cards)||!Number.isInteger(limit)||limit<1||limit>14||
       !Array.isArray(favorites)||favorites.length>14)
      return {status:"NO_VERIFIED_WEEKLY_INPUT",reportDate:null,items:[],alignedContracts:0,
        excludedOtherWeeks:0,readyContracts:0,sourceTimeAttested:false,
        institutionalOrderFlow:false,tradingSignal:false};
    const fav=new Set(favorites.filter(x=>typeof x==="string"&&/^[A-Z0-9]{6}$/.test(x)));
    const ready=cards.filter(x=>x&&ALLOWED.has(x.status)&&validDate(x.reportDate)&&
      typeof x.code==="string"&&/^[A-Z0-9]{6}$/.test(x.code)&&
      Array.isArray(x.labels)&&x.labels.length===2&&
      x.deltas&&Number.isFinite(x.deltas.first)&&Number.isFinite(x.deltas.second)&&
      (!favoritesOnly||fav.has(x.code)));
    if(!ready.length)return {
      status:favoritesOnly&&fav.size===0?"WATCHLIST_EMPTY":"NO_VERIFIED_WEEKLY_INPUT",
      reportDate:null,items:[],alignedContracts:0,excludedOtherWeeks:0,readyContracts:0,
      sourceTimeAttested:false,institutionalOrderFlow:false,tradingSignal:false
    };
    const reportDate=ready.map(x=>x.reportDate).sort().at(-1);
    const sameWeek=ready.filter(x=>x.reportDate===reportDate);
    const moves=sameWeek.map(x=>{
      const primary=Math.abs(x.deltas.first)>=Math.abs(x.deltas.second)?"first":"second";
      const value=x.deltas[primary];
      return {code:x.code,id:x.id,name:x.name,dataset:x.dataset,
        category:x.labels[primary==="first"?0:1],
        netChangePp:value,absChangePp:Math.abs(value),
        direction:value>0?"NET_INCREASE":value<0?"NET_DECREASE":"UNCHANGED",
        reportDate,source:x.source,
        claim:"AGGREGATE_FUTURES_NET_POSITION_CHANGE_ONLY",
        firstSeenVerified:false,spotMappingVerified:false,tradingSignal:false};
    }).filter(x=>x.absChangePp>0)
      .sort((a,b)=>b.absChangePp-a.absChangePp||a.code.localeCompare(b.code));
    return {status:moves.length?"PUBLIC_COT_MOVERS_DESCRIPTIVE":"NO_NET_CHANGES",
      reportDate,items:moves.slice(0,limit),alignedContracts:sameWeek.length,
      excludedOtherWeeks:ready.length-sameWeek.length,readyContracts:ready.length,
      sourceTimeAttested:false,institutionalOrderFlow:false,tradingSignal:false};
  }
  return Object.freeze({scan});
});