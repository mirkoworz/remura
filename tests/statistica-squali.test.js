const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const core=require('../statistica-squali-core.js');

function sample(){
 const segments=[];
 for(const horizonHours of [1,4,24])for(const segment of core.SEGMENTS){
  segments.push({horizonHours,segment,samples:0,reportWeeks:0,
    maturedCohorts:0,unevaluatedMatured:0,coveragePct:null,
    verdict:'Campione insufficiente'});
 }
 return {schema:'remura-forward-validation-v1',mode:'research_only',
   cohorts:0,outcomes:0,segments};
}
function at(doc,horizon,segment){
 return doc.segments.find(x=>x.horizonHours===horizon&&x.segment===segment);
}
function filled(item){
 Object.assign(item,{
  samples:1,reportWeeks:1,maturedCohorts:2,unevaluatedMatured:1,
  coveragePct:50,verdict:'Campione insufficiente',
  directionHitPct:100,wilson95Pct:[20.7,100],
  meanDirectionalBps:12.45,meanLongBenchmarkBps:12.45,
  meanFavorableBps:18.88,meanAdverseBps:-9.25
 });
}

test('fresh valid aggregate is represented without inventing a full sample',()=>{
 const doc=sample();filled(at(doc,1,'all'));
 const result=core.read(doc);
 assert.equal(result.cohorts,0);
 assert.equal(result.items['1:all'].hit,100);
 assert.equal(result.items['1:all'].verdict,'Campione insufficiente');
 assert.equal(result.items['4:all'].hit,null);
 assert.equal(result.items['1:all'].unevaluated,1);
 assert.equal(core.formatPercent(null),'—');
 assert.match(core.formatBps(12.45),/^\+12,45 bp$/);
});

test('empty snapshot never renders a fabricated 0 percent success rate',()=>{
 const model=core.read(sample());
 assert.ok(model);
 for(const h of [1,4,24])assert.equal(model.items[h+':all'].hit,null);
});

test('reject fake metrics, invalid type coercion, and missing segments',()=>{
 const cases=[];
 const a=sample();at(a,1,'all').directionHitPct=85;cases.push(a);
 const b=sample();filled(at(b,1,'all'));at(b,1,'all').samples=5;cases.push(b);
 const c=sample();filled(at(c,1,'all'));at(c,1,'all').verdict='Descrittivo, non prova predittiva';cases.push(c);
 const d=sample();d.segments.pop();cases.push(d);
 const e=sample();e.segments[0].coveragePct=70;cases.push(e);
 const f=sample();filled(at(f,1,'all'));at(f,1,'all').wilson95Pct=[101,102];cases.push(f);
 const g=sample();g.mode='trading_auto';cases.push(g);
 const h=sample();filled(at(h,1,'all'));at(h,1,'all').meanDirectionalBps='99';cases.push(h);
 for(const doc of cases)assert.equal(core.read(doc),null);
});

test('native iPhone route, no mock stats, private source and PWA cache wiring',()=>{
 const html=fs.readFileSync('statistica-squali.html','utf8');
 const js=fs.readFileSync('statistica-squali.js','utf8');
 const server=fs.readFileSync('scripts/private_server.py','utf8');
 const sw=fs.readFileSync('sw.js','utf8');
 const nav=fs.readFileSync('nav.js','utf8');
 assert.match(html,/statistica-squali-core\.js\?v=144/);
 assert.match(html,/statistica-squali\.js\?v=144/);
 assert.match(html,/nav\.js\?v=144/);
 assert.match(js,/private-api\/signals\/validation/);
 assert.match(js,/cache:'no-store'/);
 assert.match(js,/area\.hidden=true/);
 assert.doesNotMatch(js,/mockData|random|fixture|placeholderStats|Math\.random/);
 assert.match(server,/statistica-squali\.html/);
 assert.match(sw,/statistica-squali\.html/);
 assert.match(nav,/Verifica Squali/);
});

