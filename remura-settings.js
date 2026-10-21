/* All data-connection inputs live in one settings surface from the hamburger menu. */
(()=>{
 "use strict";
 const retail=document.getElementById("retail-module"),capital=document.getElementById("remura-capital");
 if(!retail||!capital||document.getElementById("remura-settings"))return;
 const panel=document.createElement("dialog");
 panel.id="remura-settings";
 panel.setAttribute("aria-label","Impostazioni e connessioni REMURA");
 panel.innerHTML='<div class="rs-head"><div><small>⚙ REMURA</small><h2>Impostazioni</h2></div>'+
   '<button type="button" id="rs-close" aria-label="Chiudi impostazioni">×</button></div>'+
   '<p class="rs-intro">Gestisci le fonti, le importazioni private e le opzioni avanzate. Le analisi quotidiane restano nelle schede.</p>'+
   '<section class="rs-info"><strong>Myfxbook · automatico</strong><p>Il sentiment viene raccolto dal VPS privato. Email e password non si cambiano dal sito: restano protette sul server.</p></section>'+
   '<section class="rs-capital"><strong>Capital.com · accesso privato</strong></section>'+
   '<section class="rs-prices"><strong>Prezzo cTrader · file locale opzionale</strong></section>'+
   '<section class="rs-info"><strong>Notifiche Squalo</strong><p>In preparazione: verranno attivate soltanto dopo test dello scanner e autorizzazione esplicita su iPhone. Non sono ancora abilitate.</p></section>';
 const source=panel.querySelector(".rs-capital");
 const capitalBox=document.createElement("div");capitalBox.className="rem-sources";
 const importBox=capital.querySelector(".ms-import");
 if(importBox){importBox.open=false;capitalBox.append(importBox);}
 source.append(capitalBox);
 const prices=panel.querySelector(".rs-prices");
 const priceBox=document.createElement("div");priceBox.className="rm-price";
 const upload=document.getElementById("remura-price-engine")?.querySelector(".rp-upload");
 if(upload)priceBox.append(upload);
 prices.append(priceBox);
 document.body.append(panel);
 const close=()=>{
   if(panel.open)panel.close();
   if(location.hash==="#remura-settings")history.replaceState(null,"",location.pathname+location.search);
 };
 const open=()=>{
   if(location.hash==="#remura-settings"&&!panel.open)panel.showModal();
 };
 document.getElementById("rs-close").addEventListener("click",close);
 panel.addEventListener("click",event=>{if(event.target===panel)close();});
 panel.addEventListener("close",()=>{
   if(location.hash==="#remura-settings")history.replaceState(null,"",location.pathname+location.search);
 });
 window.addEventListener("hashchange",open);
 open();
})();
