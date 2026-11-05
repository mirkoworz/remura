const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const pages=['index.html','forex.html','mercati.html','asset.html','catalogo.html','fonti.html','impostazioni.html','stato-prezzi.html','statistica-squali.html'];
test('all pages use v1.63 menu and no old version labels',()=>{
 for(const p of pages){const html=fs.readFileSync(p,'utf8');assert.ok(html.includes('nav.js?v=163'),p);assert.ok(!html.includes('REMURA v0.8')&&!html.includes('REMURA v1.5 ·')&&!html.includes('VERSIONE 0.5'),p);}
 const nav=fs.readFileSync('nav.js','utf8');assert.match(nav,/Aggiornamento v1\.63 · \d{2}\/\d{2}\/2026/);
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
test('v1.63 includes prepared Italian build timestamp and distinct cache',()=>{
 const nav=fs.readFileSync('nav.js','utf8');
 assert.ok(nav.includes('Aggiornamento v1.63 · 05/11/2026 16:00 (Italia, preparazione)'));
 const sw=fs.readFileSync('sw.js','utf8');
 assert.ok(sw.includes('remura-shell-v77-v1.63-shark-splash'));
 for(const p of pages){const html=fs.readFileSync(p,'utf8');assert.ok(!html.includes('REMURA v1.51'),p);}
});

test('v1.55 infrastructure center uses only local GET and states clearly unverified costs',()=>{
 const html=fs.readFileSync('impostazioni.html','utf8');
 const js=fs.readFileSync('impostazioni.js','utf8');
 const nav=fs.readFileSync('nav.js','utf8');
 assert.ok(html.includes('id="centro-controllo"')&&html.includes('id="obs-grid"'));
 assert.ok(nav.includes('./impostazioni.html#centro-controllo'));
 for(const endpoint of ['/private-api/health','/private-api/resources','/private-api/prices/status','/private-api/cot/status','/private-api/signals/status','/private-api/autoupdate'])assert.ok(js.includes(endpoint));
 assert.ok(js.includes('cache:"no-store"')&&js.includes('credentials:"same-origin"'));
 assert.ok(html.includes('quote Oracle e costi')&&html.includes('integrità SQLite'));
});

test('v1.55 separa tecnica, dati e consumi senza numeri provider inventati',()=>{
 const html=fs.readFileSync('impostazioni.html','utf8'),js=fs.readFileSync('impostazioni.js','utf8');
 assert.ok(html.includes('id="obs-data-summary"')&&html.includes('id="obs-usage"'));
 assert.ok(js.includes('"Tecnica"')&&js.includes('"Dati"')&&js.includes('"Consumi"'));
 assert.ok(js.includes('const closed=analyzed===0')&&js.includes('webApi?.allGet'));
 assert.ok(js.includes('/private-api/retail/latest.json'));
 assert.ok(js.includes('NON sono chiamate cTrader')&&html.includes('restano N/D'));
});
test('v1.55: 38 candele verificate nel weekend e scanner senza analisi non sono dati freschi',()=>{
 const vm=require('node:vm'),source=fs.readFileSync('impostazioni.js','utf8');
 const start=source.indexOf('const labels={ok:');
 const end=source.indexOf('const elt=(tag,cls,txt)=>',start);
 assert.ok(start>=0&&end>start);
 const report=vm.runInNewContext(source.slice(start,end)+'\nreport;');
 const iso='2026-11-01T10:30:00Z',now=Date.parse('2026-11-01T10:40:00Z');
 const docs={
  health:{name:'REMURA Private',collector:'running',
   ctraderPreflight:{sdk:'installed',configuration:'ready'},
   ctraderBackup:{enabled:true,configuration:'ready'},instruments:['EURUSD'],
   lastSuccess:'2026-10-31T23:00:00Z',
   retailStatus:'running',retailLastSuccess:iso,capitalStatus:'disabled',igStatus:'disabled'},
  resources:{schema:'remura-resources-v1',sampledAt:iso,memory:{total:100,used:27},disk:{total:100,used:8},cpu:{load1:0.07},webApi:{allGet:120,privateGet:50}},
  prices:{schema:'remura-price-status-v1',collector:'running',total:38,
   qualityTotals:{verified:38,invalid:0,missing:0,insufficient:0},
   freshnessTotals:{weekend:38,recent:0,stale:0},markets:[]},
  signals:{schema:'remura-squalincome-monitor-v1',enabled:true,trackedMarkets:34,
   diagnostics:{lastScanAt:iso,analyzed:0,excluded:34,exclusionReasons:{market_closed:34}}},
  cot:{schema:'remura-cot-status-v1',enabled:true,state:'ready',datasets:{tff:{contracts:11,expectedContracts:11},disagg:{contracts:3,expectedContracts:3}}},
  update:{enabled:true,state:'up_to_date',installedSha:'a'.repeat(40)},
  retail:{status:'ok',source:'Myfxbook Community Outlook',updatedAt:iso,symbols:{EURUSD:{}}}
 };
 const output=report(docs,now);
 const row=name=>output.rows.find(x=>x.name===name);
 assert.equal(row('cTrader · principale').state,'ok');
 assert.equal(row('cTrader · principale').data,'closed');
 assert.equal(row('Qualità candele M15/H1/H4').data,'closed');
 assert.equal(row('Scanner Squalincome').state,'ok');
 assert.equal(row('Scanner Squalincome').data,'closed');
 assert.equal(row('Myfxbook sulla VPS').data,'closed');
 assert.equal(row('cTrader · riserva').data,'unknown');
 assert.equal(row('Capital Google / Firestore').data,'unknown');
 assert.equal(output.counters.allGet,120);
 assert.equal(output.dataTotals.closed>=3,true);
});
