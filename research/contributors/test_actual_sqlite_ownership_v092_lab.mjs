// REMURA Contributors v0.92 LAB — original full SQL on in-memory SQLite.
// New cases only. No Cloudflare D1 SQL, provider, secrets or deploy.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
import {accessBinding} from './access_binding_candidate.mjs';
import {submit,receipts,queue,history,review,revokeContributor} from './d1_access_candidate.mjs';
import {privateWorkerCandidateV092 as worker} from './private_worker_composition_v092_lab.mjs';
import {normalizeNewLevelV076,newLevelFingerprintV076,claimNewLevelV076,inspectNewLevelV076} from './level_attempt_journal_v076_lab.mjs';

const ORIGIN='https://sql-fixture.remura.invalid';
const ACCOUNT='b'.repeat(32),AUD='a'.repeat(64);
const USERS=Object.freeze({
 a:{account_id:ACCOUNT,user_uuid:'11111111-1111-4111-8111-111111111111',email:'a@invalid.test',service_token_status:false,service_token_id:null},
 b:{account_id:ACCOUNT,user_uuid:'22222222-2222-4222-8222-222222222222',email:'b@invalid.test',service_token_status:false,service_token_id:null},
 owner:{account_id:ACCOUNT,user_uuid:'33333333-3333-4333-8333-333333333333',email:'owner@invalid.test',service_token_status:false,service_token_id:null}
});
const PAYLOAD=(id,price)=>({
 request_id:id,market:'EURUSD',provider:'OANDA',ticker:'EURUSD',product:'SPOT',contract:'',
 period:'WEEK',kind:'DELTA_PEAK',price,
 anchor_utc:'2026-11-01T00:00:00Z',observed_utc:'2026-11-02T00:00:00Z',note:'synthetic only'
});
const RID='00000000-0000-4000-8000-000000000001';
const STAMP='2026-11-21T21:45:00Z';
const SCHEMA=readFileSync(new URL('./d1_access_candidate.sql',import.meta.url),'utf8');
const LEVEL_SCHEMA=readFileSync(new URL('./new_level_attempts_v076_lab.sql',import.meta.url),'utf8');

