const test=require("node:test");
const assert=require("node:assert/strict");
require("../squalincome-freshness-core.js");
const policy=globalThis.REMURA_SQUAL_FRESHNESS;
const scanned="2026-11-03T09:19:07Z";
const frame=t=>({bars:100,lastClosedAt:t});
function data(){
  return {
    scanAt:scanned,observedAt:scanned,
    priceQuality:{integrity:"verified",freshness:"recent",ready:true,checkedAt:scanned},
    frames:{M15:frame("2026-11-03T09:00:00Z"),
            H1:frame("2026-11-03T09:00:00Z"),
            H4:frame("2026-11-03T08:00:00Z")}
  };
}
function staleData(){
  const record=data();
  record.frames={
    M15:frame("2026-11-03T07:30:00Z"),
    H1:frame("2026-11-03T07:00:00Z"),
    H4:frame("2026-11-03T04:00:00Z")
  };
  return record;
}
function verifiedBatch(){
  return {provenance:"server_collector_schedule",state:"running",lastOutcome:"ok",
    lastSuccessfulCollectionAt:"2026-11-03T07:31:00Z",
    nextExpectedAt:"2026-11-03T09:31:00Z"};
}

test("all verified and original 180/120/300 thresholds classify price only",()=>{
  const r=policy.evaluate(data());
  assert.equal(r.state,policy.STATES.LIVE);
  assert.equal(r.livePriceEligible,true);
  assert.equal(r.signalAuthorized,false);
  assert.deepEqual(r.overdue,[]);
  assert.deepEqual(policy.LIMITS,{M15:180,H1:120,H4:300});
});
test("real #31 109/139/319 pattern is stale even when M15 is recent",()=>{
  const r=policy.evaluate(staleData());
  assert.equal(r.state,policy.STATES.STALE);
  assert.equal(r.livePriceEligible,false);
  assert.equal(r.signalAuthorized,false);
  assert.deepEqual(r.overdue,["H1","H4"]);
  assert.ok(r.ageMinutes.M15>109 && r.ageMinutes.M15<110);
  assert.ok(r.ageMinutes.H1>139 && r.ageMinutes.H1<140);
});
test("waiting requires server-attested next batch AND never authorizes a signal",()=>{
  const d=staleData();
  d.batch=verifiedBatch();
  const r=policy.evaluate(d);
  assert.equal(r.state,policy.STATES.WAIT);
  assert.equal(r.livePriceEligible,false);
  assert.equal(r.signalAuthorized,false);
  assert.deepEqual(r.overdue,["H1","H4"]);
});
test("inferred/failed/late/too-distant batch cannot masquerade as a verified wait",()=>{
  const mutations=[
    {provenance:"inferred_from_average"},
    {state:"idle"},
    {lastOutcome:"request_failed"},
    {nextExpectedAt:"2026-11-03T09:00:00Z"},
    {nextExpectedAt:"2026-11-03T10:15:00Z"},
    {lastSuccessfulCollectionAt:"2026-11-03T07:00:00Z"},
    {lastSuccessfulCollectionAt:"2026-11-03T10:00:00Z"},
    {nextExpectedAt:"PRIVATE_NEXT_TIME"},
  ];
  for(const patch of mutations){
    const d=staleData(); d.batch={...verifiedBatch(),...patch};
    assert.equal(policy.evaluate(d).state,policy.STATES.STALE,JSON.stringify(patch));
  }
});
test("bad quality, closed market and insufficient OHLC fail closed",()=>{
  const patches=[
    {integrity:"partial"},{integrity:"invalid"},{integrity:"missing"},
    {freshness:"weekend"},{freshness:"stale"},{ready:false},
    {checkedAt:"2026-11-03T09:17:00Z"},
    {checkedAt:"2026-11-03T09:19:08Z"},
    {checkedAt:"2026-11-03T09:30:00Z"},
  ];
  for(const patch of patches){
    const d=data();d.priceQuality={...d.priceQuality,...patch};
    assert.equal(policy.evaluate(d).state,policy.STATES.UNKNOWN,JSON.stringify(patch));
  }
  for(const key of ["M15","H1","H4"]){
    const d=data();d.frames[key].bars=54;
    assert.equal(policy.evaluate(d).state,policy.STATES.UNKNOWN);
  }
});
test("old, future, malformed or naive snapshot timestamps never authorize live",()=>{
  for(const patch of [
    {observedAt:"2026-11-03T09:40:00Z"},
    {observedAt:"2026-11-03T09:00:00Z"},
    {scanAt:"PRIVATE_SCAN"},
    {scanAt:"2026-11-03T09:19:07"},
    {observedAt:"2026-11-03T09:19:07"},
    {observedAt:"2026-11-03T09:19:07+99:99"}
  ]){
    const d={...data(),...patch};
    const r=policy.evaluate(d);
    assert.equal(r.state,policy.STATES.UNKNOWN,JSON.stringify(patch));
    assert.equal(r.livePriceEligible,false);
    assert.equal(r.signalAuthorized,false);
    assert.ok(!JSON.stringify(r).includes("PRIVATE"));
  }
});
test("future/unaligned/absent M15 H1 H4 bars fail closed without estimating closes",()=>{
  const variants=[
    ["M15","2026-11-03T09:20:00Z"],
    ["M15","2026-11-03T09:15:01Z"],
    ["H1","2026-11-03T09:15:00Z"],
    ["H4","2026-11-03T08:01:00Z"],
    ["H4","BAD_BROKER_SECRET"]
  ];
  for(const [key,value] of variants){
    const d=data();d.frames[key].lastClosedAt=value;
    assert.equal(policy.evaluate(d).state,policy.STATES.UNKNOWN);
    assert.equal(policy.evaluate(d).signalAuthorized,false);
  }
  const d=data();delete d.frames.H4;
  assert.equal(policy.evaluate(d).state,policy.STATES.UNKNOWN);
});
test("exact H1 gate equality passes, but a one-second overrun blocks live",()=>{
  // At 10:00 UTC, H1 is exactly 120 minutes old, others still valid.
  const d=data();
  d.scanAt="2026-11-03T10:00:00Z";d.observedAt=d.scanAt;
  d.priceQuality.checkedAt=d.scanAt;
  d.frames={M15:frame("2026-11-03T09:00:00Z"),
            H1:frame("2026-11-03T08:00:00Z"),
            H4:frame("2026-11-03T08:00:00Z")};
  assert.equal(policy.evaluate(d).state,policy.STATES.LIVE);
  d.observedAt="2026-11-03T10:00:01Z";
  assert.equal(policy.evaluate(d).state,policy.STATES.STALE);
  assert.deepEqual(policy.evaluate(d).overdue,["H1"]);
});
test("a later H1 or H4 than the available M15 cannot be called live",()=>{
  const d=data();
  d.frames.M15.lastClosedAt="2026-11-03T08:15:00Z";
  assert.equal(policy.evaluate(d).state,policy.STATES.UNKNOWN);
  const d2=data();
  d2.frames.H1.lastClosedAt="2026-11-03T07:00:00Z";
  assert.equal(policy.evaluate(d2).state,policy.STATES.UNKNOWN);
});
test("source-backed pure classifier never calls fetch or mutates input",()=>{
  const d=staleData();d.batch=verifiedBatch();
  const input=structuredClone(d);
  const before=JSON.stringify(d);
  const oldFetch=globalThis.fetch;
  globalThis.fetch=()=>{throw Error("UNEXPECTED_NETWORK");};
  try{
    const result=policy.evaluate(input);
    assert.equal(result.state,policy.STATES.WAIT);
    assert.equal(JSON.stringify(input),before);
    assert.equal(result.signalAuthorized,false);
  }finally{
    globalThis.fetch=oldFetch;
  }
});
