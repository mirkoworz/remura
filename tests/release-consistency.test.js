const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const pages=['index.html','forex.html','mercati.html','asset.html','catalogo.html','fonti.html','impostazioni.html','stato-prezzi.html','statistica-squali.html'];
test('all pages use v1.54 menu and no old version labels',()=>{
 for(const p of pages){const html=fs.readFileSync(p,'utf8');assert.ok(html.includes('nav.js?v=154'),p);assert.ok(!html.includes('REMURA v0.8')&&!html.includes('REMURA v1.5 ·')&&!html.includes('VERSIONE 0.5'),p);}
 const nav=fs.readFileSync('nav.js','utf8');assert.match(nav,/Aggiornamento v1\.54 · \d{2}\/\d{2}\/2026/);
});
test('Forex has no generated market samples',()=>{
 const code=fs.readFileSync('forex.html','utf8');
 assert.ok(!code.includes('makeDemo')&&!code.includes('DEMO_DATI_SIMULATI'));
 assert.ok(code.includes("sourceMode='missing'")&&code.includes("if(sourceMode!=='live'||commonDates.length<2)return;"));
});
test('Settings displays public and private feed freshness',()=>{
 const html=fs.readFileSync('impostazioni.html','utf8');
 const js=fs.readFileSync('impostazioni.js','utf8');
 assert.ok(html.includes('feed-health-core.js')&&html.includes('public-status'));
 assert.ok(js.includes('feedHealth.inspect(cleaned,symbols)')&&js.includes('checkPublic()'));
});
test('v1.54 includes correct Italian build timestamp and distinct cache',()=>{
 const nav=fs.readFileSync('nav.js','utf8');
 assert.ok(nav.includes('Aggiornamento v1.54 · 01/11/2026 11:27 (Italia, preparazione)'));
 const sw=fs.readFileSync('sw.js','utf8');
 assert.ok(sw.includes('remura-shell-v68-v1.54-monitor'));
 for(const p of pages){const html=fs.readFileSync(p,'utf8');assert.ok(!html.includes('REMURA v1.51'),p);}
});

test('v1.54 infrastructure center uses only local GET and states clearly unverified costs',()=>{
 const html=fs.readFileSync('impostazioni.html','utf8');
 const js=fs.readFileSync('impostazioni.js','utf8');
 const nav=fs.readFileSync('nav.js','utf8');
 assert.ok(html.includes('id="centro-controllo"')&&html.includes('id="obs-grid"'));
 assert.ok(nav.includes('./impostazioni.html#centro-controllo'));
 for(const endpoint of ['/private-api/health','/private-api/resources','/private-api/prices/status','/private-api/cot/status','/private-api/signals/status','/private-api/autoupdate'])assert.ok(js.includes(endpoint));
 assert.ok(js.includes('cache:"no-store"')&&js.includes('credentials:"same-origin"'));
 assert.ok(html.includes('quote Oracle e costi')&&html.includes('integrità SQLite'));
});
