/* REMURA v1.14: lightweight private monitoring of all 38 markets. */
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
 card.append(rowText("Ultima M15:",entry.lastComplete?prettyTime(entry.lastComplete)+" · "+age:"N/D"));
 let origin="N/D";
 if(entry.source==="primary")origin="Principale";
 if(entry.source==="backup")origin="Riserva";
 const ticker=typeof entry.providerSymbol==="string"?entry.providerSymbol:"";
 card.append(rowText("Fonte:",origin+(ticker?" · "+ticker:"")));
 card.append(rowText("Ultimo tentativo:",prettyTime(entry.lastAttempt)));
 const reason=core.OUTCOMES[entry.lastOutcome];
 if(reason&&entry.lastOutcome!=="ok"){
  const warning=node("div","detail warning","Ultimo esito: "+reason);
  card.append(warning);
 }else if(entry.lastOutcome==="ok"){
  card.append(node("div","detail","Ultimo esito: salvataggio riuscito"));
 }else{
  card.append(node("div","detail","Ultimo esito: non ancora registrato"));
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
