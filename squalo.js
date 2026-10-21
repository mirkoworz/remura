/* Per-pair "Verdetto Squalo": no prediction or financial advice, no background polling. */
(()=>{
 "use strict";
 const core=window.REMURA_SQUALO,layout=document.querySelector(".layout");
 if(!core||!layout||document.getElementById("squalo-verdict"))return;
 const params=new URLSearchParams(location.search);
 const query=(params.get("symbol")||"XAUUSD").toUpperCase();
 const symbol=window.REMURA_MARKETS?.symbols?.includes(query)?query:"XAUUSD";
 const box=document.createElement("section");
 box.id="squalo-verdict";box.className="sq-verdict";
 box.setAttribute("aria-label","Verdetto Squalo per "+symbol);
 box.innerHTML=
 '<header class="sq-top"><div><small>🦈 REMURA · VERDETTO SQUALO</small><h2 id="sq-title">Analisi in preparazione</h2></div>'+
 '<span id="sq-score" class="sq-score">N/D</span></header>'+
 '<p id="sq-summary">Controllo il COT ufficiale, i sentiment e le candele cTrader.</p>'+
 '<div class="sq-bar" role="img" aria-label="Punteggio descrittivo delle evidenze"><i id="sq-fill"></i></div>'+
 '<p class="sq-clarify">Punteggio delle evidenze, <strong>non</strong> probabilità di guadagno né ordini istituzionali in diretta.</p>'+
 '<div class="sq-checks" id="sq-checks" aria-live="polite"></div>'+
 '<details class="sq-explain"><summary>Perché REMURA dà questo verdetto?</summary>'+
 '<ul id="sq-reasons"></ul><p id="sq-age"></p>'+
 '<p>Il COT è settimanale e i cross Forex sono ricostruzioni normalizzate di futures valutari. Il retail è un campione diverso.</p></details>'+
 '<a class="sq-link" href="./squalo.html">Apri Scanner Squalo ↗</a>';
 layout.prepend(box);
 const $=id=>document.getElementById(id);
 let retail=null,retailHistory=[];
 function render(){
   const cot=window.REMURA_INSIGHTS?.getAnalysis?.()||null;
   const price=window.REMURA_PRICE_OBSERVATION?.symbol===symbol?window.REMURA_PRICE_OBSERVATION.result:null;
   const capital=window.REMURA_CAPITAL_OBSERVATION?.symbol===symbol?window.REMURA_CAPITAL_OBSERVATION:null;
   const report=core.evaluate({symbol,cot,price,retail,capital,retailHistory});
   box.dataset.stage=report.stage;
   $("sq-title").textContent=report.title;
   $("sq-summary").textContent=report.summary;
   $("sq-score").textContent=report.score===null?"N/D":report.score+"/100";
   $("sq-fill").style.width=(report.score||0)+"%";
   const holder=$("sq-checks");holder.replaceChildren();
   for(const c of report.checks){
     const row=document.createElement("div");row.className="sq-check";row.dataset.status=c.status;
     const icon=document.createElement("span");
     icon.className="sq-icon";icon.textContent=c.status==="support"?"✓":c.status==="missing"?"·":c.status==="mixed"?"!":"–";
     const body=document.createElement("div");
     const name=document.createElement("strong");name.textContent=c.name;
     const detail=document.createElement("p");detail.textContent=c.detail;
     body.append(name,detail);row.append(icon,body);holder.append(row);
   }
   const items=$("sq-reasons");items.replaceChildren();
   for(const reason of [...report.evidence,...report.risks]){
     const li=document.createElement("li");li.textContent=reason;items.append(li);
   }
   $("sq-age").textContent=report.updatedAt?"Data posizioni COT: "+report.updatedAt:"COT non disponibile.";
 }
 window.addEventListener("remura:retail",e=>{
   if(e.detail?.symbol!==symbol)return;
   retail=e.detail.current?{row:e.detail.current,fresh:e.detail.fresh===true}:null;
   retailHistory=Array.isArray(e.detail.history)?e.detail.history:[];
   render();
 });
 for(const name of ["remura:capital","remura:price","remura:cot"]){
   window.addEventListener(name,e=>{if(e.detail?.symbol===symbol)render();});
 }
 render();
})();
