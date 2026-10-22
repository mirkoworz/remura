const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const core=require("../sentiment-trend-core.js");
const now=Date.parse("2026-10-22T12:00:00Z");
const at=h=>new Date(now-h*3600000).toISOString();
const row=(h,l,lots=null,shortLots=null)=>({
 t:at(h),lPct:l,sPct:100-l,...(lots===null?{}:{lLots:lots,sLots:shortLots})
});
test("24h compares real sample near 24h ago, not the previous tick",()=>{
 const history=[row(25,78,1000,200),row(4,75,900,300)];
 const result=core.analyze(history,row(1,69,650,550),"24h",now);
 assert.equal(result.available,true);
 assert.equal(result.direction,"short");
 assert.equal(result.deltaLong,-9);
 assert.equal(result.deltaShort,9);
 assert.equal(result.deltaLongLots,-350);
 assert.equal(result.elapsedHours,24);
 assert.equal(result.samples,3);
 assert.equal(result.stale,false);
 assert.match(result.headline,/verso SHORT/);
});
test("crossing the majority threshold is different from just reducing longs",()=>{
 const r=core.analyze([row(25,53)],row(1,45),"24h",now);
 assert.match(r.headline,/maggioranza LONG a SHORT/);
 const weak=core.analyze([row(25,80)],row(1,75),"24h",now);
 assert.doesNotMatch(weak.headline,/maggioranza LONG a SHORT/);
});
test("refuses undersampled windows and does not fabricate intermediate values",()=>{
 const r=core.analyze([row(9,70),row(3,60)],row(1,50),"24h",now);
 assert.equal(r.available,false);
 assert.equal(r.samples,3);
 assert.equal(core.analyze([row(30,80)],row(1,75),"24h",now).available,false);
});
test("stale feed or small community blocks common directional verdict",()=>{
 const stale=core.analyze([row(32,70)],row(8,60),"24h",now);
 const fresh=core.analyze([row(25,70)],row(1,60),"24h",now);
 assert.equal(stale.stale,true);
 assert.match(core.joint(stale,fresh),/datata/);
 const low=core.analyze([{...row(25,70),lPos:9,sPos:8}],
  {...row(1,60),lPos:9,sPos:8},"24h",now);
 assert.equal(low.lowSample,true);
 assert.match(core.joint(low,fresh),/troppo piccolo/);
});
test("automatic window prioritizes 24h if both sources have matching history",()=>{
 const inputs=[{history:[row(25,78)],current:row(1,69)},
  {history:[row(24.5,62)],current:row(1,58)}];
 assert.equal(core.recommend(inputs,now),"24h");
 const a=core.analyze(inputs[0].history,inputs[0].current,"24h",now);
 const b=core.analyze(inputs[1].history,inputs[1].current,"24h",now);
 assert.match(core.joint(a,b),/entrambe verso SHORT/);
});
test("saved real Myfxbook fixture supports 24h comparisons without synthetic data",()=>{
 const dataset=JSON.parse(fs.readFileSync("tests/fixtures/myfxbook-eurusd-gaps.json","utf8"));
 const last=dataset.records.at(-1);
 const actual=core.analyze(dataset.records,last,"24h",Date.parse(last.t)+3600000);
 assert.equal(actual.available,true);
 assert.ok(actual.samples>=2);
 assert.ok(actual.first.t!==actual.last.t);
});
