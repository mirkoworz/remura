/* REMURA v1.39 · Mobile-contained, source-backed VPS evolution radar. */
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
    timeframe_disagreement:"Timeframe discordanti (storico v1.35, motivo non distinto)",
    ohlc_mismatch:"Errore verificato: candele H1/H4 non coerenti con M15",
    trend_disagreement:"Tendenze H1 e H4 opposte (candele corrette)",
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
      updatedObservations:count(d.updatedObservations),
      reasons:[],exclusions:[],markets:[],observations:[],
      history:[],historyTotal:count(data.historyTotal)};
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
    // New per-market data is optional until the VPS manually receives v1.36.
    // Do not infer current timestamps from the device clock or invent snapshots.
    if(Array.isArray(d.markets)){
      if(d.markets.length!==tracked)return {kind:"invalid"};
      const seen=new Set();
      for(const market of d.markets){
        if(!market || typeof market.symbol!=="string" ||
           !/^[A-Z0-9]{3,8}$/.test(market.symbol) ||
           typeof market.analyzed!=="boolean" || seen.has(market.symbol))return {kind:"invalid"};
        seen.add(market.symbol);
        const frames={};
        for(const key of ["M15","H1","H4"]){
          const row=market.timeframes?.[key];
          const bars=count(row?.bars),age=row?.ageMinutes;
          const validAge=Number.isSafeInteger(age)&&Math.abs(age)<=10000000;
          const date=typeof row?.lastClosedAt==="string" && Number.isFinite(Date.parse(row.lastClosedAt))?
            row.lastClosedAt:null;
          frames[key]={bars:bars??null,ageMinutes:validAge?age:null,lastClosedAt:date};
        }
        summary.markets.push({symbol:market.symbol,analyzed:market.analyzed,frames,
          reasons:summary.exclusions.find(row=>row.symbol===market.symbol)?.labels||[]});
      }
      summary.markets.sort((a,b)=>a.symbol.localeCompare(b.symbol));
    }
    if(Array.isArray(data.observations)){
      for(const row of data.observations){
        if(!row||typeof row.symbol!=="string"||!/^[A-Z0-9]{3,8}$/.test(row.symbol))continue;
        if(!["aligned","divergent"].includes(row.state) ||
           !["confirmed","partial","watch"].includes(row.priceState))continue;
        summary.observations.push({
          symbol:row.symbol,state:row.state,priceState:row.priceState,
          priceTime:typeof row.priceTime==="string"?row.priceTime:null,
          observedAt:typeof row.observedAt==="string"?row.observedAt:null,
          reportDate:typeof row.reportDate==="string"?row.reportDate:null
        });
      }
    }
    // Strict allowlist: never render free-form source text or private provider payload.
    if(Array.isArray(data.history)){
      for(const row of data.history){
        if(!row||typeof row.symbol!=="string"||
           !/^[A-Z0-9]{3,8}$/.test(row.symbol)||
           !["aligned","divergent"].includes(row.state)||
           !["watch","partial","confirmed"].includes(row.priceState)||
           !["baseline","update","first_after_upgrade"].includes(row.origin)||
           ![-1,1].includes(row.cotSide)||![-1,1].includes(row.priceSide)||
           !["string"].includes(typeof row.observedAt)||
           !Number.isFinite(Date.parse(row.observedAt))||
           !Number.isFinite(Date.parse(row.priceTime))||
           !/^\d{4}-\d{2}-\d{2}$/.test(row.reportDate))continue;
        const dir=v=>[-1,0,1].includes(v)?v:null;
        const delta=typeof row.cotWeekly==="number"&&
          Number.isFinite(row.cotWeekly)&&Math.abs(row.cotWeekly)<=200?row.cotWeekly:null;
        const event=["new_convergence","new_divergence","confirmation_strengthened"].includes(row.eventType)?
          row.eventType:null;
        summary.history.push({symbol:row.symbol,state:row.state,priceState:row.priceState,
          cotSide:row.cotSide,priceSide:row.priceSide,
          h4Side:dir(row.h4Side),h1Side:dir(row.h1Side),m15Side:dir(row.m15Side),
          reportDate:row.reportDate,priceTime:row.priceTime,observedAt:row.observedAt,
          cotWeekly:delta,cotSustained:row.cotSustained===1,
          origin:row.origin,eventType:event});
      }
    }
    // A source-backed UI interpretation, not a change to the VPS scan.
    // Never disguise missing COT, stale data or errors as a simple weekend.
    const trueDataFaults=new Set(["cot_missing","cot_stale","cot_nonconsecutive",
      "prices_missing","prices_stale","candles_insufficient",
      "timeframe_disagreement","ohlc_mismatch","trend_disagreement","price_error","scan_error"]);
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

  const DIRECTION=Object.freeze({1:"↑ Rialzista","-1":"↓ Ribassista",0:"→ Neutrale"});
  const PRICE_LEVEL=Object.freeze({watch:"osservazione",partial:"parziale",confirmed:"conferma tecnica"});
  const EVENT_LABELS=Object.freeze({
    new_convergence:"nuova convergenza verificata",
    new_divergence:"nuova divergenza verificata",
    confirmation_strengthened:"rafforzamento verificato"
  });
  function shortDate(value){
    const t=Date.parse(value);
    return Number.isFinite(t)?new Intl.DateTimeFormat("it-IT",
      {timeZone:"Europe/Rome",day:"2-digit",month:"2-digit",hour:"2-digit",minute:"2-digit"}).format(new Date(t)):"N/D";
  }

  function stampParts(value){
    const t=Date.parse(value);
    if(!Number.isFinite(t))return {date:"N/D",time:"—"};
    const local=new Date(t);
    return {
      date:new Intl.DateTimeFormat("it-IT",{timeZone:"Europe/Rome",day:"2-digit",month:"2-digit"}).format(local),
      time:new Intl.DateTimeFormat("it-IT",{timeZone:"Europe/Rome",hour:"2-digit",minute:"2-digit"}).format(local)
    };
  }
  // Group only server-backed observations. Do not interpolate missing intervals,
  // calculate a predictive score or turn technical confirmations into events.
  function evolutionModel(history){
    const bySymbol=new Map();
    if(!Array.isArray(history))return [];
    for(const point of history){
      if(!point||typeof point.symbol!=="string"||!/^[A-Z0-9]{3,8}$/.test(point.symbol)||
         !Number.isFinite(Date.parse(point.observedAt)))continue;
      if(!bySymbol.has(point.symbol))bySymbol.set(point.symbol,[]);
      bySymbol.get(point.symbol).push(point);
    }
    return [...bySymbol].map(([symbol,rows])=>{
      const points=rows.slice().sort((a,b)=>Date.parse(a.observedAt)-Date.parse(b.observedAt)||
        Date.parse(a.priceTime)-Date.parse(b.priceTime));
      const last=points[points.length-1];
      const changes=[];
      for(let i=1;i<points.length;i++){
        const previous=points[i-1],current=points[i],labels=[];
        if(previous.state!==current.state)labels.push(
          previous.state==="divergent"?"divergenza → concordanza":"concordanza → divergenza");
        if(previous.priceState!==current.priceState)
          labels.push("conferma tecnica "+PRICE_LEVEL[previous.priceState]+" → "+PRICE_LEVEL[current.priceState]);
        for(const [key,label] of [["h4Side","H4"],["h1Side","H1"],["m15Side","M15"]]){
          if(previous[key]!==current[key])labels.push(label+" "+(DIRECTION[previous[key]]||"N/D")+
            " → "+(DIRECTION[current[key]]||"N/D"));
        }
        if(previous.reportDate!==current.reportDate || previous.cotSide!==current.cotSide)
          labels.push("nuova osservazione COT o nuovo report");
        // The backend alone decides whether a change meets event criteria.
        if(current.eventType&&EVENT_LABELS[current.eventType])
          labels.push("EVENTO verificato: "+EVENT_LABELS[current.eventType]);
        if(labels.length)changes.push({at:current.observedAt,labels,
          verified:!!(current.eventType&&EVENT_LABELS[current.eventType])});
      }
      const verifiedEvents=points.filter(x=>x.eventType&&EVENT_LABELS[x.eventType]).length;
      let divergentSamples=0;
      for(let i=points.length-1;i>=0&&points[i].state==="divergent";i--)divergentSamples++;
      return {symbol,points,last,changes,verifiedEvents,divergentSamples};
    }).sort((a,b)=>a.symbol.localeCompare(b.symbol));
  }
  function trendCell(value){
    return value===1?{label:"↑",state:"up"}:
      value===-1?{label:"↓",state:"down"}:
      value===0?{label:"→",state:"flat"}:{label:"—",state:"missing"};
  }
  function makeRadarCard(model){
    const item=make("article","radar-evolution-card");
    const last=model.last,top=make("div","radar-evolution-top");
    const name=make("strong","radar-evolution-name",model.symbol);
    const state=make("span","radar-state",last.state==="aligned"?"Δ COT/prezzo concordi":"Δ COT/prezzo divergenti");
    state.setAttribute("data-state",last.state);
    top.append(name,state);
    item.append(top);
    item.append(make("p","monitor-caption",
      "Δ COT settimanale "+(DIRECTION[last.cotSide]||"N/D")+
      " · "+(last.cotWeekly===null?"entità N/D":last.cotWeekly.toFixed(2)+" pp")+
      " · Prezzo "+(DIRECTION[last.priceSide]||"N/D")+
      " · stato tecnico: "+PRICE_LEVEL[last.priceState]));
    item.append(make("p","monitor-caption",
      "COT: "+last.reportDate+" · Ultima osservazione: "+itDate(last.observedAt)+
      " · "+model.points.length+" campioni visualizzati"+
      (model.verifiedEvents?" · "+model.verifiedEvents+" eventi COT/prezzo qualificati nei campioni visibili":
       " · nessun evento COT/prezzo qualificato nei campioni visibili")));
    const chart=make("details","radar-chart-details");
    chart.append(make("summary",null,"Confronto nel tempo · Δ COT, H4, H1, M15"));
    const note=make("p","monitor-caption radar-chart-note",
      "Scorri lateralmente la matrice. Ogni colonna = un campione salvato, "+
      "non una candela consecutiva. Δ COT è settimanale e può ripetersi.");
    chart.append(note);
    const scroll=make("div","radar-matrix-scroll");
    scroll.tabIndex=0;
    scroll.setAttribute("role","region");
    scroll.setAttribute("aria-label","Tabella scorrevole delle osservazioni "+model.symbol);
    const matrix=make("div","radar-matrix");
    matrix.setAttribute("role","table");
    matrix.setAttribute("aria-label","Cronologia direzionale "+model.symbol);
    const points=model.points;
    matrix.style.gridTemplateColumns="76px repeat("+points.length+",72px)";
    function row(label,values){
      const head=make("span","radar-axis-label",label);
      head.setAttribute("role","rowheader");
      matrix.append(head);
      for(let i=0;i<points.length;i++){
        const v=values[i];
        const el=make("span","radar-matrix-cell",v.stamp?"":v.label);
        if(v.stamp){
          const parts=stampParts(points[i].observedAt);
          el.append(make("span","radar-stamp-date",parts.date),
                    make("span","radar-stamp-hour",parts.time));
        }
        el.setAttribute("role","cell");
        el.setAttribute("data-side",v.state);
        el.setAttribute("title",itDate(points[i].observedAt)+" · "+label+": "+v.description);
        el.setAttribute("aria-label",label+" "+v.description+" il "+itDate(points[i].observedAt));
        matrix.append(el);
      }
    }
    row("Data / ora",points.map(x=>({label:shortDate(x.observedAt),state:"stamp",
      stamp:true,description:itDate(x.observedAt)})));
    for(const [label,key] of [["Δ COT","cotSide"],["H4","h4Side"],["H1","h1Side"],["M15","m15Side"]]){
      row(label,points.map(p=>{
        const dir=trendCell(p[key]);
        return {...dir,description:(DIRECTION[p[key]]||"direzione N/D")+
          (key==="cotSide"?" · variazione settimanale del report "+p.reportDate:"")};
      }));
    }
    row("Relazione",points.map(p=>({
      label:p.state==="aligned"?"=":"≠",state:p.state,
      description:p.state==="aligned"?"COT e prezzo concordi":"COT e prezzo divergenti"
    })));
    row("Tecnica",points.map(p=>({
      label:p.priceState==="watch"?"○":p.priceState==="partial"?"◐":"●",
      state:p.priceState,description:PRICE_LEVEL[p.priceState]
    })));
    scroll.append(matrix);
    chart.append(scroll);
    const legend=make("details","radar-legend");
    legend.append(make("summary",null,"Legenda e significato degli stati"));
    legend.append(make("p","monitor-caption",
      "↑ spinta rialzista, ↓ ribassista, → neutro, — non disponibile; "+
      "= Δ COT e prezzo concordi, ≠ divergenti; ○ osservazione, ◐ conferma parziale, ● conferma tecnica."));
    legend.append(make("p","monitor-caption",
      "Δ COT misura la variazione settimanale della posizione netta/open interest del gruppo CFTC selezionato: "+
      "NON equivale necessariamente a posizione netta long/short né rivela ordini istituzionali live."));
    legend.append(make("p","monitor-caption",
      "Conferma tecnica = criteri EMA e breakout H4/H1/M15 soddisfatti: "+
      "non conferma un'operazione istituzionale e non è una previsione."));
    chart.append(legend);
    item.append(chart);
    const changes=make("details","radar-change-details");
    changes.append(make("summary",null,"Cambiamenti osservati · "+model.changes.length));
    if(!model.changes.length)changes.append(make("p","monitor-caption",
      "Nessun cambio di classificazione tra i campioni visibili. Non significa prezzo immobile."));
    else {
      const ul=make("ul","radar-change-list");
      for(const change of model.changes){
        const li=make("li",change.verified?"radar-verified":"radar-observed",
          shortDate(change.at)+" · "+change.labels.join("; "));
        ul.append(li);
      }
      changes.append(ul);
    }
    item.append(changes);
    if(last.state==="divergent"){
      item.append(make("p","monitor-caption","Divergenza osservata negli ultimi "+
        model.divergentSamples+" campioni visibili. Non prova continuità tra i campioni né inversione futura."));
    }
    return item;
  }
  function renderEvolution(history,historyTotal,host){
    const models=evolutionModel(history);
    if(!models.length){
      host.append(make("p","monitor-caption",historyTotal===null?
        "Radar Evoluzione non disponibile: lo storico VPS richiede il backend v1.37 o successivo.":
        "Nessun campione nello storico v1.37. I riferimenti preesistenti non vengono modificati."));
      return;
    }
    const panel=make("section","monitor-evolution radar-evolution");
    const divergent=models.filter(m=>m.last.state==="divergent").length;
    const withEvent=models.filter(m=>m.verifiedEvents>0).length;
    const h=make("div","radar-evolution-heading");
    h.append(make("h3",null,"Radar Evoluzione Squali"));
    h.append(make("p","monitor-caption",models.length+" mercati con storico · "+
      divergent+" divergenti · "+(models.length-divergent)+" concordi · "+
      withEvent+" con eventi COT/prezzo qualificati nei campioni visibili"));
    panel.append(h);
    panel.append(make("p","monitor-caption radar-monitor-context",
      "Vista STORICA: mercati con campioni già archiviati, anche se non idonei "+
      "nell'ultima scansione. Ultimi 12 campioni per mercato, nessuna interpolazione "+
      "né sentiment inventato. Cronologia dalla v1.37; nessuna previsione."));
    const filterBox=make("div","radar-filters");
    filterBox.setAttribute("role","group");
    filterBox.setAttribute("aria-label","Filtro radar evoluzione");
    const result=make("div","radar-evolution-results");
    const options=[
      ["all","Tutti",models.length],
      ["divergent","Divergenti",divergent],
      ["aligned","Concordi",models.length-divergent],
      ["verified","Eventi verificati",withEvent]];
    const buttons=[];
    function update(mode){
      result.replaceChildren();
      for(const [key,btn] of buttons){
        btn.setAttribute("aria-pressed",key===mode?"true":"false");
      }
      const filtered=models.filter(m=>mode==="all"||
        (mode==="verified"?m.verifiedEvents>0:m.last.state===mode));
      if(!filtered.length){
        result.append(make("p","monitor-caption",mode==="verified"?
          "Nessun evento COT/prezzo qualificato nei campioni visibili. I cambi tecnici non provano movimenti istituzionali.":
          "Nessun mercato corrisponde al filtro nei dati disponibili."));
      }else for(const m of filtered)result.append(makeRadarCard(m));
    }
    for(const [key,label,total] of options){
      const b=make("button","radar-filter",label+" ("+total+")");
      b.type="button";
      b.addEventListener("click",()=>update(key));
      buttons.push([key,b]);filterBox.append(b);
    }
    panel.append(filterBox,result);
    update("all");
    host.append(panel);
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
      ["Mercati controllati",view.tracked],["Idonei nella scansione corrente",view.analyzed],
      ["Esclusi dalla scansione corrente",view.excluded],["Riferimenti iniziali salvati",view.baselines],
      ["Eventi COT/prezzo qualificati",view.events]];
    for(const [name,val] of metrics){
      const box=make("div","monitor-metric");
      box.append(make("small",null,name),make("strong",null,val===null?"—":val));
      grid.append(box);
    }
    host.append(grid);
    host.append(make("p","monitor-caption",
      "Idonei = mercati che nell'ULTIMA scansione superano i criteri Δ COT e prezzo H4/H1. "+
      "Il Radar storico può contenerne più di quanti siano idonei ora. "+
      "La conferma tecnica del prezzo non dimostra un'operazione istituzionale."));
    const state=make("p","monitor-outcome",OUTCOMES[view.displayOutcome]);
    state.setAttribute("data-outcome",view.displayOutcome);
    host.append(state);
    host.append(make("p","monitor-caption","Ultima scansione: "+(view.newBaselines??"—")+" nuovi riferimenti · "+
      (view.updatedObservations??"—")+" riferimenti aggiornati · "+(view.newEvents??"—")+
      " nuovi eventi. I totali del registro sono distinti dagli incrementi."));
    if(view.reasons.length){
      const section=make("div","monitor-reasons");
      section.append(make("h3",null,"Perché alcuni mercati sono esclusi"));
      const ul=make("ul");
      for(const r of view.reasons)ul.append(make("li",null,r.label+": "+r.count));
      section.append(ul,make("p","monitor-caption","Uno stesso mercato può avere più motivi: la somma dei motivi può superare gli esclusi."));
      host.append(section);
    }
    renderEvolution(view.history,view.historyTotal,host);
    if(view.observations.length){
      const panel=make("details","monitor-exclusions");
      panel.append(make("summary",null,"Mostra i "+view.observations.length+" riferimenti con ultima osservazione"));
      const list=make("ul");
      for(const item of view.observations){
        const label=item.state==="aligned"?"COT e prezzo concordi":"COT e prezzo divergenti";
        const level={watch:"prezzo in osservazione",partial:"prezzo parziale",confirmed:"prezzo tecnicamente confermato"}[item.priceState];
        list.append(make("li",null,item.symbol+" · "+label+" ("+level+")"+
          " · prezzo "+itDate(item.priceTime)+" · registrato "+itDate(item.observedAt)));
      }
      panel.append(list);
      host.append(panel);
    }else if(view.markets.length){
      host.append(make("p","monitor-caption","Nessun dettaglio dei riferimenti disponibile: il database VPS potrebbe non contenere osservazioni."));
    }
    if(view.markets.length){
      const panel=make("details","monitor-exclusions");
      panel.append(make("summary",null,"Freschezza M15/H1/H4 · "+view.tracked+" mercati"));
      panel.append(make("p","monitor-caption","Orari delle ultime candele CHIUSE in Italia, età calcolata dalla VPS al momento della scansione. Il dato recente M15 non garantisce H1/H4 recenti."));
      const list=make("div","monitor-frame-list");
      for(const market of view.markets){
        const row=make("div","monitor-frame-row");
        row.append(make("strong",null,market.symbol+(market.analyzed?" · idoneo":" · escluso")));
        const times=make("div","monitor-frame-times");
        for(const name of ["M15","H1","H4"]){
          const frame=market.frames[name];
          const when=frame.lastClosedAt?itDate(frame.lastClosedAt):"N/D";
          const age=frame.ageMinutes===null?"età N/D":frame.ageMinutes+" min";
          times.append(make("span",null,name+" · "+when+" · "+age+
            " · "+(frame.bars??"—")+" candele"));
        }
        row.append(times);
        if(market.reasons.length)row.append(make("p","monitor-caption",market.reasons.join("; ")));
        list.append(row);
      }
      panel.append(list);
      host.append(panel);
    }else{
      host.append(make("p","monitor-caption","Dettaglio per timeframe non disponibile dal backend VPS precedente alla v1.36."));
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
  root.REMURA_SQUAL_DIAGNOSTICS={read,render,evolutionModel,REASONS,OUTCOMES};
})(typeof window!=="undefined"?window:globalThis);
