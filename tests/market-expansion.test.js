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