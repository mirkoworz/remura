// REMURA Gateway LAB v0.8.22 TEST — aggiornamento 13/11/2026 15:25 CET
// Test di richieste SINTETICHE in Node: non richiedono rete né Cloudflare.
import test from "node:test";
import assert from "node:assert/strict";
import gateway, { validateSnapshot } from "./worker.mjs";

const FAKE_TOKEN = "fakeTestSecretOnly_NotDeployed_ABCDEF0123456789";
const IP = "52.89.214.238";
const URL_BASE = "https://example.invalid/ingest/";

class FakeD1 {
  constructor() { this.rows = new Map(); }
  prepare(sql) {
    return {
      bind: (...params) => ({
        first: async () => {
          assert.match(sql, /^SELECT COUNT/);
          const since = params[0];
          return { n: [...this.rows.values()]
            .filter((r) => r.received_at_ms >= since).length };
        },
        run: async () => {
          assert.match(sql, /^INSERT OR IGNORE/);
          const [key, received_at_ms, bar_close_ms, symbol,
            timeframe, event_type, version, is_timely, raw_json] = params;
          if (this.rows.has(key)) return { success: true, meta: { changes: 0 } };
          this.rows.set(key, {
            received_at_ms, bar_close_ms, symbol, timeframe,
            event_type, version, is_timely, raw_json
          });
          return { success: true, meta: { changes: 1 } };
        }
      })
    };
  }
}

async function env() {
  const digest = await crypto.subtle.digest("SHA-256",
    new TextEncoder().encode(FAKE_TOKEN));
  const hex = [...new Uint8Array(digest)]
    .map((v) => v.toString(16).padStart(2, "0")).join("");
  return { INGEST_ENABLED: "true", WEBHOOK_TOKEN_SHA256: hex,
    TELEMETRY_DB: new FakeD1(),
    INGEST_RATE_LIMITER: {
      calls: 0,
      async limit({ key }) {
        assert.equal(key, "remura-tv-fxcm-eurusd-m5");
        this.calls++;
        return { success: true };
      }
    }
  };
}
function sample(barCloseMs = Date.now() - 5000) {
  return {
    schema: "remura.tv.flow.v1",
    source: "TRADINGVIEW_INTRABAR_ESTIMATE",
    indicator: "REMURA_ALL_IN_ONE_PREMIUM",
    version: "0.8.1-lab",
    event_type: "BAR_EVENT",
    symbol: "FXCM:EURUSD", feed: "FXCM", timeframe: "5",
    bar_open_ms: barCloseMs - 300_000, bar_close_ms: barCloseMs,
    sent_clock_ms: barCloseMs + 1000,
    confirmed: true, realtime: true,
    ohlc: {
      open: 1.110, high: 1.112, low: 1.109,
      close: 1.111, prev_close: 1.110, atr14: 0.0012
    },
    delta_intrabar: 2400, effort: 4.8,
    signed_result_atr: 0.012, efficiency: 0.0025,
    footprint: {
      available: true, buy: 1900, sell: 1650, delta: 250,
      total: 3550, delta_pct: 7.04, poc: 1.111,
      vah: 1.112, val: 1.110, imb_buy_rows: 3, imb_sell_rows: 1
    },
    levels: {
      day1: 1.111, day2: null, day3: null,
      previous_day: null, week: 1.110,
      current_month: 1.109, previous_month: null
    },
    level_scores: { day1: 2400, day2: null, day3: null },
    level_origin_ms: {
      day1: barCloseMs, day2: null, day3: null,
      previous_day: null, week: barCloseMs - 300_000,
      current_month: barCloseMs - 300_000, previous_month: null
    },
    events: {
      peak: true, er_positive: true, er_negative: false,
      day_level_action: "ADDED", day_level_rank: 1,
      evicted_day_price: null, evicted_day_origin_ms: null,
      retest_day1: false, retest_day2: false,
      retest_day3: false, retest_previous_day: false
    },
    quality: {
      bar_closed: true, source_type: "VOLUME_CLASSIFIED_NOT_CME_EXECUTIONS",
      has_intrabar_delta: true, has_footprint: true,
      freshness_ms: 1000, daily_anchor: "HL2", lower_tf: "1"
    }
  };
}
function request(p = sample(), options = {}) {
  const { token = FAKE_TOKEN, ip = IP, type = "application/json",
    body = JSON.stringify(p), url = URL_BASE + token } = options;
  return new Request(url, {
    method: "POST",
    headers: { "content-type": type, "cf-connecting-ip": ip },
    body
  });
}
async function send(e, p, options = {}) {
  const res = await gateway.fetch(request(p, options), e);
  return { status: res.status, body: await res.json() };
}
const expectInvalid = (mutate) => {
  const p = sample(); mutate(p);
  assert.throws(() => validateSnapshot(p));
};

