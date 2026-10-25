const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
require("../squalincome-diagnostics.js");
const diagnostics=globalThis.REMURA_SQUAL_DIAGNOSTICS;
const payload=(d,baselines=0,eventsTotal=0)=>({
  schema:"remura-squalincome-monitor-v1",enabled:true,baselines,eventsTotal,
  lastEvents:[],diagnostics:d
});
const valid=()=>({
  lastScanAt:"2026-10-25T08:26:00+00:00",trackedMarkets:34,analyzed:0,excluded:34,
  outcome:"data_insufficient",newBaselines:0,newEvents:0,
  exclusionReasons:{market_closed:34,cot_stale:2},
  exclusions:Array.from({length:34},(_,i)=>({symbol:"XAU"+String(i).padStart(3,"0"),
    reasons:["market_closed"]}))
});
test("never confuse first unscanned VPS with zero meaningful events",()=>{
  assert.equal(diagnostics.read(payload(null)).kind,"not_scanned");
  assert.equal(diagnostics.read(payload(valid())).outcome,"data_insufficient");
  const scan={...valid(),analyzed:34,excluded:0,exclusionReasons:{},exclusions:[],
    outcome:"no_significant_event"};
  const view=diagnostics.read(payload(scan,34));
  assert.equal(view.outcome,"no_significant_event");
  assert.equal(view.analyzed,34);
  assert.equal(view.baselines,34);
});
test("diagnostics show real rejection reasons without treating them as distinct markets",()=>{
  const view=diagnostics.read(payload(valid(),0,0));
  assert.equal(view.excluded,34);
  assert.equal(view.reasons.reduce((n,r)=>n+r.count,0),36);
  assert.equal(view.reasons[0].code,"market_closed");
  assert.ok(view.date.includes("25/10/2026"));
  assert.equal(view.exclusions.length,34);
});
test("reject inconsistent counters and unknown schema rather than guessing",()=>{
  assert.equal(diagnostics.read(payload({...valid(),analyzed:1})).kind,"invalid");
  assert.equal(diagnostics.read({...payload(valid()),schema:"unknown"}),null);
});
test("only whitelisted codes are displayed, never leak diagnostic free text",()=>{
  const scan=valid();
  scan.exclusionReasons={scan_error:1,secret_api_token:15};
  scan.exclusions=[...scan.exclusions.slice(0,33),{symbol:"EURUSD",reasons:["scan_error","secret_api_token"]}];
  const view=diagnostics.read(payload(scan));
  assert.equal(view.reasons.length,1);
  assert.equal(view.exclusions.at(-1).labels.length,1);
  assert.ok(!JSON.stringify(view).includes("secret_api_token"));
});
test("Radar Squali wires only private endpoint and same-origin script",()=>{
  const html=fs.readFileSync("mercati.html","utf8");
  assert.ok(html.includes('id="monitor-diagnostics"'));
  assert.ok(html.includes('squalincome-diagnostics.js?v=134'));
  assert.ok(html.includes("./private-api/signals/status"));
});
