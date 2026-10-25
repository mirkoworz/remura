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
  exclusionReasons:{market_closed:34,cot_group_conflict:13,cot_no_direction:4},
  exclusions:Array.from({length:34},(_,i)=>({symbol:"XAU"+String(i).padStart(3,"0"),
    reasons:["market_closed",...(i<13?["cot_group_conflict"]:i<17?["cot_no_direction"]:[])]}))
});
test("never confuse first unscanned VPS with zero meaningful events",()=>{
  assert.equal(diagnostics.read(payload(null)).kind,"not_scanned");
  const legacy=payload(null); delete legacy.diagnostics;
  assert.equal(diagnostics.read(legacy).kind,"legacy");
  assert.equal(diagnostics.read(payload(valid())).outcome,"data_insufficient");
  assert.equal(diagnostics.read(payload(valid())).displayOutcome,"market_closed");
  const scan={...valid(),analyzed:34,excluded:0,exclusionReasons:{},exclusions:[],
    outcome:"no_significant_event"};
  const view=diagnostics.read(payload(scan,34));
  assert.equal(view.outcome,"no_significant_event");
  assert.equal(view.displayOutcome,"no_significant_event");
  assert.equal(view.analyzed,34);
  assert.equal(view.baselines,34);
});
test("diagnostics show real rejection reasons without treating them as distinct markets",()=>{
  const view=diagnostics.read(payload(valid(),0,0));
  assert.equal(view.excluded,34);
  assert.equal(view.reasons.reduce((n,r)=>n+r.count,0),51);
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
test("weekend alone is clearly separated from genuine data gaps",()=>{
  const closed=valid();
  assert.equal(diagnostics.read(payload(closed)).displayOutcome,"market_closed");
  const cotMissing=structuredClone(closed);
  cotMissing.exclusionReasons.cot_missing=1;
  cotMissing.exclusions[0].reasons.push("cot_missing");
  assert.equal(diagnostics.read(payload(cotMissing)).displayOutcome,"data_insufficient");
  const barsBroken=structuredClone(closed);
  barsBroken.exclusionReasons.price_error=1;
  barsBroken.exclusions[0].reasons.push("price_error");
  assert.equal(diagnostics.read(payload(barsBroken)).displayOutcome,"data_insufficient");
  const unknown=structuredClone(closed);
  unknown.exclusionReasons.unrecognized_error=1;
  unknown.exclusions[0].reasons.push("unrecognized_error");
  assert.equal(diagnostics.read(payload(unknown)).displayOutcome,"data_insufficient");
});
test("open or mixed markets cannot be reported as wholly closed",()=>{
  const mixed=valid();
  mixed.analyzed=1;
  mixed.excluded=33;
  mixed.exclusions.pop();
  assert.equal(diagnostics.read(payload(mixed)).displayOutcome,"data_insufficient");
  const notClosed=valid();
  notClosed.exclusions[0].reasons=["cot_group_conflict"];
  assert.equal(diagnostics.read(payload(notClosed)).displayOutcome,"data_insufficient");
  const clean=valid();
  clean.analyzed=34;
  clean.excluded=0;
  clean.exclusions=[];
  clean.exclusionReasons={};
  clean.outcome="no_significant_event";
  assert.equal(diagnostics.read(payload(clean)).displayOutcome,"no_significant_event");
});
test("Radar Squali wires only private endpoint and same-origin script",()=>{
  const html=fs.readFileSync("mercati.html","utf8");
  assert.ok(html.includes('id="monitor-diagnostics"'));
  assert.ok(html.includes('squalincome-diagnostics.js?v=135'));
  assert.ok(html.includes("./private-api/signals/status"));
});
