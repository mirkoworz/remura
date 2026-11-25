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
 function cleanCapitalLatest(doc,allowed,now=Date.now()){
  if(doc?.status!=="ok"||doc.environment!=="demo"||!doc.symbols||
     typeof doc.symbols!=="object"||Array.isArray(doc.symbols)||
     !Array.isArray(allowed)||allowed.length>60)
   throw Error("Il file non è un archivio Capital.com DEMO valido");
  const rootTime=Date.parse(doc.updatedAt);
  if(!Number.isFinite(rootTime)||rootTime>now+300000||rootTime<now-100*86400000)
   throw Error("Data archivio non valida");
  const symbols={};
  for(const sym of allowed){
   if(!/^[A-Z0-9]{3,8}$/.test(sym))continue;
   const row=doc.symbols[sym];
   if(!valid(row))continue;
   const epoch=Date.parse(row.t||doc.updatedAt);
   if(!Number.isFinite(epoch)||epoch>now+300000||epoch<now-100*86400000)continue;
   symbols[sym]={t:new Date(epoch).toISOString(),
    lPct:Number(row.lPct),sPct:Number(row.sPct),metric:"client_positions"};
  }
  if(Object.keys(symbols).length===0)throw Error("Nessun mercato REMURA valido nel file");
  return {status:"ok",environment:"demo",source:"Capital.com Client Sentiment",
   updatedAt:new Date(rootTime).toISOString(),symbols};
 }
 function cleanCapitalHistory(doc,symbol,now=Date.now()){
  if(!/^[A-Z0-9]{3,8}$/.test(symbol)||doc?.symbol!==symbol||
    !Array.isArray(doc.records)||doc.records.length>5000)
   throw Error("File storico non corrispondente allo strumento");
  const records=points(doc.records,Infinity,now).map(p=>({
   t:p.t,lPct:p.lPct,sPct:p.sPct,metric:"client_positions"
  }));
  if(!records.length)throw Error("Lo storico non contiene osservazioni valide");
  return {symbol,source:"Capital.com Client Sentiment",records};
 }
 return {valid,ageMs,fresh,side,compare,points,cleanCapitalLatest,cleanCapitalHistory};
});
