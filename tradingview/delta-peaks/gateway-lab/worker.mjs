// REMURA GATEWAY LAB v0.8.6 (SOLO GITHUB, NO DEPLOY) — aggiornamento 13/11/2026 06:35 CET
// Guard rail prima di D1: binding obbligatorio INGEST_RATE_LIMITER quando ingest è ON.
// Receiver LIVE Cloudflare resta v0.8.5, disabilitato.
// Il deploy è ancora a cura dell'utente: ingest disattivato di default.
// Ricevitore Cloudflare Worker + D1. Fail-closed per configurazione predefinita.
// Ingresso SOLO da TradingView su IP documentati + token segreto nell'URL HTTPS.
// Token MAI nel repository, nel Pine, nel corpo JSON o nei log.

const ALLOWED_IPS = new Set([
  "52.89.214.238", "34.212.75.30", "54.218.53.128", "52.32.178.7"
]);
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

export function validateSnapshot(payload, receivedMs = Date.now()) {
  const p = shape(payload, FIELDS.root, "root");
  ensure(p.schema === "remura.tv.flow.v1" &&
    p.source === "TRADINGVIEW_INTRABAR_ESTIMATE" &&
    p.indicator === "REMURA_ALL_IN_ONE_PREMIUM" &&
    p.version === "0.8.1-lab", "contract");
  ensure(p.event_type === "BAR_EVENT" || p.event_type === "HEARTBEAT",
    "event_type");
  ensure(p.symbol === "FXCM:EURUSD" && p.feed === "FXCM" &&
    p.timeframe === "5", "pilot_feed_or_timeframe");
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
    timely: lagMs >= 0 && lagMs <= MAX_PROSPECTIVE_LAG_MS,
    symbol: p.symbol, timeframe: p.timeframe,
    eventType: p.event_type, barCloseMs: p.bar_close_ms, version: p.version
  };
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
    // Il binding usa una namespace dedicata e un budget configurato a 20/60s;
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
      const snap = validateSnapshot(payload, receivedMs);

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
