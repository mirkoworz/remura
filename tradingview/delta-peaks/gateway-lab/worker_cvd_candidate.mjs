// REMURA v0.8.60 — 14/11/2026 CET — CVD candidate, NEVER deployed.
// Weekend transport diagnostic: BINANCE:BTCUSDT M5, bounded by receiver clock.
// EURUSD unchanged; BTC never eligible for the prospective FX research cohort.
// Deploy only to the isolated TEST Worker with owner dispatch; default remains OFF.
// Ricevitore Cloudflare Worker + D1. Fail-closed per configurazione predefinita.
// Ingresso SOLO da TradingView su IP documentati + token segreto nell'URL HTTPS.
// Token MAI nel repository, nel Pine, nel corpo JSON o nei log.

const ALLOWED_IPS = new Set([
  "52.89.214.238", "34.212.75.30", "54.218.53.128", "52.32.178.7"
]);
// Fixed UTC bounds: no new configuration, permission, or scheduled mutation.
const BTC_TEST_START_MS = Date.UTC(2026, 10, 14, 0, 0, 0);
const BTC_TEST_END_MS = Date.UTC(2026, 10, 16, 0, 0, 0);
const MAX_BYTES = 20_000;
const MAX_EVENTS_PER_MINUTE = 20;
const MAX_PROSPECTIVE_LAG_MS = 120_000;
const MAX_FUTURE_MS = 120_000;
const MAX_STALE_MS = 86_400_000;
const FIELDS = {
  root: ["schema", "source", "indicator", "version", "event_type",
    "symbol", "feed", "timeframe", "bar_open_ms", "bar_close_ms", "sent_clock_ms",
    "confirmed", "realtime", "ohlc", "delta_intrabar", "effort",
    "signed_result_atr", "efficiency", "footprint", "levels", "level_scores",
    "level_origin_ms", "events", "quality"],
  ohlc: ["open", "high", "low", "close", "prev_close", "atr14"],
  footprint: ["available", "buy", "sell", "delta", "total", "delta_pct",
    "poc", "vah", "val", "imb_buy_rows", "imb_sell_rows"],
  levels: ["day1", "day2", "day3", "previous_day", "week",
    "current_month", "previous_month"],
  scores: ["day1", "day2", "day3"],
  events: ["peak", "er_positive", "er_negative", "day_level_action",
    "day_level_rank", "evicted_day_price", "evicted_day_origin_ms",
    "retest_day1", "retest_day2", "retest_day3", "retest_previous_day"],
  quality: ["bar_closed", "source_type", "has_intrabar_delta",
    "has_footprint", "freshness_ms", "daily_anchor", "lower_tf"]
};

class InvalidInput extends Error {
  constructor(reason) { super(reason); this.name = "InvalidInput"; }
}
class TooLarge extends Error {
  constructor() { super("payload_too_large"); this.name = "TooLarge"; }
}
function ensure(ok, message) {
  if (!ok) throw new InvalidInput(message);
}
function shape(value, required, context) {
  ensure(value !== null && typeof value === "object" && !Array.isArray(value),
    context + ":not_object");
  ensure(Object.keys(value).length === required.length &&
    required.every((name) => Object.hasOwn(value, name)),
    context + ":keys");
  return value;
}
function number(value, nullable = false) {
  return (nullable && value === null) ||
    (typeof value === "number" && Number.isFinite(value));
}
function ms(value, nullable = false) {
  return (nullable && value === null) ||
    (Number.isSafeInteger(value) && value > 1_000_000_000_000);
}
function validFlag(value) { return typeof value === "boolean"; }

