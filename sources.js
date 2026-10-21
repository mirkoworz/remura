/* REMURA Capital.com client sentiment: private same-origin, authenticated
   personal Firestore, or manual local JSON fallback. No Capital API in browser.
   Never infer institutional flows from client sentiment.
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
 el("div","eyebrow","03 · SENTIMENT RETAIL · FONTE 2 DI 2"),
 el("h2","","Capital.com · cosa fanno i suoi clienti"),
 el("p","","Queste percentuali indicano quante posizioni dei clienti Capital.com sono long o short. Sono dati retail diversi dai lotti Myfxbook, non movimenti istituzionali.")
);
section.append(top);
const status=el("span","ms-status ms-stale","Archivio privato non collegato");
top.append(status);
const main=el("div","ms-main");
section.append(main);
const readings=el("div","ms-readings");
const longBox=el("div","ms-reading"),shortBox=el("div","ms-reading");
const longValue=el("strong","","—"),shortValue=el("strong","","—");
longBox.append(el("small","","Clienti con posizioni LONG"),longValue);
shortBox.append(el("small","","Clienti con posizioni SHORT"),shortValue);
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
chartHeader.append(el("h3","","Come cambiano le posizioni nel tempo?"),
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
compare.append(el("h3","","Myfxbook e Capital.com: coincidono o divergono?"));
const comparisonText=el("p","","Attendo entrambi i feed.");
compare.append(comparisonText);
main.insertBefore(compare,chartWrap);
const foot=el("p","ms-legend",
 "Myfxbook misura la quota del volume in lotti; Capital.com misura la quota di posizioni dei suoi clienti. Non sono la stessa popolazione né la stessa metrica: niente media artificiale. Un segnale contrarian va verificato sul prezzo e sul COT.");
const link=el("a","ms-link","Capital.com · sito ufficiale ↗");
link.href="https://capital.com/it";link.target="_blank";link.rel="noopener noreferrer";
section.append(foot,link);
const LOCAL_CAPITAL="remura:capital:demo:v1";
const cloud=window.REMURA_CAPITAL_CLOUD||null;
let cloudConnected=false;
let cloudError="";

let importedLatest=null,importedHistory=null;
const savedLatest=()=>readStored(LOCAL_CAPITAL+":latest");
const savedHistory=()=>readStored(LOCAL_CAPITAL+":history:"+symbol);
function readStored(key){
 try{const raw=localStorage.getItem(key);return raw?JSON.parse(raw):null;}
 catch(_){return null;}
}
function writeStored(key,obj){
 try{localStorage.setItem(key,JSON.stringify(obj));return true;}
 catch(_){return false;}
}
const importPanel=el("details","ms-import");
const importSummary=el("summary","","Accesso privato Google e importazione file · Tocca per aprire");
importPanel.append(importSummary);
importPanel.append(
 el("h3","","Collegamento ai dati Capital.com privati"),
 el("p","",cloud?.enabled?
  "Collega il tuo account Google autorizzato: REMURA leggerà automaticamente i dati Capital.com privati da Firestore. In alternativa puoi ancora importare i JSON manualmente.":
  "La pagina pubblica non può leggere GitHub privato. Per ora importa latest.json; il collegamento automatico con accesso Google sarà disponibile dopo la configurazione Firestore.")
);
const githubLink=el("a","ms-link","Apri latest.json privato su GitHub ↗");
githubLink.href="https://github.com/mirkoworz/remura-collector/blob/main/private/capital/latest.json";
githubLink.target="_blank";githubLink.rel="noopener noreferrer";
const steps=el("p","ms-import-help","Per importare manualmente: su GitHub apri il file → menu ⋯ → Download raw file, quindi scegli il file qui.");
if(cloud?.enabled){
 const cloudControls=el("div","ms-import-controls");
 const login=el("button","ms-clear","Collega Google per aggiornamenti automatici");
 login.type="button";
 const logout=el("button","ms-clear","Scollega Google");
 logout.type="button";
 logout.hidden=true;
 const cloudInfo=el("p","ms-import-help","Il login Google serve esclusivamente per l'accesso privato al feed Firestore. Nessun token Capital.com viene inviato al browser.");
 const updateButtons=async()=>{
  const signed=await cloud.isSignedIn();
  cloudConnected=signed;login.hidden=signed;logout.hidden=!signed;
  if(signed)cloudInfo.textContent="Account Google collegato. REMURA leggerà automaticamente il feed privato.";
 };
 login.addEventListener("click",async()=>{
  login.disabled=true;
  try{
   await cloud.signIn();cloudError="";
   await updateButtons();
   await loadCapital();
  }catch(e){
   cloudError="Login Google non riuscito. Controlla l'account e i domini autorizzati in Firebase.";
   cloudInfo.textContent=cloudError;
  }finally{login.disabled=false;}
 });
 logout.addEventListener("click",async()=>{
  logout.disabled=true;
  try{
   await cloud.signOut();
   cloudConnected=false;
   await updateButtons();
   await loadCapital();
  }catch(_){cloudInfo.textContent="Disconnessione non riuscita.";}
  finally{logout.disabled=false;}
 });
 cloudControls.append(login,logout);
 importPanel.append(cloudControls,cloudInfo);
 cloud.isSignedIn().then(updateButtons).catch(()=>{
  cloudInfo.textContent="Firebase non raggiungibile. Resta disponibile l'importazione manuale.";
 });
}
const fields=el("div","ms-import-controls");
const latestLabel=el("label","ms-file-label","Carica latest.json");
const latestFile=el("input","ms-file");
latestFile.type="file";latestFile.accept=".json,application/json";
latestFile.setAttribute("aria-label","Importa l'ultimo snapshot Capital.com dal repository privato");
latestLabel.append(latestFile);
const historyLabel=el("label","ms-file-label","Carica storico "+symbol+" (facoltativo)");
const historyFile=el("input","ms-file");
historyFile.type="file";historyFile.accept=".json,application/json";
historyFile.setAttribute("aria-label","Importa lo storico privato Capital.com di "+symbol);
historyLabel.append(historyFile);
const clearButton=el("button","ms-clear","Cancella dati importati");
clearButton.type="button";
const importStatus=el("p","ms-import-help","Nessun dato viene caricato sui server REMURA.");
fields.append(latestLabel,historyLabel,clearButton);
importPanel.append(githubLink,steps,fields,importStatus);
section.append(importPanel);
async function readFileSafe(file){
 if(!file||file.size<=0||file.size>1_000_000)
  throw Error("Seleziona un file JSON non superiore a 1 MB.");
 try{return JSON.parse(await file.text());}
 catch(_){throw Error("Impossibile leggere il JSON selezionato.");}
}
latestFile.addEventListener("change",async()=>{
 try{
  const cleaned=core.cleanCapitalLatest(await readFileSafe(latestFile.files?.[0]),cfg.symbols);
  importedLatest=cleaned;
  const stored=writeStored(LOCAL_CAPITAL+":latest",cleaned);
  importStatus.textContent=Object.keys(cleaned.symbols).length+
   " mercati importati. "+(stored?"Dati conservati soltanto su questo dispositivo.":"Visualizzazione temporanea: salvataggio locale non disponibile.");
  await loadCapital();
 }catch(e){importStatus.textContent="Importazione non riuscita: "+e.message;}
 finally{latestFile.value="";}
});
historyFile.addEventListener("change",async()=>{
 try{
  const cleaned=core.cleanCapitalHistory(await readFileSafe(historyFile.files?.[0]),symbol);
  importedHistory=cleaned;
  const stored=writeStored(LOCAL_CAPITAL+":history:"+symbol,cleaned);
  importStatus.textContent=cleaned.records.length+" rilevazioni storiche importate per "+symbol+
   (stored?" e salvate sul dispositivo.":"; salvataggio locale non disponibile.");
  await loadCapital();
 }catch(e){importStatus.textContent="Storico non importato: "+e.message;}
 finally{historyFile.value="";}
});
clearButton.addEventListener("click",async()=>{
 try{
  localStorage.removeItem(LOCAL_CAPITAL+":latest");
  for(const sym of cfg.symbols)localStorage.removeItem(LOCAL_CAPITAL+":history:"+sym);
 }catch(_){}
 importedLatest=null;importedHistory=null;
 importStatus.textContent="Dati importati eliminati dal browser, se la memoria locale era disponibile.";
 await loadCapital();
});

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
 capital=null;
 let doc=null,via="locale";
 try{
  const response=await fetch("./private-api/capital/latest.json",{cache:"no-store"});
  if(response.ok){
   const raw=await response.json();
   doc=core.cleanCapitalLatest(raw,cfg.symbols);
   via="privato";
  }
 }catch(_){/* GitHub Pages cannot fetch a private file: cloud or local follows */}
 if(!doc&&cloud?.enabled){
  try{
   cloudConnected=await cloud.isSignedIn();
   if(cloudConnected){
    const remote=await cloud.latest();
    if(remote){doc=core.cleanCapitalLatest(remote,cfg.symbols);via="cloud";}
   }
  }catch(_){cloudError="Firestore non disponibile o accesso negato";cloudConnected=false;}
 }
 if(!doc){
  try{
   const stored=importedLatest||savedLatest();
   if(stored)doc=core.cleanCapitalLatest(stored,cfg.symbols);
  }catch(_){}
 }
 if(!doc){
  longValue.textContent="—";shortValue.textContent="—";
  green.style.width="0";red.style.width="0";
  state(cloud?.enabled?"Capital.com · accesso privato richiesto":"Dati privati · importa latest.json");
  observed.textContent=cloud?.enabled?
   (cloudError||"Accedi con Google per vedere automaticamente il sentiment. In alternativa importa il file JSON."):
   "Nessun file Capital.com sul dispositivo. Scarica latest.json da GitHub privato e caricalo qui sotto.";
  allHistory=[];drawHistory();updateComparison();
  return;
 }
 const row=doc.symbols[symbol];
 if(!core.valid(row)){
  longValue.textContent="—";shortValue.textContent="—";
  green.style.width="0";red.style.width="0";
  state("Mercato non ancora disponibile");
  observed.textContent="Questo file non contiene un campione valido per "+symbol+". Gli altri mercati importati rimangono disponibili.";
  allHistory=[];drawHistory();updateComparison();
  return;
 }
 const recent=core.fresh(row,doc.updatedAt);
 capital={row,fresh:recent};
 longValue.textContent=percent(+row.lPct);
 shortValue.textContent=percent(+row.sPct);
 green.style.width=Number(row.lPct)+"%";
 red.style.width=Number(row.sPct)+"%";
 observed.textContent="Rilevato il "+dateLabel(row.t||doc.updatedAt)+
  " (ora italiana) · Capital.com DEMO · "+
  (via==="locale"?"Copia privata caricata sul tuo dispositivo.":
   via==="cloud"?"Firestore privato (accesso Google).":"Archivio privato REMURA.")+
  (recent?" Dato recente.":" Dato datato, non confrontare come segnale attuale.");
 state(recent?"Capital.com · "+(via==="locale"?"importato":via==="cloud"?"cloud privato":"aggiornato"):"Capital.com · dato datato",recent);
 allHistory=[];
 if(via==="privato"){
  try{
   const response=await fetch("./private-api/capital/history/"+encodeURIComponent(symbol)+".json",{cache:"no-store"});
   if(response.ok){
    const raw=await response.json();
    allHistory=core.cleanCapitalHistory(raw,symbol).records;
   }
  }catch(_){}
 }
 if(!allHistory.length&&via==="cloud"&&cloudConnected){
  try{
   const remote=await cloud.history(symbol);
   if(remote)allHistory=core.cleanCapitalHistory(remote,symbol).records;
  }catch(_){/* Firestore history unavailable: retain single real latest point. */}
 }
 if(!allHistory.length){
  try{
   const saved=importedHistory||savedHistory();
   if(saved)allHistory=core.cleanCapitalHistory(saved,symbol).records;
  }catch(_){}
 }
 // A latest snapshot is a real observation, even if history has not been imported.
 if(!allHistory.some(item=>item.t===row.t)){
  allHistory.push({...row});
 }
 drawHistory();
 updateComparison();
}
updateComparison();
loadCapital();
})();