async function fixture(){
 const db=new DatabaseSync(':memory:');
 db.exec(SCHEMA);db.exec(LEVEL_SCHEMA);
 const counters={primarySessions:0,reads:0,writes:0};
 const D1={withSession(mode){
  assert.equal(mode,'first-primary');
  counters.primarySessions++;
  return {prepare(sql){return {bind(...args){
   return {
    async all(){
     counters.reads++;
     const rows=db.prepare(sql).all(...args);
     return {success:true,meta:{served_by_primary:true},results:rows};
    },
    async run(){
     counters.writes++;
     const r=db.prepare(sql).run(...args);
     return {success:true,meta:{served_by_primary:true,changes:Number(r.changes)}};
    }
   };
  }};}};
 }};
 const env={
  STAGING_ORIGIN:ORIGIN,STAGING_ENABLED:'D1_CANDIDATE',
  PRIVATE_WORKER_V078:'OFFLINE_FIXTURE_ONLY',HTTP_CANDIDATE_ENABLED:'LAB_ONLY',
  LEVEL_HTTP_V074:'OFFLINE_FIXTURE_ONLY',LEVEL_JOURNAL_V076:'OFFLINE_FIXTURE_ONLY',
  ACCESS_AUD:AUD,ACCESS_ACCOUNT:ACCOUNT,
  IDENTITY_HMAC_KEY:'c'.repeat(64),INTENT_HMAC_KEY:'d'.repeat(64),
  CONTRIBUTORS_GENERATION:'e'.repeat(32),CONTRIBUTORS_JOURNAL_PIN:'f'.repeat(64),
  CONTRIBUTORS_DB:D1,CONTRIBUTORS_RATE_LIMITER:{async limit(){return {success:true}}}
 };
 const ctx=who=>({access:{aud:AUD,getIdentity:async()=>USERS[who]}});
 const tags={};
 for(const k of Object.keys(USERS))tags[k]=await accessBinding(ctx(k),env);
 db.prepare('UPDATE lab_state SET read_enabled=1,write_enabled=1,recovery_enabled=1 WHERE id=1').run();
 for(const [i,k] of ['a','b'].entries())db.prepare(
  'INSERT INTO lab_identities(subject,email_tag,slot,revoked) VALUES(?,?,?,0)'
 ).run(tags[k].subject,tags[k].email_tag,i===0?'friend-a':'friend-b');
 db.prepare('INSERT INTO lab_owner(id,subject,email_tag,revoked) VALUES(1,?,?,0)')
   .run(tags.owner.subject,tags.owner.email_tag);
 db.prepare('INSERT INTO lab_generation(id,generation,journal_pin) VALUES(1,?,?)')
   .run(env.CONTRIBUTORS_GENERATION,env.CONTRIBUTORS_JOURNAL_PIN);
 db.prepare("INSERT INTO lab_catalog(market,provider,ticker,product,contract,source_group,active) VALUES('EURUSD','OANDA','EURUSD','SPOT','','SYNTHETIC',1)").run();
 async function get(who,path){
  return worker(new Request(ORIGIN+path),env,ctx(who));
 }
 return {db,D1,env,ctx,tags,counters,get};
}
async function within(fn){
 const x=await fixture();
 try{await fn(x);}finally{x.db.close();}
}
test('01 full original SQL gives A only its own receipts, even when B also has levels',async()=>within(async x=>{
 const ra=await submit(x.ctx('a'),x.env,PAYLOAD(RID,'1.0854'));
 const rb=await submit(x.ctx('b'),x.env,PAYLOAD(RID,'1.1001'));
 assert.notEqual(ra.id,rb.id);
 assert.deepEqual((await receipts(x.ctx('a'),x.env)).map(r=>r.id),[ra.id]);
 assert.deepEqual((await receipts(x.ctx('b'),x.env)).map(r=>r.id),[rb.id]);
 assert.equal(x.counters.writes,2);
}));
test('02 same request UUID is idempotent per subject, not cross-user',async()=>within(async x=>{
 const a=await submit(x.ctx('a'),x.env,PAYLOAD(RID,'1.0854'));
 const b=await submit(x.ctx('b'),x.env,PAYLOAD(RID,'1.0854'));
 assert.notEqual(a.id,b.id);
 const again=await submit(x.ctx('a'),x.env,PAYLOAD(RID,'1.0854'));
 assert.equal(again.id,a.id);assert.equal(again.duplicate,true);
 assert.equal(x.db.prepare('SELECT count(*) AS n FROM lab_entries').get().n,2);
}));
test('03 OWNER queue may audit both friends; Contributor cannot access OWNER area',async()=>within(async x=>{
 const a=await submit(x.ctx('a'),x.env,PAYLOAD(RID,'1.0854'));
 const b=await submit(x.ctx('b'),x.env,PAYLOAD(RID,'1.1001'));
 assert.deepEqual((await queue(x.ctx('owner'),x.env)).map(r=>r.id),[a.id,b.id]);
 assert.equal((await x.get('a','/owner/levels/')).status,403);
 assert.equal((await x.get('b','/owner/')).status,403);
 assert.equal((await x.get('owner','/owner/')).status,200);
}));
test('04 real revocation SQL trigger blocks A while B remains readable',async()=>within(async x=>{
 await submit(x.ctx('a'),x.env,PAYLOAD(RID,'1.0854'));
 const b=await submit(x.ctx('b'),x.env,PAYLOAD(RID,'1.1001'));
 assert.equal((await x.get('a','/contributors/')).status,200);
 assert.equal((await revokeContributor(x.ctx('owner'),x.env,'friend-a')).status,'REVOKED');
 assert.equal(x.db.prepare('SELECT revoked FROM lab_identities WHERE slot=?').get('friend-a').revoked,1);
 await assert.rejects(receipts(x.ctx('a'),x.env));
 assert.equal((await x.get('a','/contributors/')).status,403);
 assert.equal((await x.get('b','/contributors/')).status,200);
 assert.deepEqual((await receipts(x.ctx('b'),x.env)).map(r=>r.id),[b.id]);
}));
test('05 changing only read flag denies both users their receipts and GET pages',async()=>within(async x=>{
 await submit(x.ctx('a'),x.env,PAYLOAD(RID,'1.0854'));
 x.db.prepare('UPDATE lab_state SET read_enabled=0 WHERE id=1').run();
 await assert.rejects(receipts(x.ctx('a'),x.env));
 await assert.rejects(receipts(x.ctx('b'),x.env));
 assert.equal((await x.get('a','/contributors/')).status,403);
}));
test('06 disabling writes prevents fresh submit but preserves read access',async()=>within(async x=>{
 const item=await submit(x.ctx('a'),x.env,PAYLOAD(RID,'1.0854'));
 x.db.prepare('UPDATE lab_state SET write_enabled=0 WHERE id=1').run();
 await assert.rejects(submit(x.ctx('a'),x.env,PAYLOAD('00000000-0000-4000-8000-000000000002','1.0855')));
 assert.deepEqual((await receipts(x.ctx('a'),x.env)).map(r=>r.id),[item.id]);
}));
test('07 changing Access email alone cannot read the original tagged contributor data',async()=>within(async x=>{
 await submit(x.ctx('a'),x.env,PAYLOAD(RID,'1.0854'));
 const altered={access:{aud:AUD,getIdentity:async()=>({...USERS.a,email:'other@invalid.test'})}};
 await assert.rejects(receipts(altered,x.env));
 assert.equal((await receipts(x.ctx('a'),x.env)).length,1);
}));
test('08 OWNER can write append-only review, and A sees status only on A own receipt',async()=>within(async x=>{
 const a=await submit(x.ctx('a'),x.env,PAYLOAD(RID,'1.0854'));
 const b=await submit(x.ctx('b'),x.env,PAYLOAD(RID,'1.1001'));
 const action=await review(x.ctx('owner'),x.env,a.id,'APPROVED','fixture review');
 assert.equal(action.id,a.id);
 assert.deepEqual((await history(x.ctx('owner'),x.env,a.id)).map(r=>r.action),['APPROVED']);
 assert.deepEqual((await receipts(x.ctx('a'),x.env)).map(r=>r.status),['APPROVED']);
 assert.deepEqual((await receipts(x.ctx('b'),x.env)).map(r=>r.id),[b.id]);
 assert.deepEqual((await receipts(x.ctx('b'),x.env)).map(r=>r.status),['UNREVIEWED']);
}));
test('09 separate durable RESERVED slot per friend, never exposes A attempt to B',async()=>within(async x=>{
 const level=normalizeNewLevelV076(PAYLOAD(RID,'1.0854'),STAMP);
 const fingerprint=await newLevelFingerprintV076(level);
 await claimNewLevelV076(x.env,x.tags.a,level,fingerprint,STAMP);
 assert.deepEqual(await inspectNewLevelV076(x.env,x.tags.a),{
  state:'UNRESOLVED',request_id:RID,receipt_id:null,can_submit:false
 });
 assert.deepEqual(await inspectNewLevelV076(x.env,x.tags.b),{
  state:'NO_ATTEMPT',request_id:null,receipt_id:null,can_submit:true
 });
}));
test('10 original partial UNIQUE index rejects double reservation without unblocking',async()=>within(async x=>{
 const first=normalizeNewLevelV076(PAYLOAD(RID,'1.0854'),STAMP);
 await claimNewLevelV076(x.env,x.tags.a,first,await newLevelFingerprintV076(first),STAMP);
 const second=normalizeNewLevelV076(PAYLOAD('00000000-0000-4000-8000-000000000002','1.1001'),STAMP);
 await assert.rejects(claimNewLevelV076(x.env,x.tags.a,second,await newLevelFingerprintV076(second),STAMP));
 assert.equal(x.db.prepare("SELECT count(*) AS n FROM lab_new_level_attempts WHERE subject=? AND state='RESERVED'").get(x.tags.a.subject).n,1);
 assert.equal((await inspectNewLevelV076(x.env,x.tags.a)).can_submit,false);
}));
test('11 original SQL trigger prevents editing another user level after insert',async()=>within(async x=>{
 const b=await submit(x.ctx('b'),x.env,PAYLOAD(RID,'1.1001'));
 assert.throws(()=>x.db.prepare('UPDATE lab_entries SET price=? WHERE id=?').run('1.2',b.id),/immutable_entry/);
 assert.throws(()=>x.db.prepare('DELETE FROM lab_entries WHERE id=?').run(b.id),/immutable_entry/);
 assert.equal((await receipts(x.ctx('b'),x.env))[0].price,'1.1001');
}));
test('12 inactive mapping blocks future writes, but does not expose other subjects',async()=>within(async x=>{
 await submit(x.ctx('a'),x.env,PAYLOAD(RID,'1.0854'));
 x.db.prepare('UPDATE lab_catalog SET active=0').run();
 await assert.rejects(submit(x.ctx('b'),x.env,PAYLOAD(RID,'1.1001')));
 assert.equal((await receipts(x.ctx('b'),x.env)).length,0);
 assert.equal((await receipts(x.ctx('a'),x.env)).length,1);
}));
test('13 owner recovery revocation denies privileged GET before any UI page',async()=>within(async x=>{
 assert.equal((await x.get('owner','/owner/')).status,200);
 x.db.prepare('UPDATE lab_state SET recovery_enabled=0 WHERE id=1').run();
 assert.equal((await x.get('owner','/owner/')).status,403);
 await assert.rejects(revokeContributor(x.ctx('owner'),x.env,'friend-a'));
}));
test('14 full schema and real SQL never equal Cloudflare D1 provider proof',async()=>within(async x=>{
 assert.equal(x.db.prepare('SELECT count(*) AS n FROM lab_identities').get().n,2);
 assert.equal(x.db.prepare('PRAGMA foreign_keys').get().foreign_keys,1);
 assert.equal(x.counters.writes,0);
 assert.equal((await x.get('a','/contributors/')).headers.get('Cache-Control'),'no-store, max-age=0');
}));
