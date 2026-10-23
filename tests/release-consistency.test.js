const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const pages=['index.html','forex.html','mercati.html','asset.html','catalogo.html','fonti.html','impostazioni.html'];
test('all pages use v1.11 menu and no old version labels',()=>{
 for(const p of pages){const html=fs.readFileSync(p,'utf8');assert.ok(html.includes('nav.js?v=111'),p);assert.ok(!html.includes('REMURA v0.8')&&!html.includes('REMURA v1.5')&&!html.includes('VERSIONE 0.5'),p);}
 const nav=fs.readFileSync('nav.js','utf8');assert.match(nav,/Aggiornamento v1\.11 · \d{2}\/\d{2}\/2026/);
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