/* REMURA: indici storici deterministici sui netti CFTC normalizzati per OI.
   Non sono percentuali di long, segnali di trading o predizioni. */
(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.REMURA_COT_INDEX_CORE = api;
})(typeof window !== "undefined" ? window : null, function () {
  "use strict";
  const WINDOWS = Object.freeze([26, 52, 156, 260]);
  function index(values) {
    if (!Array.isArray(values) || values.length < 2 || values.some(v => !Number.isFinite(v))) return null;
    const min = Math.min(...values), max = Math.max(...values);
    if (max === min) return null; // Intervallo nullo: nessun indice 0-100 inventato.
    const current = values[values.length - 1];
    return { value: Math.max(0, Math.min(100, 100 * (current - min) / (max - min))), min, max, current };
  }
  function evaluate(series, period) {
    if (!WINDOWS.includes(period)) throw new RangeError("Finestra COT non supportata");
    const unique = new Map();
    if (Array.isArray(series)) for (const r of series) {
      if (!r || !/^\d{4}-\d{2}-\d{2}$/.test(r.date || "") ||
          !Number.isFinite(r.a) || !Number.isFinite(r.b)) continue;
      unique.set(r.date, {date:r.date,a:r.a,b:r.b});
    }
    const sorted = [...unique.values()].sort((a,b)=>a.date.localeCompare(b.date));
    if (sorted.length < period) {
      return {state:"insufficient",period,available:sorted.length,required:period,a:null,b:null,gapIndex:null,gap:null,gapSeries:[]};
    }
    const rows = sorted.slice(-period);
    const gapSeries = rows.map(r=>({date:r.date,gap:r.a-r.b}));
    return {
      state:"ok", period, available:sorted.length, required:period,
      asof:rows[rows.length-1].date,
      a:index(rows.map(r=>r.a)),
      b:index(rows.map(r=>r.b)),
      gapIndex:index(gapSeries.map(r=>r.gap)),
      gap:gapSeries[gapSeries.length-1].gap,
      gapSeries
    };
  }
  return {WINDOWS, index, evaluate};
});
