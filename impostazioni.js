/* REMURA v1.7: settings and authenticated Capital.com read-only diagnostics. */
(()=>{
"use strict";
const $=id=>document.getElementById(id);
const cloud=window.REMURA_CAPITAL_CLOUD||null;
const core=window.REMURA_SENTIMENT_CORE||null;
const feedHealth=window.REMURA_FEED_HEALTH;
const symbols=window.REMURA_MARKETS?.symbols||[];
const localKey="remura:capital:demo:v1";
const status=(id,message,type="")=>{const e=$(id);if(!e)return;e.textContent=message;e.dataset.status=type;};
function buttons(connected){
 $("google-connect").hidden=!cloud?.enabled||connected;
 $("google-disconnect").hidden=!cloud?.enabled||!connected;
}
async function checkGoogle(){
 if(!cloud?.enabled){
  buttons(false);
  status("google-status","Collegamento Google non disponibile: configurazione Firebase non caricata.","error");
  $("google-detail").textContent="Controlla il caricamento dei file Firebase sulla VPS. Non inserire password o chiavi qui.";
  return;
 }
 try{
  const connected=await cloud.isSignedIn();
  buttons(connected);
  if(!connected){
   status("google-status","Firebase disponibile. Account Google non collegato.","");
   $("google-detail").textContent="Premi Collega Google per ripristinare l'accesso al feed privato.";
   return;
  }
  status("google-status","Google collegato. Controllo la lettura dei dati Capital.com…","");
  const doc=await cloud.latest();
  if(!doc){
   status("google-status","Google collegato, ma il documento Capital.com non è disponibile.","error");
   $("google-detail").textContent="Verifica che la sincronizzazione su Firestore sia attiva e che le regole consentano la lettura al tuo account.";
   return;
  }
  const cleaned=core.cleanCapitalLatest(doc,symbols);
  const h=feedHealth.inspect(cleaned,symbols);
  const time=new Intl.DateTimeFormat("it-IT",{dateStyle:"short",timeStyle:"short",timeZone:"Europe/Rome"}).format(new Date(cleaned.updatedAt));
  status("google-status",h.recent?"Google collegato · Capital.com recente":"Google collegato · Capital.com DATATO",h.recent?"ok":"error");
  $("google-detail").textContent="Ultima raccolta: "+time+" (ora italiana), "+h.ageMinutes+" min fa. Copertura "+h.covered+"/"+h.expected+" mercati. La connessione funziona anche se i dati sono vecchi.";
 }catch(e){
  // No token or account details are written to the UI.
  status("google-status","Collegamento Google presente, ma verifica del feed non riuscita.","error");
  $("google-detail").textContent="Possibili cause: rete, permessi Firestore o sessione scaduta. Prova a scollegare e ricollegare Google.";
 }
}
$("google-connect").addEventListener("click",async()=>{
 const btn=$("google-connect");btn.disabled=true;
 try{
  if(!cloud?.enabled)throw Error("Firebase non disponibile");
  await cloud.signIn();
  await checkGoogle();
 }catch(_){
  status("google-status","Accesso Google non riuscito. Controlla le finestre di accesso e i domini autorizzati.","error");
 }finally{btn.disabled=false;}
});
$("google-disconnect").addEventListener("click",async()=>{
 const btn=$("google-disconnect");btn.disabled=true;
 try{await cloud.signOut();await checkGoogle();}
 catch(_){status("google-status","Disconnessione Google non riuscita.","error");}
 finally{btn.disabled=false;}
});
$("google-check").addEventListener("click",checkGoogle);
async function checkPrivate(){
 const sources=[{url:"./private-api/retail/latest.json",label:"Myfxbook VPS"},{url:"./private-api/capital/latest.json",label:"Capital VPS"}];
 const results=[];let allFresh=true;
 for(const item of sources){
  try{
   const response=await fetch(item.url,{cache:"no-store"});if(!response.ok)throw Error("absent");
   const h=feedHealth.inspect(await response.json(),symbols);
   if(!h.valid){allFresh=false;results.push(item.label+": dati non validi");continue;}
   if(!h.recent)allFresh=false;
   results.push(item.label+": "+(h.recent?"recente":"DATATO")+" ("+h.ageMinutes+" min, "+h.covered+"/"+h.expected+" mercati)");
  }catch(_){allFresh=false;results.push(item.label+": non raggiungibile da questo indirizzo");}
 }
 status("private-status",results.join(" · "),allFresh?"ok":"");
}
async function checkPublic(){
 try{
  const response=await fetch("./data/myfxbook/latest.json?t="+Date.now(),{cache:"no-store"});
  if(!response.ok)throw Error("absent");
  const h=feedHealth.inspect(await response.json(),symbols);if(!h.valid)throw Error("invalid");
  const stamp=new Intl.DateTimeFormat("it-IT",{dateStyle:"short",timeStyle:"short",timeZone:"Europe/Rome"}).format(new Date(h.updatedAt));
  status("public-status","Myfxbook GitHub · "+(h.recent?"recente":"DATATO")+" · "+stamp+" · "+h.ageMinutes+" min · "+h.covered+"/"+h.expected+" mercati",h.recent?"ok":"error");
 }catch(_){status("public-status","Archivio pubblico Myfxbook non disponibile o non valido.","error");}
}
async function checkAutoupdate(){
 try{
  const response=await fetch("./private-api/autoupdate",{cache:"no-store"});
  if(!response.ok)throw Error("private-only");
  const data=await response.json();
  if(!data.enabled){
   status("autoupdate-status","Aggiornamenti automatici non ancora attivati.","");
   $("autoupdate-detail").textContent="Per attivare serve un ultimo comando Termius dopo aver installato la v1.7.";
   return;
  }
  const names={configured:"Configurato · prima verifica in attesa",up_to_date:"Versione aggiornata",updated:"Ultimo aggiornamento riuscito",waiting_ci:"In attesa dei test GitHub",data_only:"Solo dati aggiornati · nessun riavvio",manual_required:"Serve approvazione manuale da Termius",blocked:"Questo commit è bloccato",error:"Verifica o installazione fallita"};
  const state=String(data.state||"unknown");
  status("autoupdate-status",names[state]||"Stato: "+state,["blocked","error","manual_required"].includes(state)?"error":["up_to_date","updated"].includes(state)?"ok":"");
  const sha=s=>typeof s==="string"&&/^[a-f0-9]{40}$/.test(s)?s.slice(0,8):"—";
  const date=s=>s&&Number.isFinite(Date.parse(s))?new Intl.DateTimeFormat("it-IT",{timeZone:"Europe/Rome",dateStyle:"short",timeStyle:"short"}).format(new Date(s)):"in attesa";
  $("autoupdate-detail").textContent="Commit installato: "+sha(data.installedSha)+" · Ultimo controllo: "+date(data.lastCheck)+". "+String(data.message||"");
 }catch(_){
  status("autoupdate-status","Stato disponibile solo nella VPS privata Tailscale.","");
  $("autoupdate-detail").textContent="Su GitHub Pages questa API non esiste. Per leggerla, apri l'indirizzo .ts.net dopo l'installazione v1.7.";
 }
}
$("check-autoupdate").addEventListener("click",checkAutoupdate);
async function checkCTrader(){
  try{
   const response=await fetch("./private-api/health",{cache:"no-store"});
   if(!response.ok)throw Error("private_server_unavailable");
   const data=await response.json();
   const check=data.ctraderPreflight;
   if(!check || typeof check!=="object"){
    status("ctrader-status","Server da aggiornare: diagnostica cTrader non disponibile.","");
    return;
   }
   const sdk=check.sdk==="installed",oauth=check.configuration==="ready";
   const backup=data.ctraderBackup;
   const verified=Array.isArray(data.instruments)?data.instruments.length:0;
   status("ctrader-status","SDK "+(sdk?"presente":"MANCANTE")+" · OAuth "+(oauth?"configurato":"incompleto")+" · "+verified+" mercati con prezzi",sdk&&oauth&&verified?"ok":"error");
   const count=data.collectorLastCount;
   const secondary=backup&&backup.enabled?(backup.configuration==="ready"?"riserva pronta":"riserva non autorizzata"):"riserva disattivata";
   $("ctrader-detail").textContent="Stato: "+String(data.collector||"N/D")+" · Ultima fonte: "+String(data.collectorSource||"N/D")+" · Secondo cTrader: "+secondary+" · Ultima raccolta: "+String(data.lastAttempt||"N/D")+" · Ultimo risultato: "+String(data.lastError||"N/D")+(count?" · Mercati salvati: "+count:"")+". Non vengono mai combinate le candele dei due broker.";
  }catch(_){
   status("ctrader-status","Collegamento cTrader verificabile solo tramite VPS Tailscale.","");
   $("ctrader-detail").textContent="Apri REMURA dal tuo indirizzo .ts.net.";
  }
}
$("check-ctrader").addEventListener("click",checkCTrader);
function store(key,doc){
 try{localStorage.setItem(key,JSON.stringify(doc));return true;}
 catch(_){return false;}
}
async function readJSON(input){
 const file=input?.files?.[0];
 if(!file||!file.size||file.size>1000000)throw Error("Seleziona un JSON fino a 1 MB.");
 try{return JSON.parse(await file.text())}
 catch(_){throw Error("Il file selezionato non è un JSON valido.")}
}
const select=$("upload-symbol");
for(const symbol of symbols){
 const option=document.createElement("option");
 option.value=symbol;option.textContent=symbol;select.append(option);
}
select.value="EURUSD";
$("upload-latest").addEventListener("change",async e=>{
 const input=e.currentTarget;
 try{
  const cleaned=core.cleanCapitalLatest(await readJSON(input),symbols);
  if(!store(localKey+":latest",cleaned))throw Error("Impossibile salvare su questo dispositivo.");
  status("import-status","Importate le percentuali di "+Object.keys(cleaned.symbols).length+" mercati. Riapri una scheda per visualizzarle.","ok");
 }catch(err){status("import-status","Importazione rifiutata: "+err.message,"error");}
 finally{input.value="";}
});
$("upload-history").addEventListener("change",async e=>{
 const input=e.currentTarget,symbol=select.value;
 try{
  const cleaned=core.cleanCapitalHistory(await readJSON(input),symbol);
  if(!store(localKey+":history:"+symbol,cleaned))throw Error("Impossibile salvare su questo dispositivo.");
  status("import-status","Importate "+cleaned.records.length+" rilevazioni storiche per "+symbol+".","ok");
 }catch(err){status("import-status","Importazione rifiutata: "+err.message,"error");}
 finally{input.value="";}
});
$("clear-local").addEventListener("click",()=>{
 try{
  localStorage.removeItem(localKey+":latest");
  for(const symbol of symbols)localStorage.removeItem(localKey+":history:"+symbol);
  status("import-status","Import locali rimossi da questo dispositivo. Google/Firestore non è stato modificato.","ok");
 }catch(_){status("import-status","Impossibile accedere alla memoria locale.","error");}
});
$("check-feeds").addEventListener("click",()=>{checkGoogle();checkPrivate();checkPublic();});
checkGoogle();checkPrivate();checkPublic();checkAutoupdate();checkCTrader();
})();

