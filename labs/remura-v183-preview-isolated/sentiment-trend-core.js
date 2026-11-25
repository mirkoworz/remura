/* REMURA v1.4 — temporal retail momentum: real observations only. */
(function(root,factory){
 const api=factory();
 if(typeof module==="object"&&module.exports)module.exports=api;
 else root.REMURA_SENTIMENT_TREND=api;
})(typeof globalThis!=="undefined"?globalThis:this,function(){
 "use strict";
 const HOUR=3600000,DAY=24*HOUR;
 const PERIODS=[{id:"6h",hours:6,tolerance:2.5},{id:"24h",hours:24,tolerance:5},
  {id:"72h",hours:72,tolerance:12},{id:"7g",hours:168,tolerance:28}];
 function valid(row){
  if(!row||row.lPct==null||row.sPct==null)return false;
  const l=Number(row.lPct),s=Number(row.sPct);
  return Number.isFinite(l)&&Number.isFinite(s)&&l>=0&&s>=0&&l<=100&&s<=100&&Math.abs(l+s-100)<=1;
 }
 function points(history,current,now=Date.now()){
  const out=new Map();
  for(const row of [...(Array.isArray(history)?history:[]),...(current?[current]:[])]){
   const ms=Date.parse(row?.t);
   if(!valid(row)||!Number.isFinite(ms)||ms>now+5*60000||ms<now-90*DAY)continue;
   out.set(ms,{...row,ms,lPct:Number(row.lPct),sPct:Number(row.sPct)});
  }
  return [...out.values()].sort((a,b)=>a.ms-b.ms);
 }
 function analyze(history,current,periodId,now=Date.now()){
  const period=PERIODS.find(p=>p.id===periodId);
  if(!period)throw Error("Periodo non supportato");
  const records=points(history,current,now);
  const last=records[records.length-1];
  const empty={available:false,periodId,hours:period.hours,samples:records.length,
   reason:records.length<2?"Servono almeno due rilevazioni reali.":"Nessuna rilevazione sufficientemente vicina all'inizio del periodo."};
  if(!last||records.length<2)return empty;
  const target=last.ms-period.hours*HOUR;
  const candidates=records.slice(0,-1).filter(p=>Math.abs(p.ms-target)<=period.tolerance*HOUR);
  if(!candidates.length)return empty;
  const first=candidates.reduce((best,p)=>Math.abs(p.ms-target)<Math.abs(best.ms-target)?p:best);
  const delta=+(last.lPct-first.lPct).toFixed(2);
  const aged=now-last.ms>3*HOUR||last.ms>now+5*60000;
  const lowSample=[first,last].some(p=>p.lPos!=null&&p.sPos!=null&&
   Number.isFinite(+p.lPos)&&Number.isFinite(+p.sPos)&&+p.lPos>=0&&+p.sPos>=0&&(+p.lPos)+(+p.sPos)<30);
  let direction="stabile",headline="Sentiment sostanzialmente stabile";
  if(delta<=-2){
   direction="short";headline=first.lPct>50&&last.lPct<50?
    "Passaggio da maggioranza LONG a SHORT":"Spostamento retail verso SHORT";
  }else if(delta>=2){
   direction="long";headline=first.lPct<50&&last.lPct>50?
    "Passaggio da maggioranza SHORT a LONG":"Spostamento retail verso LONG";
  }
  const lots=(key)=>first[key]!=null&&last[key]!=null&&Number.isFinite(+first[key])&&
   Number.isFinite(+last[key])&&+first[key]>=0&&+last[key]>=0?
   +(+last[key]-(+first[key])).toFixed(2):null;
  return {available:true,periodId,hours:period.hours,first,last,deltaLong:delta,
   deltaShort:+(last.sPct-first.sPct).toFixed(2),direction,headline,
   strength:Math.abs(delta)>=5?"marcato":Math.abs(delta)>=2?"moderato":"limitato",
   elapsedHours:+((last.ms-first.ms)/HOUR).toFixed(1),
   samples:records.filter(p=>p.ms>=first.ms&&p.ms<=last.ms).length,
   stale:aged,lowSample,deltaLongLots:lots("lLots"),deltaShortLots:lots("sLots")};
 }
 function recommend(inputs,now=Date.now()){
  const series=Array.isArray(inputs)?inputs:[];
  for(const id of ["24h","6h","72h","7g"]){
   const checks=series.filter(s=>s&&s.current).map(s=>analyze(s.history,s.current,id,now));
   if(checks.length>=2&&checks.every(a=>a.available))return id;
  }
  for(const id of ["24h","6h","72h","7g"]){
   if(series.some(s=>s&&analyze(s.history,s.current,id,now).available))return id;
  }
  return "24h";
 }
 function joint(a,b){
  if(!a?.available||!b?.available)return "Confronto del cambiamento non disponibile per entrambe le fonti in questa finestra.";
  if(a.stale||b.stale)return "Almeno una fonte è datata: non usare l'eventuale concordanza come segnale attuale.";
  if(a.lowSample||b.lowSample)return "Campione troppo piccolo in almeno una fonte: confronto non affidabile.";
  if(a.direction===b.direction&&a.direction!=="stabile")
   return "Le due comunità retail si spostano entrambe verso "+a.direction.toUpperCase()+
    ", ma su metriche diverse: non prova la direzione degli istituzionali.";
  if(a.direction!=="stabile"&&b.direction!=="stabile"&&a.direction!==b.direction)
   return "DIVERGENZA: le due comunità retail si muovono in direzioni opposte. Non forzare un segnale.";
  return "Nessuna direzione comune sufficientemente chiara tra le due fonti retail.";
 }
 return {PERIODS,valid,points,analyze,recommend,joint};
});
