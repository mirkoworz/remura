const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const parser=require('../cot-week-watch-core.js');
const codes={tff:['099741','096742','097741','232741','090741','092741',
 '112741','13874A','209742','124603','098662'],disagg:['088691','084691','067651']};
function group(kind,complete=true,seen=true){
 const expected=codes[kind],missing=complete?[]:[expected.at(-1)];
 const present=expected.length-missing.length;
 return {present,expected:expected.length,missingCodes:missing,
  firstSeenKnown:seen?present:0,firstSeenUnknown:seen?0:present,
  invalidFirstSeen:0,recentlyCapturedRows48h:seen?present:0};
}
function example(){
 const latest='2026-10-27',prev='2026-10-20';
 const weeks=[{cotWeek:latest,complete:true,
  datasets:{tff:group('tff'),disagg:group('disagg')}},
  {cotWeek:prev,complete:true,
   datasets:{tff:group('tff',true,false),disagg:group('disagg',true,false)}}];
 return {schema:'remura-cot-week-watch-v1',mode:'diagnostic_only',
  collectorCadenceHours:6,officialReleaseTimeVerified:false,
  captureMeans:'first_local_capture_not_publication',
  enabled:true,status:'ready',expectedContracts:14,
  latestCommonCompleteWeek:latest,previousCommonCompleteWeek:prev,
  hasTwoCompleteReferenceWeeks:true,latestWeekLocallyCapturedIn48h:true,
  datasets:Object.fromEntries(['tff','disagg'].map(kind=>[kind,
    {...group(kind),latestCotWeek:latest,reportAgeDays:2,
      collectorState:'ok',state:'ok',
      lastCollectorAttemptUtc:'2026-10-29T08:00:00+00:00',
      lastSuccessUtc:'2026-10-29T08:00:00+00:00'}])),
  weeks};
}
test('parses two complete weekly datasets and legitimate new first-capture',()=>{
 const x=parser.read(example());assert.ok(x);
 assert.equal(x.lastComplete,'2026-10-27');
 assert.equal(x.previousComplete,'2026-10-20');
 assert.equal(x.datasets.tff.present,11);
 assert.equal(x.datasets.disagg.present,3);
 assert.equal(x.weeks[1].datasets.tff.firstSeenUnknown,11);
 assert.equal(x.newCapture,true);
});
test('rejects invented official publication and broken contract accounting',()=>{
 const mutations=[
  x=>x.officialReleaseTimeVerified=true,
  x=>x.captureMeans='published_by_CFTC',
  x=>x.datasets.tff.expected=12,
  x=>x.datasets.tff.present=12,
  x=>x.datasets.tff.missingCodes=['unknown'],
  x=>x.datasets.tff.firstSeenKnown=12,
  x=>x.datasets.disagg.recentlyCapturedRows48h=4,
  x=>x.datasets.tff.state='missing_fake',
  x=>x.weeks[0].complete=false,
  x=>x.weeks[0].datasets.disagg.missingCodes=['067651'],
  x=>x.latestWeekLocallyCapturedIn48h='yes',
  x=>x.hasTwoCompleteReferenceWeeks=false,
  x=>x.status='disabled',
  x=>x.previousCommonCompleteWeek='2026-19-20'
 ];
 for(const mutate of mutations){
  const x=example();mutate(x);
  assert.equal(parser.read(x),null);
 }
});
test('partial week is explicit and does not show last full week as new',()=>{
 const x=example();
 x.weeks[0].complete=false;
 x.weeks[0].datasets.disagg=group('disagg',false);
 x.datasets.disagg={...x.datasets.disagg,...group('disagg',false),
   state:'incomplete'};
 x.status='attention';
 x.latestCommonCompleteWeek='2026-10-20';
 x.previousCommonCompleteWeek=null;
 x.hasTwoCompleteReferenceWeeks=false;
 x.latestWeekLocallyCapturedIn48h=false;
 assert.ok(parser.read(x));
});
test('disabled collection should not be called ready',()=>{
 const x=example();x.enabled=false;x.status='disabled';
 x.datasets.tff.state='disabled';x.datasets.disagg.state='disabled';
 assert.ok(parser.read(x));
});
test('first authentic complete weekly acquisition is recognized without duplicating cohorts',()=>{
 const x=parser.read(example());assert.ok(x);
 const result=parser.captureSummary(x);
 assert.equal(result.state,'fully_tracked');
 assert.equal(result.cotWeek,'2026-10-27');
 assert.equal(result.traced,14);
 assert.equal(result.tff,11);
 assert.equal(result.disagg,3);
 assert.equal(result.collectorReady,true);
 // Evidence remains even after the 48h flag expires; it is a local capture record.
 x.newCapture=false;
 assert.equal(parser.captureSummary(x).state,'fully_tracked');
});
test('legacy reports are not backdated and do not become 14 genuine captures',()=>{
 const x=example();
 for(const kind of ['tff','disagg']){
  const group=x.datasets[kind];
  group.firstSeenUnknown=group.present;group.firstSeenKnown=0;
  group.recentlyCapturedRows48h=0;
  const wk=x.weeks[0].datasets[kind];
  wk.firstSeenUnknown=wk.present;wk.firstSeenKnown=0;
  wk.recentlyCapturedRows48h=0;
 }
 x.latestWeekLocallyCapturedIn48h=false;
 const proof=parser.captureSummary(parser.read(x));
 assert.equal(proof.state,'legacy');
 assert.equal(proof.traced,0);
 assert.equal(proof.missing,0);
});
test('partial new week never gets certified even when old complete week exists',()=>{
 const x=example();
 x.weeks[0].datasets.disagg=group('disagg',false);
 x.weeks[0].complete=false;
 x.datasets.disagg={...x.datasets.disagg,...group('disagg',false),state:'incomplete'};
 x.latestCommonCompleteWeek='2026-10-20';
 x.previousCommonCompleteWeek=null;
 x.hasTwoCompleteReferenceWeeks=false;
 x.status='attention';
 x.latestWeekLocallyCapturedIn48h=false;
 const summary=parser.captureSummary(parser.read(x));
 assert.equal(summary.state,'partial');
 assert.equal(summary.missing,1);
 assert.equal(summary.traced,13);
});
test('invalid timestamp and source error are distinct from the proof of capture',()=>{
 const x=example();
 x.weeks[0].datasets.tff.invalidFirstSeen=1;
 x.weeks[0].datasets.tff.firstSeenKnown=10;
 x.weeks[0].datasets.tff.recentlyCapturedRows48h=10;
 x.datasets.tff.invalidFirstSeen=1;
 x.datasets.tff.firstSeenKnown=10;
 x.datasets.tff.recentlyCapturedRows48h=10;
 x.datasets.tff.state='timestamp_review';
 x.status='attention';
 const bad=parser.captureSummary(parser.read(x));
 assert.equal(bad.state,'invalid');
 assert.equal(bad.collectorReady,false);
 const ok=example();
 ok.datasets.tff.state='source_error';ok.status='attention';
 const proof=parser.captureSummary(parser.read(ok));
 assert.equal(proof.state,'fully_tracked');
 assert.equal(proof.collectorReady,false);
});

test('v1.51 page and private API remain uncached, no trading',()=>{
 const html=fs.readFileSync('statistica-squali.html','utf8');
 const server=fs.readFileSync('scripts/private_server.py','utf8');
 const ui=fs.readFileSync('cot-week-watch-ui.js','utf8');
 const backend=fs.readFileSync('scripts/cot_week_watch.py','utf8');
 const cache=fs.readFileSync('sw.js','utf8');
 assert.match(html,/id="cot-week-watch-panel"/);
 assert.match(html,/id="cot-capture-attestation"/);
 assert.match(html,/cot-week-watch-ui\.js\?v=151/);
 assert.match(server,/COT_WEEK_WATCH_PATH/);
 assert.match(ui,/private-api\/cot\/week-watch/);
 assert.match(ui,/cache:'no-store'/);
 assert.match(ui,/textContent/);
 assert.match(ui,/captureSummary/);
 assert.match(cache,/cot-week-watch-core\.js/);
 assert.match(backend,/PRAGMA query_only=ON/);
 assert.doesNotMatch(ui,/Math\.random|placeOrder|localStorage|innerHTML/);
});
