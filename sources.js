/* REMURA v0.8: source-comparison hub. No invented sentiment readings. */
(()=>{
"use strict";
const symbol=(new URLSearchParams(location.search).get("symbol")||"XAUUSD").toUpperCase();
const cfg=window.REMURA_MARKETS;
if(!cfg||!cfg.symbols.includes(symbol))return;
const holder=document.getElementById("retail-module");
if(!holder)return;
const group=cfg.other[symbol]?.group||(symbol.length===6?"forex":"other");
const isFX=group==="forex",isMetal=group==="metals",isIndex=group==="indices";
const sourceDefs=[
 {id:"myfxbook",name:"Myfxbook",measure:"Volume in lotti e numero di posizioni della community",
   status:"api",coverage:"Tutti gli strumenti restituiti dal suo endpoint",
   url:()=> "https://www.myfxbook.com/community/outlook/"+encodeURIComponent(symbol),
   note:"Un dato automatico già collegato. % lotti e % posizioni non equivalgono al numero di trader unici.",
   ok:true},
 {id:"dukascopy",name:"Dukascopy SWFX",measure:"Sentiment del flusso di operazioni / liquidità",
   status:"widget",coverage:"Coppie Forex selezionate",url:()=> "https://www.dukascopy.com/trading-tools/widget/historical_sentiment_index",
   note:"Widget ufficiale sui consumatori di liquidità, distinto dalle posizioni Myfxbook. Non sono i lotti aperti della community.",
   ok:isFX},
 {id:"ig",name:"IG Client Sentiment",measure:"Percentuale di posizioni long/short presso IG",
   status:"api_external",coverage:"Forex, metalli e indici a seconda del mercato",
   url:()=> "https://www.ig.com/it/dati-di-mercato",
   note:"IG dispone di un'API ufficiale, ma Remura non ha ancora un accesso API IG autorizzato.",
   ok:true},
 {id:"fxblue",name:"FX Blue",measure:"Conti reali net long/short",
   status:"external",coverage:"Forex, disponibilità per mercato da controllare",
   url:()=> "https://www.fxblue.com/market-data/tools/sentiment",
   note:"Conta i conti reali, non i lotti. Utile per una conferma indipendente dai grandi volumi dei singoli account.",
   ok:isFX},
 {id:"oanda",name:"OANDA Position Book",measure:"Posizioni e ordini dei clienti per livello di prezzo",
   status:"external",coverage:"16 strumenti, Forex e alcuni metalli, da verificare",
   url:()=> "https://www.oanda.com/bvi-en/cfds/tools/orderbook/",
   note:"Distribuzione per livello di prezzo: non è una singola percentuale long/short confrontabile direttamente.",
   ok:isFX||isMetal},
 {id:"forexfactory",name:"Forex Factory",measure:"Traders long/short e lotti, campione di conti collegati",
   status:"external",coverage:"Forex e Gold, copertura in pagina",
   url:()=> "https://www.forexfactory.com/trades",
   note:"Le statistiche possono mostrare conti e lotti, ma Remura non dispone di un'API ufficiale autorizzata.",
   ok:isFX||symbol==="XAUUSD"},
 {id:"fxcm",name:"FXCM SSI Pro",measure:"Rapporto fra posizioni speculative dei clienti FXCM",
   status:"commercial",coverage:"Forex, Gold, Silver, indici selezionati",
   url:()=> "https://www.fxcm.com/pro/market-data/sentiment/",
   note:"Feed professionale XML: per importarci i valori serve accesso commerciale. Non è attivo in Remura.",
   ok:isFX||isMetal||isIndex}
];
const section=document.createElement("section");
section.className="panel overview rem-sources";
section.id="remura-multisource";
holder.insertAdjacentElement("afterend",section);
const intro=document.createElement("div");intro.className="ms-intro";
intro.innerHTML='<div><div class="eyebrow">REMURA · CONFERME INDIPENDENTI</div><h2>Confronto sentiment multi-fonte</h2><p>Un unico punto di accesso alle fonti più utili per <strong>'+symbol+'</strong>. Separiamo API automatiche, widget, consultazione esterna e feed professionali.</p></div>';
section.append(intro);
const summary=document.createElement("div");summary.className="ms-summary";
summary.textContent="Dati numerici automatici: verifica in corso. Le altre fonti rimangono separate e non entrano nel calcolo di una falsa media.";
section.append(summary);
const host=document.createElement("div");host.className="ms-list";section.append(host);
const manual=document.createElement("div");manual.className="ms-legend";
manual.innerHTML='<strong>Come confrontarli:</strong> Myfxbook misura lotti/posizioni; IG conta posizioni; FX Blue misura conti reali; Dukascopy osserva flussi e liquidità; OANDA raggruppa livelli di prezzo. <b>Non sommiamo o mediamo queste percentuali.</b> Il COT istituzionale rimane nella scheda sopra ed è settimanale.';
section.append(manual);
const providers=sourceDefs.filter(p=>p.ok);
function elem(tag,className,txt){const n=document.createElement(tag);if(className)n.className=className;if(txt!==undefined)n.textContent=txt;return n;}
function dateLabel(value){
 const d=new Date(value);
 return Number.isFinite(+d)?new Intl.DateTimeFormat("it-IT",{day:"2-digit",month:"short",hour:"2-digit",minute:"2-digit",timeZone:"Europe/Rome"}).format(d):"sconosciuta";
}
for(const p of providers){
 const card=elem("article","ms-card");card.id="ms-"+p.id;
 const header=elem("div","ms-card-top"),heading=elem("h3","",p.name);
 const status=elem("span","ms-status",p.id==="myfxbook"?"Verifica dati…":p.status==="widget"?"Widget ufficiale":p.status==="api_external"?"API da attivare":p.status==="commercial"?"Professionale":"Sito esterno");
 header.append(heading,status);
 const measure=elem("p","ms-measure",p.measure);
 const note=elem("p","ms-note",p.note);
 const coverage=elem("p","ms-coverage","Copertura: "+p.coverage);
 const bottom=elem("div","ms-actions");
 const a=elem("a","ms-link","Apri fonte originale ↗");a.href=p.url();a.target="_blank";a.rel="noopener noreferrer";
 bottom.append(a);
 if(p.status==="widget"){
   const w=elem("button","ms-widget-button","Mostra widget Dukascopy");
   w.type="button";w.setAttribute("aria-expanded","false");
   w.addEventListener("click",()=>showWidget(card,w));
   bottom.prepend(w);
 }
 card.append(header,measure,note,coverage,bottom);
 host.append(card);
}
function showWidget(card,button){
 const old=card.querySelector(".ms-widget");
 if(old){const wasHidden=old.hidden;old.hidden=!wasHidden;button.setAttribute("aria-expanded",String(wasHidden));button.textContent=wasHidden?"Nascondi widget":"Mostra widget Dukascopy";return;}
 const panel=elem("div","ms-widget");
 const info=elem("div","ms-widget-info","Widget ufficiale: scegli lo strumento all'interno del pannello Dukascopy. Potrebbe essere bloccato da Safari o da restrizioni del provider.");
 const slot=elem("div","ms-widget-slot");
 const loading=elem("div","ms-widget-loading","Caricamento widget esterno. Se non appare, usa il link alla fonte originale.");
 slot.append(loading);panel.append(info,slot);card.append(panel);
 button.setAttribute("aria-expanded","true");button.textContent="Nascondi widget";
 // Official Dukascopy widget loader, configured for the forex instruments available in Remura.
 window.DukascopyApplet={
   type:"historical_sentiment_index",
   params:{
     showHeader:false,tableBorderColor:"#30565f",liquidity:"consumers",
     availableInstruments:[symbol.slice(0,3)+"/"+symbol.slice(3),"EUR/USD","GBP/USD","USD/JPY","USD/CHF","EUR/JPY","GBP/JPY"],
     availableCurrencies:["AUD","CAD","CHF","GBP","HKD","JPY","MXN","NOK","NZD","PLN","RUB","SEK","SGD","TRY","USD","ZAR","EUR","XAG","XAU"],
     last:true,sixhours:true,oneday:true,fivedays:true,width:"100%",height:"280",adv:"popup"
   }
 };
 const script=document.createElement("script");
 script.src="https://freeserv-static.dukascopy.com/2.0/core.js";
 script.async=true;script.onerror=()=>{loading.textContent="Widget non caricato. Apri Dukascopy dal collegamento originale.";};
 slot.append(script);
}
async function myfxbook(){
 const card=section.querySelector("#ms-myfxbook");if(!card)return;
 const tag=card.querySelector(".ms-status");
 try{
  const request=await fetch("./data/myfxbook/latest.json?t="+Date.now(),{cache:"no-store"});
  if(!request.ok)throw Error("file non raggiungibile");
  const data=await request.json(),r=data.symbols?.[symbol];
  if(!r||r.lPct==null||r.sPct==null){tag.textContent="N/D";summary.textContent="Nessun campione Myfxbook valido per "+symbol+". Le altre fonti rimangono consultabili esternamente.";return;}
  const age=Date.now()-Date.parse(r.t||data.updatedAt),fresh=Number.isFinite(age)&&age>=0&&age<3*3600000;
  tag.textContent=fresh?"API collegata":"API collegata · datato";
  tag.classList.add(fresh?"ms-live":"ms-stale");
  const info=elem("div","ms-readings");
  const lots=elem("div","ms-reading"),trades=elem("div","ms-reading");
  const formatter=new Intl.NumberFormat("it-IT",{maximumFractionDigits:1});
  lots.append(elem("small","","Quota lotti long"),elem("strong","",formatter.format(+r.lPct)+"%"));
  const countLong=+r.lPos,countShort=+r.sPos,total=countLong+countShort;
  const positionPercent=Number.isFinite(total)&&total>0?formatter.format(countLong/total*100)+"%":"N/D";
  trades.append(elem("small","","Quota posizioni long"),elem("strong","",positionPercent));
  info.append(lots,trades);card.insertBefore(info,card.querySelector(".ms-coverage"));
  card.append(elem("p","ms-data-time","Ultimo campione "+dateLabel(r.t||data.updatedAt)+" (ora italiana)"+(fresh?"":" · ATTENZIONE: DATATO")));
  const supported=providers.length;
  summary.textContent="1 fonte con valori automatici verificabili (Myfxbook), "+(supported-1)+" ulteriori fonti consultabili o predisposte per "+symbol+". Nessuna media aggregata senza metriche omogenee.";
 }catch(e){tag.textContent="N/D";summary.textContent="Il feed Myfxbook non è raggiungibile in questa pagina. Verifica i collegamenti originali.";}
}
myfxbook();
})();