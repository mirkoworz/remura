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
  return {analyze, retailContext, combine, legsFor, fmt, signed};
});