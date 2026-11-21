// REMURA Contributors v0.64 LAB — synthetic Access context + complete SQL schema.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fixture} from './amendment_http_fixture_v062_lab.mjs';
import {inspectMyAmendmentRecoveryV064 as mine,inspectOwnerRecoveryQueueV064 as queue} from './reconciliation_reader_v064_lab.mjs';
const deny=async p=>assert.rejects(p,/RECONCILIATION_BLOCKED/);
async function setup(t){
 const x=await fixture(t);x.db.exec(readFileSync(new URL('./d1_reconciliation_v064_lab.sql',import.meta.url),'utf8'));
 x.env.RECONCILIATION_V064_ENABLED='OFFLINE_FIXTURE_ONLY';
 const stamp=v=>new Date(v).toISOString().slice(0,19)+'Z';
 const start=stamp(Date.now()-100000),received=stamp(Date.now()-30000),reviewed=stamp(Date.now()-20000),released=stamp(Date.now()-10000);
 const req=(n=3)=>'00000000-0000-4000-8000-'+String(n).padStart(12,'0');
 const reserve=(actor='alice',src=1,n=3)=>{
  const p=x.payload(src,n);return x.db.prepare('INSERT INTO lab_amend_attempts_v064(subject,request_id,source_entry_id,price,observed_utc,note,reserved_utc) VALUES(?,?,?,?,?,?,?)')
    .run(x.actors[actor].subject,p.request_id,src,p.price,p.observed_utc,p.note,start);
 };
 const commit=(actor='alice',src=1,n=3)=>{
  const p=x.payload(src,n);return x.db.prepare('INSERT INTO lab_level_amendments_v059(subject,source_entry_id,request_id,price,observed_utc,received_utc,note) VALUES(?,?,?,?,?,?,?)')
    .run(x.actors[actor].subject,src,p.request_id,p.price,p.observed_utc,received,p.note);
 };
 const review=(action='APPROVED')=>x.db.prepare('INSERT INTO lab_level_amendment_reviews_v059(amendment_id,owner,action,at_utc,reason) VALUES(?,?,?,?,?)').run(1,x.actors.owner.subject,action,reviewed,'fixture');
 const release=(type='REVIEWED')=>x.db.prepare('INSERT INTO lab_amend_releases_v064(attempt_id,owner,disposition,reason,released_utc) VALUES(?,?,?,?,?)').run(1,x.actors.owner.subject,type,'manual fixture',released);
 return {...x,req,reserve,commit,review,release};
}
test('01 authenticated Alice without attempts gets non-authorizing NO_ATTEMPT',async t=>{const x=await setup(t);assert.deepEqual(await mine(x.ctx,x.env),{status:'NO_ATTEMPT',mayResubmit:false,manualApprovalRequired:true});});
test('02 outstanding attempt shown after fresh request',async t=>{const x=await setup(t);x.reserve();const r=await mine(x.ctx,x.env);assert.equal(r.status,'UNRESOLVED');assert.equal(r.mayResubmit,false);});
test('03 committed but unreviewed remains locked',async t=>{const x=await setup(t);x.reserve();x.commit();assert.equal((await mine(x.ctx,x.env)).status,'COMMITTED_UNREVIEWED');});
test('04 reviewed but not released still locked',async t=>{const x=await setup(t);x.reserve();x.commit();x.review();assert.equal((await mine(x.ctx,x.env)).status,'COMMITTED_REVIEWED');});
test('05 released state still never gives authorization to resubmit',async t=>{const x=await setup(t);x.reserve();x.release('ABORTED_BY_OWNER');const r=await mine(x.ctx,x.env);assert.equal(r.status,'CLOSED');assert.equal(r.mayResubmit,false);});
test('06 approved and manually released visible as CLOSED',async t=>{const x=await setup(t);x.reserve();x.commit();x.review();x.release();assert.equal((await mine(x.ctx,x.env)).status,'CLOSED');});
test('07 request id returned but no price or note disclosed',async t=>{const x=await setup(t);x.reserve();const r=await mine(x.ctx,x.env);assert.equal(r.request_id,x.req());assert.equal('price'in r,false);assert.equal('note'in r,false);assert.equal('subject'in r,false);});
test('08 Bob cannot see Alice unresolved attempt',async t=>{const x=await setup(t);x.reserve();x.who('bob');assert.equal((await mine(x.ctx,x.env)).status,'NO_ATTEMPT');});
test('09 Alice cannot see OWNER recovery queue',async t=>{const x=await setup(t);x.reserve();await deny(queue(x.ctx,x.env));});
test('10 OWNER queue sees one unresolved subject',async t=>{const x=await setup(t);x.reserve();x.who('owner');const r=await queue(x.ctx,x.env);assert.equal(r.length,1);assert.equal(r[0].status,'UNRESOLVED');assert.equal(r[0].subject,x.actors.alice.subject);});
test('11 OWNER queue excludes already-released attempts',async t=>{const x=await setup(t);x.reserve();x.release('ABORTED_BY_OWNER');x.who('owner');assert.deepEqual(await queue(x.ctx,x.env),[]);});
test('12 OWNER queue shows committed pending review',async t=>{const x=await setup(t);x.reserve();x.commit();x.who('owner');assert.equal((await queue(x.ctx,x.env))[0].status,'COMMITTED_UNREVIEWED');});
test('13 OWNER queue shows reviewed but still locked',async t=>{const x=await setup(t);x.reserve();x.commit();x.review();x.who('owner');assert.equal((await queue(x.ctx,x.env))[0].status,'COMMITTED_REVIEWED');});
test('14 OWNER review after revoked contributor does not bypass read gate',async t=>{const x=await setup(t);x.reserve();x.db.prepare('UPDATE lab_identities SET revoked=1 WHERE subject=?').run(x.actors.alice.subject);await deny(mine(x.ctx,x.env));});
test('15 removed trusted ctx denies',async t=>{const x=await setup(t);x.ctx.access=null;await deny(mine(x.ctx,x.env));});
test('16 wrong Access audience denies',async t=>{const x=await setup(t);x.ctx.access.aud='0'.repeat(64);await deny(mine(x.ctx,x.env));});
test('17 service-token identity denies',async t=>{const x=await setup(t);x.identity('alice').service_token_status=true;await deny(mine(x.ctx,x.env));x.identity('alice').service_token_status=false;});
test('18 missing feature gate denies',async t=>{const x=await setup(t);delete x.env.RECONCILIATION_V064_ENABLED;await deny(mine(x.ctx,x.env));});
test('19 wrong generation denies',async t=>{const x=await setup(t);x.env.CONTRIBUTORS_GENERATION='f'.repeat(32);await deny(mine(x.ctx,x.env));});
test('20 absent rate limiter denies',async t=>{const x=await setup(t);delete x.env.CONTRIBUTORS_RATE_LIMITER;await deny(mine(x.ctx,x.env));});
test('21 limiter rejection denies',async t=>{const x=await setup(t);x.env.CONTRIBUTORS_RATE_LIMITER={limit:async()=>({success:false})};await deny(mine(x.ctx,x.env));});
test('22 read-disabled denies',async t=>{const x=await setup(t);x.db.exec('UPDATE lab_state SET read_enabled=0');await deny(mine(x.ctx,x.env));});
test('23 primary metadata must confirm true',async t=>{const x=await setup(t);x.hooks.badReadPrimary=true;await deny(mine(x.ctx,x.env));});
test('24 invalid owner pagination fails before DB access',async t=>{const x=await setup(t);x.who('owner');await deny(queue(x.ctx,x.env,-1));});
test('25 changed identity between gate and return blocked',async t=>{const x=await setup(t);x.reserve();let count=0;x.hooks.read=()=>{count++;if(count===3)x.who('bob')};await deny(mine(x.ctx,x.env));});
test('26 recovery API never writes',async t=>{const x=await setup(t);x.reserve();const before=x.counts().writes;await mine(x.ctx,x.env);x.who('owner');await queue(x.ctx,x.env);assert.equal(x.counts().writes,before);});
test('27 owner cannot use contributor recovery endpoint',async t=>{const x=await setup(t);x.who('owner');await deny(mine(x.ctx,x.env));});
test('28 contributor request state remains non-authorizing after refresh-equivalent second reader',async t=>{const x=await setup(t);x.reserve();assert.equal((await mine(x.ctx,x.env)).status,'UNRESOLVED');assert.equal((await mine(x.ctx,x.env)).status,'UNRESOLVED');});
