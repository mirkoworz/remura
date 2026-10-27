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
 assert.match(html,/statistica-squali-core\.js\?v=140/);
 assert.match(html,/statistica-squali\.js\?v=140/);
 assert.match(html,/nav\.js\?v=140/);
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
