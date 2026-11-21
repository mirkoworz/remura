// REMURA v0.66 LAB — 45 genuinely new end-to-end cases against exact full D1 schema.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {fixture,json,clock,origin,identities,handler,submit,intent,reconcile,review,queue} from './fullstack_fixture_v066_lab.mjs';
test('01 byte-exact original base + two additive schema layers',async t=>{
 const names=['d1_access_candidate.sql','d1_amendment_v059_lab.sql','d1_reconciliation_v064_lab.sql'];
 const digests=['9ed38b6ed83755186af05f1bf28b4608cdc5f901','289cb54f0b3e33976b255ce976ca5e00bc43ab3c','2cc5f0ccdda660771bc56dc4ddb34bfc942f973a'];
 for(let i=0;i<names.length;i++){const raw=readFileSync(new URL('./'+names[i],import.meta.url));assert.equal(createHash('sha1').update('blob '+raw.length+'\0').update(raw).digest('hex'),digests[i]);}
 const x=await fixture(t);assert.equal(x.db.prepare('PRAGMA foreign_key_check').all().length,0);
});
test('02 real Access HMAC + real HMAC intent + original SQLite full-schema success',async t=>{
 const x=await fixture(t),p=x.payload();const r=await x.submitWith(p);const j=await json(r);
 assert.equal(j.status,200);assert.equal(j.data.status,'UNREVIEWED');assert.equal(x.n('lab_amend_attempts_v064'),1);assert.equal(x.n('lab_intent_used'),1);assert.equal(x.n('lab_level_amendments_v059'),1);
});
test('03 confirmed request remains COMMITTED_UNREVIEWED, not released',async t=>{const x=await fixture(t);await x.submitWith(x.payload());assert.equal((await x.getState()).data.status,'COMMITTED_UNREVIEWED');assert.equal((await x.getState()).data.mayResubmit,false);});
test('04 Alice cannot modify Bob source entry with genuine triggers',async t=>{const x=await fixture(t);const r=await x.submitWith(x.payload(3,2));assert.equal(r.status,409);assert.equal(x.n('lab_level_amendments_v059'),0);});
test('05 Alice cannot see Bob recovery records',async t=>{const x=await fixture(t);await x.submitWith(x.payload());x.setWho('bob');assert.equal((await x.getState()).data.status,'NO_ATTEMPT');});
test('06 Bob cannot write Alice source entry',async t=>{const x=await fixture(t);x.setWho('bob');const r=await x.submitWith(x.payload());assert.equal(r.status,409);});
test('07 parent original is unchanged after confirmed correction',async t=>{const x=await fixture(t);await x.submitWith(x.payload());assert.equal(x.db.prepare('SELECT price FROM lab_entries WHERE id=1').get().price,'1.123');});
test('08 no attempt before intent issuance',async t=>{const x=await fixture(t);await x.issue(submit,x.payload());assert.equal(x.n('lab_amend_attempts_v064'),0);});
test('09 missing HMAC token cannot reserve',async t=>{const x=await fixture(t);assert.equal((await x.call(submit,x.payload())).status,409);assert.equal(x.n('lab_amend_attempts_v064'),0);});
test('10 tampered signed body fails without reservation',async t=>{const x=await fixture(t),p=x.payload(),token=await x.issue(submit,p);const r=await x.call(submit,{...p,price:'9.9'},token);assert.equal(r.status,409);assert.equal(x.n('lab_amend_attempts_v064'),0);});
test('11 replay of same intent after success is denied without new reservation',async t=>{const x=await fixture(t),p=x.payload(),token=await x.issue(submit,p);assert.equal((await x.call(submit,p,token)).status,200);assert.equal((await x.call(submit,p,token)).status,409);assert.equal(x.n('lab_amend_attempts_v064'),1);});
test('12 second intent while first unresolved fails in SQL',async t=>{const x=await fixture(t);await x.submitWith(x.payload());const r=await x.submitWith(x.payload(4));assert.equal(r.status,409);assert.equal(x.n('lab_amend_attempts_v064'),1);});
test('13 late response lost after reservation leaves lock and status UNRESOLVED',async t=>{
 const x=await fixture(t);let reserved=false;x.setAfterWrite(sql=>{if(sql.includes('lab_amend_attempts_v064')){reserved=true;throw Error('lost reservation acknowledgement')}});
 const p=x.payload();assert.equal((await x.submitWith(p)).status,409);assert.equal(reserved,true);assert.equal(x.n('lab_amend_attempts_v064'),1);assert.equal(x.n('lab_level_amendments_v059'),0);x.setAfterWrite(null);assert.equal((await x.getState()).data.status,'UNRESOLVED');
});
test('14 no implicit resubmission after lost reservation response',async t=>{
 const x=await fixture(t);x.setAfterWrite(sql=>{if(sql.includes('lab_amend_attempts_v064'))throw Error('lost')});await x.submitWith(x.payload());x.setAfterWrite(null);
 const r=await x.submitWith(x.payload(4));assert.equal(r.status,409);assert.equal(x.n('lab_amend_attempts_v064'),1);
});
test('15 lost write response after insert survives recovery across new requests',async t=>{
 const x=await fixture(t);x.setAfterWrite(sql=>{if(sql.includes('lab_level_amendments_v059'))throw Error('lost commit reply')});
 assert.equal((await x.submitWith(x.payload())).status,409);x.setAfterWrite(null);assert.equal(x.n('lab_level_amendments_v059'),1);assert.equal((await x.getState()).data.status,'COMMITTED_UNREVIEWED');
});
test('16 recovery endpoint cannot release or submit',async t=>{const x=await fixture(t);await x.submitWith(x.payload());await x.getState();assert.equal(x.n('lab_amend_releases_v064'),0);});
test('17 owner queue sees recovery lock while Alice cannot see it',async t=>{
 const x=await fixture(t);await x.submitWith(x.payload());assert.equal((await x.call(queue,{after:0})).status,403);x.setWho('owner');const r=await json(await x.call(queue,{after:0}));assert.equal(r.status,200);assert.equal(r.data.length,1);
});
test('18 owner APPROVED changes projection but not release until manual closure',async t=>{
 const x=await fixture(t);await x.submitWith(x.payload());x.setWho('owner');const res=await x.reviewWith({id:1,action:'APPROVED',reason:'fixture'});assert.equal(res.status,200);
 assert.equal(x.n('lab_amend_releases_v064'),0);x.setWho('alice');assert.equal((await x.getState()).data.status,'COMMITTED_REVIEWED');
 const r=await json(await x.call('/api/amendment/approved',{}));assert.equal(r.status,200);assert.equal(r.data[0].price,'1.234');
});
test('19 owner can manually close only after review with SQL guard',async t=>{
 const x=await fixture(t);await x.submitWith(x.payload());x.setWho('owner');await x.reviewWith({id:1,action:'APPROVED',reason:'fixture'});
 x.db.prepare('INSERT INTO lab_amend_releases_v064(attempt_id,owner,disposition,reason,released_utc) VALUES(?,?,?,?,?)').run(1,x.actors.owner.subject,'REVIEWED','verified offline',clock());
 x.setWho('alice');assert.equal((await x.getState()).data.status,'CLOSED');
});
test('20 contributor never receives resubmit=true even after owner release',async t=>{
 const x=await fixture(t);await x.submitWith(x.payload());x.setWho('owner');await x.reviewWith({id:1,action:'REJECTED',reason:'fixture'});
 x.db.prepare('INSERT INTO lab_amend_releases_v064(attempt_id,owner,disposition,reason,released_utc) VALUES(?,?,?,?,?)').run(1,x.actors.owner.subject,'REVIEWED','verified offline',clock());
 x.setWho('alice');const s=(await x.getState()).data;assert.equal(s.status,'CLOSED');assert.equal(s.mayResubmit,false);
});
test('21 an unauthorized owner impersonation cannot approve',async t=>{const x=await fixture(t);await x.submitWith(x.payload());const out=await x.call(review,{id:1,action:'APPROVED',reason:'fake'},'bad');assert.equal(out.status,409);});
test('22 revoked user cannot read their old recovery after access lost',async t=>{const x=await fixture(t);await x.submitWith(x.payload());x.db.prepare('UPDATE lab_identities SET revoked=1 WHERE subject=?').run(x.actors.alice.subject);assert.equal((await x.call(reconcile,{})).status,403);});
test('23 role-separated owner cannot access contributor-only recovery',async t=>{const x=await fixture(t);x.setWho('owner');assert.equal((await x.call(reconcile,{})).status,403);});
test('24 Access identity changes after intent burn blocks reservation',async t=>{
 const x=await fixture(t),p=x.payload();const tk=await x.issue(submit,p);x.setWho('bob');const r=await x.call(submit,p,tk);assert.equal(r.status,409);assert.equal(x.n('lab_amend_attempts_v064'),0);
});
test('25 missing primary metadata denies new reservation',async t=>{const x=await fixture(t);const tk=await x.issue(submit,x.payload());x.setPrimary(false);const r=await x.call(submit,x.payload(),tk);assert.equal(r.status,409);});
test('26 wrong generation disables intent issuance',async t=>{const x=await fixture(t);x.env.CONTRIBUTORS_GENERATION='a'.repeat(32);const r=await json(await x.call(intent,{path:submit,body:x.payload()}));assert.equal(r.status,403);});
test('27 missing rate limiter denies issue',async t=>{const x=await fixture(t);x.setRate(false);assert.equal((await x.call(intent,{path:submit,body:x.payload()})).status,403);});
test('28 origin/CSRF must be present for status lookup',async t=>{const x=await fixture(t);assert.equal((await x.call(reconcile,{},undefined,{headers:{Origin:'https://evil.invalid'}})).status,403);});
test('29 malformed payload cannot burn intent',async t=>{const x=await fixture(t);const r=await x.call(submit,{...x.payload(),price:'1e9'});assert.equal(r.status,400);assert.equal(x.n('lab_intent_used'),0);});
test('30 all three schema layers retain intact foreign keys',async t=>{const x=await fixture(t);await x.submitWith(x.payload());assert.deepEqual(x.db.prepare('PRAGMA foreign_key_check').all(),[]);});

