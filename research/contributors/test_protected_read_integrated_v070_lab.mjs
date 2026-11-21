// REMURA Contributors v0.70 LAB — NEW targeted integration of the v0.69 bridge
// with the ORIGINAL v0.66 SQLite/D1 fixture; historical v0.66 suites are not rerun.
// Run: node --test research/contributors/test_protected_read_integrated_v070_lab.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import {fixture,origin,reqId,reconcile,queue} from './fullstack_fixture_v066_lab.mjs';
import {protectedReadCandidateV069 as read} from './protected_read_composition_v069_lab.mjs';
const headers={Origin:origin,'Sec-Fetch-Site':'same-origin','X-Remura-CSRF':'1','Content-Type':'application/json'};
const request=(path=reconcile,body={},override={})=>new Request(origin+path,{method:'POST',headers:{...headers,...override},body:JSON.stringify(body)});
const env=x=>({...x.env,READ_BRIDGE_V069:'OFFLINE_FIXTURE_ONLY'});
const call=(x,path=reconcile,body={},over={},requestHeaders={})=>read(request(path,body,requestHeaders),{...env(x),...over},x.ctx);
const result=async r=>({status:r.status,body:await r.json()});
test('01 original fixture Access+HMAC+D1 profile admits Alice recovery via new bridge',async t=>{
 const x=await fixture(t);const v=await result(await call(x));assert.equal(v.status,200);assert.equal(v.body.data.status,'NO_ATTEMPT');
});
test('02 original fixture receipts endpoint is served through new bridge',async t=>{
 const x=await fixture(t);const v=await result(await call(x,'/api/amendment/mine',{after:0}));assert.equal(v.status,200);assert.equal(v.body.data.length,1);assert.equal(v.body.data[0].id,1);
});
test('03 OWNER can inspect reservation queue through new bridge',async t=>{
 const x=await fixture(t);assert.equal((await x.submitWith(x.payload())).status,200);x.setWho('owner');
 const v=await result(await call(x,queue,{after:0}));assert.equal(v.status,200);assert.equal(v.body.data.length,1);assert.equal(v.body.data[0].request_id,reqId(3));
});
test('04 Alice cannot elevate to OWNER even when route is direct',async t=>{
 const x=await fixture(t);assert.equal((await call(x,queue,{after:0})).status,403);
});
test('05 OWNER cannot impersonate a contributor in recovery view',async t=>{
 const x=await fixture(t);x.setWho('owner');assert.equal((await call(x)).status,403);
});
test('06 Bob never receives Alice reservation through the new bridge',async t=>{
 const x=await fixture(t);assert.equal((await x.submitWith(x.payload())).status,200);x.setWho('bob');
 const v=await result(await call(x));assert.equal(v.status,200);assert.equal(v.body.data.status,'NO_ATTEMPT');
});
test('07 personal receipts remain partitioned by D1 subject',async t=>{
 const x=await fixture(t);x.setWho('bob');const v=await result(await call(x,'/api/amendment/mine',{after:0}));
 assert.equal(v.status,200);assert.equal(v.body.data.length,1);assert.equal(v.body.data[0].id,2);
});
test('08 read bridge cannot write D1',async t=>{
 const x=await fixture(t),before=x.counts.write;await call(x);await call(x,'/api/amendment/mine',{after:0});
 assert.equal(x.counts.write,before);
});
test('09 contributor DB revocation blocks bridge immediately',async t=>{
 const x=await fixture(t);x.db.prepare('UPDATE lab_identities SET revoked=1 WHERE subject=?').run(x.actors.alice.subject);
 assert.equal((await call(x)).status,403);
});
test('10 OWNER DB revocation blocks recovery queue',async t=>{
 const x=await fixture(t);x.db.prepare('UPDATE lab_owner SET revoked=1 WHERE subject=?').run(x.actors.owner.subject);x.setWho('owner');
 assert.equal((await call(x,queue,{after:0})).status,403);
});
test('11 primary-only metadata denial blocks reads',async t=>{
 const x=await fixture(t);x.setPrimary(false);assert.equal((await call(x)).status,403);
});
test('12 fixture limiter denial blocks the backend',async t=>{
 const x=await fixture(t);x.setRate(false);assert.equal((await call(x)).status,403);
});
test('13 wrong Access audience blocks pre-DB entry',async t=>{
 const x=await fixture(t);x.ctx.access.aud='f'.repeat(64);assert.equal((await call(x)).status,403);
});
test('14 Access service token is refused by original accessBinding',async t=>{
 const x=await fixture(t);x.identity('alice').service_token_status=true;t.after(()=>{x.identity('alice').service_token_status=false});
 assert.equal((await call(x)).status,403);
});
test('15 changing generation pin denies persisted reconciliation',async t=>{
 const x=await fixture(t);assert.equal((await call(x,reconcile,{}, {CONTRIBUTORS_JOURNAL_PIN:'f'.repeat(64)})).status,403);
});
test('16 missing v0.70 lab flag fails closed, never enables production',async t=>{
 const x=await fixture(t);assert.equal((await read(request(),x.env,x.ctx)).status,403);
});
test('17 forged user-role header is refused before original backend',async t=>{
 const x=await fixture(t);assert.equal((await call(x,reconcile,{}, {},{'X-Remura-Role':'OWNER'})).status,403);
});
test('18 cross-site request is refused before original backend',async t=>{
 const x=await fixture(t);assert.equal((await call(x,reconcile,{}, {},{'Sec-Fetch-Site':'cross-site'})).status,403);
});
test('19 oversized JSON never gets read by original backend',async t=>{
 const x=await fixture(t);assert.equal((await call(x,reconcile,{untrusted:'x'.repeat(5000)})).status,403);
});
test('20 mutation cannot use read-only bridge, even with a valid profile',async t=>{
 const x=await fixture(t),before=x.counts.write;assert.equal((await call(x,'/api/amendment/submit',x.payload())).status,403);
 assert.equal((await call(x,'/owner/amendment/review',{id:1,action:'APPROVED',reason:'attack'})).status,403);
 assert.equal(x.counts.write,before);
});
test('21 invalid receipt cursor fails before any backend callback',async t=>{
 const x=await fixture(t);assert.equal((await call(x,'/api/amendment/mine',{after:-1})).status,403);
});
test('22 failed original D1 read never leaks SQL errors',async t=>{
 const x=await fixture(t);x.setFailure('beforeRead');const r=await call(x);assert.equal(r.status,403);
 assert.equal((await r.text()).includes('synthetic read'),false);
});
test('23 no-store output retained for real fixture handler response',async t=>{
 const x=await fixture(t);const r=await call(x);assert.equal(r.status,200);assert.match(r.headers.get('Cache-Control'),/no-store/);
});
test('24 no live Worker entrypoint is exported by protected composition',async()=>{
 const module=await import('./protected_read_composition_v069_lab.mjs');assert.equal('default' in module,false);assert.equal('fetch' in module,false);
});
