/* REMURA v1.18: lightweight private monitoring of all 38 markets. */
(()=>{
"use strict";
const $=id=>document.getElementById(id);
const core=window.REMURA_PRICE_STATUS_CORE;
const config=window.REMURA_MARKETS;
let data=null,loading=false;
const labels={recent:"RECENTE",stale:"DATATO",missing:"N/D"};
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
  render();
 }catch(_){
  data=null;
  $("price-message").dataset.error="true";
  $("price-message").textContent="Stato privato non disponibile. Apri REMURA dalla tua web app .ts.net e verifica che la VPS sia connessa; su GitHub Pages i dati del server non sono accessibili.";
  $("price-last-run").textContent="Nessun dato ricevuto: non mostriamo prezzi simulati.";
  $("price-list").replaceChildren();
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

/* REMURA v1.18 · private read-only dashboard, no synthetic prices. */
(()=>{
"use strict";
const $=id=>document.getElementById(id);
const core=window.REMURA_PRICE_STATUS_CORE.macro;
const marketInfo=[
 {symbol:"GER30",label:"DAX 40",note:"Candele GER30: non sostituite con GER40"},
 {symbol:"DXY",label:"Dollar Index",note:"Prezzo cTrader USDX, possibile scadenza del contratto"},
 {symbol:"VIX",label:"Volatilità",note:"Contratto broker con scadenza, non indice spot CBOE"}
];
const docs={};
const stamp=t=>{const d=new Date(t||"");return Number.isFinite(d.getTime())?new Intl.DateTimeFormat("it-IT",{dateStyle:"short",timeStyle:"short",timeZone:"Europe/Rome"}).format(d):"N/D"};
function el(tag,cls,text){
 const e=document.createElement(tag);
 if(cls)e.className=cls;
 if(text!==undefined)e.textContent=text;
 return e;
}
function line(parent,label,value,cls="fact"){
 const div=el("div",cls);
 div.append(el("b",null,label+" "),document.createTextNode(value));
 parent.append(div);
}
function qualityCard(symbol,title,note,data){
 const card=el("article","market");
 const h=el("div");
 const head=el("strong",null,title+" · "+symbol);
 h.append(head);
 const quality=data?core.audit(data,Date.now()):{state:"missing",counts:{M15:0,H1:0,H4:0}};
 const labels={recent:"RECENTE",stale:"DATATO",missing:"N/D",invalid:"VERIFICA"};
 const chip=el("span","badge",labels[quality.state]||"N/D");
 chip.dataset.state=quality.state;h.append(chip);
 card.append(h,el("div","foot",note));
 line(card,"Candele:","M15 "+quality.counts.M15+" · H1 "+quality.counts.H1+" · H4 "+quality.counts.H4);
 if(quality.state==="missing"){
  line(card,"Disponibilità:","storico non ancora acquisito");
  return card;
 }
 line(card,"Ultima M15:",stamp(quality.asof)+" · "+quality.ageMinutes+" min dalla chiusura");
 line(card,"Interruzioni nelle ultime 97 M15:",String(quality.recentGaps)+" (possono essere pause di mercato)");
 line(card,"Ricostruzione H1:",quality.h1.verified+"/"+quality.h1.checked+" verificati · "+quality.h1.mismatched+" non coerenti");
 line(card,"Ricostruzione H4:",quality.h4.verified+"/"+quality.h4.checked+" verificati · "+quality.h4.mismatched+" non coerenti");
 if(quality.h1.missingInputs||quality.h4.missingInputs)
  line(card,"Copertura non verificabile:",(quality.h1.missingInputs+quality.h4.missingInputs)+" intervalli senza tutte le M15");
 if(quality.state==="invalid")card.append(el("div","warn","Anomalie di integrità: non utilizzare per conferme operative."));
 if(quality.state==="stale")card.append(el("div","warn","Prezzo datato: mercato chiuso, scadenza o raccolta da verificare."));
 if(!quality.ready)card.append(el("div","warn","Storico insufficiente per interpretazione tecnica a 55 candele H4."));
 return card;
}
async function load(symbol){
 if(Object.prototype.hasOwnProperty.call(docs,symbol))return docs[symbol];
 try{
  const r=await fetch("./private-api/prices/"+encodeURIComponent(symbol),{cache:"no-store"});
  if(!r.ok)throw Error("missing");
  const parsed=await r.json();
  const record=parsed?.schema==="remura-price-v1"?parsed?.markets?.[symbol]:null;
  if(!record||record.symbol!==symbol||record.provider!=="ctrader")throw Error("invalid");
  docs[symbol]=record;
 }catch(_){docs[symbol]=null;}
 return docs[symbol];
}
async function refresh(){
 const status=$("macro-status"),b=$("macro-refresh");b.disabled=true;
 status.dataset.error="false";status.textContent="Leggo le tre serie dalla VPS privata…";
 for(const k of Object.keys(docs))delete docs[k];
 try{
  const results=await Promise.all(marketInfo.map(m=>load(m.symbol)));
  const box=$("macro-markets");box.replaceChildren();
  for(let i=0;i<marketInfo.length;i++){
   const info=marketInfo[i];box.append(qualityCard(info.symbol,info.label,info.note,results[i]));
  }
  const pairs=[["GER30","DXY"],["GER30","VIX"],["DXY","VIX"]];
  const table=el("table"),head=el("tr");
  for(const col of ["Mercati","Pearson H1","Campioni UTC"])head.append(el("th",null,col));
  const header=el("thead");header.append(head);table.append(header);
  const body=el("tbody");
  for(const [left,right] of pairs){
   const one=docs[left],two=docs[right],row=el("tr"),c=one&&two?core.correlation(one,two):{state:"insufficient",samples:0,value:null};
   const trusted=one&&two&&core.pairEligible(one,two);
   row.append(el("td",null,left+" / "+right),
              el("td",null,c.state==="ok"&&trusted?c.value.toFixed(3):"N/D"),
              el("td",null,c.samples+" · "+(c.state==="ok"&&!trusted?"prezzi datati/anomali":c.state==="ok"?"allineati":"insufficienti")));
   body.append(row);
  }
  table.append(body);
  $("macro-pairs").replaceChildren(table);
  const n=results.filter(Boolean).length;
  status.textContent=n+"/3 serie prezzi ricevute dalla VPS · "+stamp(new Date().toISOString())+". N/D dove la verifica non è possibile.";
  if(n<3)status.textContent+=" DXY/VIX potrebbero essere ancora in fase di primo storico.";
 }catch(_){
  status.dataset.error="true";
  status.textContent="Impossibile verificare la VPS privata. Apri REMURA su .ts.net; non mostriamo dati fittizi.";
 }finally{b.disabled=false;}
}
async function selected(){
 const symbol=$("macro-symbol").value,b=$("macro-check");b.disabled=true;
 $("macro-extra").textContent="Verifico "+symbol+"…";
 try{const record=await load(symbol);$("macro-extra").replaceChildren(qualityCard(symbol,symbol,"Verifica privata su richiesta",record));}
 catch(_){$("macro-extra").textContent="Dati non disponibili.";}
 finally{b.disabled=false;}
}
let macroInitialized=false;
function initMacro(){
 if(macroInitialized||location.hash!=="#macro")return;
 macroInitialized=true;
 const marketSymbols=window.REMURA_MARKETS?.symbols||marketInfo.map(x=>x.symbol);
 for(const sym of marketSymbols){const o=el("option",null,sym);o.value=sym;$("macro-symbol").append(o);}
 $("macro-symbol").value="GER30";
 $("macro-refresh").addEventListener("click",refresh);
 $("macro-check").addEventListener("click",selected);
 refresh();
}
window.addEventListener("hashchange",initMacro);
initMacro();
})();