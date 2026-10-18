/* REMURA v1.3: Myfxbook dedicated above; Capital.com DEMO below.
   Only same-origin PRIVATE numeric endpoints. No calls to Capital API in browser.
   No other providers/widgets; never publish private Capital observations.
*/
(()=>{
"use strict";
const core=window.REMURA_SENTIMENT_CORE;
const cfg=window.REMURA_MARKETS;
const symbol=(new URLSearchParams(location.search).get("symbol")||"XAUUSD").toUpperCase();
const holder=document.getElementById("retail-module");
if(!core||!cfg?.symbols?.includes(symbol)||!holder)return;
const el=(tag,cls,txt)=>{
 const n=document.createElement(tag);
 if(cls)n.className=cls;
 if(txt!==undefined)n.textContent=txt;
 return n;
};
const fmt=new Intl.NumberFormat("it-IT",{maximumFractionDigits:2});
const percent=n=>fmt.format(n)+"%";
const dateLabel=t=>{
 const d=new Date(t);
 return Number.isFinite(+d)?new Intl.DateTimeFormat("it-IT",{
  day:"2-digit",month:"short",hour:"2-digit",minute:"2-digit",timeZone:"Europe/Rome"
 }).format(d):"N/D";
};
const section=el("section","panel overview rem-sources");
section.id="remura-capital";
holder.insertAdjacentElement("afterend",section);
const top=el("div","ms-intro");
top.append(
 el("div","eyebrow","SENTIMENT RETAIL · SECONDA FONTE"),
 el("h2","","Capital.com"),
 el("p","","Posizioni dei clienti Capital.com DEMO: un campione diverso dai lotti Myfxbook. Entrambi sono dati retail, non ordini istituzionali.")
);
section.append(top);
const status=el("span","ms-status ms-stale","Archivio privato non collegato");
top.append(status);
const main=el("div","ms-main");
section.append(main);
const readings=el("div","ms-readings");
const longBox=el("div","ms-reading"),shortBox=el("div","ms-reading");
const longValue=el("strong","","—"),shortValue=el("strong","","—");
longBox.append(el("small","","Posizioni LONG Capital"),longValue);
shortBox.append(el("small","","Posizioni SHORT Capital"),shortValue);
readings.append(longBox,shortBox);
main.append(readings);
const split=el("div","ms-split");
split.setAttribute("aria-label","Distribuzione long short Capital.com");
const green=el("i","ms-long"),red=el("i","ms-short");
split.append(green,red);main.append(split);
const observed=el("p","ms-data-time","In attesa della prima rilevazione disponibile per questo strumento.");
main.append(observed);
const chartWrap=el("div","ms-chart");
const chartHeader=el("div","ms-chart-header");
chartHeader.append(el("h3","","Storico posizioni Capital.com"),
 el("p","","Bande da rilevazioni numeriche reali: non corrispondono ai timeframe del prezzo."));
const periods=el("div","ms-periods");periods.setAttribute("role","group");
periods.setAttribute("aria-label","Periodo dello storico Capital.com");
const windows={"6h":6*3600000,"24h":86400000,"7g":7*86400000,"30g":30*86400000,"Tutto":Infinity};
let selected="7g",allHistory=[],retail=null,capital=null;
for(const name of Object.keys(windows)){
 const button=el("button","",name);button.type="button";
 button.setAttribute("aria-pressed",String(name===selected));
 button.addEventListener("click",()=>{
  selected=name;
  for(const item of periods.querySelectorAll("button"))
   item.setAttribute("aria-pressed",String(item===button));
  drawHistory();
 });
 periods.append(button);
}
const graph=el("div","ms-history-panel","Lo storico apparirà dopo due osservazioni valide.");
const graphInfo=el("p","ms-data-time","Verde: LONG · Rosa: SHORT");
chartWrap.append(chartHeader,periods,graph,graphInfo);
main.append(chartWrap);
const compare=el("div","ms-comparison");
compare.append(el("h3","","Confronto Myfxbook ↔ Capital.com"));
const comparisonText=el("p","","Attendo entrambi i feed.");
compare.append(comparisonText);
section.append(compare);
const foot=el("p","ms-legend",
 "Myfxbook misura la quota del volume in lotti; Capital.com misura la quota di posizioni dei suoi clienti. Non sono la stessa popolazione né la stessa metrica: niente media artificiale. Un segnale contrarian va verificato sul prezzo e sul COT.");
const link=el("a","ms-link","Capital.com · sito ufficiale ↗");
link.href="https://capital.com/it";link.target="_blank";link.rel="noopener noreferrer";
section.append(foot,link);
function state(label,ok=false){
 status.className="ms-status "+(ok?"ms-live":"ms-stale");
 status.textContent=label;
}
function updateComparison(){
 const result=core.compare(retail,capital);
 comparisonText.textContent=result.text;
 compare.dataset.state=result.status;
}
function drawHistory(){
 const records=core.points(allHistory,windows[selected]);
 graph.replaceChildren();
 graphInfo.textContent=records.length+" rilevazioni reali nel periodo "+selected+". · Verde: LONG, Rosa: SHORT.";
 if(records.length<2){
  graph.append(el("div","ms-no-chart",records.length===1?
   "Un punto disponibile ("+dateLabel(records[0].t)+"). Serve almeno un'altra rilevazione per tracciare le bande.":
   "Nessun andamento storico per questo periodo. Le rilevazioni mancanti non vengono ricostruite."));
  return;
 }
 const xmlns="http://www.w3.org/2000/svg",W=730,H=235,LEFT=48,RIGHT=14,TOP=17,BOTTOM=38;
 const svg=document.createElementNS(xmlns,"svg");
 svg.setAttribute("viewBox","0 0 "+W+" "+H);
 svg.setAttribute("role","img");
 svg.setAttribute("aria-label","Capital.com storico osservato: verde percentuale long, rosa percentuale short; interruzioni in presenza di dati mancanti");
 const start=records[0].ms,end=records[records.length-1].ms;
 const X=t=>LEFT+(t-start)/Math.max(1,end-start)*(W-LEFT-RIGHT);
 const Y=v=>TOP+(100-v)/100*(H-TOP-BOTTOM);
 const add=(tag,attrs,text)=>{
  const node=document.createElementNS(xmlns,tag);
  for(const [k,v] of Object.entries(attrs))node.setAttribute(k,String(v));
  if(text!==undefined)node.textContent=text;
  svg.append(node);
  return node;
 };
 for(const v of [0,25,50,75,100]){
  const y=Y(v);
  add("line",{x1:LEFT,y1:y,x2:W-RIGHT,y2:y,stroke:"#315461","stroke-dasharray":"3 5"});
  add("text",{x:LEFT-8,y:y+4,"text-anchor":"end",fill:"#a7c9cc","font-size":11},String(v)+"%");
 }
 for(const [x,t] of [[LEFT,start],[W-RIGHT,end]])
  add("text",{x,y:H-12,"text-anchor":x===LEFT?"start":"end",fill:"#a7c9cc","font-size":11},dateLabel(t));
 const groups=[];let group=[];
 for(let i=0;i<records.length;i++){
  // A schedule is nominally every 2h. Draw gaps instead of invented curves.
  if(i>0&&records[i].ms-records[i-1].ms>4*3600000){
   if(group.length)groups.push(group);
   group=[];
  }
  group.push(records[i]);
 }
 if(group.length)groups.push(group);
 for(const [key,color] of [["lPct","#51d8a6"],["sPct","#f78e95"]]){
  for(const group of groups){
   if(group.length===1){
    add("circle",{cx:X(group[0].ms),cy:Y(group[0][key]),r:3.5,fill:color});
   }else{
    const points=group.map(p=>X(p.ms).toFixed(1)+","+Y(p[key]).toFixed(1)).join(" ");
    const path="M "+group.map(p=>X(p.ms).toFixed(1)+" "+Y(p[key]).toFixed(1)).join(" L ")+
      " L "+X(group[group.length-1].ms).toFixed(1)+" "+Y(0)+" L "+X(group[0].ms).toFixed(1)+" "+Y(0)+" Z";
    add("path",{d:path,fill:color,"fill-opacity":0.13,stroke:"none"});
    add("polyline",{points,fill:"none",stroke:color,"stroke-width":2.5,"stroke-linejoin":"round","stroke-linecap":"round"});
   }
  }
 }
 graph.append(svg);
}
window.addEventListener("remura:retail",e=>{
 if(e.detail?.symbol!==symbol)return;
 retail=e.detail.current?{row:e.detail.current,fresh:e.detail.fresh===true}:null;
 updateComparison();
});
async function loadCapital(){
 try{
  const response=await fetch("./private-api/capital/latest.json",{cache:"no-store"});
  if(!response.ok)throw Error(String(response.status));
  const data=await response.json(),row=data?.symbols?.[symbol];
  if(data?.status!=="ok"||data.environment!=="demo"||!core.valid(row)){
   state("Mercato non ancora coperto");
   observed.textContent="Il collector Capital.com non ha dati verificati per "+symbol+". Nessun valore stimato.";
   updateComparison();
   return;
  }
  const age=core.ageMs(row,data.updatedAt),recent=core.fresh(row,data.updatedAt);
  capital={row,fresh:recent};
  longValue.textContent=percent(+row.lPct);
  shortValue.textContent=percent(+row.sPct);
  green.style.width=Number(row.lPct)+"%";
  red.style.width=Number(row.sPct)+"%";
  const when=row.t||data.updatedAt;
  observed.textContent="Rilevato il "+dateLabel(when)+" (ora italiana) · Conto DEMO · "+
   (recent?"Dato recente.":"Dato datato: non usare per confronto attuale.");
  state(recent?"Capital.com · rilevazione recente":"Capital.com · dato datato",recent);
  try{
   const archive=await fetch("./private-api/capital/history/"+encodeURIComponent(symbol)+".json",{cache:"no-store"});
   if(archive.ok){
    const raw=await archive.json();
    allHistory=raw.symbol===symbol&&Array.isArray(raw.records)?raw.records:[];
   }
  }catch(_){/* no provider request, history is optional */}
  drawHistory();
  updateComparison();
 }catch(_){
  state("Dati Capital.com riservati");
  observed.textContent="Capital.com raccoglie i numeri nel repository privato REMURA. La pagina attuale non ha ancora accesso autenticato a quell'archivio.";
  updateComparison();
 }
}
updateComparison();
loadCapital();
})();