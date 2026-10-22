/* REMURA dual retail sentiment: strict samples, independent metrics, honest gaps. */
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs");
const core=require("../sentiment-core.js");
const now=Date.parse("2026-10-18T16:30:00Z");
const when="2026-10-18T16:00:00Z";
const lot={t:when,lPct:78,sPct:22,lLots:100,sLots:25,lPos:300,sPos:90};
const capital={t:when,lPct:19,sPct:81};

test("strict long short percentages; false or incomplete samples excluded",()=>{
 assert.equal(core.valid(lot),true);
 assert.equal(core.valid(capital),true);
 for(const x of [null,{}, {lPct:null,sPct:100},
  {lPct:NaN,sPct:40},{lPct:Infinity,sPct:20},
  {lPct:-1,sPct:101},{lPct:70,sPct:70}])
  assert.equal(core.valid(x),false);
});
test("freshness is timestamped: no recent-looking stale or future feeds",()=>{
 assert.equal(core.fresh(lot,when,now),true);
 assert.equal(core.fresh({...lot,t:"2026-10-18T07:00:00Z"},null,now),false);
 assert.equal(core.fresh({...lot,t:"2026-10-19T00:00:00Z"},null,now),false);
 assert.equal(core.fresh({...lot,t:"invalid"},null,now),false);
});
test("divergence when volume and positions disagree, no institutional proof",()=>{
 const result=core.compare({row:lot,fresh:true},{row:capital,fresh:true});
 assert.equal(result.status,"divergence");
 assert.match(result.text,/Myfxbook per volume in lotti/);
 assert.match(result.text,/Capital.com per posizioni/);
 assert.match(result.text,/Non dimostra/);
 assert.doesNotMatch(result.text,/istituzionali sono short/i);
});
test("both agreeing, neutral, or stale are never invented consensus",()=>{
 const agree=core.compare({row:lot,fresh:true},{row:{...capital,lPct:71,sPct:29},fresh:true});
 assert.equal(agree.status,"aligned");
 assert.match(agree.text,/non è una conferma istituzionale/i);
 assert.equal(core.compare({row:lot,fresh:true},{row:{...capital,lPct:49,sPct:51},fresh:true}).status,"neutral");
 assert.equal(core.compare({row:lot,fresh:true},{row:capital,fresh:false}).status,"unavailable");
 assert.equal(core.compare(null,{row:capital,fresh:true}).status,"unavailable");
});
test("history respects true sample timestamps and window, never fabricates intermediate points",()=>{
 const dates=[
  {t:"2026-10-18T05:00:00Z",lPct:60,sPct:40},
  {...lot,t:"2026-10-18T12:00:00Z"},
  {...lot,t:"2026-10-18T12:00:00Z",lPct:75,sPct:25},
  {...lot,t:"2026-10-18T16:00:00Z"},
  {...lot,t:"invalid"},
  {...lot,t:"2026-10-20T16:00:00Z"}
 ];
 const last=core.points(dates,6*3600000,now);
 assert.deepEqual(last.map(x=>x.t),["2026-10-18T12:00:00Z","2026-10-18T16:00:00Z"]);
 assert.equal(last[0].lPct,75);
 assert.equal(core.points(dates,3600000,now).length,1);
});
test("all 35 market pages use only Myfxbook and Capital display code; no provider credentials",()=>{
 const html=fs.readFileSync("asset.html","utf8");
 const js=fs.readFileSync("sources.js","utf8");
 const retail=fs.readFileSync("retail.js","utf8");
 const css=fs.readFileSync("sources.css","utf8");
 for(const asset of ["sentiment-core.js?v=14","sources.js?v=16","sources.css?v=15","retail.js?v=14"])
  assert.ok(html.includes(asset),asset);
 assert.ok(html.indexOf("retail.js?v=14")<html.indexOf("sentiment-core.js?v=14"));
 assert.ok(html.indexOf("sentiment-core.js?v=14")<html.indexOf("sources.js?v=16"));
 assert.ok(retail.includes("./data/myfxbook/"),"public Myfxbook archive path must be used as fallback");
 assert.ok(retail.includes("./private-api/retail/"),"private reader retained");
 assert.ok(js.includes("/private-api/capital/latest.json"));
 assert.ok(js.includes("/private-api/capital/history/"));
 assert.ok(js.includes("remura:retail"),"do not fetch Myfxbook twice");
 assert.ok(js.includes("core.compare"));
 assert.ok(js.includes("Camp")||css.includes("ms-reading"));
 for(const provider of ["Dukascopy","FX Blue","FXCM","IG Client Sentiment","OANDA","Forex Factory"])
  assert.ok(!js.includes(provider),provider+" must be removed from pair pages");
 for(const secret of ["CAPITAL_API_KEY","CAPITAL_IDENTIFIER","CAPITAL_API_PASSWORD","MYFXBOOK_PASSWORD"])
  assert.ok(!js.includes(secret),"no secrets in browser code");
 assert.ok(html.includes("remura:")===false||html.includes("retail-module"));
});
test("Capital DEMO snapshot strips secrets and imports EURUSD 64.09%",()=>{
 const now=Date.parse("2026-10-19T07:26:00Z");
 const raw={status:"ok",environment:"demo",updatedAt:"2026-10-19T07:25:21Z",
  API_KEY:"do-not-store",symbols:{
   EURUSD:{t:"2026-10-19T07:25:21Z",lPct:64.09,sPct:35.91,marketId:"EURUSD",SECRET:"private"},
   EURJPY:{t:"2026-10-19T07:25:21Z",lPct:65.56,sPct:34.44},
   XAGUSD:{t:"2026-10-19T07:25:21Z",lPct:90.42,sPct:9.58},
   EURAUD:{t:"2026-10-19T07:25:21Z",lPct:90,sPct:90}
  }};
 const cleaned=core.cleanCapitalLatest(raw,["EURUSD","EURJPY","XAGUSD","EURAUD"],now);
 assert.deepEqual(Object.keys(cleaned.symbols),["EURUSD","EURJPY","XAGUSD"]);
 assert.equal(cleaned.symbols.EURUSD.lPct,64.09);
 assert.equal(cleaned.symbols.EURUSD.sPct,35.91);
 for(const secret of ["API_KEY","SECRET","marketId","do-not-store"])
  assert.ok(!JSON.stringify(cleaned).includes(secret));
 assert.equal(core.cleanCapitalLatest(cleaned,["EURUSD"],now).symbols.EURUSD.lPct,64.09);
});
test("Capital import rejects live credentials, malformed, old and future snapshots",()=>{
 const now=Date.parse("2026-10-19T07:26:00Z");
 const raw={status:"ok",environment:"demo",updatedAt:"2026-10-19T07:25:21Z",
  symbols:{EURUSD:{t:"2026-10-19T07:25:21Z",lPct:64,sPct:36}}};
 for(const changed of [
  {...raw,environment:"live"},{...raw,status:"invalid"},
  {...raw,updatedAt:"2026-06-01T00:00:00Z"},
  {...raw,updatedAt:"2026-10-20T00:00:00Z"},
  {...raw,symbols:{EURUSD:{t:"bad",lPct:64,sPct:36}}},
  {...raw,symbols:{EURUSD:{t:"2026-10-19T07:25:21Z",lPct:64,sPct:85}}}
 ])assert.throws(()=>core.cleanCapitalLatest(changed,["EURUSD"],now));
});
test("Capital historical import checks exact pair and strips extra fields",()=>{
 const now=Date.parse("2026-10-19T07:26:00Z");
 const p={t:"2026-10-19T07:25:21Z",lPct:64.09,sPct:35.91,CST:"secret"};
 const old={symbol:"EURUSD",records:[p,p,{t:"bad",lPct:50,sPct:50}]};
 const result=core.cleanCapitalHistory(old,"EURUSD",now);
 assert.equal(result.records.length,1);
 assert.equal(result.records[0].lPct,64.09);
 assert.ok(!JSON.stringify(result).includes("secret"));
 assert.throws(()=>core.cleanCapitalHistory(old,"EURJPY",now));
});
test("capital UI imports locally without browser secrets or direct private GitHub fetch",()=>{
 const ui=fs.readFileSync("sources.js","utf8"),html=fs.readFileSync("asset.html","utf8");
 assert.ok(ui.includes('latestFile.type="file"'));
 assert.ok(ui.includes("core.cleanCapitalLatest"));
 assert.ok(ui.includes("localStorage"));
 assert.ok(ui.includes("/private-api/capital/latest.json"));
 assert.ok(ui.includes("remura-collector/blob/main/private/capital/latest.json"));
 assert.ok(html.includes("sentiment-core.js?v=14"));
 for(const secret of ["CAPITAL_API_KEY","CAPITAL_API_PASSWORD","X-SECURITY-TOKEN"])
  assert.ok(!ui.includes(secret));
});
test("asset and sources page no longer advertise seven live retail sources",()=>{
 const html=fs.readFileSync("asset.html","utf8"),sources=fs.readFileSync("fonti.html","utf8");
 assert.match(sources,/Myfxbook/);
 assert.match(sources,/Capital\.com/);
 assert.doesNotMatch(sources,/7 provider|Dukascopy|IG Client Sentiment|FX Blue|FXCM SSI/);
 assert.doesNotMatch(html,/(Myfxbook, Dukascopy|IG, FX Blue)/);
});