test("health endpoint stays available in disabled mode", async () => {
  const res = await gateway.fetch(new Request("https://example.invalid/health"),
    { INGEST_ENABLED: "false" });
  assert.equal(res.status, 200);
  assert.equal((await res.json()).accepting, false);
});
test("fail-closed enabled missing binding", async () => {
  const { status } = await send({ INGEST_ENABLED: "true" }, sample());
  assert.equal(status, 503);
});
test("fail-closed disabled even if bindings configured", async () => {
  const e = await env(); e.INGEST_ENABLED = "false";
  const { status } = await send(e, sample());
  assert.equal(status, 503);
});
test("health returns accepting=false if limiter is missing with ingest enabled", async () => {
  const e = await env(); delete e.INGEST_RATE_LIMITER;
  const res = await gateway.fetch(new Request("https://example.invalid/health"), e);
  assert.equal((await res.json()).accepting, false);
});
test("health returns accepting=true only with complete configured mock bindings", async () => {
  const e = await env();
  const res = await gateway.fetch(new Request("https://example.invalid/health"), e);
  assert.equal((await res.json()).accepting, true);
});
test("fail-closed no limiter even with enabled ingestion, zero database writes", async () => {
  const e = await env(); delete e.INGEST_RATE_LIMITER;
  const response = await send(e, sample());
  assert.equal(response.status, 503);
  assert.equal(response.body.status, "disabled");
  assert.equal(e.TELEMETRY_DB.rows.size, 0);
});
test("limiter denies authenticated requests before D1 reads and writes", async () => {
  const e = await env();
  e.INGEST_RATE_LIMITER.limit = async () => {
    e.INGEST_RATE_LIMITER.calls++;
    return { success: false };
  };
  const response = await send(e, sample());
  assert.equal(response.status, 429);
  assert.equal(response.body.status, "rate_limited");
  assert.equal(e.TELEMETRY_DB.rows.size, 0);
  assert.equal(e.INGEST_RATE_LIMITER.calls, 1);
});
test("limiter error returns 503 and fails closed without D1 operations", async () => {
  const e = await env();
  e.INGEST_RATE_LIMITER.limit = async () => {
    throw new Error("limiter unavailable");
  };
  const response = await send(e, sample());
  assert.equal(response.status, 503);
  assert.equal(response.body.status, "limiter_unavailable");
  assert.equal(e.TELEMETRY_DB.rows.size, 0);
});
test("bad source IP is rejected without consuming the authenticated limiter", async () => {
  const e = await env();
  const response = await send(e, sample(), { ip: "198.51.100.1" });
  assert.equal(response.status, 403);
  assert.equal(e.INGEST_RATE_LIMITER.calls, 0);
  assert.equal(e.TELEMETRY_DB.rows.size, 0);
});
test("correctly authenticated request hits limiter exactly once", async () => {
  const e = await env();
  const response = await send(e, sample());
  assert.equal(response.status, 200);
  assert.equal(e.INGEST_RATE_LIMITER.calls, 1);
});

