/* REMURA v1.22: pure, testable classification of factual cTrader metadata. */
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
 const macro=(function(){
const HOUR=3600000,QUARTER=900000;
const TFS=Object.freeze({M15:QUARTER,H1:HOUR,H4:4*HOUR});
const finite=v=>typeof v==="number"&&Number.isFinite(v);
const time=v=>Date.parse(v);
function validBar(b,duration){
 if(!b||typeof b!=="object")return false;
 const t=time(b.t);
 if(!Number.isFinite(t)||t%duration!==0)return false;
 if(!["o","h","l","c"].every(k=>finite(b[k])&&b[k]>0))return false;
 return b.h>=Math.max(b.o,b.c,b.l)&&b.l<=Math.min(b.o,b.c,b.h);
}
function timeframe(bars,tf){
 if(!Array.isArray(bars))return {valid:false,rows:[],bad:1,duplicates:0};
 const step=TFS[tf],rows=bars.filter(x=>validBar(x,step)).sort((a,b)=>time(a.t)-time(b.t));
 let duplicates=0;
 for(let i=1;i<rows.length;i++)if(time(rows[i].t)===time(rows[i-1].t))duplicates++;
 return {valid:rows.length===bars.length&&duplicates===0,rows,bad:bars.length-rows.length,duplicates};
}
// Only the immediately preceding Friday late session may be displayed as a
// clearly marked *historical* weekend snapshot. Not an exchange calendar:
 // broker instruments may have different sessions or expiring contracts.
function romeParts(value){
 const d=new Intl.DateTimeFormat("en-US",{
  timeZone:"Europe/Rome",weekday:"short",hour:"2-digit",hourCycle:"h23"
 }).formatToParts(new Date(value));
 const get=type=>d.find(x=>x.type===type)?.value;
 return {weekday:get("weekday"),hour:Number(get("hour"))};
}
function weekendSnapshot(lastClosed,now){
 if(!Number.isFinite(lastClosed)||!Number.isFinite(now)||
    lastClosed>now+5*60000||now-lastClosed>72*HOUR)return false;
 const today=romeParts(now),last=romeParts(lastClosed);
 return (today.weekday==="Sat"||today.weekday==="Sun")&&
   last.weekday==="Fri"&&last.hour>=16;
}
function audit(doc,now=Date.now()){
 if(!doc||typeof doc!=="object"||!doc.timeframes)return {state:"missing",counts:{M15:0,H1:0,H4:0}};
 const frames=Object.fromEntries(Object.keys(TFS).map(k=>[k,timeframe(doc.timeframes[k],k)]));
 const M15=frames.M15.rows, H1=frames.H1.rows, H4=frames.H4.rows;
 if(!M15.length)return {state:"missing",counts:{M15:0,H1:H1.length,H4:H4.length}};
 const last=time(M15[M15.length-1].t),ageMinutes=Math.floor((now-(last+QUARTER))/60000);
 const recent=M15.slice(-97);
 let gaps=0,maxGap=0;
 for(let i=1;i<recent.length;i++){
  const delta=(time(recent[i].t)-time(recent[i-1].t))/60000;
  if(delta!==15){gaps++;maxGap=Math.max(maxGap,delta);}
 }
 const byM15=new Map(M15.map(x=>[time(x.t),x]));
 function checkRollup(rows,parts){
  let verified=0,missingInputs=0,mismatched=0;
  for(const row of rows.slice(-30)){
   const start=time(row.t),sub=Array.from({length:parts},(_,i)=>byM15.get(start+i*QUARTER));
   if(sub.some(x=>!x)){missingInputs++;continue;}
   const values={o:sub[0].o,h:Math.max(...sub.map(x=>x.h)),l:Math.min(...sub.map(x=>x.l)),c:sub[parts-1].c};
   const same=Object.keys(values).every(k=>Math.abs(values[k]-row[k])<=1e-9*Math.max(1,Math.abs(values[k])));
   if(same)verified++;else mismatched++;
  }
  return {verified,missingInputs,mismatched,checked:Math.min(30,rows.length)};
 }
 const h1=checkRollup(H1,4),h4=checkRollup(H4,16);
 const malformed=Object.values(frames).some(x=>!x.valid);
 const inconsistent=h1.mismatched>0||h4.mismatched>0||malformed;
 const state=inconsistent?"invalid":ageMinutes< -5||!Number.isFinite(ageMinutes)?"invalid":
  weekendSnapshot(last+QUARTER,now)?"weekend":ageMinutes>180?"stale":"recent";
 return {state,counts:{M15:M15.length,H1:H1.length,H4:H4.length},
  ageMinutes,asof:new Date(last).toISOString(),recentGaps:gaps,largestGapMinutes:maxGap,
  h1,h4,malformed,ready:H4.length>=55&&H1.length>=55&&M15.length>=55};
}
function returns(doc){
 const frame=timeframe(doc?.timeframes?.H1,"H1");
 if(!frame.valid)return new Map();
 const m=new Map();
 for(let i=1;i<frame.rows.length;i++){
  const prev=frame.rows[i-1],curr=frame.rows[i],t=time(curr.t);
  if(t-time(prev.t)!==HOUR)continue;
  m.set(t,Math.log(curr.c/prev.c));
 }
 return m;
}
function correlation(a,b,{now=Date.now(),hours=336,minPoints=30}={}){
 const x=returns(a),y=returns(b),threshold=now-hours*HOUR;
 const shared=[...x.keys()].filter(t=>t>=threshold&&t<=now&&y.has(t)).sort((a,b)=>a-b);
 if(shared.length<minPoints)return {state:"insufficient",samples:shared.length,value:null};
 let n=0,meanX=0,meanY,sXX=0,sYY=0,sXY=0;
 meanY=0;
 for(const t of shared){
  n++;
  const vx=x.get(t),vy=y.get(t),dx=vx-meanX,dy=vy-meanY;
  meanX+=dx/n;meanY+=dy/n;
  sXX+=dx*(vx-meanX);sYY+=dy*(vy-meanY);sXY+=dx*(vy-meanY);
 }
 if(sXX<=1e-20||sYY<=1e-20)return {state:"insufficient",samples:n,value:null};
 const v=Math.max(-1,Math.min(1,sXY/Math.sqrt(sXX*sYY)));
 return {state:"ok",samples:n,value:+v.toFixed(3),
   from:new Date(shared[0]).toISOString(),to:new Date(shared[shared.length-1]).toISOString()};
}

function describeCorrelation(observation,benchmark){
 // Qualitative magnitudes are only explanatory bins, never calibrated trade signals.
 if(observation?.state!=="ok"||!Number.isFinite(observation.value)||
    Math.abs(observation.value)>1||!Number.isInteger(observation.samples)||observation.samples<30)
  return {state:"unavailable",label:"Relazione non valutabile",
    detail:"Servono almeno 30 rendimenti H1 comuni e serie coerenti e ammissibili.",strength:null};
 const r=observation.value,abs=Math.abs(r),n=observation.samples;
 const direction=abs<0.1?"none":r>0?"positive":"negative";
 const strength=abs<0.1?"quasi nulla":abs<0.3?"debole":abs<0.7?"moderata":"elevata";
 const label=direction==="none"?"Relazione lineare quasi nulla":
  "Relazione "+(direction==="positive"?"positiva":"inversa")+" "+strength;
 let detail;
 if(direction==="none")
  detail="Nella finestra osservata i rendimenti orari non mostrano una relazione lineare apprezzabile.";
 else if(direction==="negative")
  detail="Nel campione osservato, quando "+benchmark+" saliva questo mercato tendeva a scendere, e viceversa.";
 else
  detail="Nel campione osservato, "+benchmark+" e questo mercato tendevano a muoversi nella stessa direzione.";
 return {state:"ok",direction,strength,label,detail,samples:n,value:r};
}
function compareMacroRelationships(symbol,dxy,vix){
 const dollar=describeCorrelation(dxy,"DXY"),fear=describeCorrelation(vix,"VIX");
 const validD=dollar.state==="ok",validV=fear.state==="ok";
 if(!validD&&!validV)return {state:"unavailable",title:symbol+": confronto non disponibile",
  summary:"Impossibile interpretare i rapporti senza dati recenti o un'ultima sessione valida per ciascuna coppia.",dollar,fear};
 if(validD&&validV){
  const difference=Math.abs(vix.value)-Math.abs(dxy.value);
  const relative=Math.abs(difference)>=0.2?
   difference>0?"VIX":"DXY":null;
  return {state:"ok",title:"Come leggere le correlazioni di "+symbol,
   summary:relative?
    "Nella finestra osservata "+relative+" ha mostrato l'associazione lineare più marcata con "+symbol+
    ". I campioni e gli orari comuni delle due coppie possono essere diversi; questo non è un segnale operativo.":
    "Nella finestra osservata l'intensità delle due associazioni è simile. Non basta per attribuire una direzione futura a "+symbol+".",
   dollar,fear};
 }
 return {state:"partial",title:"Confronto parziale di "+symbol,
  summary:"Solo uno dei due confronti ha dati utilizzabili. Evitare conclusioni sulla relazione con l'altro indicatore.",
  dollar,fear};
}
function pairEligible(a,b,now=Date.now()){
 const valid=new Set(["recent","weekend"]);
 return valid.has(audit(a,now).state)&&valid.has(audit(b,now).state);
}

function pulse(doc,{now=Date.now(),period=4}={}){
 const quality=audit(doc,now);
 if(quality.state!=="recent"&&quality.state!=="weekend")
  return {state:"unavailable",direction:null,changePct:null,referencePct:null};
 const frame=timeframe(doc?.timeframes?.H1,"H1");
 if(!frame.valid)return {state:"unavailable",direction:null,changePct:null,referencePct:null};
 const rows=frame.rows;
 const changes=[];
 for(let i=period;i<rows.length;i++){
  let contiguous=true;
  for(let j=i-period+1;j<=i;j++)if(time(rows[j].t)-time(rows[j-1].t)!==HOUR){contiguous=false;break;}
  if(contiguous)changes.push({stamp:rows[i].t,pct:(rows[i].c/rows[i-period].c-1)*100,index:i});
 }
 const recent=changes.at(-1);
 if(!recent||recent.index!==rows.length-1||changes.length<12)
  return {state:"insufficient",direction:null,changePct:null,referencePct:null};
 const values=changes.slice(-80).map(x=>Math.abs(x.pct)).sort((a,b)=>a-b);
 const mid=values.length>>1;
 const median=values.length%2?values[mid]:(values[mid-1]+values[mid])/2;
 const changePct=recent.pct,referencePct=median;
 const direction=Math.abs(changePct)<=median?"flat":changePct>0?"up":"down";
 return {state:"ok",direction,changePct:+changePct.toFixed(3),
  referencePct:+referencePct.toFixed(3),asof:recent.stamp,samples:values.length,
  historical:quality.state==="weekend"};
}
function describeContext(dollar,fear){
 // "flat" means a 4-hour move not larger than the instrument's own
 // recent median absolute 4-hour move. It does NOT mean zero change.
 const valid=new Set(["up","down","flat"]);
 if(dollar?.state!=="ok"||fear?.state!=="ok"||
    !valid.has(dollar.direction)||!valid.has(fear.direction))
  return {state:"unavailable",dollar,fear,label:"Dati insufficienti per valutare il contesto",
   description:"Servono candele fresche e almeno 12 intervalli storici validi di quattro ore per entrambi gli indicatori."};
 const d=dollar.direction,v=fear.direction;
 let result;
 if(v==="up"&&d==="up")
  result=["caution","Volatilità e dollaro in aumento",
   "Combinazione compatibile con alcune fasi di avversione al rischio. Non prova vendite istituzionali né anticipa necessariamente un ribasso."];
 else if(v==="down"&&d==="down")
  result=["calm","Volatilità e dollaro in calo",
   "Combinazione compatibile con una distensione, ma non dimostra da sola una propensione al rischio o un segnale long."];
 else if(v==="flat"&&d==="flat")
  result=["neutral","DXY e VIX senza variazioni significative",
   "Entrambi i movimenti sono contenuti rispetto alle mediane recenti: non emerge un cambiamento macro netto dalle ultime quattro ore."];
 else if(v==="down"&&d==="flat")
  result=["easing","Volatilità in calo, dollaro sostanzialmente stabile",
   "Possibile attenuazione della tensione sui mercati azionari USA, senza una conferma direzionale significativa dal dollaro. Non è un segnale long."];
 else if(v==="up"&&d==="flat")
  result=["watch","Volatilità in aumento, dollaro sostanzialmente stabile",
   "Possibile aumento della tensione sui mercati azionari USA, senza una conferma significativa dal dollaro. Non è un segnale short."];
 else if(v==="flat"&&d==="up")
  result=["neutral","Dollaro in aumento, volatilità sostanzialmente stabile",
   "Il rafforzamento del dollaro può dipendere anche da tassi o fattori valutari. Il VIX non segnala uno spostamento altrettanto significativo."];
 else if(v==="flat"&&d==="down")
  result=["neutral","Dollaro in calo, volatilità sostanzialmente stabile",
   "L'indebolimento del dollaro non dimostra, senza altre conferme, un aumento della propensione al rischio."];
 else if(v==="up"&&d==="down")
  result=["mixed","Volatilità in aumento, dollaro in calo",
   "Dinamiche macro diverse: maggiore volatilità attesa insieme a dollaro debole. Controllare i singoli mercati, senza inferire automaticamente una direzione."];
 else
  result=["mixed","Volatilità in calo, dollaro in aumento",
   "La volatilità attesa diminuisce mentre il dollaro si rafforza: segnali macro differenti, non necessariamente in contraddizione."];
 return {state:result[0],dollar,fear,label:result[1],description:result[2]};
}
function context(dxy,vix,{now=Date.now()}={}){
 return describeContext(pulse(dxy,{now}),pulse(vix,{now}));
}
return Object.freeze({validBar,timeframe,audit,weekendSnapshot,returns,correlation,describeCorrelation,compareMacroRelationships,pairEligible,pulse,describeContext,context,TFS});
 })();
 const api=Object.freeze({LIMIT_MINUTES,OUTCOMES,interpret,summarize,macro});
 if(typeof module==="object"&&module.exports)module.exports=api;
 if(root)root.REMURA_PRICE_STATUS_CORE=api;
})(typeof window==="undefined"?null:window);
