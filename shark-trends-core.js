/* REMURA Shark COT Trends v1.70 LAB — 23/11/2026 15:01 CET (Europe/Rome).
 * Pure weekly CFTC plot geometry; only inputs from existing historyFor().
 * Never bridge absent Tuesdays, estimate a report, infer individual trades or call APIs.
 */
(function(root,factory){
  const api=factory();
  if(typeof module==="object"&&module.exports)module.exports=api;
  if(root)root.REMURA_SHARK_TRENDS=api;
})(typeof window!=="undefined"?window:null,function(){
  "use strict";
  const WEEK=7*86400000;
  const BOX=Object.freeze({width:560,height:220,left:57,right:528,top:17,bottom:176});
  const status=(name,reason)=>({status:name,reason,points:[],series:[],gaps:0,
    axes:null,metric:"NET_POSITION_PCT_OPEN_INTEREST",noInterpolatedPoints:true});
  const round=n=>Math.round(n*100)/100;
  function validRow(row){
    if(!row||typeof row.date!=="string"||!/^\d{4}-\d{2}-\d{2}$/.test(row.date))return null;
    const at=Date.parse(row.date+"T00:00:00Z");
    if(!Number.isFinite(at)||new Date(at).toISOString().slice(0,10)!==row.date||
      new Date(at).getUTCDay()!==2)return null;
    if(!Number.isFinite(row.first)||!Number.isFinite(row.second)||
      Math.abs(row.first)>100||Math.abs(row.second)>100)return null;
    return {at,date:row.date,first:row.first,second:row.second};
  }
  function build(history){
    if(!history||history.status==="QUARANTINE_CONFLICT")
      return status("BLOCKED","Report con conflitti: nessun grafico.");
    if(history.status!=="UNATTESTED_PUBLIC_REPORT_HISTORY"||!Array.isArray(history.rows))
      return status("NO_DATA","Storico CFTC non disponibile.");
    // The core returns exactly the real Tuesday rows in chronological order.
    if(history.rows.length<2)return status("INSUFFICIENT","Servono almeno due report reali.");
    if(history.rows.length>12)return status("INVALID","Troppi report nella vista.");
    const rows=history.rows.map(validRow);
    if(rows.some(x=>!x))return status("INVALID","Data o percentuale CFTC non valida.");
    for(let i=1;i<rows.length;i++){
      if(rows[i].at<=rows[i-1].at)return status("INVALID","Report non ordinati o duplicati.");
    }
    const start=rows[0].at,end=rows.at(-1).at,span=end-start;
    if(span<=0)return status("INVALID","Intervallo temporale insufficiente.");
    const all=rows.flatMap(r=>[r.first,r.second]);
    const dataLow=Math.min(0,...all),dataHigh=Math.max(0,...all);
    const pad=Math.max(2,(dataHigh-dataLow)*0.09);
    const low=Math.max(-100,dataLow-pad),high=Math.min(100,dataHigh+pad);
    if(!(high>low))return status("INVALID","Intervallo percentuale non valido.");
    const x=at=>round(BOX.left+(at-start)/span*(BOX.right-BOX.left));
    const y=value=>round(BOX.bottom-(value-low)/(high-low)*(BOX.bottom-BOX.top));
    const points=rows.map((r,i)=>({
      date:r.date,at:r.at,first:round(r.first),second:round(r.second),
      x:x(r.at),firstY:y(r.first),secondY:y(r.second),
      consecutive:i===0?null:r.at-rows[i-1].at===WEEK
    }));
    const gaps=points.slice(1).filter(p=>!p.consecutive).length;
    const series=["first","second"].map(key=>{
      const segments=[];
      let run=[];
      for(const p of points){
        if(p.consecutive===false&&run.length){segments.push(run);run=[];}
        run.push({date:p.date,x:p.x,y:key==="first"?p.firstY:p.secondY,value:p[key]});
      }
      if(run.length)segments.push(run);
      return {key,segments};
    });
    return {status:"READY",reason:null,points,series,gaps,
      axes:{...BOX,low:round(low),high:round(high),zeroY:low<=0&&high>=0?y(0):null},
      startDate:rows[0].date,endDate:rows.at(-1).date,
      metric:"NET_POSITION_PCT_OPEN_INTEREST",
      source:"CFTC_PUBLIC_WEEKLY_HISTORY",firstSeenVerified:false,
      noInterpolatedPoints:true,tradeTimingVerified:false,tradingSignal:false};
  }
  return Object.freeze({build});
});