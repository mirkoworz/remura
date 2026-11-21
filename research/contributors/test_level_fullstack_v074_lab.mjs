// REMURA Contributors v0.74 LAB — only NEW integration cases, never historic suites.
import test from 'node:test';
import assert from 'node:assert/strict';
import {fixture,origin,reqId} from './fullstack_fixture_v066_lab.mjs';
import {privateWorkerCandidateV074 as worker} from './private_levels_composition_v074_lab.mjs';
const env=x=>({...x.env,PRIVATE_WORKER_V074:'OFFLINE_FIXTURE_ONLY',LEVEL_HTTP_V074:'OFFLINE_FIXTURE_ONLY',HTTP_CANDIDATE_ENABLED:'LAB_ONLY'});
const request=(p,body={},token)=>new Request(origin+p,{method:'POST',headers:{Origin:origin,'Sec-Fetch-Site':'same-origin','X-Remura-CSRF':'1','Content-Type':'application/json',...(token?{'X-Remura-Intent':token}:{})},body:JSON.stringify(body)});
const call=(x,p,body={},token,over={})=>worker(request(p,body,token),{...env(x),...over},x.ctx);
const get=(x,p,over={})=>worker(new Request(origin+p),{...env(x),...over},x.ctx);
const data=async r=>({status:r.status,...await r.json()});
const level=(id='3',src='1.234')=>({request_id:reqId(id),market:'EURUSD',provider:'OANDA',ticker:'EURUSD',product:'SPOT',contract:'',period:'DAY',kind:'DELTA_PEAK',price:src,anchor_utc:new Date(Date.now()-3600000).toISOString().slice(0,10)+'T00:00:00Z',observed_utc:new Date(Date.now()-600000).toISOString().slice(0,19)+'Z',note:'synthetic intake'});
async function intent(x,path,body){const r=await data(await call(x,'/api/intent',{path,body}));assert.equal(r.status,200,JSON.stringify(r));return r.data.intent;}
test('01 Alice gets contributor-only private iPhone entry page',async t=>{
 const x=await fixture(t),r=await get(x,'/contributors/levels/');assert.equal(r.status,200);assert.match(await r.text(),/REMURA .*v0\.74 LAB/);
});
test('02 contributor cannot access private OWNER level desk',async t=>{
 const x=await fixture(t);assert.equal((await get(x,'/owner/levels/')).status,403);
});
test('03 OWNER can access own level desk but not contributor page',async t=>{
 const x=await fixture(t);x.setWho('owner');assert.equal((await get(x,'/owner/levels/')).status,200);
 assert.equal((await get(x,'/contributors/levels/')).status,403);
});
test('04 static level form scripts are role separated',async t=>{
 const x=await fixture(t);assert.equal((await get(x,'/contributors/levels/contributors_levels_ui_v074_lab.mjs')).status,200);
 assert.equal((await get(x,'/owner/levels/contributors_levels_ui_v074_lab.mjs')).status,403);
});
test('05 original D1 profile verifies contributor role through new Worker',async t=>{
 const x=await fixture(t),r=await data(await call(x,'/api/profile'));assert.equal(r.status,200);assert.equal(r.data.role,'CONTRIBUTOR');assert.equal(r.data.can_read,true);
});
test('06 original D1 catalog returns only permitted exact mapping',async t=>{
 const x=await fixture(t),r=await data(await call(x,'/api/catalog'));assert.equal(r.status,200);assert.equal(r.data.length,1);assert.equal(r.data[0].market,'EURUSD');
});
test('07 original D1 personal receipts hide Bob entries from Alice',async t=>{
 const x=await fixture(t);const r=await data(await call(x,'/api/receipts',{after:0}));
 assert.equal(r.status,200);assert.equal(r.data.length,1);assert.equal(r.data[0].id,1);
});
test('08 original D1 personal receipts hide Alice entries from Bob',async t=>{
 const x=await fixture(t);x.setWho('bob');const r=await data(await call(x,'/api/receipts',{after:0}));
 assert.equal(r.status,200);assert.equal(r.data.length,1);assert.equal(r.data[0].id,2);
});
test('09 contributor cannot access OWNER queue even with known level ids',async t=>{
 const x=await fixture(t);assert.equal((await call(x,'/owner/queue',{after:0})).status,403);
});
test('10 contributor cannot approve their own level',async t=>{
 const x=await fixture(t);assert.equal((await call(x,'/owner/review',{id:1,action:'APPROVED',reason:'fraud'})).status,403);
});
test('11 owner cannot submit new contributor levels',async t=>{
 const x=await fixture(t);x.setWho('owner');assert.equal((await call(x,'/api/submit',level())).status,403);
});
test('12 OWNER can inspect original queue through new protected candidate',async t=>{
 const x=await fixture(t);x.setWho('owner');const r=await data(await call(x,'/owner/queue',{after:0}));
 assert.equal(r.status,200);assert.equal(r.data.length,2);
});
test('13 full synthetic level path: intent, insert, private receipt, OWNER approval',async t=>{
 const x=await fixture(t),p=level('3','1.234');const tk=await intent(x,'/api/submit',p);
 const submitted=await data(await call(x,'/api/submit',p,tk));assert.equal(submitted.status,200,JSON.stringify(submitted));
 assert.equal(submitted.data.status,'UNREVIEWED');assert.equal(submitted.data.duplicate,false);
 const own=await data(await call(x,'/api/receipts',{after:0}));assert.equal(own.status,200);assert.equal(own.data.length,2);
 const id=submitted.data.id;x.setWho('owner');
 const q=await data(await call(x,'/owner/queue',{after:0}));assert.equal(q.status,200);assert.equal(q.data.length,3);
 const d={id,action:'APPROVED',reason:'synthetic verified'};const t2=await intent(x,'/owner/review',d);
 const approved=await data(await call(x,'/owner/review',d,t2));assert.equal(approved.status,200);assert.equal(approved.data.action,'APPROVED');
 x.setWho('alice');const receipt=await data(await call(x,'/api/receipts',{after:id-1}));
 assert.equal(receipt.status,200);assert.equal(receipt.data.length,1);assert.equal(receipt.data[0].status,'APPROVED');
});
test('14 one-use HMAC intent replay does not create another level',async t=>{
 const x=await fixture(t),p=level('4','1.236'),tk=await intent(x,'/api/submit',p);
 const first=await data(await call(x,'/api/submit',p,tk));assert.equal(first.status,200);
 const before=x.n('lab_entries'),second=await call(x,'/api/submit',p,tk);
 assert.equal(second.status,409);assert.equal(x.n('lab_entries'),before);
});
test('15 refused user identity can never POST or load catalog',async t=>{
 const x=await fixture(t);x.db.prepare('UPDATE lab_identities SET revoked=1 WHERE subject=?').run(x.actors.alice.subject);
 assert.equal((await call(x,'/api/catalog')).status,403);assert.equal((await get(x,'/contributors/levels/')).status,403);
});
test('16 OWNER revocation disables privileged desk immediately',async t=>{
 const x=await fixture(t);x.db.prepare('UPDATE lab_owner SET revoked=1 WHERE subject=?').run(x.actors.owner.subject);x.setWho('owner');
 assert.equal((await get(x,'/owner/levels/')).status,403);assert.equal((await call(x,'/owner/queue',{after:0})).status,403);
});
test('17 D1 non-primary metadata makes private level page fail closed',async t=>{
 const x=await fixture(t);x.setPrimary(false);assert.equal((await get(x,'/contributors/levels/')).status,403);
 assert.equal((await call(x,'/api/catalog')).status,403);
});
test('18 rate limiter denial blocks level HTTP API',async t=>{
 const x=await fixture(t);x.setRate(false);assert.equal((await call(x,'/api/catalog')).status,403);
});
test('19 absent v0.74 switches prevent all staging and writes',async t=>{
 const x=await fixture(t);assert.equal((await worker(new Request(origin+'/contributors/levels/'),x.env,x.ctx)).status,403);
 assert.equal((await call(x,'/api/profile',{},undefined,{LEVEL_HTTP_V074:'DISABLED'})).status,403);
});
test('20 no real handler/default Worker export is enabled by fixture composition',async()=>{
 const m=await import('./private_levels_composition_v074_lab.mjs');
 assert.equal('default' in m,false);assert.equal('fetch' in m,false);
});
