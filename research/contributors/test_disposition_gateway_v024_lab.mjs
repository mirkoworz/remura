// REMURA Experience v0.24 LAB — 20/11/2026 CET
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {makeDispositionGatewayV024} from './disposition_gateway_v024_lab.mjs';
import {makeConsumerV2, validateV2} from './consumer_v021.mjs';
import {createHomeV2} from './home_v022.mjs';

const T=Date.parse('2026-11-20T22:15:00Z');
const hex=(c)=>c.repeat(64);
const pairs=['EURUSD','GBPUSD','AUDUSD','NZDUSD','USDJPY','USDCAD','USDCHF','EURGBP','EURJPY','EURCHF','EURCAD','EURAUD','EURNZD','GBPJPY','GBPCHF','GBPCAD','GBPAUD','GBPNZD','AUDJPY','AUDCHF','AUDCAD','AUDNZD','NZDJPY','NZDCAD','NZDCHF','CADJPY','CADCHF','CHFJPY'];
const copy=x=>structuredClone(x);
function validView(seq=2){return {schema:'REMURA_SHARED_VIEW_FIXTURE_V2',revision:seq,as_of:new Date(T).toISOString().replace('.000Z','Z'),synthetic:true,scientific_admission:false,prices:[{instrument:'EURUSD',price:1.25,observed_at:new Date(T).toISOString().replace('.000Z','Z'),source:'FIXTURE_PRICE',freshness:'WITHIN_DEMO_WINDOW'}],cot:pairs.map(pair=>({pair,status:'UNAVAILABLE',asset_gap:null,leveraged_gap:null,synthetic:true,scientific_admission:false})),sentiment:{myfxbook:'UNAVAILABLE',capital:'UNAVAILABLE'},delta:'UNAVAILABLE'};}
function validHead(seq=2,status='PUBLISHED'){return {schema:'REMURA_AUTHORITY_HEAD_FIXTURE_V024',generation:'fixture-v024-disposition',sequence:seq,revision:seq,intent_id:'synthetic-intent-'+seq,audience_subject:'lab-contributor',candidate_digest:hex('a'),journal_tag:hex('b'),authority_tag:hex(seq===2?'c':'d'),disposition:status,expires_at_ms:T+30000,signed_at_ms:T-1};}
function fixture(){
 const s={time:T,head:validHead(),view:validView(),identity:{role:'CONTRIBUTOR',subject:'lab-contributor',session_version:'session-1'},pin:{sequence:2,authority_tag:hex('c')},verified:true,authCalls:0,readCalls:0,verifyCalls:0};
 s.request=makeDispositionGatewayV024({
  clock:()=>s.time,
  authorize:async()=>{s.authCalls++;return copy(s.identity);},
  readConsistent:async()=>{s.readCalls++;return {head:copy(s.head),view:copy(s.view)};},
  verifyAuthority:async()=>{s.verifyCalls++;return s.verified;},
  readIndependentPin:async()=>copy(s.pin)
 });
 s.setDisposition=(seq,status)=>{s.head=validHead(seq,status);s.pin={sequence:seq,authority_tag:s.head.authority_tag};};
 return s;
}
function none(r){assert.notEqual(r.status,200);assert.ok(!r.body.includes('1.25'));assert.deepEqual(Object.keys(JSON.parse(r.body)).sort(),['schema','state']);assert.equal(r.headers['Cache-Control'],'no-store, max-age=0');assert.equal(r.headers.Vary,'Cookie, Authorization');}

