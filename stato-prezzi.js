/* REMURA v1.25: private N/D diagnostics and opt-in OHLC verification. */
(()=>{
"use strict";
const $=id=>document.getElementById(id);
const core=window.REMURA_PRICE_STATUS_CORE;
const config=window.REMURA_MARKETS;
let data=null,loading=false;
const labels={recent:"RECENTE",stale:"DATATO",missing:"N/D"};
const fixes={
 ticker_unavailable:"Verifica il nome esatto del ticker sul conto cTrader e la mappatura privata.",
 no_historical_bars:"Verifica che lo strumento sia negoziabile e abbia storico M15 sul broker.",
 incomplete_history:"Lo storico restituito non è completo: verificare le finestre richieste.",
 invalid_bars:"Le candele non superano i controlli di formato e timestamp.",
 request_failed:"Controlla OAuth, connessione e collector della VPS.",
 unknown_error:"Controlla l'ultimo tentativo e, se persiste, i log privati della VPS."
};
const prettyTime=value=>{
 const date=new Date(value||"");
 return Number.isFinite(date.getTime())
  ?new Intl.DateTimeFormat("it-IT",{dateStyle:"short",timeStyle:"short",timeZone:"Europe/Rome"}).format(date)
  :"mai";
};
function node(tag,classname,txt){
 const element=document.createElement(tag);
 if(classname)element.className=classname;
 if(txt!==undefined)element.textContent=txt;
 return element;
}
function rowText(label,value){
 const r=node("div","detail");
 r.append(node("strong",null,label+" "),document.createTextNode(value));
 return r;
}
function categoryOf(symbol){
 return config?.other?.[symbol]?.group||"forex";
}
function titleOf(symbol){
 if(config?.other?.[symbol]?.name)return config.other[symbol].name;
 const group=config?.groups?.find(g=>g.id==="forex");
 return group?.items?.find(x=>x.s===symbol)?.n||symbol;
}
function marketCard(entry,serverTime){
 const result=core.interpret(entry,serverTime);
 const card=node("article","market");
 card.dataset.state=result.state;
 const head=node("div","market-head");
 head.append(node("b",null,entry.symbol),node("span","tag",labels[result.state]));
 card.append(head,node("div","desc",titleOf(entry.symbol)));
 const counts=node("div","counts");
 for(const timeframe of ["M15","H1","H4"]){
  const n=Number(entry.counts?.[timeframe])||0;
  counts.append(node("span","count",timeframe+" "+n.toLocaleString("it-IT")));
 }
 card.append(counts);
 const age=result.age===null?"N/D":result.age+" min";
 const lastM15=entry.lastComplete?prettyTime(entry.lastComplete)+" · "+age:"N/D";
 card.append(node("div","price-snapshot",entry.lastComplete?"Ultima M15: "+lastM15:"Ultima M15: N/D · dati ancora assenti"));
 const reason=core.OUTCOMES[entry.lastOutcome];
 if(reason&&entry.lastOutcome!=="ok"){
  card.append(node("div","price-summary-warning","Ultimo esito: "+reason));
 }else if(!entry.lastAttempt){
  card.append(node("div","price-summary-muted","Nessun tentativo registrato dalla nuova diagnostica"));
 }else{
  card.append(node("div","price-summary-muted","Ultimo tentativo: "+prettyTime(entry.lastAttempt)));
 }
 if(result.state==="missing")card.append(node("div","price-summary-warning",
  "Come sbloccarlo: "+(fixes[entry.lastOutcome]||"Controlla il prossimo tentativo di acquisizione cTrader.")));
 const more=node("details","market-more");
 more.append(node("summary",null,"Dettagli e provenienza"));
 let origin="N/D";
 if(entry.source==="primary")origin="Principale";
 if(entry.source==="backup")origin="Riserva";
 const ticker=typeof entry.providerSymbol==="string"?entry.providerSymbol:"";
 more.append(
  rowText("Ultima M15:",lastM15),
  rowText("Fonte:",origin+(ticker?" · "+ticker:"")),
  rowText("Ultimo tentativo:",prettyTime(entry.lastAttempt)),
  rowText("Ultimo esito:",reason||"Non ancora registrato")
 );
 card.append(more);
 if(result.state!=="missing"){
  const button=node("button","price-quality-button","Verifica qualità M15/H1/H4");
  button.type="button";
  const output=node("div","price-quality","");
  output.setAttribute("role","status");
  button.addEventListener("click",async()=>{
   button.disabled=true;
   output.textContent="Verifico lo storico privato di "+entry.symbol+"…";
   const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);
   try{
    const response=await fetch("./private-api/prices/"+encodeURIComponent(entry.symbol),
       {cache:"no-store",signal:controller.signal});
    if(!response.ok)throw Error("no_price");
    const bundle=await response.json();
    const doc=bundle?.schema==="remura-price-v1"?bundle.markets?.[entry.symbol]:null;
    if(doc?.symbol!==entry.symbol||doc?.provider!=="ctrader")throw Error("invalid");
    const q=core.macro.audit(doc,Date.parse(serverTime));
    const h1=q.h1||{verified:0,checked:0,missingInputs:0,mismatched:0};
    const h4=q.h4||{verified:0,checked:0,missingInputs:0,mismatched:0};
    const names={recent:"RECENTE",weekend:"ULTIMA SESSIONE VENERDÌ — NON LIVE",
       stale:"DATATO",invalid:"INCOERENTE",missing:"NESSUNA M15"};
    const lines=[
      "Stato: "+(names[q.state]||"Non verificabile"),
      "Campioni: M15 "+(q.counts?.M15||0)+" · H1 "+(q.counts?.H1||0)+" · H4 "+(q.counts?.H4||0),
      "H1 verificate: "+h1.verified+"/"+h1.checked+
         "; input mancanti "+h1.missingInputs+"; incoerenti "+h1.mismatched,
      "H4 verificate: "+h4.verified+"/"+h4.checked+
         "; input mancanti "+h4.missingInputs+"; incoerenti "+h4.mismatched,
      "Discontinuità ultime 97 M15: "+(q.recentGaps??"N/D")+
         " (possono includere pause regolari di mercato)"
    ];
    if(!q.ready)lines.push("Storico insufficiente: servono almeno 55 candele per timeframe.");
    if(q.state==="invalid"||h1.mismatched||h4.mismatched)
      lines.push("Non utilizzare i segnali prezzo finché i dati sono incoerenti.");
    if(q.state==="weekend")
      lines.push("La fotografia del venerdì non equivale a una conferma live.");
    output.dataset.state=q.state;
    output.textContent=lines.join("\n");
   }catch(_){
    output.dataset.state="error";
    output.textContent="Verifica non disponibile. Apri REMURA dalla VPS privata .ts.net.";
   }finally{clearTimeout(timer);button.disabled=false;}
  });
  card.append(button,output);
 }
 const link=node("a",null,"Apri scheda →");
 link.href=config?.detailUrl?.(entry.symbol)||"./asset.html?symbol="+encodeURIComponent(entry.symbol);
 card.append(link);
 return card;
}
function render(){
 if(!data||!Array.isArray(data.markets))return;
 const query=$("price-search").value.trim().toUpperCase();
 const state=$("price-filter").value,group=$("price-group").value;
 const ordering={missing:0,stale:1,recent:2};
 const values=data.markets.filter(entry=>{
  const cat=categoryOf(entry.symbol);
  const label=titleOf(entry.symbol);
  const s=core.interpret(entry,data.serverTime).state;
  return (state==="all"||s===state)&&(group==="all"||cat===group)
   &&(!query||entry.symbol.includes(query)||label.toUpperCase().includes(query));
 }).sort((a,b)=>{
  const ra=ordering[core.interpret(a,data.serverTime).state];
  const rb=ordering[core.interpret(b,data.serverTime).state];
  return ra-rb||a.symbol.localeCompare(b.symbol);
 });
 const target=$("price-list");target.replaceChildren();
 for(const row of values)target.append(marketCard(row,data.serverTime));
 $("price-results-count").textContent=values.length+" mercati visualizzati su "+data.total+". Le voci N/D appaiono per prime.";
}
async function refresh(){
 if(loading)return;
 loading=true;
 $("price-refresh").disabled=true;
 $("price-message").textContent="Leggo lo stato dei prezzi dalla VPS…";
 $("price-message").dataset.error="false";
 try{
  const response=await fetch("./private-api/prices/status",{cache:"no-store"});
  if(!response.ok)throw Error("unavailable");
  const parsed=await response.json();
  if(parsed?.schema!=="remura-price-status-v1"||!Array.isArray(parsed.markets)
      ||parsed.markets.length!==38||parsed.total!==38)throw Error("schema");
  data=parsed;
  const totals=core.summarize(parsed.markets,parsed.serverTime);
  $("price-total").textContent=parsed.total;
  $("price-recent").textContent=totals.recent;
  $("price-stale").textContent=totals.stale;
  $("price-missing").textContent=totals.missing;
  $("price-message").textContent="VPS collegata · Stato aggiornato alle "+prettyTime(parsed.serverTime)+" (Italia)";
  const last=prettyTime(parsed.lastAttempt);
  $("price-last-run").textContent="Collector: "+String(parsed.collector||"N/D")+
   " · Ultima richiesta: "+last+" · Gruppo: "+String(parsed.collectorBatch||"N/D")+
   " · Rotazione nominale 120 minuti";
  const missing=parsed.markets.filter(e=>core.interpret(e,parsed.serverTime).state==="missing");
  $("price-missing-summary").textContent=missing.length?
   "SENZA STORICO ("+missing.length+"): "+
   missing.map(e=>e.symbol+" · "+(core.OUTCOMES[e.lastOutcome]||"motivo non registrato")).join(" | ")+
   ". I dettagli qui sotto mostrano il prossimo controllo da fare.":
   "Tutti i 38 mercati hanno M15 archiviate. Controlla comunque freschezza e qualità prima di generare segnali.";
  render();
 }catch(_){
  data=null;
  $("price-message").dataset.error="true";
  $("price-message").textContent="Stato privato non disponibile. Apri REMURA dalla tua web app .ts.net e verifica che la VPS sia connessa; su GitHub Pages i dati del server non sono accessibili.";
  $("price-last-run").textContent="Nessun dato ricevuto: non mostriamo prezzi simulati.";
  $("price-list").replaceChildren();
  $("price-missing-summary").textContent="La VPS non risponde: mercati N/D non identificabili da GitHub.";
  $("price-results-count").textContent="";
  for(const id of ["price-total","price-recent","price-stale","price-missing"])$(id).textContent="—";
 }finally{loading=false;$("price-refresh").disabled=false;}
}
for(const id of ["price-search","price-filter","price-group"]){
 $(id).addEventListener(id==="price-search"?"input":"change",render);
}
$("price-refresh").addEventListener("click",refresh);
refresh();
setInterval(()=>{if(document.visibilityState==="visible")refresh();},180000);
})();

