/* REMURA quick glance: read existing validated displays; do not infer institutional trades. */
(() => {
  "use strict";
  const params=new URLSearchParams(window.location.search);
  const conf=window.REMURA_MARKETS;
  const requested=(params.get("symbol")||"XAUUSD").toUpperCase();
  const symbol=conf?.symbols?.includes(requested)?requested:"XAUUSD";
  const alert=document.getElementById("alert");
  if(!alert || document.getElementById("remura-quicklook"))return;

  const section=document.createElement("section");
  section.id="remura-quicklook";
  section.className="rq";
  section.setAttribute("aria-label","REMURA: quadro rapido del mercato");
  section.innerHTML=`
    <div class="rq-head">
      <div><span class="rq-eyebrow">REMURA · QUADRO RAPIDO</span>
        <h2>Tre prospettive su <span id="rq-symbol"></span></h2>
        <p>Posizioni COT settimanali, sentiment retail e struttura del prezzo: dati diversi, senza attribuire al retail operazioni istituzionali.</p>
      </div>
      <span class="rq-note">Dati verificati · non segnali di ingresso</span>
    </div>
    <div class="rq-grid">
      <article class="rq-card" aria-label="Posizionamento istituzionale">
        <h3>COT · Istituzionali</h3>
        <strong id="rq-cot-main">In attesa del report</strong>
        <p id="rq-cot-details">Report CFTC settimanale, non in tempo reale.</p>
        <a href="#rm-insights">Analisi COT ↓</a>
      </article>
      <article class="rq-card" aria-label="Sentiment Myfxbook">
        <h3>Myfxbook · Retail</h3>
        <strong id="rq-retail-main">In attesa della rilevazione</strong>
        <p id="rq-retail-details">Percentuali sul volume dei lotti, non numero di trader.</p>
        <a href="#retail-module">Sentiment e bande ↓</a>
      </article>
      <article class="rq-card rq-price" aria-label="Struttura del prezzo">
        <h3>Prezzo · cTrader</h3>
        <strong id="rq-price-main">In attesa dei prezzi</strong>
        <p id="rq-price-details">Timeframe H4, H1 e M15 da candele chiuse.</p>
        <a href="#remura-price-engine">Analisi prezzo ↓</a>
      </article>
    </div>
    <nav class="rq-links" aria-label="Vai alle sezioni della scheda">
      <a href="#rm-insights">COT dettagliato</a>
      <a href="#remura-price-engine">Prezzi</a>
      <a href="#retail-module">Myfxbook</a>
      <a href="#remura-multisource">Altre fonti</a>
      <a href="#chart">Storico istituzionale</a>
    </nav>
    <p class="rq-disclaimer">Le divergenze sono indizi da analizzare, non la prova che gli istituzionali siano sul lato opposto del retail.</p>`;
  alert.insertAdjacentElement("afterend",section);

  const get=id=>document.getElementById(id)?.textContent?.trim()||"";
  const put=(id,value)=>{const node=document.getElementById(id);if(node)node.textContent=value;};
  put("rq-symbol",symbol);

  function refreshCot(){
    const status=get("rm-state"),title=get("rm-title");
    if(status && !/caricamento|in attesa/i.test(status)){
      put("rq-cot-main",status);
      put("rq-cot-details",title && !/preparazione/i.test(title)?title+" · COT settimanale.":"Report CFTC settimanale: verifica la data prima di interpretare.");
    }else{
      put("rq-cot-main","In attesa del report");
    }
  }
  function refreshRetail(){
    const status=get("r-status");
    const l=get("r-lp"),s=get("r-sp"),recorded=get("r-updated");
    const valid=x=>/^\d+(?:[.,]\d+)?%$/.test(x);
    if(valid(l)&&valid(s)&&!/non collegato|da attivare|sentiment n\/d/i.test(status)){
      put("rq-retail-main",l+" long · "+s+" short");
      put("rq-retail-details",(status||"Myfxbook")+(recorded && recorded!=="Non collegato"?" · "+recorded:"")+
        " · Quote lotti, non posizioni istituzionali.");
    }else{
      put("rq-retail-main","Sentiment N/D");
      put("rq-retail-details",status||"Attendo una rilevazione Myfxbook verificata.");
    }
  }
  function refreshPrice(){
    const names=["rp-h4","rp-h1","rp-m15"].map(get);
    const state=get("rp-state"),last=get("rp-last");
    if(names.every(n=>n && n!=="N/D" && n!=="—" && n!=="In attesa")){
      put("rq-price-main","H4 "+names[0]+" · H1 "+names[1]+" · M15 "+names[2]);
      put("rq-price-details",(state||"Struttura in osservazione")+
          (last&&!/N\/D/.test(last)?" · "+last:""));
    }else{
      put("rq-price-main","Prezzo in attesa");
      put("rq-price-details",state||"Servono M15, H1 e H4 verificati.");
    }
  }
  const refresh=()=>{refreshCot();refreshRetail();refreshPrice();};
  for(const name of ["remura:cot","remura:retail","remura:price"]){
    window.addEventListener(name,event=>{
      if(event.detail?.symbol!==symbol)return;
      // All source widgets own their DOM. Refresh after their updates finish.
      window.setTimeout(refresh,0);
    });
  }
  refresh();
})();
