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
   const verified=Array.isArray(data.instruments)?data.instruments.length:0;
   status("ctrader-status","SDK "+(sdk?"presente":"MANCANTE")+" · OAuth "+(oauth?"configurato":"incompleto")+" · "+verified+" mercati con prezzi",sdk&&oauth&&verified?"ok":"error");
   const count=data.collectorLastCount;
   $("ctrader-detail").textContent="Stato: "+String(data.collector||"N/D")+" · Ultima raccolta: "+String(data.lastAttempt||"N/D")+" · Ultimo risultato: "+String(data.lastError||"N/D")+(count?" · Mercati salvati: "+count:"")+". Se l'SDK manca, installalo solo nell'ambiente Python privato della VPS.";
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