/* REMURA v1.23 · global DXY/VIX context and per-market comparison, private/read-only. */
(()=>{
"use strict";
const $=id=>document.getElementById(id),core=window.REMURA_PRICE_STATUS_CORE.macro;
const MACRO=[{symbol:"DXY",name:"DXY · dollaro",note:"USDX del broker, contratto con possibile scadenza"},
             {symbol:"VIX",name:"VIX · volatilità",note:"Contratto broker; diverso dall'indice spot VIX"}];
const docs=Object.create(null);
const fmt=n=>(Number.isFinite(n)?n.toLocaleString("it-IT",{maximumFractionDigits:3,minimumFractionDigits:0}):"N/D");
const when=t=>{const d=new Date(t||"");return Number.isFinite(d.getTime())?new Intl.DateTimeFormat("it-IT",{dateStyle:"short",timeStyle:"short",timeZone:"Europe/Rome"}).format(d):"N/D"};
const elt=(tag,cls,text)=>{const node=document.createElement(tag);if(cls)node.className=cls;if(text!==undefined)node.textContent=text;return node};
function fact(root,label,value,cls="fact"){
 const div=elt("div",cls);div.append(elt("b",null,label+" "),document.createTextNode(value));root.append(div);
}
function auditCard(symbol,name,note,doc){
 const result=core.audit(doc,Date.now()),card=elt("article","market"),header=elt("div");
 const statusName={recent:"RECENTE",weekend:"ULTIMA SESSIONE",stale:"DATATO",missing:"N/D",invalid:"VERIFICA"};
 header.append(elt("strong",null,name),elt("span","badge",statusName[result.state]||"N/D"));
 header.lastChild.dataset.state=result.state;
 card.append(header,elt("div","foot",note));
 fact(card,"Storico:","M15 "+result.counts.M15+" · H1 "+result.counts.H1+" · H4 "+result.counts.H4);
 if(result.state==="missing"){fact(card,"Qualità:","nessuno storico cTrader ancora disponibile");return card}
 fact(card,"Ultima M15:",when(result.asof)+" · "+result.ageMinutes+" min dalla chiusura");
 fact(card,"Interruzioni ultime 97 M15:",result.recentGaps+" (comprese pause sessione)");
 fact(card,"H1 ricostruite:",result.h1.verified+"/"+result.h1.checked+" verificate; "+result.h1.mismatched+" incoerenti");
 fact(card,"H4 ricostruite:",result.h4.verified+"/"+result.h4.checked+" verificate; "+result.h4.mismatched+" incoerenti");
 if(result.h1.missingInputs||result.h4.missingInputs)fact(card,"Dati non verificabili:",result.h1.missingInputs+result.h4.missingInputs+" aggregazioni con M15 incomplete");
 if(result.state==="weekend")
  card.append(elt("div","foot","Pausa del fine settimana: ultimi prezzi del venerdì, NON aggiornati in tempo reale."));
 else if(result.state!=="recent")
  card.append(elt("div","warn","Per l'analisi macro sono richiesti dati recenti e coerenti."));
 return card;
}
async function getPrice(sym){
 if(Object.prototype.hasOwnProperty.call(docs,sym))return docs[sym];
 try{
  const response=await fetch("./private-api/prices/"+encodeURIComponent(sym),{cache:"no-store"});
  if(!response.ok)throw Error("missing");
  const body=await response.json();
  const record=body?.schema==="remura-price-v1"?body?.markets?.[sym]:null;
  if(!record||record.provider!=="ctrader"||record.symbol!==sym)throw Error("invalid");
  docs[sym]=record;
 }catch(_){docs[sym]=null}
 return docs[sym];
}
function macroPulseText(info){
 if(info.state!=="ok")return "N/D (candele mancanti, datate o non sufficienti)";
 const sign=info.changePct>0?"+":"";
 const movement={up:"aumento significativo rispetto alla propria mediana",down:"calo significativo rispetto alla propria mediana",flat:"variazione contenuta rispetto alla propria mediana"}[info.direction];
 return sign+fmt(info.changePct)+"% nelle ultime 4 ore H1 contigue · "+movement;
}
function qualifiedCorrelation(left,right){
 const one=docs[left],two=docs[right];
 const result=one&&two?core.correlation(one,two):{state:"insufficient",samples:0,value:null};
 const eligible=!!(one&&two&&core.pairEligible(one,two));
 return eligible?result:{...result,state:"unavailable",value:null};
}
function rowCorrelation(root,left,right,one,two){
 const c=qualifiedCorrelation(left,right);
 const trust=!!(one&&two&&core.pairEligible(one,two));
 const historical=trust&&[one,two].some(doc=>core.audit(doc,Date.now()).state==="weekend");
 const row=elt("tr");
 row.append(elt("td",null,left+" / "+right),
  elt("td",null,c.state==="ok"&&trust?fmt(c.value):"N/D"),
  elt("td",null,c.samples+" · "+(historical?"ultima sessione, non live":trust?"ore UTC abbinate":"serie assenti, datate o non coerenti")));
 root.append(row);
}
function correlations(pairs){
 const table=elt("table"),tr=elt("tr");
 for(const h of ["Confronto","Pearson H1","Campioni"])tr.append(elt("th",null,h));
 const head=elt("thead");head.append(tr);table.append(head);
 const body=elt("tbody");
 for(const [x,y] of pairs)rowCorrelation(body,x,y,docs[x],docs[y]);
 table.append(body);
 return table;
}
function explainPair(box,benchmark,report){
 const section=elt("div","relationship-pair");
 const label=elt("strong",null,benchmark+": "+report.label);
 const description=elt("p",null,report.detail);
 section.append(label,description);
 box.append(section);
}
function explainMarket(symbol){
 const dxy=qualifiedCorrelation(symbol,"DXY"),vix=qualifiedCorrelation(symbol,"VIX");
 const alias=symbol==="GER30"?"DAX 40 (GER30)":symbol;
 const report=core.compareMacroRelationships(alias,dxy,vix);
 const box=elt("section","relationship-insight");
 box.append(elt("h3",null,report.title),elt("p",null,report.summary));
 explainPair(box,"DXY",report.dollar);
 explainPair(box,"VIX",report.fear);
 const isWeekend=docs[symbol]&&docs.DXY&&docs.VIX&&
  [symbol,"DXY","VIX"].some(sym=>core.audit(docs[sym],Date.now()).state==="weekend");
 if(isWeekend)box.append(elt("p","session-note","ULTIMA SESSIONE: interpretazione storica, non live."));
 box.append(elt("p","foot","Valori di Pearson sui rendimenti H1: relazione storica, non causalità, previsione o prova di ordini istituzionali. Le fasce qualitative sono soltanto descrittive e possono cambiare con il periodo selezionato."));
 return box;
}
function macroContext(){
 const result=core.context(docs.DXY,docs.VIX,{now:Date.now()});
 const closed=docs.DXY&&docs.VIX&&
  core.audit(docs.DXY,Date.now()).state==="weekend"&&
  core.audit(docs.VIX,Date.now()).state==="weekend";
 const banner=closed
  ?elt("div","session-note","ULTIMA SESSIONE DEL VENERDÌ · Contesto storico, non segnale in tempo reale.")
  :null;
 $("macro-context").replaceChildren(...(banner?[banner]:[]),
  elt("h3",null,result.label),elt("p",null,result.description));
 fact($("macro-context"),"DXY:",macroPulseText(result.dollar));
 fact($("macro-context"),"VIX:",macroPulseText(result.fear));
 $("macro-context").dataset.state=result.state;
 $("macro-pairs").replaceChildren(correlations([["DXY","VIX"]]));
}
async function compareMarket(){
 const symbol=$("macro-symbol").value,button=$("macro-check");
 if(!symbol)return;
 button.disabled=true;
 $("macro-extra").textContent="Recupero "+symbol+" dalla VPS privata…";
 try{
  const target=await getPrice(symbol);
  $("macro-extra").replaceChildren(auditCard(symbol,symbol,"Strumento scelto per confronto con DXY e VIX",target));
  $("macro-target-correlations").replaceChildren(
   correlations([[symbol,"DXY"],[symbol,"VIX"]]));
  $("macro-target-interpretation").replaceChildren(explainMarket(symbol));
 }finally{button.disabled=false}
}
async function refreshMacro(){
 const button=$("macro-refresh"),status=$("macro-status");
 button.disabled=true;status.dataset.error="false";
 status.textContent="Verifico USDX e VIX sul server privato…";
 for(const k of Object.keys(docs))delete docs[k];
 try{
  await Promise.all(MACRO.map(async m=>getPrice(m.symbol)));
  const box=$("macro-markets");box.replaceChildren();
  for(const info of MACRO)box.append(auditCard(info.symbol,info.name,info.note,docs[info.symbol]));
  macroContext();
  const available=MACRO.filter(m=>docs[m.symbol]).length;
  const weekend=MACRO.every(m=>core.audit(docs[m.symbol],Date.now()).state==="weekend");
  status.dataset.error=String(available===0);
  status.textContent=available+"/2 indicatori con storico · "+when(new Date().toISOString())+
   (available<2?" · N/D finché il raccoglitore non fornisce le candele.":
    weekend?" · PAUSA WEEKEND: analisi dell'ultima sessione del venerdì, non live.":
    " · Analisi basata su dati cTrader.");
  if($("macro-symbol").value)await compareMarket();
 }catch(_){
  status.dataset.error="true";
  status.textContent="Analisi non disponibile dalla VPS privata. Nessun indicatore simulato.";
 }finally{button.disabled=false}
}
let initialized=false;
function initialize(){
 if(initialized||location.hash!=="#macro")return;
 initialized=true;
 const select=$("macro-symbol");
 const groups=window.REMURA_MARKETS?.groups||[];
 const included=new Set();
 const placeholder=elt("option",null,"Scegli un mercato…");placeholder.value="";select.append(placeholder);
 for(const group of groups){
  if(group.id==="macro")continue;
  for(const item of group.items){
   if(included.has(item.s))continue;
   included.add(item.s);
   const label=elt("option",null,item.n+" · "+item.s);label.value=item.s;
   select.append(label);
  }
 }
 $("macro-refresh").addEventListener("click",refreshMacro);
 $("macro-check").addEventListener("click",compareMarket);
 select.addEventListener("change",()=>{
  if(!select.value){$("macro-extra").replaceChildren();$("macro-target-correlations").replaceChildren();
   $("macro-target-interpretation").replaceChildren();return;}
  compareMarket();
 });
 refreshMacro();
}
window.addEventListener("hashchange",initialize);
initialize();
})();