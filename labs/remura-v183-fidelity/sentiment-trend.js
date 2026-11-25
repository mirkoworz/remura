/* REMURA v1.4 — explanation of how both retail populations actually evolve. */
(()=>{
 "use strict";
 const core=window.REMURA_SENTIMENT_TREND;
 const target=document.getElementById("retail-module");
 if(!core||!target)return;
 const symbol=(new URLSearchParams(location.search).get("symbol")||"XAUUSD").toUpperCase();
 const el=(tag,cls,text)=>{
  const node=document.createElement(tag);
  if(cls)node.className=cls;
  if(text!==undefined)node.textContent=text;
  return node;
 };
 const shell=el("section","panel overview rm-momentum");
 shell.id="remura-sentiment-momentum";
 shell.setAttribute("aria-labelledby","rm-momentum-title");
 const head=el("div","rm-momentum-header");
 const title=el("div");
 title.append(el("div","eyebrow","02 · EVOLUZIONE SENTIMENT NEL TEMPO"),
  el("h2","","Come sta cambiando il retail su "+symbol+"?"),
  el("p","","REMURA confronta osservazioni storiche vere. Ti dice se i long aumentano o diminuiscono, non soltanto la fotografia attuale."));
 const badge=el("span","rm-momentum-badge","Analisi automatica");
 head.append(title,badge);
 const controls=el("div","rm-momentum-controls");
 controls.setAttribute("role","group");
 controls.setAttribute("aria-label","Intervallo per il confronto del sentiment");
 const cards=el("div","rm-momentum-grid");
 const results={};
 for(const [key,label,metric] of [
  ["myfxbook","Myfxbook","Quota del volume in lotti"],
  ["capital","Capital.com","Quota delle posizioni clienti"]]){
  const card=el("article","rm-momentum-card");
  const name=el("div","rm-momentum-name");
  name.append(el("strong","",label),el("small","",metric));
  const verdict=el("div","rm-momentum-verdict","Raccolta dati in corso…");
  const amounts=el("div","rm-momentum-values","—");
  const detail=el("p","rm-momentum-detail","Servono osservazioni con data e ora per il confronto.");
  const note=el("p","rm-momentum-meta","");
  card.append(name,verdict,amounts,detail,note);
  cards.append(card);
  results[key]={card,verdict,amounts,detail,note};
 }
 const together=el("p","rm-momentum-joint","Sto verificando le due fonti separatamente.");
 const legend=el("p","rm-momentum-legend",
  "Una variazione di −5 punti LONG implica +5 punti SHORT nella stessa fonte, non necessariamente nuovi contratti short. Myfxbook misura lotti; Capital.com misura posizioni clienti. I due campioni non identificano gli istituzionali. Intervallo scelto sulle rilevazioni realmente disponibili.");
 shell.append(head,controls,cards,together,legend);
 target.insertAdjacentElement("beforebegin",shell);
 const feeds={myfxbook:{current:null,history:[]},capital:{current:null,history:[]}};
 let period="24h",manual=false;
 const fmt=n=>new Intl.NumberFormat("it-IT",{maximumFractionDigits:2}).format(n);
 const signed=n=>(n>0?"+":"")+fmt(n);
 const date=t=>{
  const d=new Date(t);
  return Number.isFinite(+d)?new Intl.DateTimeFormat("it-IT",{
   day:"2-digit",month:"short",hour:"2-digit",minute:"2-digit",timeZone:"Europe/Rome"
  }).format(d):"N/D";
 };
 for(const p of core.PERIODS){
  const button=el("button","",p.id==="7g"?"7 giorni":p.id);
  button.type="button";button.dataset.period=p.id;
  button.setAttribute("aria-pressed",String(p.id===period));
  button.addEventListener("click",()=>{manual=true;period=p.id;draw();});
  controls.append(button);
 }
 function renderCard(key,result){
  const ui=results[key];
  ui.card.dataset.direction=result.available?result.direction:"unknown";
  if(!result.available){
   ui.verdict.textContent="Storico non sufficiente";
   ui.amounts.textContent="Long — · Short —";
   ui.detail.textContent=result.reason+" REMURA non inventa campioni mancanti.";
   ui.note.textContent=feeds[key].current?
    "Ultima rilevazione: "+date(feeds[key].current.t)+".":"Feed non ancora disponibile o non valido.";
   return;
  }
  const a=result;
  ui.verdict.textContent=a.headline;
  ui.amounts.textContent="LONG "+fmt(a.first.lPct)+"% → "+fmt(a.last.lPct)+"% ("+signed(a.deltaLong)+" pp) · "+
   "SHORT "+fmt(a.first.sPct)+"% → "+fmt(a.last.sPct)+"% ("+signed(a.deltaShort)+" pp)";
  const volume=key==="myfxbook"&&a.deltaLongLots!==null&&a.deltaShortLots!==null?
   " · Lotti: long "+signed(a.deltaLongLots)+", short "+signed(a.deltaShortLots)+".":"";
  ui.detail.textContent="Confronto su "+fmt(a.elapsedHours)+" ore effettive, "+a.samples+
   " campioni. Intensità "+a.strength+"."+volume;
  ui.note.textContent="Dal "+date(a.first.t)+" al "+date(a.last.t)+" (ora italiana)."+
   (a.stale?" ATTENZIONE: ultimo campione oltre 3 ore fa, non è una lettura attuale.":"")+
   (a.lowSample?" Campione sotto 30 posizioni: cautela.":"");
 }
 function draw(){
  if(!manual)period=core.recommend(Object.values(feeds));
  badge.textContent=manual?"Intervallo scelto":"Intervallo automatico · "+period;
  for(const b of controls.querySelectorAll("button"))
   b.setAttribute("aria-pressed",String(b.dataset.period===period));
  const a=core.analyze(feeds.myfxbook.history,feeds.myfxbook.current,period);
  const b=core.analyze(feeds.capital.history,feeds.capital.current,period);
  renderCard("myfxbook",a);renderCard("capital",b);
  together.textContent="Lettura combinata: "+core.joint(a,b);
  together.dataset.state=a.available&&b.available&&!a.stale&&!b.stale&&a.direction===b.direction&&a.direction!=="stabile"?"aligned":"normal";
 }
 window.addEventListener("remura:retail",e=>{
  if(e.detail?.symbol!==symbol)return;
  feeds.myfxbook={current:e.detail.current||null,history:e.detail.history||[]};
  draw();
 });
 window.addEventListener("remura:capital",e=>{
  if(e.detail?.symbol!==symbol)return;
  feeds.capital={current:e.detail.current||null,history:e.detail.history||[]};
  draw();
 });
 draw();
})();
