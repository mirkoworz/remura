/* REMURA v1.14: pure, testable classification of factual cTrader metadata. */
(function(root){
 "use strict";
 const LIMIT_MINUTES=180; // Rotation of 8 batches ~120 min, 60 min buffer.
 const OUTCOMES=Object.freeze({
   ok:"Salvataggio riuscito",
   ticker_unavailable:"Ticker non riconosciuto dal conto",
   no_historical_bars:"Nessuna candela storica restituita",
   incomplete_history:"Risposta storica incompleta",
   invalid_bars:"Candele non valide",
   request_failed:"Richiesta cTrader non riuscita",
   unknown_error:"Tentativo non riuscito, causa non determinata"
 });
 function interpret(market,serverTime){
   const count=Number(market?.counts?.M15)||0;
   const ts=Date.parse(market?.lastComplete||"");
   const now=Date.parse(serverTime||"");
   if(!count||!Number.isFinite(ts))
     return {state:"missing",age:null};
   if(!Number.isFinite(now)||ts>now+5*60*1000)
     return {state:"stale",age:null};
   const age=Math.max(0,Math.floor((now-ts)/60000));
   return {state:age<=LIMIT_MINUTES?"recent":"stale",age};
 }
 function summarize(markets,serverTime){
   const counts={recent:0,stale:0,missing:0};
   for(const market of markets||[])counts[interpret(market,serverTime).state]++;
   return counts;
 }
 const api=Object.freeze({LIMIT_MINUTES,OUTCOMES,interpret,summarize});
 if(typeof module==="object"&&module.exports)module.exports=api;
 if(root)root.REMURA_PRICE_STATUS_CORE=api;
})(typeof window==="undefined"?null:window);
