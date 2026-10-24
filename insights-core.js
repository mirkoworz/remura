/* REMURA v0.9 — motore deterministico e verificabile. Nessun ordine, target o probabilità inventata. */
(function (root, factory) {
  "use strict";
  const core = factory();
  if (typeof module === "object" && module.exports) module.exports = core;
  if (root) root.REMURA_INSIGHTS_CORE = core;
})(typeof window !== "undefined" ? window : null, function () {
  "use strict";
  const MIN_DELTA = 0.45; // Punti percentuali di netto/OI: soglia descrittiva, non ottimizzata.
  const MIN_FOUR_WEEKS = 1.2;
  const DAY = 86400000;
  const isNum = x => typeof x === "number" && Number.isFinite(x);
  const fmt = (n, digits = 1) => isNum(n) ? new Intl.NumberFormat("it-IT", { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(n) : "N/D";
  const signed = (n, digits = 1) => isNum(n) ? (n > 0 ? "+" : "") + fmt(n, digits) : "N/D";
  const direction = n => n > MIN_DELTA ? 1 : n < -MIN_DELTA ? -1 : 0;
  const dirName = n => n > 0 ? "rialzista" : n < 0 ? "ribassista" : "neutrale";
  function analyze(series, options = {}) {
    const symbol = String(options.symbol || "").toUpperCase();
    const isFX = !!options.isFX, isMetal = !!options.isMetal;
    const labels = Array.isArray(options.labels) ? options.labels : (isMetal ? ["Managed Money", "Producer / Merchant"] : ["Asset Manager", "Leveraged Funds"]);
    const now = isNum(options.now) ? options.now : Date.now();
    if (!Array.isArray(series) || series.length < 2) {
      return { state: "missing", title: "COT non disponibile", bias: 0, reasons: ["Servono almeno due report COT ufficiali per confrontare i movimenti."], caveats: ["Nessun dato viene simulato."], symbol };
    }
    const rows = series.filter(x => x && /^\d{4}-\d{2}-\d{2}$/.test(x.date || "") && isNum(x.a) && isNum(x.b)).slice().sort((x,y) => x.date.localeCompare(y.date));
    if (rows.length < 2) return { state: "missing", title: "COT non disponibile", bias: 0, reasons: ["Storico COT insufficiente."], caveats: [], symbol };
    const last = rows[rows.length - 1], prev = rows[rows.length - 2], specKey = isMetal ? "a" : "b";
    const specLabel = labels[isMetal ? 0 : 1], secondaryKey = isMetal ? "b" : "a";
    const secondaryLabel = labels[isMetal ? 1 : 0];
    const currentNet = last[specKey], weekly = currentNet - prev[specKey];
    const fourWeeks = rows.length >= 5 ? currentNet - rows[rows.length - 5][specKey] : null;
    const secondaryWeekly = last[secondaryKey] - prev[secondaryKey];
    const recent = rows.slice(-4);
    let increases = 0, decreases = 0;
    for (let i = 1; i < recent.length; i++) {
      const diff = recent[i][specKey] - recent[i - 1][specKey];
      if (diff > MIN_DELTA) increases++;
      if (diff < -MIN_DELTA) decreases++;
    }
    const momentum = direction(weekly);
    const sustained = momentum !== 0 && isNum(fourWeeks) && direction(fourWeeks) === momentum &&
      Math.abs(fourWeeks) >= MIN_FOUR_WEEKS && (momentum > 0 ? increases : decreases) >= 2;
    const age = Math.max(0, Math.floor((now - Date.parse(last.date + "T00:00:00Z")) / DAY));
    const stale = !isNum(age) || age > 14;
    const conflict = !isMetal && momentum !== 0 && direction(secondaryWeekly) === -momentum;
    const caveats = [];
    if (isFX) caveats.push("Cross Forex: differenza normalizzata dei futures delle due valute contro USD; non è un COT diretto su " + symbol + ". USD vale zero soltanto come riferimento di calcolo.");
    else caveats.push("Report sul future di riferimento; non fotografa tutte le posizioni sul mercato spot o CFD.");
    if (isMetal) caveats.push("Producer / Merchant svolgono spesso coperture: una posizione opposta ai Managed Money non equivale automaticamente a uno scontro direzionale.");
    if (stale) caveats.push("Report datato (" + age + " giorni dalla data delle posizioni). Evitare interpretazioni operative aggiornate.");
    caveats.push("TradingView è incorporato, ma non espone a REMURA candele OHLC verificabili: prezzo e rotture H4/H1 non sono ancora confermati automaticamente.");
    const reasons = [];
    reasons.push(specLabel + ": netto " + signed(currentNet) + "% OI; variazione settimanale " + signed(weekly) + " punti percentuali.");
    if (isNum(fourWeeks)) reasons.push("Ultime 4 settimane: " + signed(fourWeeks) + " pp; " + increases + " aumenti e " + decreases + " riduzioni significative nelle ultime 3 variazioni.");
    else reasons.push("Storico inferiore a 5 rilevazioni: trend a 4 settimane non verificabile.");
    reasons.push(secondaryLabel + ": variazione settimanale " + signed(secondaryWeekly) + " pp" + (conflict ? ", in direzione opposta al gruppo speculativo." : "."));
    let state = "watch", title = "COT in osservazione";
    let bias = 0;
    if (stale) { state = "stale"; title = "COT datato: attendere dati"; }
    else if (momentum === 0) { state = "neutral"; title = "Spinta speculativa contenuta"; }
    else {
      bias = momentum;
      if (conflict) {
        state = "conflict";
        title = "Gruppi istituzionali discordanti";
      } else if (sustained) {
        state = "trend";
        title = "Pressione COT " + dirName(momentum) + " persistente";
      } else {
        title = "Pressione COT " + dirName(momentum) + " da monitorare";
      }
    }
    return {
      state, title, bias, sustained, conflict, stale, age, asof: last.date, symbol,
      labels, specLabel, secondaryLabel, weekly, fourWeeks, secondaryWeekly,
      currentNet, increases, decreases, reasons, caveats,
      summary: stale ? "Il report non è abbastanza recente per un verdetto aggiornato." :
        bias === 0 ? "Non emerge una variazione speculativa settimanale sufficientemente marcata." :
        (sustained ? "La spinta speculativa è proseguita per più rilevazioni." : "È presente una variazione settimanale ma manca una sequenza storica convincente.") +
        (conflict ? " I gruppi istituzionali mostrano segnali discordanti." : "") +
        " Non è una conferma dell'andamento del prezzo.",
      next: "Confermare struttura H4/H1 e reazione M15 sul grafico; verificare che il prossimo COT non smentisca la tendenza. Nessun ingresso automatico senza dati prezzo validati.",
      side: bias > 0 ? "bias COT rialzista" : bias < 0 ? "bias COT ribassista" : "bias COT neutrale"
    };
  }
  function retailContext(current, records, now = Date.now()) {
    if (!current || typeof current !== "object") return { valid: false, text: "Sentiment Myfxbook non disponibile per questo strumento." };
    const stamp = Date.parse(current.t || "");
    const age = now - stamp;
    const sample = Number(current.lPos) + Number(current.sPos);
    const longLots = Number(current.lLots), shortLots = Number(current.sLots);
    if (!Number.isFinite(age) || age < -300000 || age > 3 * 3600000) return {valid:false, text:"Sentiment Myfxbook datato: non usato nel confronto."};
    if (!Number.isFinite(sample) || sample < 30 || !Number.isFinite(longLots) || !Number.isFinite(shortLots) || longLots + shortLots <= 0) {
      return {valid:false, text:"Campione Myfxbook insufficiente o volumi non disponibili: escluso dal confronto."};
    }
    const pct = 100 * longLots / (longLots + shortLots);
    const skew = pct >= 70 ? 1 : pct <= 30 ? -1 : 0;
    const points = Array.isArray(records) ? records.filter(r => r && Number.isFinite(Date.parse(r.t)) && Number.isFinite(+r.lLots) && Number.isFinite(+r.sLots)) .sort((a,b) => Date.parse(a.t)-Date.parse(b.t)) : [];
    const freshPoints = points.filter(x => now - Date.parse(x.t) <= DAY && now - Date.parse(x.t) >= 0);
    let movement = null;
    if (freshPoints.length >= 2) {
      const start = freshPoints[0], end = freshPoints[freshPoints.length - 1];
      if (Date.parse(end.t) - Date.parse(start.t) >= 15 * 60000) {
        movement = {long: (+end.lLots) - (+start.lLots), short: (+end.sLots) - (+start.sLots),
          hours: (Date.parse(end.t) - Date.parse(start.t)) / 3600000};
      }
    }
    return {valid: true, pct, skew, sample, movement,
      text: "Myfxbook: " + fmt(pct, 0) + "% dei lotti long e " + fmt(100 - pct, 0) + "% short su " + sample.toLocaleString("it-IT") + " posizioni del campione. " +
        (skew === 1 ? "Forte prevalenza retail long." : skew === -1 ? "Forte prevalenza retail short." : "Distribuzione retail senza estremo 70/30.") +
        (movement ? " Nell'archivio delle ultime " + fmt(movement.hours,1) + " ore: lotti long " + signed(movement.long,2) + ", short " + signed(movement.short,2) + "." : " Storico di variazione non ancora sufficiente.")};
  }
  function combine(cot, retail) {
    if (!cot || cot.state === "missing") return "Mancano report COT sufficienti: nessun verdetto direzionale.";
    if (cot.stale) return "COT datato: non utilizzare l'eventuale sentiment recente per formulare segnali operativi.";
    if (!retail || !retail.valid) return "Il sentiment retail non può ancora confermare o contraddire il contesto.";
    if (!cot.bias || !retail.skew) return "Il retail non genera una divergenza contrarian netta (70/30) con un bias COT chiaro.";
    if (cot.bias === -retail.skew) return "Possibile divergenza contrarian: la community Myfxbook è maggiormente " + (retail.skew > 0 ? "long" : "short") +
      " mentre il posizionamento speculativo COT si muove in senso opposto. Non implica che il resto degli operatori sia istituzionale.";
    return "Retail e spinta speculativa COT hanno lo stesso verso: non emerge una divergenza contrarian 70/30.";
  }
  function legsFor(series, cfg) {
    if (!Array.isArray(series)) return [];
    const isFX = !!cfg.isFX;
    if (!isFX) return [{name:cfg.symbol, rows:series.filter(r=>r.raw).map(r=>({date:r.date, data:r.raw}))}];
    const base = cfg.symbol.slice(0,3), quote=cfg.symbol.slice(3);
    return [base, quote].filter(c=>c !== "USD").map(c=>({
      name:c, rows:series.filter(r=>r.parts && r.parts[c === base ? "base" : "quote"]).map(r=>({date:r.date, data:r.parts[c === base ? "base" : "quote"]}))
    }));
  }
 const HOUR=3600000;
 const sideName=n=>n>0?"rialzista":n<0?"ribassista":"senza direzione";
 function cotEvidence(cot){
  if(!cot||cot.state==="missing")return {status:"missing",side:0,title:"COT non disponibile",detail:"Nessuna posizione istituzionale dedotta da altri strumenti."};
  if(cot.stale||cot.state==="stale")return {status:"stale",side:0,title:"COT datato",detail:"L'ultima fotografia settimanale è troppo vecchia per una conclusione."};
  if(cot.conflict||cot.state==="conflict")return {status:"mixed",side:0,title:"Gruppi COT non concordi",detail:"Il gruppo speculativo e quello secondario indicano variazioni contrapposte."};
  if((cot.bias!==1&&cot.bias!==-1)||!["watch","trend"].includes(cot.state))
   return {status:"neutral",side:0,title:"COT senza spinta netta",detail:"Non emerge una variazione settimanale robusta nel netto dei futures."};
  return {status:"valid",side:cot.bias,title:"Spinta COT "+sideName(cot.bias),detail:
   (cot.sustained?"Variazioni persistenti su più rilevazioni. ":"Variazione settimanale ancora da confermare. ")+
   "Si riferisce ai futures CFTC, non agli ordini del broker."};
 }
 function priceEvidence(price,now=Date.now()){
  if(!price||price.state==="unavailable")return {status:"missing",side:0,title:"Prezzo non verificato",detail:"Mancano candele H4/H1/M15 idonee o recenti."};
  const latest=Date.parse(price.metrics?.M15?.latest||"");
  const weekend=[0,6].includes(new Date(now).getUTCDay());
  const maxAge=(weekend?72:3)*HOUR;
  if(!Number.isFinite(latest)||latest>now+300000||now-latest>maxAge)
   return {status:"stale",side:0,title:"Prezzo non aggiornato",detail:"Le candele non sono sufficientemente recenti per questo verdetto."};
  if(price.state==="conflict")return {status:"mixed",side:0,title:"H4 e H1 discordanti",detail:"La struttura dei timeframe non sostiene una direzione univoca."};
  if((price.side!==1&&price.side!==-1)||!["watch","partial","confirmed"].includes(price.state))
   return {status:"neutral",side:0,title:"Prezzo senza direzione comune",detail:"H4 e H1 non forniscono una lettura concorde utilizzabile."};
  return {status:"valid",side:price.side,title:"Struttura prezzo "+sideName(price.side),
   detail:price.state==="confirmed"?"Conferma tecnica H4/H1/M15 completa sul campione chiuso.":
    price.state==="partial"?"H4 e H1 coerenti, ma manca conferma M15 completa.":
     "Tendenza H4/H1 coerente; rotture ancora incomplete."};
 }
 function retailEvidence(feed,source,now=Date.now()){
  const current=feed?.current,stamp=Date.parse(current?.t||"");
  const age=now-stamp;
  if(!current)return {status:"missing",side:0,title:source+" N/D",detail:"Campione non disponibile."};
  if(feed.fresh!==true||!Number.isFinite(age)||age< -300000||age>3*HOUR)
   return {status:"stale",side:0,title:source+" datato",detail:"Rilevazione retail conservata, ma non valida come lettura corrente."};
  const lots=source==="Myfxbook";
  if(lots){
   const count=Number(current.lPos)+Number(current.sPos);
   const l=Number(current.lLots),s=Number(current.sLots);
   if(!Number.isFinite(count)||count<30||!Number.isFinite(l)||!Number.isFinite(s)||l<0||s<0||l+s<=0)
    return {status:"missing",side:0,title:"Myfxbook: campione insufficiente",detail:"Servono almeno 30 posizioni e lotti effettivi."};
  }
  const pct=lots?100*Number(current.lLots)/(Number(current.lLots)+Number(current.sLots)):Number(current.lPct);
  if(!Number.isFinite(pct)||pct<0||pct>100)return {status:"missing",side:0,title:source+" non valido",detail:"Distribuzione long/short non verificabile."};
  const side=pct>=70?1:pct<=30?-1:0;
  return {status:side?"extreme":"neutral",side,
   title:source+(side?" · prevalenza retail "+(side>0?"long":"short"):" · retail bilanciato"),
   detail:"Long "+pct.toFixed(1).replace(".",",")+"% nella propria popolazione. "+
    (lots?"Misura i lotti della community.":"Misura la quota di posizioni clienti.")+
    " Nessuna posizione istituzionale dedotta."};
 }
 function macroEvidence(info){
  if(!info||info.state==="unavailable")return {status:"missing",title:"Macro non disponibile",detail:"DXY e VIX non hanno entrambi una serie verificabile."};
  return {status:info.historical?"historical":"context",title:info.label||"Contesto macro disponibile",
   detail:(info.historical?"Ultima sessione del venerdì, non live. ":"")+
    "Il contesto DXY/VIX descrive il rischio generale, non aggiunge automaticamente un voto long o short."};
 }
 function evaluate({symbol,cot,price,myfxbook,capital,macro,now=Date.now()}={}){
  const items={
   cot:cotEvidence(cot),
   price:priceEvidence(price,now),
   myfxbook:retailEvidence(myfxbook,"Myfxbook",now),
   capital:retailEvidence(capital,"Capital.com",now),
   macro:macroEvidence(macro)
  };
  const c=items.cot,p=items.price;
  let state="incomplete",side=0,title="Prove insufficienti per un verdetto",
   narrative="Il quadro non contiene due conferme indipendenti e coerenti fra COT e prezzo.";
  if(c.status==="valid"&&p.status==="valid"){
   if(c.side===p.side){
    state="aligned";side=c.side;
    const strong=cot.state==="trend"&&price.state==="confirmed";
    title=strong?"Tracce concordi, da verificare":"Coerenza preliminare, da monitorare";
    narrative="La spinta speculativa COT settimanale e la struttura del prezzo indicano entrambe una direzione "+
     sideName(side)+". "+(strong?"Il prezzo conferma H4/H1/M15. ":"Mancano conferme tecniche o persistenza sufficienti. ")+
     "Non identifica acquisti o vendite istituzionali in tempo reale.";
   }else{
    state="divergent";title="COT e prezzo in contrasto";
    narrative="Il COT indica una spinta "+sideName(c.side)+
      ", mentre la struttura H4/H1 suggerisce un movimento "+sideName(p.side)+
      ". Non attribuire una direzione affidabile allo Squalo.";
   }
  }else if(c.status==="mixed"||p.status==="mixed"){
   state="mixed";title="Segnali principali non concordi";
   narrative="Almeno uno dei due fattori principali è internamente contraddittorio: nessun verdetto direzionale.";
  }else if(c.status==="stale"||p.status==="stale"){
   state="stale";title="Dati principali datati";
   narrative="L'analisi necessita di posizionamento COT e prezzo sufficientemente recenti.";
  }
  const retailNotes=[];
  for(const k of ["myfxbook","capital"]){
   const f=items[k];
   if(f.status==="extreme"){
    if(side&&state==="aligned")retailNotes.push(
     (k==="myfxbook"?"Myfxbook":"Capital.com")+
     (f.side===-side?" presenta un estremo retail opposto alla direzione COT/prezzo.":" presenta un estremo retail nella stessa direzione COT/prezzo.")+
     " È un indizio descrittivo, non una conferma istituzionale.");
    else retailNotes.push((k==="myfxbook"?"Myfxbook":"Capital.com")+
     " mostra un estremo retail, ma senza COT e prezzo concordi non è un segnale contrarian.");
   }
  }
  return {symbol:String(symbol||""),state,side,title,narrative,items,retailNotes,
   note:"Analisi descrittiva: COT settimanale, prezzi broker, due campioni retail diversi e contesto macro. Nessuna probabilità, ordine o promessa di rendimento."};
 }

  const verdict=Object.freeze({cotEvidence,priceEvidence,retailEvidence,macroEvidence,evaluate});
  return {analyze, retailContext, combine, legsFor, fmt, signed, verdict};
});