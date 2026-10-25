/* REMURA v1.35 · Read-only VPS diagnostics; never fetches secrets or OHLC. */
(function(root) {
  "use strict";
  const REASONS=Object.freeze({
    cot_missing:"COT mancante (almeno due report comparabili)",
    cot_stale:"COT datato (oltre 14 giorni)",
    cot_nonconsecutive:"COT non consecutivo o non comparabile",
    cot_no_direction:"COT valido, ma variazione non direzionale",
    cot_group_conflict:"COT valido, ma gruppi istituzionali contrapposti",
    prices_missing:"Storico prezzi mancante",
    prices_stale:"Prezzi datati, non utilizzabili come live",
    market_closed:"Prezzi non recenti: mercato chiuso/weekend",
    candles_insufficient:"Candele M15/H1/H4 insufficienti o incomplete",
    timeframe_disagreement:"Timeframe discordanti o candele aggregate incoerenti",
    price_no_direction:"Prezzo valido, ma tendenza non definita",
    price_error:"Integrità prezzi non verificata",
    scan_error:"Errore durante l'analisi (dettagli privati)",
    no_qualifying_setup:"Configurazione non valida per un confronto"
  });
  const OUTCOMES=Object.freeze({
    events_detected:"Nuovi eventi significativi verificati nell'ultima scansione.",
    no_significant_event:"Nessun evento significativo: ci sono mercati effettivamente analizzati.",
    market_closed:"Mercati chiusi nell'ultima scansione: candele non recenti, nessun riferimento live creato. Alla riapertura serviranno nuove candele valide e una direzione COT idonea.",
    data_insufficient:"Dati insufficienti per analizzare tutti i mercati esclusi. Non equivale a nessun segnale.",
    no_qualifying_setup:"Nessuna configurazione direzionale idonea: i dati non sono necessariamente mancanti."
  });
  function count(value){return Number.isSafeInteger(value)&&value>=0?value:null;}
  function itDate(value){
    const n=Date.parse(value);
    return Number.isFinite(n)?new Intl.DateTimeFormat("it-IT",{timeZone:"Europe/Rome",year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit",second:"2-digit"}).format(new Date(n)):"non disponibile";
  }
  function make(tag,css,text){
    const el=document.createElement(tag);
    if(css)el.className=css;
    if(text!==undefined)el.textContent=String(text);
    return el;
  }
  function read(data){
    if(!data||data.schema!=="remura-squalincome-monitor-v1"||!Array.isArray(data.lastEvents))return null;
    if(!Object.prototype.hasOwnProperty.call(data,"diagnostics"))return {kind:"legacy"};
    const d=data.diagnostics;
    if(!d)return {kind:"not_scanned",baselines:count(data.baselines),events:count(data.eventsTotal)};
    const analyzed=count(d.analyzed),excluded=count(d.excluded),tracked=count(d.trackedMarkets);
    if(analyzed===null||excluded===null||tracked===null||analyzed+excluded!==tracked||
       !Array.isArray(d.exclusions)||d.exclusions.length!==excluded||
       !d.lastScanAt||!OUTCOMES[d.outcome])return {kind:"invalid"};
    const summary={kind:"scanned",analyzed,excluded,tracked,date:itDate(d.lastScanAt),
      outcome:d.outcome,newBaselines:count(d.newBaselines),newEvents:count(d.newEvents),
      baselines:count(data.baselines),events:count(data.eventsTotal),
      reasons:[],exclusions:[]};
    const reasons=d.exclusionReasons&&typeof d.exclusionReasons==="object"?d.exclusionReasons:{};
    for(const [code,value] of Object.entries(reasons)){
      const n=count(value);
      if(REASONS[code]&&n!==null&&n>0)summary.reasons.push({code,label:REASONS[code],count:n});
    }
    summary.reasons.sort((a,b)=>b.count-a.count||a.label.localeCompare(b.label));
    for(const row of d.exclusions){
      if(!row||typeof row.symbol!=="string"||!/^[A-Z0-9]{3,8}$/.test(row.symbol)||!Array.isArray(row.reasons))continue;
      summary.exclusions.push({symbol:row.symbol,labels:row.reasons.filter(r=>REASONS[r]).map(r=>REASONS[r])});
    }
    // A source-backed UI interpretation, not a change to the VPS scan.
    // Never disguise missing COT, stale data or errors as a simple weekend.
    const trueDataFaults=new Set(["cot_missing","cot_stale","cot_nonconsecutive",
      "prices_missing","prices_stale","candles_insufficient",
      "timeframe_disagreement","price_error","scan_error"]);
    const hiddenFaults=Object.entries(reasons).some(([code,n])=>
      (!REASONS[code] || trueDataFaults.has(code)) && count(n)>0);
    const solelyClosed=d.outcome==="data_insufficient" && tracked>0 &&
      analyzed===0 && excluded===tracked && summary.exclusions.length===excluded &&
      !hiddenFaults &&
      d.exclusions.every(row=>Array.isArray(row.reasons) &&
        row.reasons.includes("market_closed") &&
        row.reasons.every(reason=>REASONS[reason] && !trueDataFaults.has(reason)));
    summary.displayOutcome=solelyClosed?"market_closed":d.outcome;
    return summary;
  }
  function render(data,host){
    host.replaceChildren();
    const view=read(data);
    if(!view||view.kind==="invalid"){
      host.append(make("p","monitor-warning","Diagnostica non valida o non disponibile: nessun conteggio stimato."));
      return false;
    }
    if(view.kind==="legacy"){
      host.append(make("p","monitor-warning","La VPS usa ancora il backend precedente alla v1.34: la diagnostica delle scansioni non è disponibile. Installazione manuale necessaria."));
      return true;
    }
    if(view.kind==="not_scanned"){
      host.append(make("p","monitor-warning","Nessuna scansione ancora registrata sulla VPS. Il registro storico non dimostra che i mercati siano stati analizzati."));
      return true;
    }
    host.append(make("p","monitor-timestamp","Ultima scansione VPS: "+view.date+" (ora italiana)"));
    const grid=make("div","monitor-metrics");
    const metrics=[
      ["Mercati controllati",view.tracked],["Analizzati (idonei)",view.analyzed],
      ["Esclusi dal confronto",view.excluded],["Riferimenti iniziali",view.baselines],
      ["Eventi registrati",view.events]];
    for(const [name,val] of metrics){
      const box=make("div","monitor-metric");
      box.append(make("small",null,name),make("strong",null,val===null?"—":val));
      grid.append(box);
    }
    host.append(grid);
    host.append(make("p","monitor-caption","Analizzati = COT direzionale e prezzi verificati su timeframe coerenti. Gli esclusi sono stati controllati, ma non hanno superato tutti i criteri."));
    const state=make("p","monitor-outcome",OUTCOMES[view.displayOutcome]);
    state.setAttribute("data-outcome",view.displayOutcome);
    host.append(state);
    host.append(make("p","monitor-caption","Ultima scansione: "+(view.newBaselines??"—")+" nuovi riferimenti · "+(view.newEvents??"—")+" nuovi eventi. I totali del registro sono distinti da questi incrementi."));
    if(view.reasons.length){
      const section=make("div","monitor-reasons");
      section.append(make("h3",null,"Perché alcuni mercati sono esclusi"));
      const ul=make("ul");
      for(const r of view.reasons)ul.append(make("li",null,r.label+": "+r.count));
      section.append(ul,make("p","monitor-caption","Uno stesso mercato può avere più motivi: la somma dei motivi può superare gli esclusi."));
      host.append(section);
    }
    if(view.exclusions.length){
      const details=make("details","monitor-exclusions");
      details.append(make("summary",null,"Mostra i "+view.excluded+" mercati esclusi"));
      const ul=make("ul");
      for(const row of view.exclusions)ul.append(make("li",null,row.symbol+" · "+(row.labels.join("; ")||"Motivo non disponibile")));
      details.append(ul);
      host.append(details);
    }
    return true;
  }
  root.REMURA_SQUAL_DIAGNOSTICS={read,render,REASONS,OUTCOMES};
})(typeof window!=="undefined"?window:globalThis);