test("valid record stored once, not sent downstream", async () => {
  const e = await env();
  const { status, body } = await send(e, sample());
  assert.equal(status, 200);
  assert.equal(body.status, "accepted");
  assert.equal(body.timely_for_prospective, true);
  assert.equal(e.TELEMETRY_DB.rows.size, 1);
  const saved = [...e.TELEMETRY_DB.rows.values()][0];
  assert.equal(JSON.parse(saved.raw_json).symbol, "FXCM:EURUSD");
  assert.equal(saved.is_timely, 1);
  assert.doesNotMatch(saved.raw_json, /fakeTestSecretOnly/);
});
test("idempotent duplicated message", async () => {
  const e = await env();
  const p = sample();
  const a = await send(e, p), b = await send(e, p);
  assert.equal(a.body.status, "accepted");
  assert.equal(b.body.status, "duplicate");
  assert.equal(e.TELEMETRY_DB.rows.size, 1);
});
test("reject wrong source IP", async () => {
  const e = await env();
  assert.equal((await send(e, sample(), { ip: "203.0.113.2" })).status, 403);
});
test("reject wrong secret path", async () => {
  const e = await env();
  assert.equal((await send(e, sample(), {
    token: "notAuthorizedToken__ThatIsAtLeastThirtyTwoChars"
  })).status, 403);
});
test("reject missing content-type", async () => {
  const e = await env();
  assert.equal((await send(e, sample(), { type: "text/plain" })).status, 415);
});
test("reject malformed JSON", async () => {
  const e = await env();
  assert.equal((await send(e, sample(), { body: "{broken" })).status, 422);
});
test("reject huge HTTP body", async () => {
  const e = await env();
  assert.equal((await send(e, sample(), { body: "A".repeat(20001) })).status, 413);
});
test("reject realtime=false or incomplete bar", () => {
  expectInvalid(p => { p.realtime = false; });
  expectInvalid(p => { p.confirmed = false; });
});
test("reject incorrect pilot symbol or version", () => {
  expectInvalid(p => { p.symbol = "CME:6E1!"; });
  expectInvalid(p => { p.version = "0.7"; });
});
test("reject missing/extra field and non-finite number", () => {
  expectInvalid(p => { delete p.quality.daily_anchor; });
  expectInvalid(p => { p.secret = "no"; });
  expectInvalid(p => { p.effort = Infinity; });
});
test("reject level with missing timestamp and score", () => {
  expectInvalid(p => { p.level_origin_ms.day1 = null; });
  expectInvalid(p => { p.level_scores.day1 = null; });
});
test("reject ER without confirmed peak and flags mismatch", () => {
  expectInvalid(p => { p.events.peak = false; });
  expectInvalid(p => { p.event_type = "HEARTBEAT"; });
});
test("valid null footprint is accepted with quality flag", async () => {
  const e = await env(), p = sample();
  for (const k of Object.keys(p.footprint))
    p.footprint[k] = k === "available" ? false : null;
  p.quality.has_footprint = false;
  const out = await send(e, p);
  assert.equal(out.status, 200);
  assert.equal(out.body.status, "accepted");
});
test("late event is preserved but excluded from prospective cohort", async () => {
  const e = await env(), p = sample(Date.now() - 150_000);
  const out = await send(e, p);
  assert.equal(out.status, 200);
  assert.equal(out.body.timely_for_prospective, false);
});
test("bar too far in future or older than 24h rejected", () => {
  expectInvalid(p => { p.bar_close_ms = Date.now() + 300_000; });
  expectInvalid(p => { p.bar_open_ms = Date.now() - 86_400_000 - 300_000;
    p.bar_close_ms = p.bar_open_ms + 300_000; });
});
test("soft per-minute rate gate for 20 saved events", async () => {
  const e = await env();
  const now = Date.now();
  for (let i = 0; i < 20; i++)
    e.TELEMETRY_DB.rows.set("demo-" + i, { received_at_ms: now });
  assert.equal((await send(e, sample())).status, 429);
});
test("wrong route never accepts webhook", async () => {
  const e = await env();
  const out = await gateway.fetch(request(sample(), {
    url: "https://example.invalid/ingest/not-a-valid-path"
  }), e);
  assert.equal(out.status, 404);
});
test("missing database does not pretend success", async () => {
  const e = await env();
  e.TELEMETRY_DB = undefined;
  assert.equal((await send(e, sample())).status, 503);
});

