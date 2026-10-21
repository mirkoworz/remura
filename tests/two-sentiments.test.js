/* REMURA two-source layout — static wiring and analytical safety. */
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const core=require("../sentiment-core.js");
const read=name=>fs.readFileSync(require("node:path").join(__dirname,"..",name),"utf8");

test("only Myfxbook and Capital are in the pair sentiment module",()=>{
 const sources=read("sources.js"),html=read("asset.html"),fonti=read("fonti.html");
 for(const s of ["Dukascopy","FX Blue","FXCM","IG Client Sentiment","OANDA","Forex Factory"]){
  assert.ok(!sources.includes(s),s+" must not be a sentiment widget");
  assert.ok(!fonti.includes(s),s+" must not be advertised");
 }
 assert.ok(sources.includes("Capital.com"));
 assert.ok(html.includes('id="retail-module"'));
 assert.ok(html.includes('sources.js?v=21'));
 assert.ok(html.includes('sentiment-core.js?v=1'));
 assert.ok(html.includes('simple-layout.js?v=2'));
 assert.ok(!html.includes('quicklook.js?v=1'));
});
test("simple layout places Myfxbook immediately before Capital, price and COT after",()=>{
 const code=read("simple-layout.js");
 assert.ok(code.includes('intro.after(retail)'));
 assert.ok(code.includes('retail.after(capital)'));
 assert.ok(code.includes('capital.after(price)'));
 assert.ok(code.includes('price.after(cotOverview)'));
 assert.ok(code.includes('cotOverview.after(insights)'));
 assert.ok(code.includes("makeDonut"));
 assert.ok(code.includes("details"));
});
test("Capital snapshot preserves only DEMO percentage/date and rejects fake metrics",()=>{
 const when="2026-10-21T15:53:59Z";
 const now=Date.parse("2026-10-21T16:24:00Z");
 const raw={status:"ok",environment:"demo",updatedAt:when,secret:"hidden",symbols:{
   EURUSD:{t:when,lPct:64.1,sPct:35.9,apiKey:"not public"},
   USDJPY:{t:when,lPct:85,sPct:40}
 }};
 const cleaned=core.cleanCapitalLatest(raw,["EURUSD","USDJPY"],now);
 assert.deepEqual(Object.keys(cleaned.symbols),["EURUSD"]);
 assert.ok(!JSON.stringify(cleaned).includes("hidden"));
 assert.ok(!JSON.stringify(cleaned).includes("apiKey"));
 assert.throws(()=>core.cleanCapitalLatest({...raw,environment:"live"},["EURUSD"],now));
});
test("different retail methodologies cannot imply institutional holdings",()=>{
 const r={row:{lPct:80,sPct:20},fresh:true},c={row:{lPct:30,sPct:70},fresh:true};
 const output=core.compare(r,c);
 assert.equal(output.status,"divergence");
 assert.match(output.text,/Non dimostra/);
 assert.equal(core.compare({...r,fresh:false},c).status,"unavailable");
});
test("server allowlist and PWA keep private API responses out of caches",()=>{
 const server=read("scripts/private_server.py"),sw=read("sw.js");
 for(const name of ["sentiment-core.js","simple-layout.js","simple-layout.css",
  "capital-cloud-config.js","capital-cloud.js"]){
  assert.ok(server.includes('"'+name+'"'),"server must serve "+name);
  assert.ok(sw.includes('"./'+name+'"'),"PWA must load "+name);
 }
 assert.ok(sw.includes('if(url.pathname.includes("/private-api/"))return;'));
});
