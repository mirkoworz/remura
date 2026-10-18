/* REMURA: separate retail samples, never infer institutional counterparties. */
(function(root,factory){
 const api=factory();
 if(typeof module==="object"&&module.exports)module.exports=api;
 else root.REMURA_SENTIMENT_CORE=api;
})(typeof globalThis!=="undefined"?globalThis:this,function(){
 "use strict";
 function valid(row){
  if(!row||row.lPct===null||row.sPct===null||row.lPct===undefined||row.sPct===undefined)return false;
  const l=Number(row.lPct),s=Number(row.sPct);
  return Number.isFinite(l)&&Number.isFinite(s)&&l>=0&&s>=0&&l<=100&&s<=100&&Math.abs(l+s-100)<=1;
 }
 function ageMs(row,latest,now=Date.now()){
  const when=Date.parse(row?.t||latest);
  return Number.isFinite(when)?now-when:Infinity;
 }
 function fresh(row,latest,now=Date.now()){
  const age=ageMs(row,latest,now);
  return valid(row)&&age>=-300000&&age<=3*3600000;
 }
 function side(long){
  const n=Number(long);
  return !Number.isFinite(n)?"nd":n>=55?"long":n<=45?"short":"equilibrio";
 }
 function compare(retail,capital){
  if(!retail?.fresh||!capital?.fresh||!valid(retail.row)||!valid(capital.row))
   return {status:"unavailable",text:"Confronto non disponibile: servono due rilevazioni recenti e verificate. Nessun segnale inventato."};
  const r=side(retail.row.lPct),c=side(capital.row.lPct);
  const label={long:"long",short:"short",equilibrio:"vicino all'equilibrio"};
  if(r==="equilibrio"||c==="equilibrio")
   return {status:"neutral",text:"Una fonte è vicina all'equilibrio. Myfxbook (lotti): "+label[r]+"; Capital.com (posizioni): "+label[c]+"."};
  if(r!==c)
   return {status:"divergence",text:"DIVERGENZA RETAIL: Myfxbook per volume in lotti prevale "+r+", Capital.com per posizioni prevale "+c+". Non dimostra da che parte siano gli istituzionali."};
  return {status:"aligned",text:"Entrambi i campioni retail prevalgono "+r+", ma misurano unità e comunità differenti. Non è una conferma istituzionale."};
 }
 function points(records,windowMs,now=Date.now()){
  if(!Array.isArray(records))return [];
  const unique=new Map();
  for(const row of records){
   const t=Date.parse(row?.t);
   if(!valid(row)||!Number.isFinite(t)||t>now+300000||t<now-100*86400000)continue;
   if(Number.isFinite(windowMs)&&t<now-windowMs)continue;
   unique.set(row.t,{t:row.t,lPct:Number(row.lPct),sPct:Number(row.sPct),ms:t});
  }
  return [...unique.values()].sort((a,b)=>a.ms-b.ms).slice(-1100);
 }
 return {valid,ageMs,fresh,side,compare,points};
});
