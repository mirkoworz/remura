const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const parser=require('../market-audit-core.js');

function statistics(n,weeks,dir=15,long=5){
  if(!n)return {samples:0,reportWeeks:0,verdict:'Campione insufficiente'};
  return {samples:n,reportWeeks:weeks,verdict:'Campione insufficiente',
    directionHitPct:50,wilson95Pct:[15,85],meanDirectionalBps:dir,
    meanLongBenchmarkBps:long,meanFavorableBps:20,meanAdverseBps:-10};
}
function pack(matured,n,weeks=1){
  return {cohortsMatured:matured,pairedSamples:n,unpairedMatured:matured-n,
    reportWeeksPaired:weeks*(n>0),calendar24:statistics(n,weeks,15),
    trading96:statistics(n,weeks,17),deltaTradingMinusCalendarBps:n?2:null};
}
function payload(){
  return {schema:'remura-market-audit-v1',mode:'research_only',
    noSyntheticCandles:true,total:pack(3,2),
    relationships:[
      {relationship:'aligned',...pack(2,1)},
      {relationship:'divergent',...pack(1,1)}
    ],
    markets:[{symbol:'XAUUSD',...pack(2,1)},{symbol:'EURUSD',...pack(1,1)}]
  };
}
test('valid market/year paired data are parsed without rankings',()=>{
  const parsed=parser.read(payload());
  assert.ok(parsed);
  assert.deepEqual(parsed.markets.map(m=>m.symbol),['EURUSD','XAUUSD']);
  assert.equal(parsed.total.matched,2);
  assert.equal(parsed.total.unmatched,1);
  assert.equal(parsed.total.delta,2);
});
test('reject unmatched cohorts in totals, fake weeks or false precision',()=>{
  const cases=[];
  let p=payload();p.total.pairedSamples=3;cases.push(p);
  p=payload();p.total.calendar24.reportWeeks=9;cases.push(p);
  p=payload();p.total.trading96.meanDirectionalBps=45;cases.push(p);
  p=payload();p.markets[0].symbol='<script>';cases.push(p);
  p=payload();p.markets[1].symbol='XAUUSD';cases.push(p);
  p=payload();p.markets[1].pairedSamples=4;cases.push(p);
  p=payload();p.relationships[0].relationship='divergent';cases.push(p);
  p=payload();p.noSyntheticCandles=false;cases.push(p);
  for(const item of cases)assert.equal(parser.read(item),null);
});
test('zero paired data never invent statistics',()=>{
  const p=payload();p.total=pack(0,0,0);
  p.markets=[];p.relationships=[
    {relationship:'aligned',...pack(0,0,0)},
    {relationship:'divergent',...pack(0,0,0)}];
  const parsed=parser.read(p);
  assert.ok(parsed);
  assert.equal(parsed.total.values[0].hit,null);
  assert.equal(parsed.total.delta,null);
});
test('v1.46 UI reads private no-store API and keeps legacy study separate',()=>{
  const html=fs.readFileSync('statistica-squali.html','utf8');
  const ui=fs.readFileSync('market-audit-ui.js','utf8');
  const api=fs.readFileSync('scripts/private_server.py','utf8');
  const sw=fs.readFileSync('sw.js','utf8');
  assert.match(html,/id="market-audit-panel"/);
  assert.match(html,/id="market-audit-select"/);
  assert.match(html,/id="dual24-panel"/);
  assert.match(ui,/dual24\/markets/);
  assert.match(ui,/cache:'no-store'/);
  assert.match(ui,/data-horizon="24"/);
  assert.match(ui,/Campione insufficiente/);
  assert.match(api,/MARKET_AUDIT_PATH/);
  assert.match(sw,/market-audit-ui\.js/);
  assert.doesNotMatch(ui,/Math\.random|localStorage|mockStats/);
});
