const test=require("node:test");
const assert=require("node:assert/strict");
const core=require("../price-core.js");
const start=Date.parse("2026-10-01T00:00:00Z");
const duration=900000;
function series(n=1400,{step=0.00004}={}){
  return Array.from({length:n},(_,i)=>{
    const c=1.1+i*step;
    return {t:new Date(start+i*duration).toISOString(),o:c-0.00002,h:c+0.00012,l:c-0.00011,c};
  });
}
function bundle(candles=series(),symbol="EURUSD"){
  // H1/H4 samples do not need interpolation: this is synthetic test fixture only.
  function group(count){
    const out=[];
    for(let i=0;i+count<=candles.length;i+=count){
      const a=candles.slice(i,i+count);
      out.push({t:a[0].t,o:a[0].o,h:Math.max(...a.map(x=>x.h)),l:Math.min(...a.map(x=>x.l)),c:a[a.length-1].c});
    }
    return out;
  }
  return {schema:"remura-price-v1",generatedAt:"2026-10-17T08:00:00Z",
    markets:{[symbol]:{symbol,provider:"csv",providerSymbol:"local",timeframes:{M15:candles,H1:group(4),H4:group(16)}}}};
}
const now=Date.parse("2026-10-17T08:00:00Z");
test("imports normalized, closed OHLC for one selected market",()=>{
  const m=core.load(bundle(), "EURUSD", {now});
  assert.equal(m.frames.M15.length,1400);
  assert.equal(m.frames.H4.length,87);
  assert.equal(m.symbol,"EURUSD");
});
test("refuses missing symbol and malformed/future OHLC bars",()=>{
  assert.throws(()=>core.load(bundle(),"XAUUSD",{now}),/non contiene/);
  const future=bundle();
  future.markets.EURUSD.timeframes.H1[0].t="2026-12-01T00:00:00Z";
  assert.throws(()=>core.load(future,"EURUSD",{now}),/Timestamps/);
  const impossible=bundle();
  impossible.markets.EURUSD.timeframes.M15[1].h=1.0;
  assert.throws(()=>core.load(impossible,"EURUSD",{now}),/OHLC/);
});
test("indicator works on closed coherent trend data with fresh timestamp",()=>{
  const candles=series(1450,{step:0.00004});
  const data=bundle(candles);
  // Fixture last date: 16 Oct => near the 17 Oct Saturday; no invented quote.
  const market=core.load(data,"EURUSD",{now});
  const analysis=core.analyze(market,{now});
  assert.ok(["neutral","watch","partial","confirmed"].includes(analysis.state));
  assert.equal(analysis.metrics.M15.trend,1);
  assert.equal(analysis.metrics.H4.trend,1);
  assert.ok(Number.isFinite(analysis.metrics.H4.support));
});
test("future timestamps after export are rejected",()=>{
  const b=bundle();
  b.generatedAt="2028-01-01T00:00:00Z";
  assert.throws(()=>core.load(b,"EURUSD",{now}),/futuro/);
});
test("missing H4 observations prevent a composite signal",()=>{
  const b=bundle();
  b.markets.EURUSD.timeframes.H4=[];
  const p=core.analyze(core.load(b,"EURUSD",{now}),{now});
  assert.equal(p.state,"unavailable");
  assert.equal(p.side,0);
});
test("stale candles invalidate the interpretation",()=>{
  const p=core.analyze(core.load(bundle(),"EURUSD",{now}),{now:Date.parse("2026-11-15T08:00:00Z")});
  assert.equal(p.state,"unavailable");
});
test("retail cannot turn missing COT into price confirmation",()=>{
  const p={state:"confirmed",side:-1};
  const retail={valid:true,skew:1};
  assert.equal(core.cross(p,null,retail).state,"monitor");
  assert.equal(core.cross(p,{state:"stale",bias:-1,stale:true},retail).state,"monitor");
});
test("opposing COT and price directions report conflict",()=>{
  const p={state:"confirmed",side:1};
  const cot={state:"trend",bias:-1,stale:false};
  assert.equal(core.cross(p,cot,null).state,"conflict");
});
test("aligned COT, price and retail remain a context, not a trading order",()=>{
  const p={state:"confirmed",side:1};
  const cot={state:"trend",bias:1,stale:false};
  const retail={valid:true,skew:-1};
  const out=core.cross(p,cot,retail);
  assert.equal(out.state,"context");
  assert.match(out.text,/Non è una probabilità/);
});

// Run the integrated multi-source verdict regression suite in existing price CI.
require("./squalo-verdict.test.js");
