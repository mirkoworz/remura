/* REMURA v1.5: settings and authenticated Capital.com read-only diagnostics. */
(()=>{
"use strict";
const $=id=>document.getElementById(id);
const cloud=window.REMURA_CAPITAL_CLOUD||null;
const core=window.REMURA_SENTIMENT_CORE||null;
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
  status("google-status","Google collegato · feed Capital.com accessibile · "+Object.keys(cleaned.symbols).length+" mercati.","ok");
  const time=new Intl.DateTimeFormat("it-IT",{dateStyle:"short",timeStyle:"short",timeZone:"Europe/Rome"}).format(new Date(cleaned.updatedAt));
  $("google-detail").textContent="Ultimo dato aggregato: "+time+" (ora italiana). L'accesso Google rimane sul tuo dispositivo.";
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
 const endpoints=[
  {url:"./private-api/retail/latest.json",label:"Myfxbook"},
  {url:"./private-api/capital/latest.json",label:"Capital.com"}
 ];
 const results=[];
 for(const item of endpoints){
  try{
   const response=await fetch(item.url,{cache:"no-store"});
   const doc=response.ok?await response.json():null;
   results.push(item.label+": "+(doc?.status==="ok"?"disponibile":"non disponibile sul server"));
  }catch(_){results.push(item.label+": non disponibile sul server");}
 }
 status("private-status",results.join(" · "),results.every(x=>x.includes(": disponibile"))?"ok":"");
}
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
checkGoogle();
checkPrivate();
})();