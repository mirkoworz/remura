// REMURA v0.8.16 — 13/11/2026, ore 13:11 CET
// 100% OFFLINE synthetic webhook -> fake D1 -> JSONL feed; no network or secrets.
import assert from "node:assert/strict";
import gateway from "./worker.mjs";

const FAKE_TOKEN = "REMURA_OFFLINE_ONLY_synthetic_token_0123456789ABCD";
const TRUSTED_IP = "52.89.214.238";

class FakeD1 {
  constructor() { this.rows = new Map(); this.reads = 0; this.writes = 0; }
  prepare(sql) {
    assert.ok(sql.startsWith("SELECT COUNT(*)") || sql.startsWith("INSERT OR IGNORE"));
    return {
      bind: (...params) => ({
        first: async () => {
          this.reads++;
          const cutoff = params[0];
          return { n: [...this.rows.values()].filter(
            r => r.received_at_ms >= cutoff).length };
        },
        run: async () => {
          this.writes++;
          const [event_key, received_at_ms, bar_close_ms, symbol,
            timeframe, event_type, version, is_timely, raw_json] = params;
          if (this.rows.has(event_key)) return { success: true, meta: { changes: 0 } };
          this.rows.set(event_key, {
            event_key, received_at_ms, bar_close_ms, symbol, timeframe,
            event_type, version, is_timely, raw_json,
          });
          return { success: true, meta: { changes: 1 } };
        },
      }),
    };
  }
}

function snapshot(t, heartbeat = false) {
  return {
    schema: "remura.tv.flow.v1",
    source: "TRADINGVIEW_INTRABAR_ESTIMATE",
    indicator: "REMURA_ALL_IN_ONE_PREMIUM",
    version: "0.8.1-lab",
    event_type: heartbeat ? "HEARTBEAT" : "BAR_EVENT",
    symbol: "FXCM:EURUSD", feed: "FXCM", timeframe: "5",
    bar_open_ms: t - 300_000, bar_close_ms: t,
    sent_clock_ms: t + 1000, confirmed: true, realtime: true,
    ohlc: { open: 1.1100, high: 1.1120, low: 1.1090,
      close: 1.1110, prev_close: 1.1100, atr14: 0.0012 },
    delta_intrabar: 2400, effort: 4.8, signed_result_atr: 0.012,
    efficiency: 0.0025,
    footprint: { available: true, buy: 1900, sell: 1650, delta: 250,
      total: 3550, delta_pct: 7.04, poc: 1.111,
      vah: 1.112, val: 1.110, imb_buy_rows: 3, imb_sell_rows: 1 },
    levels: { day1: 1.111, day2: null, day3: null, previous_day: null,
      week: 1.110, current_month: 1.109, previous_month: null },
    level_scores: { day1: 2400, day2: null, day3: null },
    level_origin_ms: { day1: t, day2: null, day3: null,
      previous_day: null, week: t - 300_000, current_month: t - 300_000,
      previous_month: null },
    events: { peak: !heartbeat, er_positive: !heartbeat, er_negative: false,
      day_level_action: heartbeat ? "NONE" : "ADDED",
      day_level_rank: heartbeat ? null : 1, evicted_day_price: null,
      evicted_day_origin_ms: null, retest_day1: false, retest_day2: false,
      retest_day3: false, retest_previous_day: false },
    quality: { bar_closed: true, source_type: "VOLUME_CLASSIFIED_NOT_CME_EXECUTIONS",
      has_intrabar_delta: true, has_footprint: true, freshness_ms: 1000,
      daily_anchor: "HL2", lower_tf: "1" },
  };
}

async function send(env, payload, { ip = TRUSTED_IP, token = FAKE_TOKEN } = {}) {
  const request = new Request(
    "https://example.invalid/ingest/" + token, {
      method: "POST",
      headers: { "content-type": "application/json", "cf-connecting-ip": ip },
      body: JSON.stringify(payload),
    });
  const response = await gateway.fetch(request, env);
  return { code: response.status, body: await response.json() };
}

async function run() {
  const d1 = new FakeD1();
  const digest = new Uint8Array(await crypto.subtle.digest(
    "SHA-256", new TextEncoder().encode(FAKE_TOKEN)));
  const hex = [...digest].map(n => n.toString(16).padStart(2, "0")).join("");
  const env = { INGEST_ENABLED: "true", TELEMETRY_DB: d1,
    WEBHOOK_TOKEN_SHA256: hex, INGEST_RATE_LIMITER: {
      async limit() { return { success: true }; },
    } };
  const now = Date.now();
  const p = snapshot(now - 7000);
  assert.equal((await send(env, p, { ip: "203.0.113.9" })).code, 403);
  assert.equal(d1.rows.size, 0);
  assert.equal((await send(env, p, { token: "FAKE_DIFFERENT_01234567890123456789012345" })).code, 403);
  assert.equal(d1.rows.size, 0);
  const a = await send(env, p);
  assert.equal(a.code, 200);
  assert.equal(a.body.status, "accepted");
  const dup = await send(env, p);
  assert.equal(dup.body.status, "duplicate");
  const late = await send(env, snapshot(now - 150_000));
  assert.equal(late.body.status, "accepted");
  assert.equal(late.body.timely_for_prospective, false);
  const heartbeat = await send(env, snapshot(now - 30_000, true));
  assert.equal(heartbeat.body.status, "accepted");
  assert.equal(d1.rows.size, 3);
  const rows = [...d1.rows.values()];
  // Print ONLY synthetic D1 rows, never a token, network information, or env.
  process.stdout.write(JSON.stringify({
    mode: "SYNTHETIC_LOCAL_NODE_WORKER_FAKE_D1",
    record_count: rows.length,
    duplicate_stored: dup.body.stored,
    invalid_ip_rejected: true,
    rows,
  }) + "\n");
}

await run();
