/* REMURA v1.0 — private automatic OHLC feed with optional local file fallback. */
(() => {
  "use strict";
  const core=window.REMURA_PRICE_CORE, cfg=window.REMURA_MARKETS;
  const sym=(new URLSearchParams(location.search).get("symbol")||"XAUUSD").toUpperCase();
  const symbol=cfg && cfg.symbols.includes(sym)?sym:"XAUUSD";
  const host=document.getElementById("retail-module");
  if(!core||!host)return;
  const el=document.createElement("section");
  el.id="remura-price-engine";
  el.className="rm-price";
  el.setAttribute("aria-label","Analisi del prezzo in modalità personale");
  el.dataset.status="unavailable";
  el.innerHTML=
    '<div class="rp-top"><div><span class="rp-eyebrow">REMURA · Motore prezzi privato</span>'+
    '<h2 id="rp-title">Analisi del prezzo in attesa</h2>'+
    '<p class="rp-muted">Candele chiuse M15 → H1 → H4. Il servizio REMURA privato aggiorna i prezzi automaticamente ogni 15 minuti, quando è configurato.</p></div><span class="rp-flag" id="rp-state">Nessun feed caricato</span></div>'+
    '<p class="rp-muted" id="rp-auto">Controllo del servizio prezzi privato…</p><div class="rp-upload"><label for="rp-file">In alternativa, importa un file locale (.json)</label>'+
    '<input id="rp-file" type="file" accept=".json,application/json" aria-describedby="rp-file-hint"/>'+
    '<p id="rp-file-hint" class="rp-muted">Usalo solo se vuoi confrontare uno storico offline. Il file resta nel browser e non viene caricato sul server.</p><button type="button" class="rp-return" id="rp-return">Riprendi aggiornamento automatico</button></div>'+
    '<div class="rp-inline"><span id="rp-provider">Fonte: N/D</span><span id="rp-last">Ultima candela: N/D</span></div>'+
    '<div class="rp-grid">'+
    '<div class="rp-box"><h4>H4 · Struttura</h4><strong id="rp-h4">N/D</strong><p id="rp-h4-extra">In attesa del feed.</p><small id="rp-h4-age"></small></div>'+
    '<div class="rp-box"><h4>H1 · Conferma</h4><strong id="rp-h1">N/D</strong><p id="rp-h1-extra">In attesa del feed.</p><small id="rp-h1-age"></small></div>'+
    '<div class="rp-box"><h4>M15 · Timing</h4><strong id="rp-m15">N/D</strong><p id="rp-m15-extra">In attesa del feed.</p><small id="rp-m15-age"></small></div>'+
    '</div><div id="rp-narrative" class="rp-result">REMURA non interpreta il prezzo finché non vengono caricate candele verificabili.</div>'+
    '<h3>Prezzo + COT + Retail</h3><div id="rp-compare" class="rp-compare">Servono prima candele M15/H1/H4 e un report COT valido. Il retail è un elemento aggiuntivo, non un ordine.</div>'+
    '<details><summary>Come produrre il file privato per REMURA</summary>'+
    '<p class="rp-muted">Sul tuo computer scarica i prezzi tramite il comando Python locale descritto in <code>PRICE-ENGINE.md</code>: supporta Twelve Data, OANDA v20 e CSV M15 di broker. Esporta il file <code>local/price-snapshot.json</code>, trasferiscilo su iPhone se necessario e selezionalo qui. Se un mercato non è disponibile dal fornitore, REMURA indica N/D.</p>'+
    '<p class="rp-muted">Attenzione: il sito GitHub Pages esistente resta pubblico. Il tuo file locale non viene caricato o pubblicato da questo pannello; l’uso personale di una fonte non rende privato il sito.</p></details>';
  host.insertAdjacentElement("beforebegin",el);
  const get = id => document.getElementById(id);
  const set=(id,v)=>{get(id).textContent=String(v)};
  const sideName=n=>n>0?"Rialzista":n<0?"Ribassista":"Neutrale";
  let priceResult=null, manualSelected=false, fetching=false;
  function combined(){
    const insights=window.REMURA_INSIGHTS;
    const cot=insights && typeof insights.getAnalysis==="function"?insights.getAnalysis():null;
    const retail=insights && typeof insights.getRetail==="function"?insights.getRetail():null;
    set("rp-compare",core.cross(priceResult,cot,retail).text);
  }
  function render(result, market) {
    priceResult=result;
    el.dataset.status=result.state;
    set("rp-title",result.title);
    set("rp-state",result.state==="confirmed"?"Struttura coerente":result.state==="unavailable"?"Dati insufficienti":result.state==="conflict"?"Segnali discordanti":"In osservazione");
    set("rp-provider","Fonte: "+market.provider+" · "+market.providerSymbol+" · UTC");
    const last=market.frames.M15[market.frames.M15.length-1];
    set("rp-last","Ultima M15 chiusa: "+(last&&Number.isFinite(Date.parse(last.t))?new Date(Date.parse(last.t)+900000).toLocaleString("it-IT",{timeZone:"Europe/Rome"}):"N/D"));
    for(const [tf,k] of [["H4","h4"],["H1","h1"],["M15","m15"]]){
      const m=result.metrics[tf];
      if(!m||m.state!=="ok"){
        set("rp-"+k,m&&m.state==="stale"?"Dati datati":"N/D");
        set("rp-"+k+"-extra",m?.text||"Intervallo mancante.");
        set("rp-"+k+"-age",m?m.count+" candele · "+m.state:"");
        continue;
      }
      set("rp-"+k,sideName(m.trend));
      set("rp-"+k+"-extra",m.text);
      set("rp-"+k+"-age","Close "+core.format(m.close)+" · S/R "+core.format(m.support)+" / "+core.format(m.resistance)+
        " · "+m.count+" candele");
    }
    set("rp-narrative",result.explanation+" "+
      (result.caveats||[]).join(" "));
    combined();
    window.dispatchEvent(new CustomEvent("remura:price",{detail:{symbol}}));
  }
  get("rp-file").addEventListener("change",async()=>{
    manualSelected=true;
    set("rp-auto","Modalità manuale: file locale selezionato, aggiornamenti automatici sospesi.");
    const file=get("rp-file").files?.[0];
    if(!file)return;
    try{
      if(file.size>12000000)throw Error("Il file supera il limite di 12 MB. Riduci --count o il numero di mercati.");
      const text=await file.text();
      const obj=JSON.parse(text);
      const market=core.load(obj,symbol);
      const result=core.analyze(market);
      render(result,market);
    }catch(e){
      priceResult=null;el.dataset.status="unavailable";
      set("rp-title","Dati prezzi non utilizzabili");
      set("rp-state","Importazione non valida");
      set("rp-narrative",String(e.message||"File non valido"));
      set("rp-provider","Fonte: N/D");set("rp-last","Ultima candela: N/D");
      for(const k of ["h4","h1","m15"]){set("rp-"+k,"N/D");set("rp-"+k+"-extra","File da verificare.");set("rp-"+k+"-age","");}
      combined();
    }
  });
  async function autoRefresh(){
    if(manualSelected||fetching||document.visibilityState==="hidden")return;
    fetching=true;
    try {
      const controller=new AbortController();
      const timeout=setTimeout(()=>controller.abort(),15000);
      let response;
      try {
        response=await fetch("./private-api/prices/"+encodeURIComponent(symbol),
          {cache:"no-store",headers:{"Accept":"application/json"},signal:controller.signal});
      } finally {clearTimeout(timeout);}
      if(manualSelected)return;
      if(!response.ok){
        if(!priceResult){
          set("rp-auto",response.status===503?
            "Collettore non ancora disponibile: in attesa della connessione cTrader.":
            "Feed privato non disponibile su questo indirizzo: avvia REMURA sul server protetto.");
        }
        return;
      }
      const obj=await response.json();
      if(manualSelected)return;
      const market=core.load(obj,symbol);
      const result=core.analyze(market);
      render(result,market);
      const d=new Date().toLocaleString("it-IT",{timeZone:"Europe/Rome",day:"2-digit",month:"2-digit",hour:"2-digit",minute:"2-digit"});
      set("rp-auto","Automatico · ultimo controllo "+d+" · aggiornamenti server previsti ogni 15 minuti.");
    }catch(e){
      if(!priceResult&&!manualSelected)set("rp-auto","Feed automatico in attesa. Nessuna candela simulata.");
    }finally{fetching=false;}
  }
  get("rp-return").addEventListener("click",()=>{
    manualSelected=false;
    get("rp-file").value="";
    set("rp-auto","Ricollegamento al feed privato…");
    autoRefresh();
  });
  window.addEventListener("visibilitychange",()=>{if(document.visibilityState==="visible")autoRefresh();});
  window.setInterval(autoRefresh,5*60*1000);
  autoRefresh();
  window.addEventListener("remura:cot",combined);
  window.addEventListener("remura:retail",combined);
})();