test('real legacy V2 validator accepts authentic synthetic fixture',()=>{assert.equal(validateV2(validView(),T).prices[0].price,1.25);});
test('valid synthetic authority + external pin delivers V2 only',async()=>{const s=fixture();const r=await s.request();assert.equal(r.status,200);assert.equal(JSON.parse(r.body).schema,'REMURA_SHARED_VIEW_FIXTURE_V2');assert.equal(JSON.parse(r.body).prices[0].price,1.25);assert.equal(Object.hasOwn(JSON.parse(r.body),'authority_tag'),false);});
test('ABANDONED yields 410 without any market digits',async()=>{const s=fixture();s.setDisposition(3,'ABANDONED');none(await s.request());assert.equal((await s.request()).status,410);});
test('PENDING yields 409 without any market digits',async()=>{const s=fixture();s.setDisposition(3,'PENDING');const r=await s.request();none(r);assert.equal(r.status,409);});
test('missing authority verification fails closed',async()=>{const s=fixture();s.verified=false;const r=await s.request();none(r);assert.equal(r.status,503);});
test('independent witness missing fails closed',async()=>{const s=fixture();s.pin=null;const r=await s.request();none(r);assert.equal(r.status,503);});
test('old independent witness blocks rollback of head',async()=>{const s=fixture();s.pin={sequence:3,authority_tag:hex('d')};const r=await s.request();none(r);assert.equal(r.status,503);});
test('malformed independent witness blocks read',async()=>{const s=fixture();s.pin={sequence:'2',authority_tag:hex('c')};none(await s.request());});
test('missing trust hook refuses gateway construction',()=>{assert.throws(()=>makeDispositionGatewayV024({}),/NO_TRUST_ADAPTER/);});
test('wrong generation rejected',async()=>{const s=fixture();s.head.generation='fixture-v023-abandonment';none(await s.request());});
test('wrong viewer role denied before data read',async()=>{const s=fixture();s.identity.role='VIEWER';const r=await s.request();none(r);assert.equal(r.status,403);assert.equal(s.readCalls,0);});
test('other Contributor cannot read someone else snapshot',async()=>{const s=fixture();s.identity.subject='attacker';const r=await s.request();none(r);assert.equal(r.status,403);});
test('revoked role during request denied after proof',async()=>{const s=fixture();const old=s.request;s.request=makeDispositionGatewayV024({clock:()=>s.time,authorize:async()=>++s.authCalls===1?copy(s.identity):{...s.identity,role:'VIEWER'},readConsistent:async()=>({head:copy(s.head),view:copy(s.view)}),verifyAuthority:async()=>true,readIndependentPin:async()=>copy(s.pin)});const r=await s.request();none(r);assert.equal(r.status,403);});
test('session rotation during read rejects',async()=>{const s=fixture();let i=0;s.request=makeDispositionGatewayV024({clock:()=>s.time,authorize:async()=>({...s.identity,session_version:'session-'+(++i)}),readConsistent:async()=>({head:copy(s.head),view:copy(s.view)}),verifyAuthority:async()=>true,readIndependentPin:async()=>copy(s.pin)});none(await s.request());});
test('future signed date rejected',async()=>{const s=fixture();s.head.signed_at_ms=T+1;none(await s.request());});
test('expired publication rejected',async()=>{const s=fixture();s.time=T+30001;none(await s.request());});
test('end-of-request expiry rejected',async()=>{const s=fixture();let c=0;s.request=makeDispositionGatewayV024({clock:()=>++c===1?T:T+30001,authorize:async()=>copy(s.identity),readConsistent:async()=>({head:copy(s.head),view:copy(s.view)}),verifyAuthority:async()=>true,readIndependentPin:async()=>copy(s.pin)});none(await s.request());});
test('clock regression rejected without numbers',async()=>{const s=fixture();let c=0;s.request=makeDispositionGatewayV024({clock:()=>++c===1?T:T-1,authorize:async()=>copy(s.identity),readConsistent:async()=>({head:copy(s.head),view:copy(s.view)}),verifyAuthority:async()=>true,readIndependentPin:async()=>copy(s.pin)});none(await s.request());});
test('invalid V2 or V1 cannot pass new gateway',async()=>{const s=fixture();s.view.schema='REMURA_SHARED_VIEW_FIXTURE_V1';none(await s.request());});
test('extra private view property denied',async()=>{const s=fixture();s.view.internal_token='not-public';none(await s.request());});
test('revision mismatch never exposes older body',async()=>{const s=fixture();s.head.revision=3;s.head.sequence=3;s.pin.sequence=3;s.pin.authority_tag=s.head.authority_tag;none(await s.request());});
test('tampered audience subject rejected',async()=>{const s=fixture();s.head.audience_subject='another';const r=await s.request();none(r);assert.equal(r.status,403);});
test('unknown disposition rejected',async()=>{const s=fixture();s.head.disposition='RECOVERED';none(await s.request());});
test('malformed trusted snapshot rejected',async()=>{const s=fixture();s.view=null;none(await s.request());});
test('changed independent pin before return denied',async()=>{const s=fixture();let n=0;s.request=makeDispositionGatewayV024({clock:()=>s.time,authorize:async()=>copy(s.identity),readConsistent:async()=>({head:copy(s.head),view:copy(s.view)}),verifyAuthority:async()=>true,readIndependentPin:async()=>++n===1?copy(s.pin):{sequence:3,authority_tag:hex('d')}});none(await s.request());});
test('authority provider exception denies',async()=>{const s=fixture();s.request=makeDispositionGatewayV024({clock:()=>s.time,authorize:async()=>copy(s.identity),readConsistent:async()=>{throw Error('offline fixture outage')},verifyAuthority:async()=>true,readIndependentPin:async()=>copy(s.pin)});none(await s.request());});
test('v0.23 raw candidate rejected by legacy V2 parser',()=>{assert.throws(()=>validateV2({schema:'REMURA_V023_SYNTHETIC_ONLY',revision:2,as_of:T,market:{price:999}},T));});
test('legacy V2 consumer hides old visible value after authenticated ABANDONED',async()=>{const s=fixture();const c=makeConsumerV2({request:s.request,clock:()=>s.time});assert.equal(await c.refresh(),'READY');assert.equal(c.read().prices[0].price,1.25);s.setDisposition(3,'ABANDONED');s.time=T+1;assert.equal(await c.refresh(),'UNAVAILABLE');assert.equal(c.read(),null);});
test('legacy V2 consumer hides old visible value after PENDING',async()=>{const s=fixture();const c=makeConsumerV2({request:s.request,clock:()=>s.time});assert.equal(await c.refresh(),'READY');s.setDisposition(3,'PENDING');s.time=T+1;assert.equal(await c.refresh(),'UNAVAILABLE');assert.equal(c.read(),null);});
test('legacy V2 consumer closes when session revoked',async()=>{const s=fixture();const c=makeConsumerV2({request:s.request,clock:()=>s.time});assert.equal(await c.refresh(),'READY');s.identity.role='VIEWER';s.time=T+1;assert.equal(await c.refresh(),'DENIED');assert.equal(c.read(),null);});
test('legacy V2 consumer cancels late result after logout',async()=>{const s=fixture();let unlock;const delayed=()=>new Promise(resolve=>unlock=resolve);const c=makeConsumerV2({request:delayed,clock:()=>T});const wait=c.refresh();c.close();unlock(await s.request());assert.equal(await wait,'CANCELLED');assert.equal(c.read(),null);});
test('no status response contains market schema or 999',async()=>{for(const status of ['PENDING','ABANDONED']){const s=fixture();s.setDisposition(3,status);const r=await s.request();none(r);assert.ok(!r.body.includes('999'));assert.ok(!r.body.includes('REMURA_SHARED_VIEW_FIXTURE_V2'));}});

test('Home v0.22 receives null after abandoned refresh, no stale number render',async()=>{
 const s=fixture(),session=makeConsumerV2({request:s.request,clock:()=>s.time}),seen=[], statuses=[];
 const home=createHomeV2({session,clock:()=>s.time,role:()=>s.identity.role,panel:()=> 'Stato prezzi',renderInfo:(_panel,v)=>seen.push(v?.prices[0]?.price??null),renderStatus:v=>statuses.push(v?.revision??null),onDenied:()=>{},schedule:()=>({}),cancel:()=>{}});
 assert.equal(await home.refresh(),'READY');assert.equal(seen.at(-1),1.25);
 s.setDisposition(3,'ABANDONED');s.time=T+1;assert.equal(await home.refresh(),'UNAVAILABLE');assert.equal(seen.at(-1),null);assert.equal(statuses.at(-1),null);home.close();
});
