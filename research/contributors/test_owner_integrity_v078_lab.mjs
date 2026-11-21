// REMURA Contributors v0.78 LAB — NEW read-only evidence drift and fault injection tests.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fixture,origin,reqId} from './fullstack_fixture_v066_lab.mjs';
import {privateWorkerCandidateV078 as worker} from './private_levels_composition_v078_lab.mjs';
import {claimNewLevelV076,normalizeNewLevelV076,newLevelFingerprintV076} from './level_attempt_journal_v076_lab.mjs';
const stamp=()=>new Date().toISOString().slice(0,19)+'Z';
const payload=(n=3,price='1.2410')=>({request_id:reqId(n),market:'EURUSD',provider:'OANDA',ticker:'EURUSD',product:'SPOT',contract:'',period:'DAY',kind:'DELTA_PEAK',price,anchor_utc:stamp().slice(0,10)+'T00:00:00Z',observed_utc:new Date(Date.now()-600000).toISOString().slice(0,19)+'Z',note:'owner audit fixture'});
const baseEnv=x=>({...x.env,PRIVATE_WORKER_V078:'OFFLINE_FIXTURE_ONLY',OWNER_INTEGRITY_V078:'OFFLINE_FIXTURE_ONLY',OWNER_LEVEL_AUDIT_V077:'OFFLINE_FIXTURE_ONLY',LEVEL_HTTP_V074:'OFFLINE_FIXTURE_ONLY',LEVEL_JOURNAL_V076:'OFFLINE_FIXTURE_ONLY',HTTP_CANDIDATE_ENABLED:'LAB_ONLY'});
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