/* REMURA v1.54: centro infrastrutturale in sola lettura, senza API provider. */
(()=>{
"use strict";
const $=id=>document.getElementById(id);
if(!$("obs-grid"))return;
const api=[
 ["health","./private-api/health",null],
 ["resources","./private-api/resources","remura-resources-v1"],
 ["prices","./private-api/prices/status","remura-price-status-v1"],
 ["cot","./private-api/cot/status","remura-cot-status-v1"],
 ["signals","./private-api/signals/status","remura-squalincome-monitor-v1"],
 ["update","./private-api/autoupdate",null]
];
const labels={ok:"Operativo",attention:"Attenzione",error:"Problema",disabled:"Non attivo",unknown:"N/D"};
const num=n=>typeof n==="number"&&Number.isFinite(n)&&n>=0;
const counter=n=>Number.isInteger(n)&&n>=0?n.toLocaleString("it-IT"):"N/D";
const time=s=>typeof s==="string"&&Number.isFinite(Date.parse(s))?Date.parse(s):null;
const when=(s,now)=>{const t=time(s);if(t===null||t>now+300000)return "N/D";const m=Math.max(0,Math.floor((now-t)/60000));return m<120?m+" min fa":m<2880?Math.floor(m/60)+" h fa":Math.floor(m/1440)+" giorni fa";};
const stamp=t=>new Intl.DateTimeFormat("it-IT",{timeZone:"Europe/Rome",dateStyle:"short",timeStyle:"short"}).format(new Date(t));
const weekend=t=>[0,6].includes(new Date(t).getUTCDay());
const card=(name,state,value,detail)=>({name,state,value,detail});
function report(docs,now){
 const rows=[],events=[];
 const event=(name,t)=>{const ms=time(t);if(ms!==null&&ms<=now+300000)events.push({name,t:ms});};
 const h=docs.health,r=docs.resources,p=docs.prices,c=docs.cot,s=docs.signals,u=docs.update;
 const server=!!h&&h.name==="REMURA Private";
 rows.push(card("VPS · server privato",server?"ok":"error",server?"API raggiungibile":"Nessuna risposta valida",
   server?"La VPS risponde: non significa che tutti i collector siano operativi.":"Accedi a REMURA tramite Tailscale, non da GitHub Pages."));
 if(r?.schema==="remura-resources-v1"){
  const percent=(used,total)=>num(used)&&num(total)&&total>0?100*used/total:null;
  const mem=percent(r.memory?.used,r.memory?.total),disk=percent(r.disk?.used,r.disk?.total);
  const high=(mem!==null&&mem>=90)||(disk!==null&&disk>=90);
  rows.push(card("RAM · CPU · disco",high?"attention":"ok",
    "RAM "+(mem===null?"N/D":mem.toFixed(1)+"%")+" · disco "+(disk===null?"N/D":disk.toFixed(1)+"%"),
    "Carico CPU 1 minuto: "+(num(r.cpu?.load1)?r.cpu.load1.toFixed(2):"N/D")+". Non sono quote OCI."));
  event("Ultimo campionamento risorse",r.sampledAt);
 }else rows.push(card("RAM · CPU · disco","unknown","N/D","Nessun dato locale attendibile."));
 if(server){
  const pre=h.ctraderPreflight||{},backup=h.ctraderBackup||{};
  const configured=pre.sdk==="installed"&&pre.configuration==="ready";
  rows.push(card("cTrader · principale",h.collector==="disabled"?"disabled":configured?"ok":"attention",
    h.collector==="disabled"?"Raccolta disattivata":configured?"SDK e autorizzazione presenti":"Configurazione da controllare",
    "Mercati con dati: "+(Array.isArray(h.instruments)?counter(h.instruments.length):"N/D")+" · Ultimo successo "+when(h.lastSuccess,now)+". Dati presenti non significa candele recenti."));
  rows.push(card("cTrader · riserva",!backup.enabled?"disabled":backup.configuration==="ready"?"ok":"attention",
    !backup.enabled?"Riserva disattivata":backup.configuration==="ready"?"Riserva configurata":"Riserva non pronta",
    "Il collegamento secondario non sostituisce né mescola automaticamente le candele del broker principale."));
  for(const [title,state,last] of [
   ["Myfxbook sulla VPS",h.retailStatus,h.retailLastSuccess],
   ["Capital sulla VPS",h.capitalStatus,h.capitalLastSuccess],
   ["IG sulla VPS",h.igStatus,h.igLastSuccess]
  ]){
   const v=String(state||"unknown").toLowerCase();
   const disabled=["disabled","not_configured","not_collected"].includes(v);
   const failed=["failed","error"].includes(v);
   const good=["ok","ready","running"].includes(v);
   const stale=time(last)!==null&&now-time(last)>3*3600000;
   const type=disabled?"disabled":failed?"attention":good&&stale&&!weekend(now)?"attention":good?"ok":"unknown";
   rows.push(card(title,type,disabled?"Collector locale disattivato":failed?"Errore segnalato":good?"Stato "+v:"Stato non disponibile",
     "Ultimo successo "+when(last,now)+". Capital via Google/Firestore è un collegamento distinto."));
  }
  event("cTrader · ultimo tentativo",h.lastAttempt);
 }else{
  for(const title of ["cTrader · principale","cTrader · riserva","Myfxbook sulla VPS","Capital sulla VPS","IG sulla VPS"])
   rows.push(card(title,"unknown","N/D","Stato non disponibile dalla VPS."));
 }
 if(p?.schema==="remura-price-status-v1"){
  const q=p.qualityTotals||{},fresh=p.freshnessTotals||{};
  const issues=(q.missing||0)+(q.invalid||0)+(q.insufficient||0)+(fresh.stale||0);
  rows.push(card("Qualità candele M15/H1/H4",p.collector==="disabled"?"disabled":issues?"attention":"ok",
    counter(q.verified)+" verificati / "+counter(p.total)+" mercati",
    "Mancanti "+counter(q.missing)+" · invalidi "+counter(q.invalid)+" · insufficienti "+counter(q.insufficient)+" · datati "+counter(fresh.stale)+" · weekend "+counter(fresh.weekend)+". Mercato chiuso non significa guasto."));
  event("Prezzi · ultimo tentativo",p.lastAttempt);
 }else rows.push(card("Qualità candele M15/H1/H4","unknown","N/D","Nessuna diagnosi prezzi verificabile."));
 if(c?.schema==="remura-cot-status-v1"){
  const t=c.datasets?.tff||{},g=c.datasets?.disagg||{};
  rows.push(card("COT ufficiale CFTC",!c.enabled?"disabled":c.state==="ready"?"ok":"attention",
    !c.enabled?"Collector disattivato":c.state==="ready"?"Copertura disponibile":"Copertura da verificare",
    "TFF "+counter(t.contracts)+"/"+counter(t.expectedContracts)+" · Disaggregated "+counter(g.contracts)+"/"+counter(g.expectedContracts)+". Cadenza settimanale."));
  event("COT · ultimo tentativo",c.lastAttempt);
 }else rows.push(card("COT ufficiale CFTC","unknown","N/D","Nessun esito verificabile."));
 if(s?.schema==="remura-squalincome-monitor-v1"){
  const last=s.diagnostics?.lastScanAt;
  const old=time(last)===null||now-time(last)>3*3600000;
  rows.push(card("Scanner Squalincome",!s.enabled?"disabled":old?"attention":"ok",
    !s.enabled?"Disattivato":"Ultima scansione "+when(last,now),
    "Monitorati "+counter(s.trackedMarkets)+" · Analizzati "+counter(s.diagnostics?.analyzed)+" · Esclusi "+counter(s.diagnostics?.excluded)+". Nessun segnale non è un errore."));
  event("Squalincome · ultima scansione",last);
 }else rows.push(card("Scanner Squalincome","unknown","N/D","Nessuna diagnosi di scansione."));
 if(u&&typeof u.enabled==="boolean"){
  const v=String(u.state||"unknown");
  const bad=["blocked","error"].includes(v);
  rows.push(card("Aggiornamenti automatici",!u.enabled?"disabled":bad?"error":v==="manual_required"?"attention":["updated","up_to_date"].includes(v)?"ok":"unknown",
    !u.enabled?"Disattivati":bad?"Problema da esaminare":v==="manual_required"?"Rilascio manuale richiesto":"Stato "+v,
    "Ultimo controllo "+when(u.lastCheck,now)+" · commit installato "+(typeof u.installedSha==="string"&&/^[0-9a-f]{40}$/.test(u.installedSha)?u.installedSha.slice(0,8):"N/D")+"."));
  event("Autoupdate · ultimo controllo",u.lastCheck);
 }else rows.push(card("Aggiornamenti automatici","unknown","N/D","Stato updater non disponibile."));
 rows.push(card("Capital Google / Firestore","unknown","Non verificato in questo controllo","Il collegamento via Google è distinto dal feed Capital della VPS; verifica nella sezione Google."));
 rows.push(card("SQLite e backup","unknown","Integrità e ultimo backup N/D","Le API dati non provano la riuscita di un backup o di un ripristino."));
 rows.push(card("Oracle e chiamate broker","unknown","Quote e costi non verificati","Le richieste GET alla VPS non equivalgono a chiamate cTrader, Capital o consumi Oracle."));
 return {rows,events:events.sort((a,b)=>b.t-a.t).slice(0,6),now,server};
}
const elt=(tag,cls,txt)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(txt!==undefined)e.textContent=txt;return e;};
function render(d){
 const alert=d.rows.filter(x=>["error","attention"].includes(x.state)).length;
 const summary=$("obs-summary");
 summary.dataset.status=d.server?(alert?"error":"ok"):"error";
 summary.textContent=d.server?("VPS raggiungibile · "+(alert?alert+" componenti da verificare":"nessuna anomalia rilevata nei controlli disponibili")):"VPS non verificabile · usa il collegamento privato Tailscale.";
 const counts=$("obs-counts");counts.replaceChildren();
 for(const [state,title] of [["ok","Operativi"],["attention","Da controllare"],["disabled","Non attivi"],["unknown","Non attestati"]]){
  const n=state==="attention"?alert:d.rows.filter(x=>x.state===state).length;
  const b=elt("div","obs-count");b.append(elt("strong","",counter(n)),elt("span","",title));counts.append(b);
 }
 const grid=$("obs-grid");grid.replaceChildren();
 for(const c of d.rows){
  const box=elt("article","obs-card"),head=elt("div","obs-header"),badge=elt("span","obs-tag",labels[c.state]);
  badge.dataset.state=c.state;head.append(elt("h3","",c.name),badge);
  box.append(head,elt("div","obs-value",c.value),elt("p","obs-detail",c.detail));grid.append(box);
 }
 const events=$("obs-events");events.replaceChildren();
 for(const row of d.events){const li=elt("li"),date=elt("time","",stamp(row.t));date.dateTime=new Date(row.t).toISOString();li.append(elt("span","",row.name),date);events.append(li);}
 if(!d.events.length)events.append(elt("li","","Nessun timestamp attendibile."));
 $("obs-sampled").textContent="Ultima verifica: "+stamp(d.now);
}
async function read(path,schema){
 const ac=new AbortController(),timer=setTimeout(()=>ac.abort(),8000);
 try{
  const response=await fetch(path,{cache:"no-store",credentials:"same-origin",signal:ac.signal,headers:{"Accept":"application/json"}});
  if(!response.ok)throw Error("not_available");
  const obj=await response.json();
  return obj&&typeof obj==="object"&&(!schema||obj.schema===schema)?obj:null;
 }catch(_){return null;}finally{clearTimeout(timer);}
}
let busy=false;
async function refresh(){
 if(busy)return;
 busy=true;$("obs-refresh").disabled=true;$("obs-loading").textContent="Lettura di sei API private…";
 try{
  const docs={};await Promise.all(api.map(async ([name,path,schema])=>{docs[name]=await read(path,schema);}));
  render(report(docs,Date.now()));
 }finally{busy=false;$("obs-refresh").disabled=false;$("obs-loading").textContent="Sola lettura · nessuna chiamata ai broker.";}
}
$("obs-refresh").addEventListener("click",refresh);
refresh();
})();
