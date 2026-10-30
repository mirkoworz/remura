const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const parser=require('../weekly-quality-core.js');
function c(recorded=0,legacy=0,after=0,missing=0){
 return {recorded_before_observation:recorded,unknown_legacy:legacy,
  captured_after_observation:after,missing_cot_reference:missing};
}
function entry(week){
 return {cotWeek:week,pairedSamples:3,alignedSamples:1,divergentSamples:2,
  alignedHits:0,divergentHits:2,divergentMinusAlignedHitPp:100,
  captureCounts:c(1,1,1),sharedFactorWarnings:[
    {factor:'USD',markets:3},{factor:'precious_metals',markets:2}
  ]};
}
function snapshot(){
 return {schema:'remura-weekly-quality-v1',mode:'research_only',
  firstSeenMeaning:'REMURA first CFTC row capture (NOT official publication)',
  legacyProvenance:'unknown_not_backfilled',noSyntheticCandles:true,
  independentCotWeeksObserved:1,weeksWithBothRelationships:1,
  weeksDivergenceBetter:1,weeksConcordanceBetter:0,weeksEqual:0,
  minCotWeeksForDescriptiveReview:8,quality:'Campione insufficiente',
  casesAudited:3,captureCounts:c(1,1,1),weekly:[entry('2026-10-20')]};
}
test('one COT week is insufficient even when 3 correlated markets succeed',()=>{
 const parsed=parser.read(snapshot());
 assert.ok(parsed);
 assert.equal(parsed.weeks,1);
 assert.equal(parsed.cases,3);
 assert.equal(parsed.better,1);
 assert.equal(parsed.weekly[0].delta,100);
 assert.equal(parsed.weekly[0].overlaps[0].factor,'USD');
 assert.equal(parsed.counts.unknown_legacy,1);
});
test('cannot label historical rows as officially published or add fictitious weeks',()=>{
 const variants=[];
 let x=snapshot();x.firstSeenMeaning='Official publication time';variants.push(x);
 x=snapshot();x.legacyProvenance='backfilled';variants.push(x);
 x=snapshot();x.captureCounts.recorded_before_observation=3;variants.push(x);
 x=snapshot();x.weekly[0].alignedSamples=7;variants.push(x);
 x=snapshot();x.weekly[0].divergentMinusAlignedHitPp=0;variants.push(x);
 x=snapshot();x.weekly[0].sharedFactorWarnings[0].factor='<img>';variants.push(x);
 x=snapshot();x.weekly[0].sharedFactorWarnings[0].markets=4;variants.push(x);
 x=snapshot();x.weeksDivergenceBetter=2;variants.push(x);
 x=snapshot();x.quality='Vantaggio dimostrato';variants.push(x);
 x=snapshot();x.weeksWithBothRelationships=2;variants.push(x);
 x=snapshot();x.independentCotWeeksObserved=8;variants.push(x);
 for(const obj of variants)assert.equal(parser.read(obj),null);
});
test('zero available weeks displays no invented successes',()=>{
 const x=snapshot();x.weekly=[];x.casesAudited=0;
 x.captureCounts=c();x.independentCotWeeksObserved=0;
 x.weeksWithBothRelationships=0;x.weeksDivergenceBetter=0;
 const parsed=parser.read(x);
 assert.ok(parsed);assert.equal(parsed.weeks,0);assert.equal(parsed.weekly.length,0);
});
test('v1.52 API and iPhone display use private no-store without making trades',()=>{
 const html=fs.readFileSync('statistica-squali.html','utf8');
 const ui=fs.readFileSync('weekly-quality-ui.js','utf8');
 const backend=fs.readFileSync('scripts/private_server.py','utf8');
 const cot=fs.readFileSync('scripts/cot_monitor.py','utf8');
 const sw=fs.readFileSync('sw.js','utf8');
 assert.match(html,/id="weekly-quality-panel"/);
 assert.match(html,/weekly-quality-ui\.js\?v=152/);
 assert.match(ui,/private-api\/signals\/weekly-quality/);
 assert.match(ui,/cache:'no-store'/);
 assert.match(ui,/textContent/);
 assert.match(backend,/WEEKLY_QUALITY_PATH/);
 assert.match(cot,/INSERT OR IGNORE INTO cot_first_seen/);
 assert.match(sw,/weekly-quality-core\.js/);
 assert.doesNotMatch(ui,/Math\.random|localStorage|mockStats|placeOrder/);
});