test("rollback OFF closes ingestion before DB, without deleting existing TEST rows", async () => {
  // Synthetic only: simulates emergency kill-switch, NOT a Cloudflare rollback.
  const e = await env();
  const first = sample(Date.now() - 15_000);
  const second = sample(Date.now() - 10_000);
  const accepted = await send(e, first);
  assert.equal(accepted.status, 200);
  assert.equal(e.TELEMETRY_DB.rows.size, 1);
  const firstStored = [...e.TELEMETRY_DB.rows.values()][0];
  const limiterCallsBefore = e.INGEST_RATE_LIMITER.calls;

  e.INGEST_ENABLED = "false";
  const health = await gateway.fetch(
    new Request("https://example.invalid/health"), e);
  assert.equal((await health.json()).accepting, false);
  const blocked = await send(e, second);
  assert.equal(blocked.status, 503);
  assert.equal(blocked.body.status, "disabled");
  assert.equal(e.TELEMETRY_DB.rows.size, 1);
  assert.deepEqual([...e.TELEMETRY_DB.rows.values()][0], firstStored);
  assert.equal(e.INGEST_RATE_LIMITER.calls, limiterCallsBefore);

  // Even if someone accidentally re-enables the flag without a limiter,
  // the worker must fail closed rather than writing a second TEST row.
  e.INGEST_ENABLED = "true";
  delete e.INGEST_RATE_LIMITER;
  const missingLimiter = await send(e, second);
  assert.equal(missingLimiter.status, 503);
  assert.equal(missingLimiter.body.status, "disabled");
  assert.equal(e.TELEMETRY_DB.rows.size, 1);
});

test("isolated TEST Worker can remain OFF with all other bindings configured", async () => {
  const e = await env();
  e.INGEST_ENABLED = "false";
  assert.equal((await send(e, sample())).status, 503);
  assert.equal(e.TELEMETRY_DB.rows.size, 0);
  const health = await gateway.fetch(new Request("https://example.invalid/health"), e);
  assert.equal((await health.json()).accepting, false);
});

test("weekend BTCUSDT transport only: fixed UTC bounds, never FX prospective", () => {
  const start = Date.UTC(2026, 10, 14), end = Date.UTC(2026, 10, 16);
  for (const at of [start, start + 60000, end - 1]) {
    const p = sample(at - 5000);
    p.symbol = "BINANCE:BTCUSDT"; p.feed = "BINANCE";
    const s = validateSnapshot(p, at);
    assert.equal(s.symbol, p.symbol);
    assert.equal(s.timely, false);
    assert.match(s.key, /^BINANCE:BTCUSDT\|/);
  }
  for (const at of [start - 1, end, end + 60000]) {
    const p = sample(at - 5000);
    p.symbol = "BINANCE:BTCUSDT"; p.feed = "BINANCE";
    assert.throws(() => validateSnapshot(p, at), /pilot_feed_or_timeframe/);
    assert.equal(validateSnapshot(sample(at - 5000), at).timely, true);
  }
});
test("BTC weekend still rejects other venues, quote currencies and timeframes", () => {
  const at = Date.UTC(2026, 10, 14, 10);
  for (const [symbol, feed, tf] of [
    ["BINANCE:BTCUSD","BINANCE","5"], ["BINANCE:BTCUSDT.P","BINANCE","5"],
    ["COINBASE:BTCUSDT","COINBASE","5"], ["BINANCE:BTCUSDT","FXCM","5"],
    ["BINANCE:BTCUSDT","BINANCE","1"]]) {
    const p = sample(at - 5000);
    p.symbol = symbol; p.feed = feed; p.timeframe = tf;
    assert.throws(() => validateSnapshot(p, at), /pilot_feed_or_timeframe/);
  }
});
test("BTC authenticated transport stores separate row, no prospective eligibility, dedupes", async () => {
  const at = Date.UTC(2026, 10, 14, 10);
  const originalNow = Date.now;
  Date.now = () => at;
  try {
    const e = await env(), p = sample(at - 5000);
    p.symbol = "BINANCE:BTCUSDT"; p.feed = "BINANCE";
    assert.equal((await send(e,p,{ip:"203.0.113.2"})).status,403);
    const first = await send(e,p), second = await send(e,p);
    assert.equal(first.status,200);
    assert.equal(first.body.timely_for_prospective,false);
    assert.equal(second.body.status,"duplicate");
    assert.equal(e.TELEMETRY_DB.rows.size,1);
    const row = [...e.TELEMETRY_DB.rows.values()][0];
    assert.equal(row.symbol,"BINANCE:BTCUSDT");
    assert.equal(row.is_timely,0);
    assert.equal((await send(e,sample(at - 5000))).status,200);
    assert.equal(e.TELEMETRY_DB.rows.size,2);
    assert.equal(e.INGEST_RATE_LIMITER.calls,3);
  } finally { Date.now = originalNow; }
});
