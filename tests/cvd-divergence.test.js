/* Offline causal CVD divergence tests; no network, broker, orders or notifications. */
"use strict";
const assert=require("node:assert/strict");
const test=require("node:test");
const core=require("../price-core.js");
const detector=require("../cvd-divergence-core.js");
const START=Date.parse("2026-11-02T00:00:00Z"),STEP=900000;
function make(side="bull",len=45,vol=100){
  const rows=[];
  for(let i=0;i<len;i++){
    const bull=side==="bull";
    let h=bull?11.2:11.2,l=bull?10.4:10.0;
    if(i===10){if(bull)l=10.0;else h=11.6;}
    if(i===22){if(bull)l=9.7;else h=11.95;}
    rows.push({t:START+i*STEP,o:bull?10.8:10.5,h,l,c:bull?11.0:10.2,v:vol});
  }
  return {symbol:"EURUSD",provider:"ctrader",providerSymbol:"EURUSD-id-1",
    frames:{M15:rows,H1:[],H4:[]}};
}
function now(market,minutes=1){
  const rows=market.frames.M15;
  return rows[rows.length-1].t+STEP+minutes*60000;
}
test("a double price low with higher proxy CVD produces bullish regular event",()=>{
  const m=make(),res=detector.analyze(m,{now:now(m)});
  assert.equal(res.status,"ok");
  assert.equal(res.events.length,1);
  const event=res.events[0];
  assert.equal(event.type,"bullish_regular");
  assert.ok(event.second.price<event.first.price);
  assert.ok(event.second.cvdProxy>event.first.cvdProxy);
  assert.equal(event.first.pivotAt,"2026-11-02T02:30:00.000Z");
  assert.equal(event.second.pivotAt,"2026-11-02T05:30:00.000Z");
  assert.equal(event.confirmedAt,"2026-11-02T06:15:00.000Z");
  assert.equal(event.state,"confirmed_technical_not_trade_signal");
  assert.equal(res.notificationEnabled,false);
  // The detector reuses EXACTLY the CVD series displayed by the current UI.
  const chart=core.flow(m,{now:now(m)});
  assert.equal(event.first.cvdProxy,chart.points[10].cvd);
  assert.equal(event.second.cvdProxy,chart.points[22].cvd);
});
test("higher price high with lower CVD is bearish regular",()=>{
  const m=make("bear"),r=detector.analyze(m,{now:now(m)});
  assert.equal(r.status,"ok");
  assert.equal(r.events.length,1);
  assert.equal(r.events[0].type,"bearish_regular");
  assert.ok(r.events[0].first.price<r.events[0].second.price);
  assert.ok(r.events[0].first.cvdProxy>r.events[0].second.cvdProxy);
});
test("right-side confirmation is causal: no premature alert, stable event ID",()=>{
  const m=make(),before={...m,frames:{...m.frames,M15:m.frames.M15.slice(0,24)}};
  assert.equal(detector.analyze(before,{now:now(before)}).events.length,0);
  const confirmed={...m,frames:{...m.frames,M15:m.frames.M15.slice(0,25)}};
  const atConfirmation=detector.analyze(confirmed,{now:now(confirmed)});
  assert.equal(atConfirmation.events.length,1);
  const later=detector.analyze(m,{now:now(m)});
  assert.equal(atConfirmation.events[0].id,later.events[0].id);
  assert.deepEqual(atConfirmation.events[0],later.events[0]);
  assert.ok(Date.parse(atConfirmation.events[0].confirmedAt)<=now(confirmed));
});
test("zero ticks and neutral CLV cannot create fake diverging pressure",()=>{
  let m=make("bull",45,0);
  assert.equal(detector.analyze(m,{now:now(m)}).events.length,0);
  m=make();
  for(const row of m.frames.M15)row.c=(row.h+row.l)/2;
  assert.equal(detector.analyze(m,{now:now(m)}).events.length,0);
});
test("missing or negative tick volume fails closed; no signals",()=>{
  let m=make();
  delete m.frames.M15[5].v;
  let x=detector.analyze(m,{now:now(m)});
  assert.equal(x.status,"missing");
  assert.deepEqual(x.events,[]);
  m=make();
  m.frames.M15[2].v=-1;
  assert.equal(detector.analyze(m,{now:now(m)}).status,"missing");
});
test("gaps and missing midnight UTC prohibit invented continuous CVD",()=>{
  let m=make();
  m.frames.M15.splice(8,1);
  let r=detector.analyze(m,{now:now(m)});
  assert.equal(r.status,"partial");
  assert.deepEqual(r.events,[]);
  m=make();
  m.frames.M15.shift();
  r=detector.analyze(m,{now:now(m)});
  assert.equal(r.status,"partial");
});
test("stale, invalid timestamps and still-open M15 never emit signals",()=>{
  let m=make();
  assert.equal(detector.analyze(m,{now:now(m,91)}).status,"stale");
  m=make();
  m.frames.M15[12].t=m.frames.M15[11].t;
  assert.equal(detector.analyze(m,{now:now(m)}).status,"invalid");
  m=make();
  assert.equal(detector.analyze(m,{now:m.frames.M15.at(-1).t+STEP-1000}).status,"invalid");
});
test("only pilot ctrader and identifiable provider are allowed",()=>{
  let m=make();
  assert.equal(detector.analyze({...m,symbol:"USOIL"},{now:now(m)}).status,"unsupported");
  assert.equal(detector.analyze({...m,provider:"csv"},{now:now(m)}).status,"missing");
  assert.equal(detector.analyze({...m,providerSymbol:""},{now:now(m)}).status,"missing");
});
test("one day UTC session reset never compares pivots to prior day",()=>{
  const m=make();
  const day2=[];
  for(let i=0;i<8;i++)day2.push({...m.frames.M15[i],t:START+86400000+i*STEP});
  m.frames.M15.push(...day2);
  const r=detector.analyze(m,{now:now(m)});
  assert.equal(r.status,"insufficient"); // Eight contiguous M15, but insufficient ATR.
  assert.equal(r.events.length,0);
});
test("pivot plateau ties are rejected and threshold suppresses noise",()=>{
  const m=make();
  m.frames.M15[11].l=m.frames.M15[10].l;
  assert.equal(detector.analyze(m,{now:now(m)}).events.length,0);
  const n=make();
  assert.equal(detector.analyze(n,{now:now(n),settings:{minCvdFraction:.99}}).events.length,0);
  assert.throws(()=>detector.parameters({right:0}),/Parametro non valido/);
  assert.throws(()=>detector.parameters({minCvdFraction:-1}),/Tolleranza/);
});
test("detector does not fetch, mutate input or persist anything",()=>{
  const m=make(),before=JSON.stringify(m);
  const r=detector.analyze(m,{now:now(m)});
  assert.equal(JSON.stringify(m),before);
  assert.equal(r.persistenceEnabled,false);
  assert.equal(r.method.includes("proxy"),true);
  assert.equal(typeof r.events[0].id,"string");
  const duplicate=detector.analyze(m,{now:now(m)});
  assert.equal(duplicate.events[0].id,r.events[0].id);
});