test("35 schede mostrano Myfxbook e Capital consecutivi, con prezzo indipendente",()=>{
 const html=fs.readFileSync("asset.html","utf8");
 const capitalUi=fs.readFileSync("sources.js","utf8");
 const priceUi=fs.readFileSync("price.js","utf8");
 const insightsUi=fs.readFileSync("insights.js","utf8");
 const retailStart=html.indexOf('id="retail-module"');
 const retailEnd=html.indexOf('</section>',retailStart);
 const priceStart=html.indexOf('id="remura-tradingview"');
 const cotStart=html.indexOf('id="cot-overview"');
 const advancedStart=html.indexOf('id="remura-advanced"');
 assert.ok(cotStart>0&&retailStart>cotStart&&retailEnd>retailStart);
 assert.ok(priceStart>retailEnd&&advancedStart>priceStart);
 assert.ok(html.slice(retailStart,retailEnd).includes('id="r-chart"'));
 assert.ok(!html.slice(retailStart,retailEnd).includes('id="r-price"'),
  "TradingView must not be in Myfxbook sentiment panel");
 assert.equal((html.match(/id="r-price"/g)||[]).length,1);
 assert.equal((html.match(/id="r-chart"/g)||[]).length,1);
 assert.match(capitalUi,/holder\.insertAdjacentElement\("afterend",section\)/,
  "Capital.com must appear immediately after Myfxbook");
 assert.match(priceUi,/getElementById\("remura-tradingview"\)/);
 assert.match(priceUi,/host\.insertAdjacentElement\("afterend",el\)/);
 assert.match(capitalUi,/el\("details","ms-import"\)/);
 assert.match(insightsUi,/<details class="rm-charts">/);
 for(const id of ["cot-overview","retail-module","remura-capital","remura-tradingview","remura-advanced"])
  assert.ok(html.includes('href="#'+id+'"'));
 assert.match(html,/Netto positivo/);
 assert.match(html,/Netto negativo/);
});
