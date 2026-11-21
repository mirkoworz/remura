// REMURA Contributors v0.76 LAB — 24 NEW durable ledger SQL / input tests.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fixture,reqId} from './fullstack_fixture_v066_lab.mjs';
import {normalizeNewLevelV076 as norm,newLevelFingerprintV076 as fp,
 claimNewLevelV076 as claim,confirmNewLevelV076 as confirm,
 inspectNewLevelV076 as inspect,LEVEL_ATTEMPT_SQL_V076 as SQL} from './level_attempt_journal_v076_lab.mjs';
const now=()=>new Date().toISOString().slice(0,19)+'Z';
const level=(n=3,price='1.234')=>({request_id:reqId(n),market:'EURUSD',provider:'OANDA',ticker:'EURUSD',product:'SPOT',contract:'',period:'DAY',kind:'DELTA_PEAK',price,anchor_utc:now().slice(0,10)+'T00:00:00Z',observed_utc:new Date(Date.now()-600000).toISOString().slice(0,19)+'Z',note:'synthetic attempt'});
async function setup(t){const x=await fixture(t);x.db.exec(readFileSync(new URL('./new_level_attempts_v076_lab.sql',import.meta.url),'utf8'));x.env.LEVEL_JOURNAL_V076='OFFLINE_FIXTURE_ONLY';return x;}
const attempt=async(x,p=level())=>{const l=norm(p,now()),f=await fp(l);await claim(x.env,x.actors.alice,l,f,now());return {l,f};};
test('01 empty new ledger does not confuse original levels with attempts',async t=>{const x=await setup(t);assert.deepEqual(await inspect(x.env,x.actors.alice),{state:'NO_ATTEMPT',request_id:null,receipt_id:null,can_submit:true});});
test('02 new reservation persists in original SQLite fixture',async t=>{const x=await setup(t);await attempt(x);assert.equal(x.n('lab_new_level_attempts'),1);});
test('03 initial reservation is conservatively unresolved before any original insert',async t=>{const x=await setup(t);await attempt(x);assert.equal((await inspect(x.env,x.actors.alice)).state,'UNRESOLVED');});
test('04 unresolved reservation never permits next submission',async t=>{const x=await setup(t);await attempt(x);assert.equal((await inspect(x.env,x.actors.alice)).can_submit,false);});
test('05 exact duplicate same request id cannot reserve twice',async t=>{const x=await setup(t),l=norm(level(),now()),f=await fp(l);await claim(x.env,x.actors.alice,l,f,now());await assert.rejects(claim(x.env,x.actors.alice,l,f,now()));assert.equal(x.n('lab_new_level_attempts'),1);});
test('06 different request id cannot bypass per-subject active slot',async t=>{const x=await setup(t);await attempt(x);const l=norm(level(4),now());await assert.rejects(claim(x.env,x.actors.alice,l,await fp(l),now()));assert.equal(x.n('lab_new_level_attempts'),1);});
test('07 different contributors have independent active slots',async t=>{const x=await setup(t);await attempt(x);const l=norm(level(4),now());await claim(x.env,x.actors.bob,l,await fp(l),now());assert.equal(x.n('lab_new_level_attempts'),2);});
test('08 Bob cannot inspect Alice attempt',async t=>{const x=await setup(t);await attempt(x);assert.equal((await inspect(x.env,x.actors.bob)).state,'NO_ATTEMPT');});
test('09 ledger cannot be deleted even by synthetic direct SQL',async t=>{const x=await setup(t);await attempt(x);assert.throws(()=>x.db.exec('DELETE FROM lab_new_level_attempts'));assert.equal(x.n('lab_new_level_attempts'),1);});
test('10 ledger cannot rebind subject or request id',async t=>{const x=await setup(t);await attempt(x);assert.throws(()=>x.db.prepare('UPDATE lab_new_level_attempts SET subject=?').run(x.actors.bob.subject));});
test('11 ledger cannot reset fingerprint or expiry',async t=>{const x=await setup(t);await attempt(x);assert.throws(()=>x.db.exec("UPDATE lab_new_level_attempts SET fingerprint='"+'f'.repeat(64)+"'"));});
test('12 ledger cannot falsely mark COMMITTED without an actual receipt',async t=>{const x=await setup(t);const {l,f}=await attempt(x);await assert.rejects(confirm(x.env,x.actors.alice,l,f,999,now()));});
test('13 attempts do not become amendment journal rows',async t=>{const x=await setup(t),before=x.n('lab_amend_attempts_v064');await attempt(x);assert.equal(x.n('lab_amend_attempts_v064'),before);});
test('14 missing explicit offline journal flag denies insertion',async t=>{const x=await setup(t),l=norm(level(),now());await assert.rejects(claim({...x.env,LEVEL_JOURNAL_V076:'LIVE'},x.actors.alice,l,await fp(l),now()));});
test('15 wrong HMAC generation pin denies claim',async t=>{const x=await setup(t),l=norm(level(),now());await assert.rejects(claim({...x.env,CONTRIBUTORS_JOURNAL_PIN:'f'.repeat(64)},x.actors.alice,l,await fp(l),now()));assert.equal(x.n('lab_new_level_attempts'),0);});
test('16 revoked actor cannot reserve a new original level',async t=>{const x=await setup(t);x.db.prepare('UPDATE lab_identities SET revoked=1 WHERE subject=?').run(x.actors.alice.subject);const l=norm(level(),now());await assert.rejects(claim(x.env,x.actors.alice,l,await fp(l),now()));});
test('17 disabled writes deny reservation',async t=>{const x=await setup(t);x.db.exec('UPDATE lab_state SET write_enabled=0');const l=norm(level(),now());await assert.rejects(claim(x.env,x.actors.alice,l,await fp(l),now()));});
test('18 disabled reads deny status inspection',async t=>{const x=await setup(t);await attempt(x);x.db.exec('UPDATE lab_state SET read_enabled=0');await assert.rejects(inspect(x.env,x.actors.alice));});
test('19 D1 first-primary assertion rejects replica metadata',async t=>{const x=await setup(t);x.setPrimary(false);const l=norm(level(),now());await assert.rejects(claim(x.env,x.actors.alice,l,await fp(l),now()));});
test('20 invalid input extra subject cannot enter journal',()=>{assert.throws(()=>norm({...level(),subject:'alice'},now()));});
test('21 impossible future observation cannot enter journal',()=>{assert.throws(()=>norm({...level(),observed_utc:'2099-01-01T00:00:00Z'},now()));});
test('22 request id and input fields are exact and canonical',async()=>{const l=norm({...level(),price:'1,2340'},now());assert.equal(l.price,'1.234');assert.equal(Object.keys(l).length,12);assert.match(await fp(l),/^[0-9a-f]{64}$/);});
test('23 fingerprint distinguishes prices but is stable for identical values',async()=>{const a=norm(level(),now()),b=norm(level(3,'1.235'),now());assert.equal(await fp(a),await fp(a));assert.notEqual(await fp(a),await fp(b));});
test('24 SQL routines do not expose an HTTP or Worker entrypoint',async()=>{assert.equal('default' in await import('./level_attempt_journal_v076_lab.mjs'),false);assert.equal(typeof SQL.claim,'string');assert.equal(typeof SQL.confirm,'string');});
