// REMURA Gateway LAB v0.8.22 TEST — aggiornamento 13/11/2026 15:25 CET
// Test di richieste SINTETICHE in Node: non richiedono rete né Cloudflare.
import test from "node:test";
import assert from "node:assert/strict";
import gateway, { validateSnapshot, validateCvdEnvelope, CVD_CONFIG, CVD_SCHEMA } from "./worker_cvd_candidate.mjs";

const FAKE_TOKEN = "fakeTestSecretOnly_NotDeployed_ABCDEF0123456789";
const IP = "52.89.214.238";
const URL_BASE = "https://example.invalid/ingest/";

class FakeD1 {
  constructor() { this.rows = new Map(); }
  prepare(sql) {
    return {
      bind: (...params) => ({
        first: async () => {
          if (sql.startsWith("SELECT raw_json")) return this.rows.get(params[0]) ?? null;
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


const T=Math.floor((Date.now()-5000)/300000)*300000;
function cvd(t=T) {
 const snapshot=sample(t);
 Object.assign(snapshot,{schema:"remura.tv.flow.cvd.snapshot.preview.v1",version:"0.9.1-cvd-lab",symbol:"FX:EURUSD",feed:"FX"});
 return {schema:CVD_SCHEMA,snapshot,configuration:{...CVD_CONFIG},cvd:{
 model:"D08_SEGMENT_PORT_V091",intrabar_count:5,complete:true,continuous:true,day_valid:true,
 segment_id:1,segment_bars:12,day_key_ms:t-12*300000,raw_delta:2400,trusted_delta:2400,
 daily_cvd:3000,segment_cvd:2800,eligible:true,price_bull:true,price_bear:false,
 cvd_bull:true,cvd_bear:false,pivot_close_ms:t-600000}};
}
test("explicit opt-in required, legacy unchanged",async()=>{
 const e=await env();
 assert.equal((await send(e,cvd())).body.status,"cvd_preview_disabled");
 assert.equal(e.TELEMETRY_DB.rows.size,0);
 assert.equal((await send(e,sample())).body.status,"accepted");
});
test("new schema accepted separately, never research timely",()=>{
 const p=cvd();
 const s=validateCvdEnvelope(p,T+5000);
 assert.equal(s.symbol,"FX:EURUSD");
 assert.equal(s.key,"FX:EURUSD|5|"+T+"|0.9.1-cvd-lab");
 assert.equal(s.timely,false);
 assert.equal(s.transportTimely,true);
 assert.throws(()=>validateSnapshot({...sample(T),symbol:"FX:EURUSD",feed:"FX"},T+5000));
});
test("reject malformed config, feed, pivot clock, late, incomplete",()=>{
 for(const mutate of [
  p=>p.configuration.cvd_left=3,p=>p.snapshot.symbol="FXCM:EURUSD",
  p=>p.cvd.pivot_close_ms=T,p=>p.cvd.price_bull=false,
  p=>p.cvd.trusted_delta=0,p=>p.cvd.complete=false,
  p=>p.cvd.day_key_ms=T+1,p=>p.extra=true
 ]){
  const p=cvd();mutate(p);assert.throws(()=>validateCvdEnvelope(p,T+5000));
 }
 assert.throws(()=>validateCvdEnvelope(cvd(),T+120001));
});
test("incomplete CVD stays null",()=>{
 const p=cvd();
 Object.assign(p.cvd,{intrabar_count:4,complete:false,continuous:null,day_valid:false,
 segment_bars:0,raw_delta:null,trusted_delta:null,daily_cvd:null,segment_cvd:null,
 eligible:false,price_bull:false,cvd_bull:false,pivot_close_ms:null});
 assert.equal(validateCvdEnvelope(p,T+5000).timely,false);
});
test("HTTP authenticated CVD stores once and retains schema, distinct from legacy",async()=>{
 const real=Date.now;
 Date.now=()=>T+5000;
 try {
  const e=await env();e.CVD_PREVIEW_ENABLED="true";
  assert.equal((await send(e,cvd())).body.status,"accepted");
  assert.equal((await send(e,cvd())).body.status,"duplicate");
  assert.equal(e.TELEMETRY_DB.rows.size,1);
  const row=[...e.TELEMETRY_DB.rows.values()][0];
  assert.equal(row.is_timely,0);
  assert.equal(JSON.parse(row.raw_json).schema,CVD_SCHEMA);
  const other=cvd();other.cvd.segment_cvd=123;
  assert.equal((await send(e,other)).status,409);
  assert.equal(JSON.parse(row.raw_json).cvd.segment_cvd,2800);
  assert.equal((await send(e,sample(T))).body.status,"accepted");
  assert.equal(e.TELEMETRY_DB.rows.size,2);
 } finally {Date.now=real;}
});
test("authentication and limit remain before storage",async()=>{
 const e=await env();e.CVD_PREVIEW_ENABLED="true";
 assert.equal((await send(e,cvd(),{ip:"203.0.113.2"})).status,403);
 assert.equal(e.INGEST_RATE_LIMITER.calls,0);
 e.INGEST_RATE_LIMITER.limit=async()=>({success:false});
 assert.equal((await send(e,cvd())).status,429);
 assert.equal(e.TELEMETRY_DB.rows.size,0);
});