test('31 two independent tabs of same contributor contend, exactly one reaches durable mutation',async t=>{
 const x=await fixture(t);
 const [a,b]=await Promise.all([x.submitWith(x.payload(3)),x.submitWith(x.payload(4))]);
 assert.deepEqual([a.status,b.status].sort(),[200,409]);
 assert.equal(x.n('lab_amend_attempts_v064'),1);assert.equal(x.n('lab_level_amendments_v059'),1);
});
test('32 independent Access contexts for Alice and Bob may submit their separate originals concurrently',async t=>{
 const x=await fixture(t);
 async function sendAs(name,p){
  const identityCtx={access:{aud:x.env.ACCESS_AUD,async getIdentity(){return {...identities[name]};}}};
  async function dispatch(path,body,token){
   const hdr={Origin:origin,'Sec-Fetch-Site':'same-origin','X-Remura-CSRF':'1','Content-Type':'application/json'};
   if(token)hdr['X-Remura-Intent']=token;
   return handler(new Request(origin+path,{method:'POST',headers:hdr,body:JSON.stringify(body)}),x.env,identityCtx);
  }
  const issued=await dispatch(intent,{path:submit,body:p});assert.equal(issued.status,200);
  return dispatch(submit,p,(await issued.json()).data.intent);
 }
 const [a,b]=await Promise.all([sendAs('alice',x.payload(3,1)),sendAs('bob',x.payload(4,2))]);
 assert.deepEqual([a.status,b.status],[200,200]);
 assert.equal(x.n('lab_amend_attempts_v064'),2);assert.equal(x.n('lab_level_amendments_v059'),2);
});
test('33 explicit separate browser tab can read shared state after a completed write',async t=>{
 const x=await fixture(t);await x.submitWith(x.payload());
 const newTabResponse=await x.call(reconcile,{});const j=await newTabResponse.json();
 assert.equal(j.data.status,'COMMITTED_UNREVIEWED');assert.equal(j.data.mayResubmit,false);
});
test('34 logout invalidates recovery; login again keeps the durable lock',async t=>{
 const x=await fixture(t);await x.submitWith(x.payload());
 const trusted=x.ctx.access;x.ctx.access=null;assert.equal((await x.call(reconcile,{})).status,403);
 x.ctx.access=trusted;assert.equal((await x.getState()).data.status,'COMMITTED_UNREVIEWED');
});
test('35 revocation occurs after intent burn but before reservation: SQL blocks write',async t=>{
 const x=await fixture(t),p=x.payload();
 x.setAfterWrite((sql)=>{if(sql.includes('lab_intent_used'))x.db.prepare('UPDATE lab_identities SET revoked=1 WHERE subject=?').run(x.actors.alice.subject)});
 const r=await x.submitWith(p);assert.equal(r.status,409);assert.equal(x.n('lab_intent_used'),1);assert.equal(x.n('lab_amend_attempts_v064'),0);
});
test('36 revocation after reservation but before amendment leaves owner-visible unresolved latch',async t=>{
 const x=await fixture(t);
 x.setAfterWrite(sql=>{if(sql.includes('INSERT INTO lab_amend_attempts_v064'))x.db.prepare('UPDATE lab_identities SET revoked=1 WHERE subject=?').run(x.actors.alice.subject)});
 assert.equal((await x.submitWith(x.payload())).status,409);assert.equal(x.n('lab_amend_attempts_v064'),1);assert.equal(x.n('lab_level_amendments_v059'),0);
 x.setWho('owner');const status=await json(await x.call(queue,{after:0}));assert.equal(status.status,200);assert.equal(status.data[0].status,'UNRESOLVED');
});
test('37 owner recovery queue cannot be read if owner access revoked',async t=>{
 const x=await fixture(t);await x.submitWith(x.payload());x.db.exec('UPDATE lab_owner SET revoked=1');x.setWho('owner');assert.equal((await x.call(queue,{after:0})).status,403);
});
test('38 unsupported service token denies issuing HMAC token',async t=>{
 const x=await fixture(t);x.identity('alice').service_token_status=true;
 assert.equal((await x.call(intent,{path:submit,body:x.payload()})).status,403);
 x.identity('alice').service_token_status=false;
});
test('39 disabled read mode hides recovery without deleting the reservation',async t=>{
 const x=await fixture(t);await x.submitWith(x.payload());x.db.exec('UPDATE lab_state SET read_enabled=0');
 assert.equal((await x.call(reconcile,{})).status,403);assert.equal(x.n('lab_amend_attempts_v064'),1);
});
test('40 disabled write mode blocks new intent while read-only recovery remains available',async t=>{
 const x=await fixture(t);await x.submitWith(x.payload());x.db.exec('UPDATE lab_state SET write_enabled=0');
 assert.equal((await x.call(intent,{path:submit,body:x.payload(4)})).status,403);
 assert.equal((await x.getState()).data.status,'COMMITTED_UNREVIEWED');
});
test('41 D1 primary metadata denial on recovery fails closed',async t=>{
 const x=await fixture(t);await x.submitWith(x.payload());x.setPrimary(false);assert.equal((await x.call(reconcile,{})).status,403);
});
test('42 source original revoked between request and owner approval cannot become visible',async t=>{
 const x=await fixture(t);await x.submitWith(x.payload());x.setWho('owner');
 x.db.prepare('INSERT INTO lab_reviews(entry_id,owner,action,at_utc,reason) VALUES(?,?,?,?,?)').run(1,x.actors.owner.subject,'REVOKED',clock(),'fixture');
 assert.equal((await x.reviewWith({id:1,action:'APPROVED',reason:'invalidated source'})).status,409);
 x.setWho('bob');const levels=await json(await x.call('/api/amendment/approved',{}));assert.equal(levels.status,200);assert.equal(levels.data.some(v=>v.id===1),false);
});
test('43 release of committed-but-unreviewed request is denied by SQL',async t=>{
 const x=await fixture(t);await x.submitWith(x.payload());
 assert.throws(()=>x.db.prepare('INSERT INTO lab_amend_releases_v064(attempt_id,owner,disposition,reason,released_utc) VALUES(?,?,?,?,?)').run(1,x.actors.owner.subject,'REVIEWED','fixture',clock()),/unreviewed_attempt/);
});
test('44 manual abort after fully ambiguous reservation blocks delayed mutation',async t=>{
 const x=await fixture(t),p=x.payload();
 x.setAfterWrite(sql=>{if(sql.includes('lab_amend_attempts_v064'))throw Error('ambiguous reserve')});
 assert.equal((await x.submitWith(p)).status,409);x.setAfterWrite(null);
 x.db.prepare('INSERT INTO lab_amend_releases_v064(attempt_id,owner,disposition,reason,released_utc) VALUES(?,?,?,?,?)').run(1,x.actors.owner.subject,'ABORTED_BY_OWNER','verified offline',clock());
 assert.throws(()=>x.db.prepare('INSERT INTO lab_level_amendments_v059(subject,source_entry_id,request_id,price,observed_utc,received_utc,note) VALUES(?,?,?,?,?,?,?)').run(x.actors.alice.subject,p.source_entry_id,p.request_id,p.price,p.observed_utc,clock(),p.note),/reservation_required/);
});
test('45 wrong generation pin on recovery denies stale second-tab view',async t=>{
 const x=await fixture(t);await x.submitWith(x.payload());x.env.CONTRIBUTORS_JOURNAL_PIN='0'.repeat(64);
 assert.equal((await x.call(reconcile,{})).status,403);
});
