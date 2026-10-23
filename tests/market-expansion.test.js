const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const read=p=>fs.readFileSync(p,'utf8');
test('Menu and catalog expose 38 assets including German index and oils',()=>{
 const nav=read('nav.js');
 for(const s of ['Cerca tra 38 strumenti','GER30:{group:"indices"','USOIL:{group:"energy"','UKOIL:{group:"energy"','id:"energy"'])
  assert.ok(nav.includes(s),s);
 assert.ok(read('catalogo.html').includes('energy:{'));
 assert.ok(read('index.html').includes('categoria=energy'));
});
test('COT WTI is genuine reference; DAX and Brent have no fabricated futures COT',()=>{
 const nav=read('nav.js'),asset=read('asset.html'),radar=read('mercati.html');
 assert.match(nav,/GER30:\{group:"indices"[^\n]*code:null,dataset:null/);
 assert.match(nav,/UKOIL:\{group:"energy"[^\n]*code:null,dataset:null/);
 assert.match(nav,/USOIL:\{group:"energy"[^\n]*code:"067651",dataset:"disagg"/);
 assert.ok(asset.includes('if(hasCOT){load();}else{'));
 assert.ok(asset.includes('COT N/D'));
 assert.ok(radar.includes("USOIL:{group:'energy'"));
 assert.ok(!radar.includes("UKOIL:{group:'energy'"));
});
test('Private market registry includes DAX and both oils',()=>{
 const p=read('scripts/price_feed.py');
 for(const key of ['"GER30"','"USOIL"','"UKOIL"'])assert.ok(p.includes(key));
});
test('VIX replaces Russell 2000, keeps a DAX 40 market and DXY price independently',()=>{
 const nav=read('nav.js'),registry=read('scripts/price_feed.py');
 const scanner=read('mercati.html'),retail=read('retail.js');
 assert.ok(nav.includes('VIX:{group:"macro"'));
 assert.ok(nav.includes('GER30:{group:"indices"'));
 assert.ok(nav.includes('DXY:{group:"macro"'));
 assert.ok(registry.includes('"VIX"'));
 assert.ok(!registry.includes('"US2000"'));
 assert.ok(!nav.includes('US2000'));
 assert.ok(!scanner.includes('US2000'));
 assert.ok(!retail.includes('US2000'));
 assert.match(nav,/VIX:\{group:"macro"[^\n]*code:null,dataset:null/);
 assert.match(nav,/GER30:\{group:"indices"[^\n]*code:null,dataset:null/);
 assert.match(scanner,/VIX:\{group:'macro'[^\n]*code:null,dataset:null/);
 assert.match(scanner,/GER30:\{group:'indices'[^\n]*code:null,dataset:null/);
 assert.ok(nav.includes('DAX 40'));
});

test('DAX and VIX do not display fabricated COT values on asset detail',()=>{
 const html=read('asset.html');
 assert.ok(html.includes('!hasCOT?"COT N/D · Prezzi cTrader"'));
 assert.ok(html.includes('VIX (contratto sulla volatilità)'));
 assert.ok(read('mercati.html').includes('SOLO PREZZI · COT N/D'));
});

test('Indices exclude both macro gauges; whole registry remains 38 symbols',()=>{
 const nav=read('nav.js'),catalog=read('catalogo.html'),home=read('index.html'),radar=read('mercati.html');
 assert.ok(nav.includes('id:"macro",label:"Indicatori macro"'));
 assert.ok(nav.includes('id:"indices",label:"Indici azionari"'));
 assert.ok(nav.includes('DXY:{group:"macro"'));
 assert.ok(nav.includes('VIX:{group:"macro"'));
 assert.ok(nav.includes('GER30:{group:"indices"'));
 assert.ok(home.includes('4 indici · 2 macro'));
 assert.ok(catalog.includes('macro:{heading:'));
 assert.ok(radar.includes('data-group="macro"'));
 assert.ok(radar.includes('group!=="macro"'));
 assert.ok(!nav.includes('Russell 2000'));
});

test('Macro is separate and radar compares selectable markets, not preselected DAX',()=>{
 const nav=read('nav.js'),site=read('stato-prezzi.html'),logic=read('stato-prezzi.js');
 assert.match(nav,/\{id:"indices",label:"Indici azionari"/);
 assert.match(nav,/\{id:"macro",label:"Indicatori macro"/);
 assert.ok(site.includes('Radar Macro globale'));
 assert.ok(site.includes('Mercato da analizzare'));
 assert.ok(site.includes('id="macro-context"'));
 assert.ok(site.includes('id="macro-target-correlations"'));
 assert.ok(!site.includes('DAX · USDX · VIX'));
 assert.ok(logic.includes('if(group.id==="macro")continue'));
 assert.ok(logic.includes('[[symbol,"DXY"],[symbol,"VIX"]]'));
 assert.ok(!logic.includes('const pairs=[["GER30","DXY"]'));
});
