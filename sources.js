/* REMURA multi-fonte: only independently collected numbers are counted. */
(()=>{
"use strict";
const symbol=(new URLSearchParams(location.search).get("symbol")||"XAUUSD").toUpperCase();
const cfg=window.REMURA_MARKETS;
const holder=document.getElementById("retail-module");
if(!cfg||!cfg.symbols.includes(symbol)||!holder)return;
const group=cfg.other[symbol]?.group||(symbol.length===6?"forex":"other");
const isFX=group==="forex",isMetal=group==="metals",isIndex=group==="indices";
const sourceDefs=[
 {id:"myfxbook",name:"Myfxbook",measure:"Lotti e numero di posizioni della community",
   status:"automatic",coverage:"Strumenti disponibili nell'API Community Outlook",
   url:()=> "https://www.myfxbook.com/community/outlook/"+encodeURIComponent(symbol),
   note:"Il volume in lotti non è il numero di trader. Le percentuali Myfxbook sono quote del volume.",ok:true},
 {id:"ig",name:"IG Client Sentiment",measure:"Percentuale delle posizioni long e short dei clienti IG",
   status:"automatic",coverage:"Gruppi di mercato restituiti dall'API IG autenticata",
   url:()=> "https://www.ig.com/it/dati-di-mercato",
   note:"Fonte indipendente, attivabile con credenziali API lato GitHub Actions. Non usa gli stessi lotti o lo stesso campione di Myfxbook.",ok:true},
 {id:"dukascopy",name:"Dukascopy SWFX",measure:"Indice del sentiment di liquidity consumers e providers",
   status:"widget",coverage:"Coppie Forex selezionate",
   url:()=> "https://www.dukascopy.com/trading-tools/widget/historical_sentiment_index",
   note:"Widget del provider aggiornato di norma ogni 30 minuti. Il dato rimane nel widget e non è importato nella nostra API.",ok:isFX},
 {id:"fxblue",name:"FX Blue",measure:"Percentuali di conti reali net long e net short",
   status:"external",coverage:"Coppie Forex disponibili sul sito",
   url:()=> "https://www.fxblue.com/market-data/tools/sentiment",
   note:"Conta conti reali, non lotti o singole operazioni. Consultazione esterna.",ok:isFX},
 {id:"oanda",name:"OANDA Position Book",measure:"Distribuzione delle posizioni per livelli di prezzo",
   status:"external",coverage:"Forex e alcuni metalli, quando supportati",
   url:()=> "https://www.oanda.com/bvi-en/cfds/tools/orderbook/",
   note:"Un position book non equivale a una percentuale complessiva long/short.",ok:isFX||isMetal},
 {id:"forexfactory",name:"Forex Factory",measure:"Trader e lotti della community collegata",
   status:"external",coverage:"Forex e Gold",
   url:()=> "https://www.forexfactory.com/trades",
   note:"Nessun feed automatico autorizzato in Remura.",ok:isFX||symbol==="XAUUSD"},
 {id:"fxcm",name:"FXCM SSI Pro",measure:"Rapporto fra posizioni speculative dei clienti FXCM",
   status:"commercial",coverage:"Forex, metalli, alcuni indici",
   url:()=> "https://www.fxcm.com/pro/market-data/sentiment/",
   note:"Accesso commerciale richiesto; nessun numero acquisito.",ok:isFX||isMetal||isIndex}
];
function elem(tag,cls,txt){
 const n=document.createElement(tag);
 if(cls)n.className=cls;
 if(txt!==undefined)n.textContent=txt;
 return n;
}
function dateLabel(value){
 const d=new Date(value);
 return Number.isFinite(+d)?new Intl.DateTimeFormat("it-IT",{day:"2-digit",month:"short",hour:"2-digit",minute:"2-digit",timeZone:"Europe/Rome"}).format(d):"sconosciuta";
}
const section=elem("section","panel overview rem-sources");
section.id="remura-multisource";holder.insertAdjacentElement("afterend",section);
const intro=elem("div","ms-intro");
intro.append(elem("div","eyebrow","REMURA · FONTI INDIPENDENTI"),elem("h2","","Confronto sentiment multi-fonte"),
 elem("p","","Solo valori realmente acquisiti dalle API entrano nel confronto. Widget e siti esterni restano strumenti di verifica separati."));
section.append(intro);
const summary=elem("div","ms-summary","Controllo dei feed in corso…");section.append(summary);
const compare=elem("div","ms-comparison");compare.hidden=true;section.append(compare);
const host=elem("div","ms-list");section.append(host);
const legend=elem("div","ms-legend");
legend.textContent="Myfxbook misura il peso dei lotti e il numero di posizioni; IG misura la quota delle posizioni dei suoi clienti. Dukascopy osserva un diverso pool di operatori. I campioni non sono rappresentativi dell'intero mercato: nessuna media e nessuna identificazione automatica delle controparti istituzionali. Il COT resta settimanale.";
section.append(legend);
const providers=sourceDefs.filter(s=>s.ok);
const cards=new Map();
for(const p of providers){
 const card=elem("article","ms-card");card.id="ms-"+p.id;
 const header=elem("div","ms-card-top"),status=elem("span","ms-status",
   p.status==="automatic"?"Controllo feed…":p.status==="widget"?"Widget esterno":p.status==="commercial"?"Commerciale":"Sito esterno");
 header.append(elem("h3","",p.name),status);
 card.append(header,elem("p","ms-measure",p.measure),elem("p","ms-note",p.note),
   elem("p","ms-coverage","Copertura: "+p.coverage));
 const bottom=elem("div","ms-actions");
 const link=elem("a","ms-link","Apri fonte originale ↗");
 link.href=p.url();link.target="_blank";link.rel="noopener noreferrer";
 if(p.status==="widget"){
  const button=elem("button","ms-widget-button","Mostra Dukascopy");
  button.type="button";button.setAttribute("aria-expanded","false");
  button.addEventListener("click",()=>showWidget(card,button));
  bottom.append(button);
 }
 bottom.append(link);card.append(bottom);host.append(card);
 cards.set(p.id,{card,status});
}
function showWidget(card,button){
 let panel=card.querySelector(".ms-widget");
 if(panel){
  panel.hidden=!panel.hidden;
  button.textContent=panel.hidden?"Mostra Dukascopy":"Nascondi Dukascopy";
  button.setAttribute("aria-expanded",String(!panel.hidden));
  return;
 }
 panel=elem("div","ms-widget");
 panel.append(elem("div","ms-widget-info","Widget ufficiale: i numeri provengono da Dukascopy e non vengono copiati nelle statistiche Remura. Se Safari lo blocca, apri la fonte originale."));
 const frame=document.createElement("iframe");
 frame.title="Dukascopy Historical Sentiment - "+symbol;
 frame.loading="lazy";frame.setAttribute("sandbox","allow-scripts allow-popups");
 frame.setAttribute("referrerpolicy","no-referrer");frame.style.cssText="width:100%;height:310px;border:0;display:block;";
 const config={type:"historical_sentiment_index",params:{
   showHeader:false,tableBorderColor:"#30565f",liquidity:"consumers",
   availableInstruments:[symbol.slice(0,3)+"/"+symbol.slice(3),"EUR/USD","GBP/USD","USD/JPY"],
   availableCurrencies:["AUD","CAD","CHF","GBP","JPY","NZD","USD","EUR"],
   last:true,sixhours:true,oneday:true,fivedays:true,width:"100%",height:"280",adv:"popup"}};
 frame.srcdoc='<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="margin:0"><script>window.DukascopyApplet='+JSON.stringify(config)+';<\/script><script src="https://freeserv-static.dukascopy.com/2.0/core.js"><\/script></body></html>';
 panel.append(frame);card.append(panel);
 button.textContent="Nascondi Dukascopy";button.setAttribute("aria-expanded","true");
}
const reading={myfxbook:null,ig:null};
const fmt=new Intl.NumberFormat("it-IT",{maximumFractionDigits:1});
function percent(n){return fmt.format(n)+"%";}
function validPercent(row){
 const l=Number(row?.lPct),s=Number(row?.sPct);
 return row&&row.lPct!==null&&row.lPct!==undefined&&row.sPct!==null&&row.sPct!==undefined&&
   Number.isFinite(l)&&Number.isFinite(s)&&l>=0&&s>=0&&l<=100&&s<=100&&Math.abs(l+s-100)<=1;
}
function setStatus(id,message,cls){
 const tag=cards.get(id)?.status;if(!tag)return;
 tag.textContent=message;tag.className="ms-status"+(cls?" "+cls:"");
}
function addNumbers(id,row,time,age,environment){
 const card=cards.get(id).card;
 const info=elem("div","ms-readings");
 const add=(label,value)=>{
  const box=elem("div","ms-reading");
  box.append(elem("small","",label),elem("strong","",value));info.append(box);
 };
 add(id==="ig"?"Posizioni long IG":"Lotti long Myfxbook",percent(+row.lPct));
 if(id==="ig")add("Posizioni short IG",percent(+row.sPct));
 else {
  const total=Number(row.lPos)+Number(row.sPos);
  add("Posizioni long Myfxbook",Number.isFinite(total)&&total>0?percent(Number(row.lPos)/total*100):"N/D");
 }
 card.insertBefore(info,card.querySelector(".ms-coverage"));
 const label=elem("p","ms-data-time","Acquisizione "+dateLabel(time)+" (ora italiana)"+
   (age>3*3600000?" · DATO DATATO":"")+
   (environment==="demo"?" · Accesso IG demo":""));
 card.append(label);
}
async function fetchJson(path){
 const response=await fetch(path+"?t="+Date.now(),{cache:"no-store"});
 if(!response.ok)throw Error("HTTP "+response.status);
 return response.json();
}
async function loadSource(id,path){
 try{
  const data=await fetchJson(path),row=data.symbols?.[symbol];
  if(data.status!=="ok"){setStatus(id,"Feed non disponibile");return;}
  if(!validPercent(row)){setStatus(id,"Mercato non coperto");return;}
  const time=row.t||data.updatedAt,age=Date.now()-Date.parse(time);
  const fresh=Number.isFinite(age)&&age>=0&&age<=3*3600000;
  const total=Number(row.lPos)+Number(row.sPos);
  const tiny=id==="myfxbook"&&Number.isFinite(total)&&total<30;
  const usable=fresh&&!tiny;
  setStatus(id,tiny?"Campione piccolo":fresh?"Dati acquisiti":"Dati datati",usable?"ms-live":"ms-stale");
  addNumbers(id,row,time,age,data.environment);
  if(tiny)cards.get(id).card.append(elem("p","ms-data-time","Campione inferiore a 30 posizioni: escluso dal confronto."));
  reading[id]={row,fresh:usable};
 }catch(error){
  setStatus(id,error.message==="HTTP 404"?"Non configurata":"Feed non raggiungibile","ms-stale");
 }
}
function updateSummary(){
 const n=Object.values(reading).filter(s=>s?.fresh).length;
 summary.textContent=n+" fonte"+(n===1?"":"i")+" numerica"+(n===1?"":"he")+" aggiornata"+(n===1?"":"e")+" su 2 possibili per "+symbol+
  ". Ogni fonte mantiene unità, campione e data propri. Widget e siti esterni non sono conteggiati.";
 const m=reading.myfxbook,i=reading.ig;
 if(!m?.fresh||!i?.fresh){compare.hidden=true;return;}
 const a=Math.abs(m.row.lPct-50)<5?"neutro":m.row.lPct>50?"long":"short";
 const b=Math.abs(i.row.lPct-50)<5?"neutro":i.row.lPct>50?"long":"short";
 compare.hidden=false;
 compare.textContent=a==="neutro"||b==="neutro"?"Uno dei due campioni è vicino all'equilibrio: nessuna convergenza forte.":
  a===b?"Entrambi i campioni hanno prevalenza "+a+", ma si basano su metriche diverse. Non è un segnale istituzionale.":
  "DIVERGENZA: Myfxbook per lotti prevale "+a+", IG per posizioni prevale "+b+". Campioni indipendenti: verificare prima di interpretare.";
}
Promise.all([
 loadSource("myfxbook","./data/myfxbook/latest.json"),
 loadSource("ig","./data/ig/latest.json")
]).then(updateSummary);
})();