function validateSharedSnapshot(payload, receivedMs, cvdMode = false) {
  const p = shape(payload, FIELDS.root, "root");
  ensure(p.schema === "remura.tv.flow.v1" &&
    p.source === "TRADINGVIEW_INTRABAR_ESTIMATE" &&
    p.indicator === "REMURA_ALL_IN_ONE_PREMIUM" &&
    p.version === "0.8.1-lab", "contract");
  ensure(p.event_type === "BAR_EVENT" || p.event_type === "HEARTBEAT",
    "event_type");
  const eurPilot = cvdMode ? p.symbol === "FX:EURUSD" && p.feed === "FX" : p.symbol === "FXCM:EURUSD" && p.feed === "FXCM";
  const btcTransportOnly = !cvdMode && p.symbol === "BINANCE:BTCUSDT" && p.feed === "BINANCE" &&
    receivedMs >= BTC_TEST_START_MS && receivedMs < BTC_TEST_END_MS;
  ensure((eurPilot || btcTransportOnly) && p.timeframe === "5", "pilot_feed_or_timeframe");
  ensure(p.confirmed === true && p.realtime === true, "not_closed_realtime");
  ensure(ms(p.bar_open_ms) && ms(p.bar_close_ms) && ms(p.sent_clock_ms) &&
    p.bar_close_ms - p.bar_open_ms === 300_000, "timestamps");
  ensure(Number.isSafeInteger(receivedMs), "receiver_clock");
  const lagMs = receivedMs - p.bar_close_ms;
  ensure(lagMs >= -MAX_FUTURE_MS && lagMs <= MAX_STALE_MS,
    "future_or_too_old");
  const o = shape(p.ohlc, FIELDS.ohlc, "ohlc");
  for (const f of ["open", "high", "low", "close"]) ensure(number(o[f]), "ohlc:" + f);
  ensure(number(o.prev_close, true) && number(o.atr14, true), "atr_or_previous_close");
  ensure(o.low <= o.open && o.open <= o.high &&
    o.low <= o.close && o.close <= o.high &&
    (o.atr14 === null || o.atr14 >= 0), "ohlc_consistency");
  for (const f of ["delta_intrabar", "effort", "signed_result_atr", "efficiency"])
    ensure(number(p[f], true), "numeric:" + f);
  ensure(p.effort === null || p.effort >= 0, "effort_negative");

  const fp = shape(p.footprint, FIELDS.footprint, "footprint");
  ensure(validFlag(fp.available), "footprint_available");
  for (const f of FIELDS.footprint.slice(1))
    ensure(number(fp[f], true), "footprint:" + f);
  if (!fp.available) {
    ensure(FIELDS.footprint.slice(1).every((f) => fp[f] === null), "footprint_null");
  } else {
    ensure(number(fp.total), "footprint_total");
    for (const f of ["imb_buy_rows", "imb_sell_rows"])
      ensure(fp[f] === null || (Number.isSafeInteger(fp[f]) && fp[f] >= 0),
        "footprint_imb_integer");
  }

  const levels = shape(p.levels, FIELDS.levels, "levels");
  const ids = shape(p.level_origin_ms, FIELDS.levels, "level_origin_ms");
  const scores = shape(p.level_scores, FIELDS.scores, "level_scores");
  for (const f of FIELDS.levels) {
    ensure(number(levels[f], true) && ms(ids[f], true) &&
      (levels[f] === null) === (ids[f] === null), "level_id:" + f);
    if (ids[f] !== null) ensure(ids[f] <= p.bar_close_ms, "level_from_future:" + f);
  }
  for (const f of FIELDS.scores)
    ensure(number(scores[f], true) &&
      (scores[f] === null) === (levels[f] === null) &&
      (scores[f] === null || scores[f] >= 0), "level_score:" + f);

  const ev = shape(p.events, FIELDS.events, "events");
  const boolNames = ["peak", "er_positive", "er_negative", "retest_day1",
    "retest_day2", "retest_day3", "retest_previous_day"];
  for (const f of boolNames) ensure(validFlag(ev[f]), "event_flag:" + f);
  ensure(["NONE", "ADDED", "REPLACED"].includes(ev.day_level_action), "level_action");
  ensure(ev.day_level_rank === null ||
    (Number.isSafeInteger(ev.day_level_rank) &&
      ev.day_level_rank >= 1 && ev.day_level_rank <= 3), "level_rank");
  ensure(number(ev.evicted_day_price, true) &&
    ms(ev.evicted_day_origin_ms, true), "evicted_level");
  ensure((ev.day_level_action !== "NONE") ===
    (ev.day_level_rank !== null), "action_rank");
  ensure((!ev.er_positive || ev.peak) &&
    (!ev.er_negative || ev.peak) &&
    !(ev.er_positive && ev.er_negative), "er_flags");
  const hasEvent = ev.day_level_action !== "NONE" ||
    boolNames.some((f) => ev[f]);
  ensure((p.event_type === "BAR_EVENT") === hasEvent, "event_classification");

  const q = shape(p.quality, FIELDS.quality, "quality");
  ensure(q.bar_closed === true &&
    q.source_type === "VOLUME_CLASSIFIED_NOT_CME_EXECUTIONS" &&
    q.has_intrabar_delta === (p.delta_intrabar !== null) &&
    q.has_footprint === fp.available &&
    (q.daily_anchor === "HL2" || q.daily_anchor === "POC FOOTPRINT") &&
    typeof q.lower_tf === "string" && q.lower_tf.length > 0 &&
    Number.isSafeInteger(q.freshness_ms), "quality");
  const key = [p.symbol, p.timeframe, p.bar_close_ms,
    p.version, p.event_type].join("|");
  return {
    key, lagMs,
    // For BTC is_timely stays zero by design (not eligible for FX prospective analysis).
    timely: eurPilot && lagMs >= 0 && lagMs <= MAX_PROSPECTIVE_LAG_MS,
    symbol: p.symbol, timeframe: p.timeframe,
    eventType: p.event_type, barCloseMs: p.bar_close_ms, version: p.version
  };
}


