// REMURA Contributors v0.77 LAB — NEW ONLY synthetic OWNER audit integration tests.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fixture,origin,reqId} from './fullstack_fixture_v066_lab.mjs';
import {privateWorkerCandidateV077 as worker} from './private_levels_composition_v077_lab.mjs';
import {claimNewLevelV076,normalizeNewLevelV076,newLevelFingerprintV076} from './level_attempt_journal_v076_lab.mjs';
const stamp=()=>new Date().toISOString().slice(0,19)+'Z';
const payload=(n=3,price='1.2410')=>({request_id:reqId(n),market:'EURUSD',provider:'OANDA',ticker:'EURUSD',product:'SPOT',contract:'',period:'DAY',kind:'DELTA_PEAK',price,anchor_utc:stamp().slice(0,10)+'T00:00:00Z',observed_utc:new Date(Date.now()-600000).toISOString().slice(0,19)+'Z',note:'owner audit fixture'});
const baseEnv=x=>({...x.env,PRIVATE_WORKER_V077:'OFFLINE_FIXTURE_ONLY',OWNER_LEVEL_AUDIT_V077:'OFFLINE_FIXTURE_ONLY',LEVEL_HTTP_V074:'OFFLINE_FIXTURE_ONLY',LEVEL_JOURNAL_V076:'OFFLINE_FIXTURE_ONLY',HTTP_CANDIDATE_ENABLED:'LAB_ONLY'});
async function init(t){
 const x=await fixture(t);
 x.db.exec(readFileSync(new URL('./new_level_attempts_v076_lab.sql',import.meta.url),'utf8'));
 x.db.exec(readFileSync(new URL('./new_level_owner_audit_v077_lab.sql',import.meta.url),'utf8'));
 Object.assign(x.env,{LEVEL_JOURNAL_V076:'OFFLINE_FIXTURE_ONLY',OWNER_LEVEL_AUDIT_V077:'OFFLINE_FIXTURE_ONLY'});
 return x;
}
async function reserve(x,name='alice',n=3){
 const p=normalizeNewLevelV076(payload(n),stamp()),actor=x.actors[name],f=await newLevelFingerprintV076(p);
 await claimNewLevelV076(x.env,actor,p,f,stamp());return {p,actor,f};
}
function insertOriginal(x,p,who='alice'){
 x.db.prepare('INSERT INTO lab_entries(subject,request_id,market,provider,ticker,product,contract,period,kind,price,anchor_utc,observed_utc,received_utc,note,source_group) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)')
  .run(x.actors[who].subject,p.request_id,p.market,p.provider,p.ticker,p.product,p.contract,p.period,p.kind,p.price,p.anchor_utc,p.observed_utc,stamp(),p.note,'fixture-fx');
 return x.db.prepare('SELECT id FROM lab_entries WHERE subject=? AND request_id=?').get(x.actors[who].subject,p.request_id).id;
}
function req(path,body={},intent,headers={}){return new Request(origin+path,{method:'POST',headers:{Origin:origin,'Sec-Fetch-Site':'same-origin','X-Remura-CSRF':'1','Content-Type':'application/json',...(intent?{'X-Remura-Intent':intent}:{}),...headers},body:JSON.stringify(body)});}
const ask=(x,path,body={},intent,env={})=>worker(req(path,body,intent),{...baseEnv(x),...env},x.ctx);
const json=async r=>({http:r.status,...await r.json()});
const pending=async x=>json(await ask(x,'/owner/new-level/pending',{after:0}));
const history=async x=>json(await ask(x,'/owner/new-level/history',{after:0}));
const draft=(x,id=null,which='RECEIPT_NOT_OBSERVED',who='alice',n=3)=>({subject:x.actors[who].subject,request_id:reqId(n),classification:which,receipt_id:id,reason:'Sintetico: verifica indipendente OWNER'});
const sign=async(x,body)=>{const r=await json(await ask(x,'/owner/new-level/audit-intent',{body}));assert.equal(r.http,200,JSON.stringify(r));assert.match(r.data.intent,/^[a-f0-9]{32}\.[0-9]{10}\.[a-f0-9]{64}$/);return r.data.intent};
const attest=(x,body,token)=>ask(x,'/owner/new-level/attest',body,token);
test('01 only OWNER sees reserved attempt queue',async t=>{const x=await init(t);await reserve(x);assert.equal((await pending(x)).http,403);x.setWho('owner');const r=await pending(x);assert.equal(r.http,200);assert.equal(r.data.rows.length,1);});
test('02 owner snapshot says not observed, not definitive absent',async t=>{const x=await init(t);await reserve(x);x.setWho('owner');const r=await pending(x);assert.equal(r.data.rows[0].evidence,'NOT_OBSERVED');assert.equal(r.data.rows[0].receipt_id,null);});
test('03 reserved original-level evidence is independent of amendment journal',async t=>{const x=await init(t),before=x.n('lab_amend_attempts_v064');await reserve(x);assert.equal(x.n('lab_amend_attempts_v064'),before);});
test('04 OWNER can read own empty audit history',async t=>{const x=await init(t);x.setWho('owner');const r=await history(x);assert.equal(r.http,200);assert.deepEqual(r.data.rows,[]);});
test('05 contributor cannot see audit history',async t=>{const x=await init(t);assert.equal((await history(x)).http,403);});
test('06 OWNER can request a signed one-use audit intent',async t=>{const x=await init(t);await reserve(x);x.setWho('owner');assert.equal(typeof await sign(x,draft(x)),'string');assert.equal(x.n('lab_new_level_owner_audit_v077'),0);});
test('07 signed owner observation appends exactly one SQL event',async t=>{const x=await init(t);await reserve(x);x.setWho('owner');const a=draft(x),tok=await sign(x,a);const r=await json(await attest(x,a,tok));assert.equal(r.http,200);assert.equal(r.data.attempt_still_locked,true);assert.equal(x.n('lab_new_level_owner_audit_v077'),1);});
test('08 append NEVER releases the durable RESERVED slot',async t=>{const x=await init(t);await reserve(x);x.setWho('owner');const a=draft(x);await attest(x,a,await sign(x,a));assert.equal(x.db.prepare('SELECT state FROM lab_new_level_attempts').get().state,'RESERVED');});
test('09 contributor remains blocked after OWNER observes no receipt',async t=>{const x=await init(t);await reserve(x);x.setWho('owner');const a=draft(x);await attest(x,a,await sign(x,a));x.setWho('alice');const r=await json(await ask(x,'/api/level-attempt/status',{}));assert.equal(r.http,200);assert.equal(r.data.can_submit,false);assert.equal(r.data.state,'UNRESOLVED');});
test('10 owner audit history exposes action and no raw email',async t=>{const x=await init(t);await reserve(x);x.setWho('owner');const a=draft(x);await attest(x,a,await sign(x,a));const r=await history(x);assert.equal(r.http,200);assert.equal(r.data.rows[0].classification,'RECEIPT_NOT_OBSERVED');assert.equal(JSON.stringify(r).includes('@'),false);});
test('11 replay of burnt HMAC cannot duplicate audit',async t=>{const x=await init(t);await reserve(x);x.setWho('owner');const a=draft(x),tok=await sign(x,a);assert.equal((await attest(x,a,tok)).status,200);assert.equal((await attest(x,a,tok)).status,409);assert.equal(x.n('lab_new_level_owner_audit_v077'),1);});
test('12 fresh nonce cannot duplicate same classification by UNIQUE',async t=>{const x=await init(t);await reserve(x);x.setWho('owner');const a=draft(x);assert.equal((await attest(x,a,await sign(x,a))).status,200);assert.equal((await attest(x,a,await sign(x,a))).status,409);assert.equal(x.n('lab_new_level_owner_audit_v077'),1);});
test('13 audit table UPDATE is blocked even by test SQL',async t=>{const x=await init(t);await reserve(x);x.setWho('owner');const a=draft(x);await attest(x,a,await sign(x,a));assert.throws(()=>x.db.exec("UPDATE lab_new_level_owner_audit_v077 SET reason='modified'"));});
test('14 audit table DELETE is blocked even by test SQL',async t=>{const x=await init(t);await reserve(x);x.setWho('owner');const a=draft(x);await attest(x,a,await sign(x,a));assert.throws(()=>x.db.exec('DELETE FROM lab_new_level_owner_audit_v077'));});
test('15 OWNER cannot invent a receipt_id when no original entry exists',async t=>{const x=await init(t);await reserve(x);x.setWho('owner');const a=draft(x,500,'RECEIPT_FOUND');assert.equal((await attest(x,a,await sign(x,a))).status,409);assert.equal(x.n('lab_new_level_owner_audit_v077'),0);});
test('16 RECEIPT_FOUND audit requires original entry matching subject and request',async t=>{const x=await init(t),{p}=await reserve(x);const id=insertOriginal(x,p);x.setWho('owner');const a=draft(x,id,'RECEIPT_FOUND');assert.equal((await attest(x,a,await sign(x,a))).status,200);assert.equal(x.n('lab_new_level_owner_audit_v077'),1);});
test('17 real fixture receipt is visible in OWNER queue',async t=>{const x=await init(t),{p}=await reserve(x);const id=insertOriginal(x,p);x.setWho('owner');const r=await pending(x);assert.equal(r.data.rows[0].evidence,'RECEIPT_FOUND');assert.equal(r.data.rows[0].receipt_id,id);});
test('18 OWNER cannot claim not observed if original entry already exists',async t=>{const x=await init(t),{p}=await reserve(x);insertOriginal(x,p);x.setWho('owner');const a=draft(x);assert.equal((await attest(x,a,await sign(x,a))).status,409);assert.equal(x.n('lab_new_level_owner_audit_v077'),0);});
test('19 stale snapshot cannot claim absence after concurrent original INSERT',async t=>{const x=await init(t),{p}=await reserve(x);x.setWho('owner');const a=draft(x),token=await sign(x,a);insertOriginal(x,p);assert.equal((await attest(x,a,token)).status,409);assert.equal(x.n('lab_new_level_owner_audit_v077'),0);});
test('20 audit with RECEIPT_FOUND still does not auto-confirm journal',async t=>{const x=await init(t),{p}=await reserve(x);const id=insertOriginal(x,p);x.setWho('owner');const a=draft(x,id,'RECEIPT_FOUND');await attest(x,a,await sign(x,a));x.setWho('alice');const r=await json(await ask(x,'/api/level-attempt/status',{}));assert.equal(r.data.state,'COMMITTED_NEEDS_OWNER');assert.equal(r.data.can_submit,false);});
test('21 owner revocation denies pending, attest, history',async t=>{const x=await init(t);await reserve(x);x.db.prepare('UPDATE lab_owner SET revoked=1 WHERE subject=?').run(x.actors.owner.subject);x.setWho('owner');assert.equal((await pending(x)).http,403);assert.equal((await history(x)).http,403);assert.equal((await attest(x,draft(x),'missing')).status,409);});
test('22 disabling OWNER recovery permission denies evidence',async t=>{const x=await init(t);await reserve(x);x.db.exec('UPDATE lab_state SET recovery_enabled=0');x.setWho('owner');assert.equal((await pending(x)).http,403);});
test('23 primary replica metadata refuses OWNER evidence read',async t=>{const x=await init(t);await reserve(x);x.setPrimary(false);x.setWho('owner');assert.equal((await pending(x)).http,403);});
test('24 wrong generation pin denies all OWNER evidence reads',async t=>{const x=await init(t);await reserve(x);x.setWho('owner');assert.equal((await ask(x,'/owner/new-level/pending',{after:0},undefined,{CONTRIBUTORS_JOURNAL_PIN:'0'.repeat(64)})).status,403);});
test('25 absent v0.77 kill switch denies pending',async t=>{const x=await init(t);x.setWho('owner');assert.equal((await ask(x,'/owner/new-level/pending',{after:0},undefined,{OWNER_LEVEL_AUDIT_V077:'LIVE'})).status,403);});
test('26 invalid cursor cannot start an expensive unrestricted scan',async t=>{const x=await init(t);x.setWho('owner');for(const after of [-1,1.4,999999999999,'0'])assert.equal((await ask(x,'/owner/new-level/pending',{after})).status,403);});
test('27 body cannot select another actor in pending queue',async t=>{const x=await init(t);x.setWho('owner');assert.equal((await ask(x,'/owner/new-level/pending',{after:0,role:'CONTRIBUTOR'})).status,403);});
test('28 browser role spoof header denied',async t=>{const x=await init(t);x.setWho('owner');const r=await worker(req('/owner/new-level/pending',{after:0},null,{'X-Remura-Role':'OWNER'}),baseEnv(x),x.ctx);assert.equal(r.status,403);});
test('29 csrf missing denied',async t=>{const x=await init(t);x.setWho('owner');const r=await worker(req('/owner/new-level/pending',{after:0},null,{'X-Remura-CSRF':'0'}),baseEnv(x),x.ctx);assert.equal(r.status,403);});
test('30 cross-origin metadata denied',async t=>{const x=await init(t);x.setWho('owner');const r=await worker(req('/owner/new-level/pending',{after:0},null,{'Sec-Fetch-Site':'cross-site'}),baseEnv(x),x.ctx);assert.equal(r.status,403);});
test('31 untrusted Access missing denied',async t=>{const x=await init(t);assert.equal((await worker(req('/owner/new-level/pending',{after:0}),baseEnv(x),{})).status,403);});
test('32 impossible path and query suffix denied',async t=>{const x=await init(t);x.setWho('owner');for(const path of ['/owner/new-level/pending?x=1','/owner/new-level/release','/owner/new-level/reset'])assert.equal((await ask(x,path,{after:0})).status,403);});
test('33 invalid signed audit token denied without row append',async t=>{const x=await init(t);await reserve(x);x.setWho('owner');assert.equal((await attest(x,draft(x),'a'.repeat(32)+'.9999999999.'+'a'.repeat(64))).status,409);assert.equal(x.n('lab_new_level_owner_audit_v077'),0);});
test('34 altered reason breaks a valid signed audit intent',async t=>{const x=await init(t);await reserve(x);x.setWho('owner');const a=draft(x),token=await sign(x,a);assert.equal((await attest(x,{...a,reason:'altered'},token)).status,409);assert.equal(x.n('lab_new_level_owner_audit_v077'),0);});
test('35 lost response after nonce burn does not allow retry',async t=>{const x=await init(t);await reserve(x);x.setWho('owner');const a=draft(x),token=await sign(x,a);x.setAfterWrite(sql=>{if(sql.startsWith('INSERT INTO lab_intent_used'))throw Error('lost after burn')});assert.equal((await attest(x,a,token)).status,409);x.setAfterWrite(null);assert.equal((await attest(x,a,token)).status,409);assert.equal(x.n('lab_new_level_owner_audit_v077'),0);});
test('36 OWNER audit after manual observation never approves an original entry',async t=>{const x=await init(t),{p}=await reserve(x);const receipt=insertOriginal(x,p);x.setWho('owner');const a=draft(x,receipt,'RECEIPT_FOUND');await attest(x,a,await sign(x,a));assert.equal(x.db.prepare('SELECT count(*) AS total FROM lab_reviews WHERE entry_id=?').get(receipt).total,0);});
test('37 OWNER audit always no-store and JSON',async t=>{const x=await init(t);x.setWho('owner');const r=await ask(x,'/owner/new-level/pending',{after:0});assert.equal(r.status,200);assert.match(r.headers.get('Cache-Control'),/no-store/);assert.match(r.headers.get('Content-Type'),/application\/json/);});
test('38 new audit composition exports neither default fetch nor deployment config',async()=>{const m=await import('./private_levels_composition_v077_lab.mjs');assert.equal('default' in m,false);assert.equal('fetch' in m,false);});
