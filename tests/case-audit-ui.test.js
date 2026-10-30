const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const parser=require('../case-audit-core.js');

function metric(direction,side){
 return {directionalBps:direction,benchmarkLongBps:side==='long'?direction:-direction,
  favorableBps:200,adverseBps:-200,directionHit:direction>0};
}
function record(sym,rel,side,week,calendar,traded){
 return {symbol:sym,cotWeek:week,initialRelationship:rel,cotSide:side,
  calendar24:metric(calendar,side),trading96:metric(traded,side),
  deltaTradingMinusCalendarBps:Math.round((traded-calendar)*100)/100};
}
function group(rows){
 const n=rows.length,avg=k=>n?Math.round(rows.reduce((s,r)=>s+r[k].directionalBps,0)*100/n)/100:null;
 return {samples:n,weeks:new Set(rows.map(r=>r.cotWeek)).size,
  positiveCalendar:rows.filter(r=>r.calendar24.directionHit).length,
  negativeOrFlatCalendar:rows.filter(r=>!r.calendar24.directionHit).length,
  positiveTraded:rows.filter(r=>r.trading96.directionHit).length,
  meanCalendarBps:avg('calendar24'),meanTradedBps:avg('trading96')};
}
function data(){
 const cases=[
  record('XAUUSD','aligned','short','2026-10-20',-126.18,-136.57),
  record('EURUSD','divergent','long','2026-10-20',25,25),
 ];
 const weekly=[{cotWeek:'2026-10-20',maturedCohorts:3,pairedSamples:2,
   aligned:group(cases.filter(r=>r.initialRelationship==='aligned')),
   divergent:group(cases.filter(r=>r.initialRelationship==='divergent'))}];
 return {schema:'remura-case-audit-v1',mode:'research_only',
   scope:'last_12_COT_reference_weeks',noSyntheticCandles:true,
   executionCostsIncluded:false,totalEligibleWeeks:1,weeksShown:1,
   pairedCasesShown:2,caseCountByRelationship:{aligned:1,divergent:1},
   weekly,cases};
}
test('real hypothetical short-COT against rising gold remains a loss for COT',()=>{
 const result=parser.read(data());
 assert.ok(result);
 const gold=result.cases.find(x=>x.symbol==='XAUUSD');
 assert.equal(gold.side,'short');
 assert.equal(gold.calendar24.directional,-126.18);
 assert.equal(gold.calendar24.benchmark,126.18);
 assert.equal(gold.calendar24.hit,false);
 assert.equal(gold.delta,-10.39);
 assert.equal(result.weekly[0].aligned.misses,1);
});
test('strictly reject synthetic, wrong direction or mismatched groups',()=>{
 const variations=[];
 let x=data();x.noSyntheticCandles=false;variations.push(x);
 x=data();x.cases[0].cotSide='long';variations.push(x);
 x=data();x.cases[0].calendar24.directionHit=true;variations.push(x);
 x=data();x.cases[0].trading96.directionalBps=900;variations.push(x);
 x=data();x.cases[0].deltaTradingMinusCalendarBps=0;variations.push(x);
 x=data();x.cases[0].symbol='<img onerror=x>';variations.push(x);
 x=data();x.cases[1].symbol='XAUUSD';variations.push(x);
 x=data();x.cases[1].cotWeek='2026-13-01';variations.push(x);
 x=data();x.weekly[0].pairedSamples=3;variations.push(x);
 x=data();x.weekly[0].aligned.meanCalendarBps=999;variations.push(x);
 x=data();x.caseCountByRelationship.aligned=99;variations.push(x);
 x=data();x.executionCostsIncluded=true;variations.push(x);
 for(const v of variations)assert.equal(parser.read(v),null);
});
test('no cases and one week with only pending outcomes show honest blanks',()=>{
 const x=data();x.cases=[];x.pairedCasesShown=0;
 x.caseCountByRelationship={aligned:0,divergent:0};
 x.weekly[0].pairedSamples=0;x.weekly[0].aligned=group([]);
 x.weekly[0].divergent=group([]);
 const out=parser.read(x);
 assert.ok(out);
 assert.equal(out.cases.length,0);
 assert.equal(out.weekly[0].divergent.mean,null);
});
test('mobile weekly case audit is private, cache-free and no mock trades',()=>{
 const page=fs.readFileSync('statistica-squali.html','utf8');
 const ui=fs.readFileSync('case-audit-ui.js','utf8');
 const backend=fs.readFileSync('scripts/private_server.py','utf8');
 const sw=fs.readFileSync('sw.js','utf8');
 assert.match(page,/id="case-audit-panel"/);
 assert.match(page,/id="case-audit-week"/);
 assert.match(page,/id="case-audit-relation"/);
 assert.match(page,/case-audit-ui\.js\?v=151/);
 assert.match(page,/id="market-audit-results"/);
 assert.match(ui,/private-api\/signals\/dual24\/cases/);
 assert.match(ui,/cache:'no-store'/);
 assert.match(ui,/market-audit-select/);
 assert.match(ui,/textContent/);
 assert.match(ui,/slice\(0,24\)/);
 assert.match(backend,/CASE_AUDIT_PATH/);
 assert.match(sw,/case-audit-core\.js/);
 assert.doesNotMatch(ui,/Math\.random|localStorage|mockStats|placeOrder/);
});
