/* Test senza librerie esterne: node --test tests/insights.test.js */
const test = require("node:test");
const assert = require("node:assert/strict");
const core = require("../insights-core.js");
const dates = ["2026-09-15","2026-09-22","2026-09-29","2026-10-06","2026-10-13"];
const make = (a,b)=>dates.map((date,i)=>({date,a:a[i],b:b[i]}));
const now = Date.parse("2026-10-17T08:00:00Z");
const opts = {symbol:"EURUSD",isFX:true,isMetal:false,labels:["Asset Manager","Leveraged Funds"],now};
test("35 markets share the same engine; negative TFF momentum persists",()=>{
  const series=make([10,10,10,10,10],[4,2,0,-2,-4]);
  const r=core.analyze(series,opts);
  assert.equal(r.bias,-1);
  assert.equal(r.state,"trend");
  assert.equal(r.sustained,true);
  assert.equal(r.weekly,-2);
  assert.match(r.title,/ribassista/);
  assert.match(r.caveats.join(" "),/proxy|differenza normalizzata/);
  assert.match(r.next,/H4\/H1/);
});
test("USDJPY synthetic sign inversion remains bearish when JPY futures net rises",()=>{
  const series=make([0,0,0,0,0],[8,6,4,2,0]); // synthetic USDJPY series (already inverted by asset.html)
  assert.equal(core.analyze(series,{...opts,symbol:"USDJPY"}).bias,-1);
});
test("opposite changes for asset managers and leveraged funds mean conflict, not strong consensus",()=>{
  const series=make([5,7,9,11,13],[5,3,1,-1,-3]);
  const r=core.analyze(series,opts);
  assert.equal(r.state,"conflict");
  assert.equal(r.conflict,true);
});
test("producer hedging does not produce artificial institutional conflict on gold",()=>{
  const series=make([1,3,5,7,9],[9,7,5,3,1]);
  const r=core.analyze(series,{symbol:"XAUUSD",isFX:false,isMetal:true,labels:["Managed Money","Producer / Merchant"],now});
  assert.equal(r.bias,1);
  assert.equal(r.state,"trend");
  assert.equal(r.conflict,false);
  assert.match(r.caveats.join(" "),/coperture/);
});
test("stale COT suppresses direction even with strong changes",()=>{
  const series=make([0,0,0,0,0],[1,3,5,7,9]);
  const r=core.analyze(series,{...opts,now:Date.parse("2026-11-16T08:00:00Z")});
  assert.equal(r.state,"stale");
  assert.equal(r.bias,0);
});
test("insufficient data yield no inferred probabilities or forced trade",()=>{
  const r=core.analyze([{date:dates[0],a:1,b:2}],opts);
  assert.equal(r.state,"missing");
  assert.equal(r.bias,0);
});
test("normal retail skew uses lot volumes, not a made-up institutional counterparty",()=>{
  const current={t:"2026-10-17T07:40:00Z",lLots:80,sLots:20,lPos:120,sPos:80};
  const x=core.retailContext(current,[],now);
  assert.equal(x.valid,true);
  assert.equal(x.skew,1);
  const cot=core.analyze(make([10,10,10,10,10],[4,2,0,-2,-4]),opts);
  assert.match(core.combine(cot,x),/Possibile divergenza contrarian/);
  assert.match(core.combine(cot,x),/Non implica/);
});
test("tiny, stale, and absent retail samples never generate a contrarian signal",()=>{
  const sample={t:"2026-10-17T07:40:00Z",lLots:8,sLots:2,lPos:2,sPos:1};
  assert.equal(core.retailContext(sample,[],now).valid,false);
  assert.equal(core.retailContext({...sample,lPos:100,sPos:100,t:"2026-10-16T01:00:00Z"},[],now).valid,false);
  assert.equal(core.retailContext(null,[],now).valid,false);
});
test("no contradictory false precision for 4-week movement with only 2 points",()=>{
  const r=core.analyze(make([0,0,0,0,0],[0,1,2,3,4]).slice(-2),opts);
  assert.equal(r.fourWeeks,null);
  assert.notEqual(r.state,"trend");
});
test("two Forex legs remain separate, and USD is not a fake future",()=>{
  const row=date=>({date,parts:{
    base:{a:{long:100,short:120},b:{long:230,short:110},oi:500},
    quote:{a:{long:85,short:60},b:{long:55,short:65},oi:400}
  }});
  const rows=[row(dates[0]),row(dates[1])];
  const two=core.legsFor(rows,{symbol:"EURJPY",isFX:true});
  assert.deepEqual(two.map(x=>x.name),["EUR","JPY"]);
  assert.equal(two[0].rows[0].data.oi,500);
  assert.equal(two[1].rows[0].data.oi,400);
  assert.deepEqual(core.legsFor(rows,{symbol:"EURUSD",isFX:true}).map(x=>x.name),["EUR"]);
  assert.deepEqual(core.legsFor(rows,{symbol:"USDJPY",isFX:true}).map(x=>x.name),["JPY"]);
});