test('mobile layout allows minimum width and displays all horizon choices',()=>{
 const html=fs.readFileSync('statistica-squali.html','utf8');
 assert.match(html,/@media\(max-width:700px\)/);
 assert.match(html,/overflow-x:hidden/);
 for(const h of [1,4,24])assert.match(html,new RegExp('data-horizon="'+h+'"'));
});

test('v1.41 keeps three iPhone horizons on one row and menu out of scrolled data',()=>{
 const html=fs.readFileSync('statistica-squali.html','utf8');
 const js=fs.readFileSync('statistica-squali.js','utf8');
 const nav=fs.readFileSync('nav.js','utf8');
 assert.match(html,/grid-template-columns:repeat\(3,minmax\(0,1fr\)\)/);
 assert.match(html,/id="stat-interpretation"/);
 assert.match(html,/main>header\.top\{padding-left:58px/);
 assert.match(js,/main\.matured===0/);
 assert.match(js,/non misura ancora/);
 assert.match(js,/Copertura coorti già mature/);
 assert.match(nav,/"asset\.html","statistica-squali\.html"\]\.includes\(page\)/);
 assert.doesNotMatch(js,/Direzione COT corretta/);
});


test('v1.42 Radar link is a bounded accessible two-line iPhone control',()=>{
 const radar=fs.readFileSync('mercati.html','utf8');
 const layout=radar.match(/<div class="stat-shortcut-wrap">([\s\S]*?)<\/div>/);
 assert.ok(layout, 'statistics link wrapper exists');
 assert.match(layout[1],/class="stat-shortcut"/);
 assert.match(layout[1],/href="\.\/statistica-squali\.html"/);
 assert.match(layout[1],/<strong>◉ Verifica Squali<\/strong>/);
 assert.match(layout[1],/<small>Statistiche dopo 1h · 4h · 24h<\/small>/);
 assert.match(radar,/\.stat-shortcut\{[^}]*display:flex[^}]*width:100%[^}]*max-width:100%/);
 assert.match(radar,/@media\(max-width:700px\)\{\.stat-shortcut\{padding-left:60px/);
 assert.doesNotMatch(radar,/class="back" href="\.\/statistica-squali\.html"/);
});


test('v1.43 session-gap UI never invents M15 or overwrites old outcome metrics',()=>{
 const html=fs.readFileSync('statistica-squali.html','utf8');
 const js=fs.readFileSync('statistica-squali.js','utf8');
 assert.match(html,/id="session-diagnostics"/);
 assert.match(html,/id="session-gaps-results"/);
 assert.match(html,/Non vengono inventate candele né ricalcolate le statistiche precedenti/);
 assert.match(js,/private-api\/signals\/session-gaps/);
 assert.match(js,/mode!=='diagnostic_only'/);
 assert.match(js,/brokerHoursConfirmed!==false/);
 assert.match(js,/ricorrente/);
 assert.match(js,/no-store/);
 assert.doesNotMatch(js,/localStorage|Math\.random|fakeCandles|mockStats/);
});


test('v1.44 manual broker schedule evidence is not mistaken for automated verification',()=>{
 const html=fs.readFileSync('statistica-squali.html','utf8');
 const js=fs.readFileSync('statistica-squali.js','utf8');
 const api=fs.readFileSync('scripts/session_gaps.py','utf8');
 assert.match(html,/orari cTrader FP Markets verificati manualmente il 28\/10\/2026/);
 assert.match(html,/non legge automaticamente il calendario ufficiale/);
 assert.match(js,/verificata manualmente il 28\/10\/2026/);
 assert.match(js,/non viene verificato automaticamente/);
 assert.doesNotMatch(js,/Possibile pausa del broker, non confermata/);
 assert.match(api,/"brokerHoursConfirmed": False/);
 assert.match(js,/result.brokerHoursConfirmed!==false/);
 assert.match(html,/Non vengono inventate candele né ricalcolate le statistiche precedenti/);
});
