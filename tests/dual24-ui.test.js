const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const core=require('../dual24-core.js');

function empty(){
  const segments=[];
  for(const metric of core.METRICS){
    for(const segment of core.SEGMENTS){
      segments.push({metric,segment,samples:0,reportWeeks:0,
        potentiallyMatureCohorts:0,unmeasuredCandidates:0,coveragePct:null,
        meanElapsedHours:null,meanVerifiedPauseCount:null,delayedExits:0,
        verdict:'Campione insufficiente'});
    }
  }
  return {schema:'remura-dual24-validation-v1',mode:'research_only',
    noSyntheticCandles:true,cohorts:0,outcomes:0,segments};
}
function segment(data,metric='calendar24',name='all'){
  return data.segments.find(x=>x.metric===metric&&x.segment===name);
}
function filled(x){
  Object.assign(x,{samples:1,reportWeeks:1,potentiallyMatureCohorts:2,
    unmeasuredCandidates:1,coveragePct:50,meanElapsedHours:25,
    meanVerifiedPauseCount:1,delayedExits:0,verdict:'Campione insufficiente',
    directionHitPct:100,wilson95Pct:[20.7,100],
    meanDirectionalBps:20.01,meanLongBenchmarkBps:20.01,
    meanFavorableBps:21.2,meanAdverseBps:-4.2});
}

test('zero samples stay unknown, never invented 0% returns',()=>{
  const data=core.read(empty());
  assert.ok(data);
  for(const kind of core.METRICS){
    assert.equal(data.items[kind+':all'].samples,0);
    assert.equal(data.items[kind+':all'].hit,null);
  }
});

test('independent metrics cannot be confused or coalesced',()=>{
  const data=empty();
  filled(segment(data,'trading96'));
  filled(segment(data,'calendar24'));
  segment(data,'calendar24').meanElapsedHours=24;
  const parsed=core.read(data);
  assert.equal(parsed.items['calendar24:all'].elapsed,24);
  assert.equal(parsed.items['trading96:all'].elapsed,25);
  assert.equal(parsed.items['trading96:observation'].samples,0);
});

test('reject missing sample proof, synthetic flags and invalid percentages',()=>{
  const cases=[];
  let x=empty();x.noSyntheticCandles=false;cases.push(x);
  x=empty();x.segments.pop();cases.push(x);
  x=empty();x.segments[0].coveragePct=0;cases.push(x);
  x=empty();filled(segment(x));segment(x).coveragePct=100;cases.push(x);
  x=empty();filled(segment(x));segment(x).meanDirectionalBps='999';cases.push(x);
  x=empty();filled(segment(x));segment(x).reportWeeks=5;cases.push(x);
  x=empty();filled(segment(x));segment(x).meanElapsedHours=23;cases.push(x);
  x=empty();filled(segment(x));segment(x).verdict='Descrittivo, non prova predittiva';cases.push(x);
  x=empty();x.segments.push({...x.segments[0]});cases.push(x);
  for(const item of cases)assert.equal(core.read(item),null);
});

test('v1.45 iPhone renders two separate 24h metrics without replacing legacy 24h',()=>{
  const html=fs.readFileSync('statistica-squali.html','utf8');
  const js=fs.readFileSync('dual24-ui.js','utf8');
  const sw=fs.readFileSync('sw.js','utf8');
  const backend=fs.readFileSync('scripts/private_server.py','utf8');
  assert.match(html,/id="dual24-panel"/);
  assert.match(html,/id="stat-overview"/);
  assert.match(html,/dual24-core\.js\?v=146/);
  assert.match(html,/dual24-ui\.js\?v=146/);
  assert.match(js,/calendar24:all/);
  assert.match(js,/trading96:all/);
  assert.match(js,/private-api\/signals\/dual24/);
  assert.match(js,/cache:'no-store'/);
  assert.match(sw,/dual24-core\.js/);
  assert.match(sw,/dual24-ui\.js/);
  assert.match(backend,/DUAL24_PATH/);
  assert.match(backend,/update_dual24\(db_path\)/);
  assert.doesNotMatch(js,/mockStats|Math\.random|localStorage/);
});


test('COT week warning uses measured counts, never a hard-coded first week',()=>{
  const js=fs.readFileSync('dual24-ui.js','utf8');
  assert.doesNotMatch(js,/Una sola settimana COT/);
  assert.match(js,/fmt\(a\.weeks\)/);
  assert.match(js,/fmt\(b\.weeks\)/);
  assert.match(js,/non provano una previsione affidabile/);
});
