// v0.65 tracked-repo security smoke suite, reduced SQLite surrogate only.
import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {createReconciliationHttpV065} from './reconciliation_http_v065_lab.mjs';
const origin='https://fixture.invalid',P='/api/amendment/submit',R='/api/amendment/reconcile',O='/owner/amendment/reconcile-queue';
const request=n=>({source_entry_id:1,request_id:'00000000-0000-4000-8000-'+String(n).padStart(12,'0'),price:'1.23',observed_utc:'2026-11-21T09:45:00Z',note:'fixture'});
function fixture(t){
 const db=new DatabaseSync(':memory:');t.after(()=>db.close());
 db.exec(`CREATE TABLE lab_state(id INTEGER,write_enabled INTEGER);INSERT INTO lab_state VALUES(1,1);
 CREATE TABLE lab_identities(subject TEXT,email_tag TEXT,revoked INTEGER);
 CREATE TABLE lab_entries(id INTEGER,subject TEXT,approved INTEGER);
 CREATE TABLE lab_amend_attempts_v064(id INTEGER PRIMARY KEY,subject TEXT,request_id TEXT,source_entry_id INTEGER,price TEXT,observed_utc TEXT,note TEXT,reserved_utc TEXT,UNIQUE(subject,request_id));
 CREATE TABLE lab_amend_releases_v064(attempt_id INTEGER PRIMARY KEY);
 CREATE TABLE lab_level_amendments_v059(id INTEGER PRIMARY KEY,subject TEXT,request_id TEXT UNIQUE);
 CREATE TRIGGER latch BEFORE INSERT ON lab_amend_attempts_v064 BEGIN SELECT CASE WHEN
 NOT EXISTS(SELECT 1 FROM lab_state WHERE write_enabled=1) OR NOT EXISTS(SELECT 1 FROM lab_identities WHERE subject=NEW.subject AND revoked=0)
 OR NOT EXISTS(SELECT 1 FROM lab_entries WHERE id=NEW.source_entry_id AND subject=NEW.subject AND approved=1)
 OR EXISTS(SELECT 1 FROM lab_amend_attempts_v064 a WHERE a.subject=NEW.subject AND NOT EXISTS(SELECT 1 FROM lab_amend_releases_v064 r WHERE r.attempt_id=a.id))
 THEN RAISE(ABORT,'blocked') END; END;`);
 const a={subject:'a'.repeat(64),email_tag:'1'.repeat(64)},b={subject:'b'.repeat(64),email_tag:'2'.repeat(64)};
 for(const [actor,id] of [[a,1],[b,2]]){db.prepare('INSERT INTO lab_identities VALUES(?,?,0)').run(actor.subject,actor.email_tag);db.prepare('INSERT INTO lab_entries VALUES(?,?,1)').run(id,actor.subject);}
 let actor=a,used=false,reserveCount=0,submitCount=0;const flags={};
 const env={STAGING_ORIGIN:origin,AMENDMENT_V065_ENABLED:'OFFLINE_FIXTURE_ONLY',AMENDMENT_V064_ENABLED:'OFFLINE_FIXTURE_ONLY',AMENDMENT_V062_ENABLED:'OFFLINE_FIXTURE_ONLY',AMENDMENT_V061_ENABLED:'OFFLINE_FIXTURE_ONLY',CONTRIBUTORS_DB:{withSession(mode){if(mode!=='first-primary')throw Error('nonprimary');return{prepare(sql){return{bind(...args){return{async run(){reserveCount++;const w=db.prepare(sql).run(...args);if(flags.unknown)throw Error('unknown');return{success:true,meta:{served_by_primary:!flags.badPrimary,changes:w.changes}};}}}};}}}}};
 const deps={fallback:async()=>new Response('{}',{status:200}),burn:async()=>{if(used||flags.invalidToken)throw Error('token');used=true;return {actor:{...actor}};},access:async(_c,_e,expected)=>{if(flags.denied||(expected&&(expected.subject!==actor.subject||expected.email_tag!==actor.email_tag)))throw Error('identity');return{...actor};},submit:async(_c,_e,p)=>{submitCount++;if(flags.lost)throw Error('lost');const w=db.prepare('INSERT INTO lab_level_amendments_v059(subject,request_id) VALUES(?,?)').run(actor.subject,p.request_id);return{id:Number(w.lastInsertRowid),status:'UNREVIEWED',duplicate:false};},mine:async()=>({status:db.prepare('SELECT count(*) AS n FROM lab_amend_attempts_v064 WHERE subject=?').get(actor.subject).n?'UNRESOLVED':'NO_ATTEMPT',mayResubmit:false,manualApprovalRequired:true}),ownerQueue:async()=>{throw Error('owner only')},now:()=> '2026-11-21T09:50:00Z'};
 const controller=createReconciliationHttpV065(deps);
 const call=(path=P,data=request(3),opts={})=>{const req=new Request(opts.url||origin+path,{method:opts.method||'POST',headers:{Origin:origin,'Sec-Fetch-Site':'same-origin','X-Remura-CSRF':'1','Content-Type':'application/json','X-Remura-Intent':'synthetic',...opts.headers},...(opts.method==='GET'?{}:{body:opts.raw??JSON.stringify(data)})});return controller(req,env,{})};
 return{db,env,flags,a,b,call,who:v=>{actor=v},resetToken:()=>{used=false},counts:()=>({reserveCount,submitCount}),count:()=>db.prepare('SELECT count(*) AS n FROM lab_amend_attempts_v064').get().n};
}
const rejected=async (r,code)=>assert.equal((await r).status,code);
test('01 valid guarded write reserves and submits',async t=>{const x=fixture(t);assert.equal((await x.call()).status,200);assert.equal(x.count(),1);assert.equal(x.counts().submitCount,1)});
test('02 second request is denied while pending',async t=>{const x=fixture(t);await x.call();x.resetToken();await rejected(x.call(P,request(4)),409);assert.equal(x.count(),1)});
test('03 unknown commit cannot be automatically retried',async t=>{const x=fixture(t);x.flags.unknown=true;await rejected(x.call(),409);assert.equal(x.counts().reserveCount,1);assert.equal(x.counts().submitCount,0)});
test('04 lost write response stays uncertain',async t=>{const x=fixture(t);x.flags.lost=true;await rejected(x.call(),409);assert.equal(x.count(),1)});
test('05 no signed intent cannot reserve',async t=>{const x=fixture(t);x.flags.invalidToken=true;await rejected(x.call(),409);assert.equal(x.count(),0)});
test('06 Alice cannot write Bob original',async t=>{const x=fixture(t);await rejected(x.call(P,{...request(3),source_entry_id:2}),409)});
test('07 revoked identity denied by SQL',async t=>{const x=fixture(t);x.db.prepare('UPDATE lab_identities SET revoked=1 WHERE subject=?').run(x.a.subject);await rejected(x.call(),409)});
test('08 write gate closed denied',async t=>{const x=fixture(t);x.db.exec('UPDATE lab_state SET write_enabled=0');await rejected(x.call(),409)});
test('09 nonprimary response is never accepted',async t=>{const x=fixture(t);x.flags.badPrimary=true;await rejected(x.call(),409)});
test('10 CSRF missing denied',async t=>{const x=fixture(t);await rejected(x.call(P,request(3),{headers:{'X-Remura-CSRF':'0'}}),403)});
test('11 cross-origin denied',async t=>{const x=fixture(t);await rejected(x.call(P,request(3),{headers:{Origin:'https://evil.invalid'}}),403)});
test('12 cross-site denied',async t=>{const x=fixture(t);await rejected(x.call(P,request(3),{headers:{'Sec-Fetch-Site':'cross-site'}}),403)});
test('13 GET denied',async t=>{const x=fixture(t);await rejected(x.call(P,request(3),{method:'GET'}),403)});
test('14 query string denied',async t=>{const x=fixture(t);await rejected(x.call(P,request(3),{url:origin+P+'?extra=1'}),403)});
test('15 missing offline gate denied',async t=>{const x=fixture(t);delete x.env.AMENDMENT_V065_ENABLED;await rejected(x.call(),403)});
test('16 invalid request id fails before burn',async t=>{const x=fixture(t);await rejected(x.call(P,{...request(3),request_id:'bad'}),400);assert.equal(x.count(),0)});
test('17 invalid price fails before burn',async t=>{const x=fixture(t);await rejected(x.call(P,{...request(3),price:'1e8'}),400)});
test('18 future timestamp rejected',async t=>{const x=fixture(t);await rejected(x.call(P,{...request(3),observed_utc:'2099-01-01T00:00:00Z'}),400)});
test('19 actor injected into body rejected',async t=>{const x=fixture(t);await rejected(x.call(P,{...request(3),subject:x.b.subject}),400)});
test('20 status lookup is read-only and never allows retry',async t=>{const x=fixture(t);await x.call();const r=await x.call(R,{});assert.equal((await r.json()).data.mayResubmit,false);assert.equal(x.counts().submitCount,1)});
test('21 other user sees NO_ATTEMPT',async t=>{const x=fixture(t);await x.call();x.who(x.b);const r=await x.call(R,{});assert.equal((await r.json()).data.status,'NO_ATTEMPT')});
test('22 reconcile lookup body cannot include request_id',async t=>{const x=fixture(t);await rejected(x.call(R,{request_id:request(3).request_id}),400)});
test('23 owner queue rejects malformed cursor',async t=>{const x=fixture(t);await rejected(x.call(O,{after:-1}),400)});
test('24 original v062 route stays delegated by design',async t=>{const x=fixture(t);assert.equal((await x.call('/api/amendment/mine',{after:0})).status,200)});
