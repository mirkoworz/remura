const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),vm=require("node:vm");
test("Lo Shark Radar usa solo indici COT 52 rilevazioni e dati CFTC",()=>{
 const html=fs.readFileSync("mercati.html","utf8");
 assert.ok(html.includes('data-scan="extremes"'));
 assert.ok(html.includes('cot-indices-core.js'));
 assert.ok(html.includes('REMURA_COT_INDEX_CORE.evaluate(data,52)'));
 assert.ok(html.includes('groupIndex<=10||groupIndex>=90'));
 assert.ok(html.includes('gapIndex<=10||gapIndex>=90'));
 assert.ok(html.includes("if(age>14||age<0"));
 const scripts=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map(match=>match[1]).filter(Boolean);
 assert.equal(scripts.length,1);
 assert.doesNotThrow(()=>new vm.Script(scripts[0]));
});
test("Le nuove metriche restano prima dei due blocchi sentiment, prezzo dopo",()=>{
 const html=fs.readFileSync("asset.html","utf8");
 assert.ok(html.indexOf('id="cot-indices"')<html.indexOf('id="retail-module"'));
 assert.ok(html.indexOf('id="retail-module"')<html.indexOf('id="remura-tradingview"'));
 assert.ok(html.includes('id="cot-period"'));
 assert.ok(html.includes('id="cot-gap-chart"'));
 assert.ok(html.includes('remura-capital'));
});
