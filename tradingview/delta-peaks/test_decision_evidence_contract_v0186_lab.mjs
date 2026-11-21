// REMURA v0.8.186 LAB: NEW synthetic tests for one-decision source admission.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import * as evidenceModule from './decision_evidence_contract_v0186_lab.mjs';
import {reviewDecisionEvidenceV0186 as review,V0186_EVIDENCE_CONTRACT as contract} from './decision_evidence_contract_v0186_lab.mjs';
const instrument=Object.freeze({market:'EURUSD',provider:'TV',ticker:'EURUSD',product:'SPOT',contract:''});
const decision=Object.freeze({at:'2026-11-21T10:05:00Z',instrument});
const cot={report_as_of:'2026-11-17T00:00:00Z',published_at:'2026-11-20T20:30:00Z',first_seen_at:'2026-11-20T20:31:00Z',instrument};
const retail={snapshot_at:'2026-11-21T10:04:00Z',first_seen_at:'2026-11-21T10:04:03Z',instrument};
const cvd={bar_close_at:'2026-11-21T10:00:00Z',first_seen_at:'2026-11-21T10:01:59Z',kind:'TRADINGVIEW_CVD',timeframe:'M5',instrument};
const sample=()=>({decision,cot:{...cot},retail:{...retail},cvd:{...cvd}});
test('01 one-decision three-source chronology is structural only, never scientific admission',()=>{
 const r=review(sample());assert.equal(r.status,'THREE_SOURCE_CLAIMS_COMPATIBLE_UNATTESTED');
 assert.equal(r.cot,'CLAIMED_TIME_ORDER_ONLY');assert.equal(r.retail,'CLAIMED_TIME_ORDER_ONLY');
 assert.equal(r.cvd,'CLAIMED_TIME_ORDER_ONLY');assert.equal(r.scientific_admission,false);
 assert.equal(r.first_seen_independently_attested,false);assert.equal(r.edge_established,false);
});
test('02 source absence remains UNKNOWN, never counted as negative',()=>{
 const a=sample();a.cot=null;a.retail=null;a.cvd=null;const r=review(a);
 assert.equal(r.status,'INCOMPLETE_OR_INCOMPARABLE');
 assert.deepEqual([r.cot,r.retail,r.cvd],['UNKNOWN','UNKNOWN','UNKNOWN']);
});
test('03 COT first-seen after decision fails causal admission',()=>{
 const a=sample();a.cot.first_seen_at='2026-11-21T10:06:00Z';
 assert.equal(review(a).cot,'LATE_OR_UNVERIFIABLE_TIME_ORDER');
});
test('04 COT cannot be seen before its claimed publication',()=>{
 const a=sample();a.cot.published_at='2026-11-21T10:04:59Z';
 assert.equal(review(a).cot,'LATE_OR_UNVERIFIABLE_TIME_ORDER');
});
test('05 retail observed AFTER first-seen is rejected',()=>{
 const a=sample();a.retail.snapshot_at='2026-11-21T10:04:04Z';
 assert.equal(review(a).retail,'LATE_OR_UNVERIFIABLE_TIME_ORDER');
});
test('06 different COT futures contract cannot be inferred to map to FX SPOT',()=>{
 const a=sample();a.cot.instrument={market:'EURUSD',provider:'CFTC',ticker:'099741',product:'FUTURE',contract:'6EZ26'};
 assert.equal(review(a).cot,'EXACT_INSTRUMENT_OR_MAPPING_UNVERIFIED');
});
test('07 late 121-second TV M5 receipt fails V2',()=>{
 const a=sample();a.cvd.first_seen_at='2026-11-21T10:02:01Z';
 assert.equal(review(a).cvd,'M5_RECEIPT_NOT_ADMISSIBLE');
});
test('08 receipt before bar closes never becomes timely',()=>{
 const a=sample();a.cvd.first_seen_at='2026-11-21T09:59:59Z';
 assert.equal(review(a).cvd,'LATE_OR_UNVERIFIABLE_TIME_ORDER');
});
test('09 cTrader tick-volume cannot masquerade as TradingView M5 CVD',()=>{
 const a=sample();a.cvd={...a.cvd,kind:'CTRADER_TICK_PROXY',timeframe:'M15'};
 assert.equal(review(a).cvd,'TICK_VOLUME_PROXY_NOT_AGGRESSOR_CVD');
});
test('10 malformed impossible UTC calendar date is not silently normalized',()=>{
 const a=sample();a.decision={...a.decision,at:'2026-02-30T10:05:00Z'};
 assert.equal(review(a).status,'DECISION_INVALID');
});
test('11 every input must be strict, plain, finite and scoped; no inherited claims',()=>{
 const a=sample();a.cot=Object.create({first_seen_at:cot.first_seen_at});
 assert.equal(review(a).cot,'INVALID_CLAIM');
});
test('12 M5 bar must close on the exact 5-minute UTC boundary',()=>{
 const a=sample();a.cvd.bar_close_at='2026-11-21T10:00:01Z';
 assert.equal(review(a).cvd,'M5_RECEIPT_NOT_ADMISSIBLE');
});
test('13 review is pure, never mutates user evidence and does not output identifiers',()=>{
 const a=sample();const before=JSON.stringify(a);const result=review(a);
 assert.equal(JSON.stringify(a),before);assert.ok(!JSON.stringify(result).includes('EURUSD'));
 assert.ok(!JSON.stringify(result).includes('2026-11-21T10:05:00Z'));
});
test('14 no default entrypoint, automatic live activation, provider or cloud calls',()=>{
 assert.equal(contract.noDefaultExport,true);assert.equal(contract.liveAllowed,false);
 assert.equal(Object.hasOwn(evidenceModule,'default'),false);
 const r=review(sample());assert.equal(r.oracle_or_cloudflare_calls,0);
 assert.equal(r.live_activation_allowed,false);assert.equal(r.protocol_modified,false);
});