// New configured CVD schema is opt-in and never accepted as a legacy snapshot.
export const CVD_SCHEMA="remura.tv.flow.cvd.preview.v1";
const CVD_VERSION="0.9.1-cvd-lab";
export const CVD_CONFIG=Object.freeze({
 symbol:"FX:EURUSD",timeframe:"5",indicator_version:CVD_VERSION,lower_tf:"1",
 lookback:30,multiplier:3.5,max_efficiency:0.07,min_peak_gap:6,fp_ticks:10,
 fp_value_area_pct:70,fp_imbalance_pct:300,daily_min_effort:1.5,daily_anchor:"HL2",
 show_daily_levels:true,show_prev_day:true,telemetry_enabled:true,telemetry_heartbeat:true,
 cvd_left:2,cvd_right:2,cvd_min_distance:3,cvd_max_distance:72,cvd_warmup:12,
 cvd_min_price_ticks:5,cvd_min_difference:10
});
export function validateSnapshot(payload, receivedMs=Date.now()) {
 return validateSharedSnapshot(payload,receivedMs,false);
}
export function validateCvdEnvelope(payload,receivedMs) {
 const e=shape(payload,["schema","snapshot","configuration","cvd"],"envelope");
 ensure(e.schema===CVD_SCHEMA,"cvd_schema");
 const p=shape(e.snapshot,FIELDS.root,"snapshot");
 ensure(p.schema==="remura.tv.flow.cvd.snapshot.preview.v1" && p.version===CVD_VERSION &&
  p.symbol==="FX:EURUSD" && p.feed==="FX" && p.timeframe==="5","cvd_snapshot_identity");
 const snap=validateSharedSnapshot({...p,schema:"remura.tv.flow.v1",version:"0.8.1-lab"},receivedMs,true);
 ensure(snap.timely && p.bar_close_ms%300000===0,"cvd_maturity");
 const cfg=shape(e.configuration,Object.keys(CVD_CONFIG),"configuration");
 ensure(Object.keys(CVD_CONFIG).every(k=>cfg[k]===CVD_CONFIG[k]),"cvd_configuration");
 ensure(p.quality.lower_tf===cfg.lower_tf && p.quality.daily_anchor===cfg.daily_anchor,"cvd_config_snapshot");
 const c=shape(e.cvd,["model","intrabar_count","complete","continuous","day_valid","segment_id",
  "segment_bars","day_key_ms","raw_delta","trusted_delta","daily_cvd","segment_cvd",
  "eligible","price_bull","price_bear","cvd_bull","cvd_bear","pivot_close_ms"],"cvd");
 ensure(c.model==="D08_SEGMENT_PORT_V091","cvd_model");
 for(const k of ["complete","day_valid","eligible","price_bull","price_bear","cvd_bull","cvd_bear"])
  ensure(validFlag(c[k]),"cvd_flag");
 ensure(c.continuous===null || validFlag(c.continuous),"cvd_continuous");
 for(const k of ["intrabar_count","segment_id","segment_bars","day_key_ms"])
  ensure(Number.isSafeInteger(c[k]) && c[k]>=0,"cvd_counter");
 ensure(c.intrabar_count<=5 && ms(c.day_key_ms) && c.day_key_ms<=p.bar_open_ms,"cvd_counter_scope");
 for(const k of ["raw_delta","trusted_delta","daily_cvd","segment_cvd"])
  ensure(number(c[k],true),"cvd_numeric");
 ensure((c.raw_delta!==null)===c.complete && (c.continuous!==null)===c.complete &&
  (c.trusted_delta!==null)===(c.continuous===true) &&
  (c.daily_cvd!==null)===c.day_valid && (c.segment_cvd!==null)===(c.segment_bars>=2),"cvd_availability");
 if(c.complete){
  ensure(c.intrabar_count===5 && c.segment_id>=1 && c.segment_bars>=1 &&
    (c.segment_bars>=2)===c.continuous,"cvd_complete");
  if(c.continuous) ensure(c.raw_delta===c.trusted_delta,"cvd_trusted_delta");
  if(c.day_valid && !c.continuous) ensure(c.day_key_ms===p.bar_open_ms,"cvd_daily_gap");
 }else ensure(c.segment_bars===0 && !c.day_valid,"cvd_incomplete");
 ensure(c.eligible===(c.continuous===true && c.segment_bars>=cfg.cvd_warmup),"cvd_eligibility");
 const candidate=c.price_bull || c.price_bear;
 ensure(!candidate || c.eligible,"cvd_pivot_quality");
 ensure((!c.cvd_bull || c.price_bull) && (!c.cvd_bear || c.price_bear),"cvd_subset");
 ensure(candidate ? c.pivot_close_ms===p.bar_close_ms-cfg.cvd_right*300000 : c.pivot_close_ms===null,"cvd_pivot_clock");
 if(c.trusted_delta!==null && p.delta_intrabar!==null)
  ensure(Number.isFinite(c.trusted_delta-p.delta_intrabar),"cvd_difference");
 // The compatibility snapshot event type is retained. The CVD flags live in
 // the raw envelope. Never mark the new cohort eligible in the legacy reader.
 return {...snap,key:[p.symbol,p.timeframe,p.bar_close_ms,CVD_VERSION].join("|"),
  version:CVD_VERSION,timely:false,transportTimely:true};
}