const integrity=async(x,after=0,extra={})=>json(await ask(x,'/owner/new-level/integrity',{after},undefined,extra));
test('01 zero reserved attempts has an empty integrity report, no release',async t=>{const x=await init(t);x.setWho('owner');const r=await integrity(x);assert.equal(r.http,200);assert.deepEqual(r.data,{rows:[],has_more:false,automatic_release:false});});
test('02 one RESERVED without receipt is NOT_OBSERVED_UNATTESTED',async t=>{const x=await init(t);await reserve(x);x.setWho('owner');const r=await integrity(x);assert.equal(r.data.rows[0].condition,'NOT_OBSERVED_UNATTESTED');});
test('03 integrity rows always indicate attempt_locked and needs_owner',async t=>{const x=await init(t);await reserve(x);x.setWho('owner');const r=await integrity(x);assert.equal(r.data.rows[0].attempt_locked,true);assert.equal(r.data.rows[0].needs_owner,true);});
test('04 signed absence observation is a snapshot only',async t=>{const x=await init(t);await reserve(x);x.setWho('owner');const a=draft(x);assert.equal((await attest(x,a,await sign(x,a))).status,200);const r=await integrity(x);assert.equal(r.data.rows[0].condition,'ABSENCE_SNAPSHOT_ONLY');});
test('05 receipt appearing AFTER an absence observation is flagged as changed',async t=>{const x=await init(t),{p}=await reserve(x);x.setWho('owner');const a=draft(x);assert.equal((await attest(x,a,await sign(x,a))).status,200);const id=insertOriginal(x,p);const r=await integrity(x);assert.equal(r.data.rows[0].condition,'EVIDENCE_CHANGED_NEEDS_OWNER');assert.equal(r.data.rows[0].observed_receipt,id);assert.equal(r.data.automatic_release,false);});
test('06 receipt observed without OWNER attest is flagged as unaudited',async t=>{const x=await init(t),{p}=await reserve(x);const id=insertOriginal(x,p);x.setWho('owner');const r=await integrity(x);assert.equal(r.data.rows[0].condition,'RECEIPT_FOUND_UNATTESTED');assert.equal(r.data.rows[0].observed_receipt,id);});
test('07 original receipt attested by OWNER stays locked',async t=>{const x=await init(t),{p}=await reserve(x);const id=insertOriginal(x,p);x.setWho('owner');const a=draft(x,id,'RECEIPT_FOUND');assert.equal((await attest(x,a,await sign(x,a))).status,200);const r=await integrity(x);assert.equal(r.data.rows[0].condition,'RECEIPT_ATTESTED_LOCKED');assert.equal(r.data.rows[0].attempt_locked,true);});
test('08 second signed observation after evidence changed updates latest classification only',async t=>{const x=await init(t),{p}=await reserve(x);x.setWho('owner');const absence=draft(x);await attest(x,absence,await sign(x,absence));const id=insertOriginal(x,p);const present=draft(x,id,'RECEIPT_FOUND');assert.equal((await attest(x,present,await sign(x,present))).status,200);const r=await integrity(x);assert.equal(r.data.rows[0].condition,'RECEIPT_ATTESTED_LOCKED');assert.equal(x.n('lab_new_level_owner_audit_v077'),2);});
test('09 two distinct observations cannot change RESERVED state',async t=>{const x=await init(t),{p}=await reserve(x);x.setWho('owner');const a=draft(x);await attest(x,a,await sign(x,a));const id=insertOriginal(x,p);const b=draft(x,id,'RECEIPT_FOUND');await attest(x,b,await sign(x,b));assert.equal(x.db.prepare('SELECT state FROM lab_new_level_attempts').get().state,'RESERVED');});
test('10 integrity read-only does not change journal, nonce, entries, or audit row counts',async t=>{const x=await init(t);await reserve(x);x.setWho('owner');const before=['lab_new_level_attempts','lab_intent_used','lab_entries','lab_new_level_owner_audit_v077'].map(k=>x.n(k));const r=await integrity(x);assert.equal(r.http,200);assert.deepEqual(['lab_new_level_attempts','lab_intent_used','lab_entries','lab_new_level_owner_audit_v077'].map(k=>x.n(k)),before);});
test('11 both contributors keep distinct pending attempts in OWNER view',async t=>{const x=await init(t);await reserve(x,'alice',3);await reserve(x,'bob',4);x.setWho('owner');const r=await integrity(x);assert.equal(r.data.rows.length,2);assert.equal(new Set(r.data.rows.map(z=>z.subject)).size,2);});
test('12 paging after first attempt yields only second distinct attempt',async t=>{const x=await init(t);await reserve(x,'alice',3);await reserve(x,'bob',4);x.setWho('owner');const first=await integrity(x);assert.equal(first.data.rows.length,2);const next=await integrity(x,first.data.rows[0].attempt_id);assert.equal(next.data.rows.length,1);assert.equal(next.data.rows[0].attempt_id,first.data.rows[1].attempt_id);});
test('13 contributor identity cannot access new diagnostic endpoint',async t=>{const x=await init(t);await reserve(x);assert.equal((await integrity(x)).http,403);});
test('14 revoked OWNER cannot access read-only integrity',async t=>{const x=await init(t);await reserve(x);x.db.prepare('UPDATE lab_owner SET revoked=1 WHERE subject=?').run(x.actors.owner.subject);x.setWho('owner');assert.equal((await integrity(x)).http,403);});
test('15 revocation after SQL diagnostic read is blocked by second permission verification',async t=>{const x=await init(t);await reserve(x);x.setWho('owner');const db=x.env.CONTRIBUTORS_DB;let tripped=false;
 x.env.CONTRIBUTORS_DB={withSession(mode){const obj=db.withSession(mode);return {prepare(sql){const inner=obj.prepare(sql);if(!sql.includes('AS audit_classification'))return inner;return {bind(...args){const bound=inner.bind(...args);return {async all(){const r=await bound.all();if(!tripped){tripped=true;x.db.prepare('UPDATE lab_owner SET revoked=1 WHERE subject=?').run(x.actors.owner.subject);}return r;}}};}}};}};
 assert.equal((await integrity(x)).http,403);assert.equal(tripped,true);
});
test('16 disabled read permission denies integrity report',async t=>{const x=await init(t);await reserve(x);x.setWho('owner');x.db.exec('UPDATE lab_state SET read_enabled=0');assert.equal((await integrity(x)).http,403);});
test('17 disabled recovery permission denies integrity report',async t=>{const x=await init(t);await reserve(x);x.setWho('owner');x.db.exec('UPDATE lab_state SET recovery_enabled=0');assert.equal((await integrity(x)).http,403);});
test('18 D1 replica metadata denied even for OWNER with valid token',async t=>{const x=await init(t);await reserve(x);x.setWho('owner');x.setPrimary(false);assert.equal((await integrity(x)).http,403);});
test('19 explicit v0.78 kill switch is mandatory',async t=>{const x=await init(t);await reserve(x);x.setWho('owner');assert.equal((await integrity(x,0,{OWNER_INTEGRITY_V078:'DISABLED'})).http,403);});
test('20 wrong journal pin blocks diagnostic visibility',async t=>{const x=await init(t);await reserve(x);x.setWho('owner');assert.equal((await integrity(x,0,{CONTRIBUTORS_JOURNAL_PIN:'f'.repeat(64)})).http,403);});
test('21 missing Access context is refused by router',async t=>{const x=await init(t);x.setWho('owner');const r=await worker(req('/owner/new-level/integrity',{after:0}),baseEnv(x),{});assert.equal(r.status,403);});
test('22 browser-supplied OWNER header cannot grant access',async t=>{const x=await init(t);x.setWho('owner');const r=await worker(req('/owner/new-level/integrity',{after:0},undefined,{'X-Remura-Role':'OWNER'}),baseEnv(x),x.ctx);assert.equal(r.status,403);});
test('23 cross-site fetch metadata cannot access diagnostic',async t=>{const x=await init(t);x.setWho('owner');const r=await worker(req('/owner/new-level/integrity',{after:0},undefined,{'Sec-Fetch-Site':'cross-site'}),baseEnv(x),x.ctx);assert.equal(r.status,403);});
test('24 missing CSRF proof refused',async t=>{const x=await init(t);x.setWho('owner');const r=await worker(req('/owner/new-level/integrity',{after:0},undefined,{'X-Remura-CSRF':'0'}),baseEnv(x),x.ctx);assert.equal(r.status,403);});
test('25 malformed cursor never unlocks unrestricted scan',async t=>{const x=await init(t);x.setWho('owner');for(const after of [-1,'0',1.5,10**12,null])assert.equal((await json(await ask(x,'/owner/new-level/integrity',{after}))).http,403);});
test('26 query or unknown release route cannot pass the router',async t=>{const x=await init(t);x.setWho('owner');for(const path of ['/owner/new-level/integrity?limit=999','/owner/new-level/integrity/','/owner/new-level/release'])assert.equal((await json(await ask(x,path,{after:0}))).http,403);});
test('27 lost response AFTER OWNER audit INSERT persists evidence and forbids token retry',async t=>{const x=await init(t);await reserve(x);x.setWho('owner');const a=draft(x),token=await sign(x,a);
 x.setAfterWrite(sql=>{if(sql.startsWith('INSERT INTO lab_new_level_owner_audit_v077'))throw Error('synthetic lost after append')});
 assert.equal((await attest(x,a,token)).status,409);x.setAfterWrite(null);
 assert.equal(x.n('lab_new_level_owner_audit_v077'),1);
 assert.equal((await attest(x,a,token)).status,409);
 const r=await integrity(x);assert.equal(r.data.rows[0].condition,'ABSENCE_SNAPSHOT_ONLY');assert.equal(r.data.rows[0].attempt_locked,true);
});
test('28 concurrent distinct HMAC nonces for same classification yield only one append',async t=>{const x=await init(t);await reserve(x);x.setWho('owner');const a=draft(x),aToken=await sign(x,a),bToken=await sign(x,a);
 const replies=await Promise.all([attest(x,a,aToken),attest(x,a,bToken)]);assert.deepEqual(replies.map(r=>r.status).sort(),[200,409]);assert.equal(x.n('lab_new_level_owner_audit_v077'),1);assert.equal(x.db.prepare('SELECT state FROM lab_new_level_attempts').get().state,'RESERVED');
});
test('29 new diagnostic explicitly returns no automatic_release even after successful audit',async t=>{const x=await init(t);await reserve(x);x.setWho('owner');const a=draft(x);await attest(x,a,await sign(x,a));const r=await integrity(x);assert.equal(r.data.automatic_release,false);});
test('30 runtime still has no executable fetch or deploy entrypoint',async()=>{const m=await import('./private_levels_composition_v078_lab.mjs');assert.equal('default' in m,false);assert.equal('fetch' in m,false);});
