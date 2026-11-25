/* REMURA v0.9 — presentazione e dati condivisi dalle 35 schede. Nessuna chiamata CFTC duplicata. */
(() => {
  "use strict";
  const core = window.REMURA_INSIGHTS_CORE;
  const market = window.REMURA_MARKETS;
  const node = id => document.getElementById(id);
  const fallback = (new URLSearchParams(location.search).get("symbol") || "XAUUSD").toUpperCase();
  const symbol = market && market.symbols.includes(fallback) ? fallback : "XAUUSD";
  if (!core || !node("alert") || !market) return;
  const section = document.createElement("section");
  section.className = "rm-insights";
  section.id = "rm-insights";
  section.setAttribute("aria-label", "REMURA: lettura e verifica dei movimenti istituzionali");
  section.dataset.state = "loading";
  section.innerHTML = '<div class="rm-head"><div><div class="rm-eyebrow">IN SINTESI · COSA DICE IL COT</div><h2 id="rm-title">Analisi istituzionale in preparazione</h2><p class="rm-desc" id="rm-summary">Verifico lo storico ufficiale CFTC prima di mostrare il contesto.</p></div><span class="rm-pill" id="rm-state">Caricamento</span></div>' +
    '<div class="rm-grid"><div class="rm-stat"><small id="rm-stat1-label">Speculatori</small><strong id="rm-stat1">—</strong><small id="rm-stat1-note">Variazione settimanale del netto/OI</small></div>' +
    '<div class="rm-stat"><small id="rm-stat2-label">Trend 4 settimane</small><strong id="rm-stat2">—</strong><small>Variazione netta, non movimento prezzo</small></div>' +
    '<div class="rm-stat"><small id="rm-stat3-label">Secondo gruppo</small><strong id="rm-stat3">—</strong><small id="rm-stat3-note">Variazione settimanale del netto/OI</small></div></div>' +
    '<div class="rm-note" id="rm-interpretation">Nessuna indicazione operativa finché non vengono verificati i dati.</div>' +
    '<h3>Perché questa lettura?</h3><ul id="rm-reasons"><li>Caricamento del COT…</li></ul>' +
    '<h3>Il contesto Myfxbook</h3><p class="rm-desc" id="rm-retail">Attendo i dati Myfxbook disponibili per lo strumento.</p><div class="rm-note" id="rm-comparison">Il retail non rappresenta l’altra faccia dei contratti istituzionali.</div>' +
    '<div class="rm-next"><b>Cosa controllare sul prezzo</b><span id="rm-next">Il grafico TradingView è consultabile sotto, ma la verifica strutturale H4/H1 richiede ancora candele OHLC accessibili al motore.</span></div>' +
    '<details class="rm-charts"><summary><b>Dettaglio: stanno aumentando i long o gli short?</b></summary>' +
    '<p class="rm-fine">Contratti del future CFTC originale, senza aggregare i lotti Myfxbook. Su un cross Forex scegli una singola valuta: il COT non esiste direttamente per ogni coppia.</p>' +
    '<div class="rm-controls"><label for="rm-leg">Future</label><select id="rm-leg" aria-label="Future/valuta"></select>' +
    '<label for="rm-group">Categoria</label><select id="rm-group" aria-label="Categoria istituzionale"></select>' +
    '<label for="rm-range">Storico</label><select id="rm-range" aria-label="Numero settimane"><option value="13">13 settimane</option><option value="26">26 settimane</option><option value="52" selected>52 settimane</option><option value="156">156 settimane</option><option value="260">260 settimane</option></select></div>' +
    '<p class="rm-trace" id="rm-trace">In attesa di dati sui contratti.</p>' +
    '<div class="rm-chart-panel"><h4>Contratti long · <span id="rm-long-now">—</span></h4><div id="rm-chart-long"></div></div>' +
    '<div class="rm-chart-panel"><h4>Contratti short · <span id="rm-short-now">—</span></h4><div id="rm-chart-short"></div></div>' +
    '<div class="rm-chart-panel"><h4>Open interest del future · <span id="rm-oi-now">—</span></h4><div id="rm-chart-oi"></div></div>' +
    '<p class="rm-fine">I tre grafici hanno scale verticali indipendenti, con gli estremi indicati; non confrontare visivamente le loro altezze. La linea unisce sole osservazioni settimanali verificate.</p></details>' +
    '<ul class="rm-caveats" id="rm-limits"><li>Nessun report COT è in tempo reale.</li></ul>';
  node("alert").insertAdjacentElement("afterend", section);
  let cotSeries = null, settings = null, retail = null, retailRecords = [];
  const empty = value => value === null || value === undefined ? "N/D" : value;
  const txt = (id, value) => {const e=node(id);if (e) e.textContent=String(empty(value));};
  function list(id, values) {
    const host = node(id);host.replaceChildren();
    for (const value of values) {
      const el = document.createElement("li"); el.textContent = value; host.append(el);
    }
  }
  function paint() {
    if (!cotSeries || !settings) return;
    const c = core.analyze(cotSeries, Object.assign({}, settings, {now:Date.now()}));
    section.dataset.state = c.state;
    txt("rm-title", c.title);
    txt("rm-state", c.state === "stale" ? "Dati datati" : c.state === "trend" ? "Trend COT" : c.state === "conflict" ? "Dati discordanti" : c.state === "neutral" ? "Spinta contenuta" : c.state === "missing" ? "Non disponibile" : "Da monitorare");
    txt("rm-summary", c.summary || "Dati non sufficienti.");
    txt("rm-stat1-label", c.specLabel || "Gruppo speculativo");
    txt("rm-stat1", Number.isFinite(c.weekly) ? core.signed(c.weekly) + " pp" : "N/D");
    txt("rm-stat2", Number.isFinite(c.fourWeeks) ? core.signed(c.fourWeeks) + " pp" : "N/D");
    txt("rm-stat3-label", c.secondaryLabel || "Secondo gruppo");
    txt("rm-stat3", Number.isFinite(c.secondaryWeekly) ? core.signed(c.secondaryWeekly) + " pp" : "N/D");
    const retailInfo = core.retailContext(retail, retailRecords);
    txt("rm-retail", retailInfo.text);
    txt("rm-comparison", core.combine(c, retailInfo));
    txt("rm-interpretation", c.state === "stale" ? "Nessun bias operativo: il COT è datato." :
      (c.side || "Nessun bias COT") + ". " + (c.conflict ? "Le categorie non sono allineate. " : "") +
      "È una lettura delle posizioni, non un segnale BUY/SELL né una previsione di prezzo.");
    txt("rm-next", c.next || "Attendere report aggiornati e verificare la struttura del prezzo.");
    list("rm-reasons", c.reasons || []);
    list("rm-limits", c.caveats || []);
    rebuildSelectors();
    drawContracts();
  }
  function rebuildSelectors() {
    if (!cotSeries || !settings) return;
    const all = core.legsFor(cotSeries, settings);
    const legs = node("rm-leg"), selectedLeg = legs.value;
    legs.replaceChildren();
    for (const entry of all) {
      const opt = document.createElement("option");opt.value=entry.name;
      opt.textContent=settings.isFX ? entry.name + " futures / USD" : entry.name + " · future";
      legs.append(opt);
    }
    if (all.some(x=>x.name===selectedLeg)) legs.value=selectedLeg;
    const groups = node("rm-group"), selectedGroup=groups.value;
    groups.replaceChildren();
    for (let i=0;i<2;i++) {
      const opt = document.createElement("option");opt.value=i===0?"a":"b";opt.textContent=settings.labels[i];groups.append(opt);
    }
    groups.value = (selectedGroup==="a" || selectedGroup==="b") ? selectedGroup : (settings.isMetal ? "a" : "b");
  }
  function simpleChart(entries, key, stroke) {
    const values=entries.map(row=>Number(row.data && row.data[key]));
    if (values.length < 2 || values.some(v=>!Number.isFinite(v) || v<0)) return null;
    const W=730,H=136,L=72,R=16,T=14,B=29;
    let min=Math.min(...values),max=Math.max(...values);
    const span=max-min,pad=Math.max(span*.18,max*.01,1);
    min=Math.max(0,min-pad);max+=pad;
    const X=i=>L+(W-L-R)*i/Math.max(1,entries.length-1);
    const Y=v=>T+(max-v)/(max-min)*(H-T-B);
    const path=values.map((v,i)=>(i?"L":"M")+X(i).toFixed(1)+","+Y(v).toFixed(1)).join(" ");
    const first=entries[0].date,last=entries[entries.length-1].date;
    const f = n => new Intl.NumberFormat("it-IT", {maximumFractionDigits:0}).format(Math.round(n));
    return '<svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="Storico settimanale '+key+' CFTC, dal '+first+' al '+last+'">' +
      '<line x1="'+L+'" x2="'+(W-R)+'" y1="'+T+'" y2="'+T+'" stroke="#3b5c63" stroke-dasharray="3 5"/>' +
      '<line x1="'+L+'" x2="'+(W-R)+'" y1="'+(H-B)+'" y2="'+(H-B)+'" stroke="#3b5c63" stroke-dasharray="3 5"/>' +
      '<text x="'+(L-8)+'" y="'+(T+4)+'" fill="#adc6ca" text-anchor="end" font-size="11">'+f(max)+'</text>' +
      '<text x="'+(L-8)+'" y="'+(H-B+3)+'" fill="#adc6ca" text-anchor="end" font-size="11">'+f(min)+'</text>' +
      '<path d="'+path+'" fill="none" stroke="'+stroke+'" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/>' +
      '<circle cx="'+X(values.length-1)+'" cy="'+Y(values[values.length-1])+'" r="4" fill="'+stroke+'"/>' +
      '<text x="'+L+'" y="'+(H-6)+'" fill="#9ebdc2" font-size="11">'+first+'</text>' +
      '<text x="'+(W-R)+'" y="'+(H-6)+'" fill="#9ebdc2" font-size="11" text-anchor="end">'+last+'</text></svg>';
  }
  function drawContracts() {
    if (!cotSeries || !settings) return;
    const legs=core.legsFor(cotSeries, settings);
    const selected=legs.find(x=>x.name===node("rm-leg").value) || legs[0];
    if (!selected || !selected.rows.length) {
      txt("rm-trace", "Nessun contratto verificato per questo future.");
      for(const id of ["rm-chart-long","rm-chart-short","rm-chart-oi"])node(id).replaceChildren();
      return;
    }
    const group=node("rm-group").value || (settings.isMetal?"a":"b");
    const limit=Number(node("rm-range").value) || 52;
    const rows=selected.rows.slice(-limit);
    const last=rows[rows.length-1].data,prev=rows.length>1?rows[rows.length-2].data:null;
    const groupRecords=rows.map(x=>({date:x.date,data:{
      long:x.data[group].long,short:x.data[group].short,oi:x.data.oi
    }}));
    const groupName = settings.labels[group==="a"?0:1];
    const fmt0=x=>Number.isFinite(x)?Math.round(x).toLocaleString("it-IT"):"N/D";
    const delta=(a,b)=>Number.isFinite(a)&&Number.isFinite(b)?core.signed(a-b,0):"N/D";
    txt("rm-long-now",fmt0(last[group].long));
    txt("rm-short-now",fmt0(last[group].short));
    txt("rm-oi-now",fmt0(last.oi));
    txt("rm-trace",selected.name+" · "+groupName+". Long: "+fmt0(last[group].long)+(prev?" ("+delta(last[group].long,prev[group].long)+" contratti rispetto al report precedente)":"")+
      ". Short: "+fmt0(last[group].short)+(prev?" ("+delta(last[group].short,prev[group].short)+" contratti)":"")+
      ". Open interest del future: "+fmt0(last.oi)+(prev?" ("+delta(last.oi,prev.oi)+" contratti)":"")+
      ". La variazione netta può dipendere da aperture E chiusure di posizioni.");
    for (const [key,id,color] of [["long","rm-chart-long","#74e2ad"],["short","rm-chart-short","#fa899a"],["oi","rm-chart-oi","#8db6ff"]]) {
      const svg=simpleChart(groupRecords,key,color);
      if (svg) node(id).innerHTML=svg; else txt(id,"Servono almeno due report verificati.");
    }
  }
  for (const id of ["rm-leg","rm-group","rm-range"])node(id).addEventListener("change",drawContracts);
  window.REMURA_INSIGHTS = {
    updateCOT(input) {
      if (!input || input.symbol!==symbol) return;
      cotSeries=input.series;settings={symbol, isFX:!!input.isFX,isMetal:!!input.isMetal,labels:input.labels};
      paint();
      window.dispatchEvent(new CustomEvent("remura:cot",{detail:{symbol}}));
    },
    getAnalysis() {
      return cotSeries&&settings ? core.analyze(cotSeries,Object.assign({},settings,{now:Date.now()})) : null;
    },
    getRetail() {
      return core.retailContext(retail,retailRecords);
    },
    error(message) {
      section.dataset.state="missing";
      txt("rm-title","COT non disponibile: impossibile interpretare");
      txt("rm-state","N/D");
      txt("rm-summary","Errore nella lettura del dataset CFTC ufficiale. Non viene generata nessuna direzione.");
      txt("rm-interpretation",String(message || "Riprova l'aggiornamento COT."));
      txt("rm-retail",core.retailContext(retail,retailRecords).text);
      txt("rm-comparison","Il sentiment retail da solo non è sufficiente per attribuire movimenti agli istituzionali.");
      txt("rm-next","Attendere la disponibilità di report COT verificabili.");
      list("rm-reasons",["Nessuna previsione o posizione simulata."]);
      list("rm-limits",["Senza COT completo, l'analisi del posizionamento non è disponibile."]);
      cotSeries=null;settings=null;
      window.dispatchEvent(new CustomEvent("remura:cot",{detail:{symbol}}));
    }
  };
  window.addEventListener("remura:retail",e=>{
    if (!e.detail || e.detail.symbol!==symbol) return;
    retail=e.detail.current || null;
    retailRecords=Array.isArray(e.detail.history)?e.detail.history:[];
    if(cotSeries)paint();
    else txt("rm-retail",core.retailContext(retail,retailRecords).text);
  });
})();