async function verifyToken(pathToken, expectedHash) {
  const bytes = new TextEncoder().encode(pathToken);
  const digested = new Uint8Array(await crypto.subtle.digest("SHA-256", bytes));
  let mismatch = 0;
  for (let i = 0; i < 32; i++) {
    mismatch |= digested[i] ^ Number.parseInt(expectedHash.slice(i * 2, i * 2 + 2), 16);
  }
  return mismatch === 0;
}

async function readBoundedText(request) {
  const length = request.headers.get("content-length");
  if (length !== null && /^\d+$/.test(length) && Number(length) > MAX_BYTES)
    throw new TooLarge();
  const reader = request.body?.getReader();
  if (!reader) throw new InvalidInput("missing_body");
  const fragments = [];
  let size = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    size += value.byteLength;
    if (size > MAX_BYTES) {
      await reader.cancel();
      throw new TooLarge();
    }
    fragments.push(value);
  }
  const joined = new Uint8Array(size);
  let at = 0;
  for (const part of fragments) {
    joined.set(part, at);
    at += part.byteLength;
  }
  try {
    return new TextDecoder("utf-8", { fatal: true, ignoreBOM: false }).decode(joined);
  } catch {
    throw new InvalidInput("invalid_utf8");
  }
}
function reply(status, code, extra = {}) {
  return new Response(JSON.stringify({ status: code, ...extra }), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      "x-content-type-options": "nosniff"
    }
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    // /health non deve mai dire accepting:true se manca un prerequisito.
    const configured = env?.INGEST_ENABLED === "true" &&
      typeof env?.TELEMETRY_DB?.prepare === "function" &&
      typeof env?.INGEST_RATE_LIMITER?.limit === "function" &&
      /^[0-9a-f]{64}$/.test(env?.WEBHOOK_TOKEN_SHA256 ?? "");
    if (request.method === "GET" && url.pathname === "/health")
      return reply(200, "lab_only", { accepting: configured });

    // Fail-closed: anche con INGEST_ENABLED=true, senza limiter si rifiuta.
    if (!configured) return reply(503, "disabled");
    if (request.method !== "POST") return reply(404, "not_found");
    const match = url.pathname.match(/^\/ingest\/([A-Za-z0-9_-]{32,128})$/);
    if (!match || url.search) return reply(404, "not_found");

    // CF-Connecting-IP è affidabile solo alle condizioni della configurazione
    // Cloudflare edge diretta. L'allowlist NON sostituisce il token segreto.
    if (!ALLOWED_IPS.has(request.headers.get("cf-connecting-ip")))
      return reply(403, "not_authorized");
    const authorized = await verifyToken(match[1], env.WEBHOOK_TOKEN_SHA256);
    if (!authorized) return reply(403, "not_authorized");
    if (!/^application\/json(?:\s*;|$)/i.test(request.headers.get("content-type") ?? ""))
      return reply(415, "json_required");

    // Limite approssimativo per il flusso autorizzato PRIMA di consumare D1.
    // Shared original limiter key for both symbols: combined 20/60s, not doubled.
    // non protegge dalle richieste anonime che già consumano Worker CPU/quota.
    try {
      const decision = await env.INGEST_RATE_LIMITER.limit({ key: "remura-tv-fxcm-eurusd-m5" });
      if (decision?.success !== true) return reply(429, "rate_limited");
    } catch {
      return reply(503, "limiter_unavailable");
    }

    try {
      const rawJson = await readBoundedText(request);
      let payload;
      try { payload = JSON.parse(rawJson); }
      catch { throw new InvalidInput("invalid_json"); }
      const receivedMs = Date.now();
      let snap;
      if (payload?.schema === CVD_SCHEMA) {
        if (env.CVD_PREVIEW_ENABLED !== "true") return reply(503, "cvd_preview_disabled");
        snap = validateCvdEnvelope(payload, receivedMs);
      } else {
        snap = validateSnapshot(payload, receivedMs);
      }

      // Controllo leggero sulla sola sorgente autorizzata; limite soft,
      // soggetto a race nei burst. Configurare un rate limit edge prima del live.
      const recent = await env.TELEMETRY_DB.prepare(
        "SELECT COUNT(*) AS n FROM tv_flow_events WHERE received_at_ms >= ?"
      ).bind(receivedMs - 60_000).first();
      if (!recent || typeof recent.n !== "number" ||
        !Number.isFinite(recent.n)) return reply(503, "storage_unavailable");
      if (recent.n >= MAX_EVENTS_PER_MINUTE)
        return reply(429, "rate_limited");

      const result = await env.TELEMETRY_DB.prepare(
        "INSERT OR IGNORE INTO tv_flow_events " +
        "(event_key, received_at_ms, bar_close_ms, symbol, timeframe, " +
        "event_type, version, is_timely, raw_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
      ).bind(snap.key, receivedMs, snap.barCloseMs, snap.symbol,
        snap.timeframe, snap.eventType, snap.version, snap.timely ? 1 : 0,
        rawJson).run();
      if (!result?.success || !Number.isFinite(result.meta?.changes))
        return reply(503, "storage_unavailable");
      // For the CVD cohort, only an exact byte-for-byte retry is a duplicate.
      // Preserve the first receipt; reject conflicting retries without overwriting.
      // This is not a persistent conflict ledger.
      if (snap.version === CVD_VERSION && result.meta.changes === 0) {
        const first = await env.TELEMETRY_DB.prepare(
          "SELECT raw_json FROM tv_flow_events WHERE event_key = ?"
        ).bind(snap.key).first();
        if (typeof first?.raw_json !== "string") return reply(503, "storage_unavailable");
        if (first.raw_json !== rawJson) return reply(409, "conflicting_retry");
      }
      return reply(200, result.meta.changes === 0 ? "duplicate" : "accepted", {
        stored: result.meta.changes > 0, timely_for_prospective: snap.timely
      });
    } catch (error) {
      if (error instanceof TooLarge) return reply(413, "too_large");
      if (error instanceof InvalidInput) return reply(422, "invalid_payload");
      // Non esporre DB, token, payload o stack. Il client può riprovare.
      return reply(503, "temporary_failure");
    }
  }
};
