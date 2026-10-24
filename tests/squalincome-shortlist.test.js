const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),vm=require("node:vm");
const html=fs.readFileSync("mercati.html","utf8");
const fragment=html.slice(html.indexOf("function crossExposures(candidate){"),
 html.indexOf("let crossMode="));
const core=vm.runInNewContext(fragment+"\n({select:selectCrossCandidates,exposures:crossExposures})");
const c=(sym,change,group="forex")=>({sym,change,meta:{group}});
test("strongest mode remains exactly highest absolute COT deltas",()=>{
 const rows=[c("GBPNZD",11),c("NZDJPY",-8.4),c("NZDCHF",-6.3),c("AUDNZD",6.2),
  c("EURUSD",5.9),c("XAUUSD",-4.3,"metals")];
 assert.deepEqual(core.select(rows,"strongest").map(x=>x.sym),
  ["GBPNZD","NZDJPY","NZDCHF","AUDNZD"]);
 assert.equal(core.select(rows,"strongest").length,4);
});
test("diverse mode reduces overlapping NZD legs without fabricating prices",()=>{
 const rows=[c("GBPNZD",11),c("NZDJPY",-8.4),c("NZDCHF",-6.3),c("AUDNZD",6.2),
  c("EURUSD",5.9),c("USDCAD",5.0),c("XAUUSD",4.9,"metals")];
 const picked=core.select(rows,"diverse");
 assert.equal(picked.length,4);
 assert.equal(picked[0].sym,"GBPNZD");
 assert.ok(picked.filter(x=>x.sym.includes("NZD")).length<=2);
 assert.ok(picked.some(x=>x.sym==="EURUSD"||x.sym==="XAUUSD"));
 assert.equal(new Set(picked.map(x=>x.sym)).size,4);
});
test("invalid and below-threshold COT movements never become candidates",()=>{
 const rows=[c("EURUSD",NaN),c("GBPJPY",.1),c("USDJPY",.45),c("XAUUSD",2,"metals")];
 assert.deepEqual(core.select(rows,"diverse").map(x=>x.sym),["XAUUSD","USDJPY"]);
 assert.throws(()=>core.select(rows,"foo"),/Modalità/);
});
test("diversification is deterministic without needing invented COT rows",()=>{
 const rows=[c("AUDNZD",6.2),c("NZDJPY",-8.4),c("NZDCHF",-6.3),c("GBPNZD",11)];
 assert.deepEqual(core.select(rows,"diverse").map(x=>x.sym),
  core.select(rows.slice().reverse(),"diverse").map(x=>x.sym));
 assert.deepEqual(core.select([]),[]);
});
