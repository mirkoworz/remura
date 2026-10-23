const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const core=require('../price-status-core.js');
const SERVER='2026-10-23T11:00:00Z';
const mk=(minutes,count=1)=>({counts:{M15:count},lastComplete:new Date(Date.parse(SERVER)-minutes*60000).toISOString()});
test('Price statuses reflect timestamps and truly missing OHLC',()=>{
 assert.equal(core.interpret(mk(30),SERVER).state,'recent');
 assert.equal(core.interpret(mk(180),SERVER).state,'recent');
 assert.equal(core.interpret(mk(181),SERVER).state,'stale');
 assert.equal(core.interpret(mk(20,0),SERVER).state,'missing');
 assert.equal(core.interpret({counts:{M15:42},lastComplete:null},SERVER).state,'missing');
 assert.equal(core.interpret(mk(-7),SERVER).state,'stale');
});
test('Summary categories never treat an unavailable broker as real price',()=>{
 const data=[mk(40),mk(400),{symbol:'DXY',counts:{M15:0},lastComplete:null}];
 assert.deepEqual(core.summarize(data,SERVER),{recent:1,stale:1,missing:1});
 assert.ok(core.OUTCOMES.ticker_unavailable.includes('Ticker'));
});
test('Dashboard uses only lightweight authenticated API, no token or fake data',()=>{
 const page=fs.readFileSync('stato-prezzi.html','utf8');
 const client=fs.readFileSync('stato-prezzi.js','utf8');
 const backend=fs.readFileSync('scripts/private_server.py','utf8');
 assert.ok(page.includes('nav.js?v=116'));
 assert.ok(client.includes('./private-api/prices/status'));
 assert.ok(backend.includes('PRICE_OVERVIEW_PATH'));
 assert.ok(backend.includes('stato-prezzi.html'));
 assert.ok(!client.includes('ctrader-tokens.json'));
 assert.ok(!page.includes('example-candles'));
});

test('Mobile monitoring keeps source diagnostics accessible in compact disclosure',()=>{
 const html=fs.readFileSync('stato-prezzi.html','utf8');
 const js=fs.readFileSync('stato-prezzi.js','utf8');
 const nav=fs.readFileSync('nav.js','utf8');
 const navCss=fs.readFileSync('nav.css','utf8');
 assert.ok(js.includes('node("details","market-more")'));
 assert.ok(js.includes('rowText("Fonte:"'));
 assert.ok(js.includes('rowText("Ultimo tentativo:"'));
 assert.ok(js.includes('Ultimo esito:'));
 assert.ok(html.includes('Come leggere i dati e la freschezza'));
 assert.ok(nav.includes('if(page==="stato-prezzi.html")'));
 assert.ok(navCss.includes('rm-scrolled-away'));
 assert.ok(navCss.includes('prefers-reduced-motion'));
});
