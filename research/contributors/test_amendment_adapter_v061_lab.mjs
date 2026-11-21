// REMURA Contributors v0.61 LAB — genuine Node 22 sqlite D1 candidate fixture, no network.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
import {webcrypto} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {dirname,join} from 'node:path';
import {accessBinding} from './access_binding_candidate.mjs';
import {submitAmendmentLab,ownAmendmentsLab,ownerAmendmentQueueLab,ownerAmendmentDecisionLab,approvedLevelsLab} from './amendment_adapter_v061_lab.mjs';

globalThis.crypto ??= webcrypto;
const ROOT=dirname(fileURLToPath(import.meta.url));
const UUID='00000000-0000-4000-8000-', stamp=ms=>new Date(ms).toISOString().slice(0,19)+'Z';
const identities={
 owner:{account_id:'a'.repeat(32),user_uuid:'cccccccc-cccc-4ccc-8ccc-cccccccccccc',email:'owner@example.invalid',service_token_status:false},
 alice:{account_id:'a'.repeat(32),user_uuid:'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',email:'alice@example.invalid',service_token_status:false},
 bob:{account_id:'a'.repeat(32),user_uuid:'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',email:'bob@example.invalid',service_token_status:false}
};
const original=(name)=>readFileSync(join(ROOT,name),'utf8');
function fakeDb(db,hooks={}) {
 return {withSession(mode){
  if(mode!=='first-primary')throw Error('wrong_session');
  hooks.session?.(mode);
  return {prepare(sql){return {bind(...args){return {
   async all(){hooks.read?.(sql,args);const results=db.prepare(sql).all(...args);return {success:true,meta:{served_by_primary:hooks.badReadPrimary!==true},results};},
   async run(){hooks.beforeWrite?.(sql,args);const out=db.prepare(sql).run(...args);hooks.afterWrite?.(sql,args);if(hooks.unknownWrite)throw Error('unknown_commit');return {success:true,meta:{served_by_primary:hooks.badWritePrimary!==true,changes:out.changes}};}
  };}};}};
 }};
}
async function fixture(t){
 const db=new DatabaseSync(':memory:');t.after(()=>db.close());
 db.exec('PRAGMA foreign_keys=ON');db.exec(original('d1_access_candidate.sql'));db.exec(original('d1_amendment_v059_lab.sql'));
 let who='alice';const hooks={};let rateCalls=0;let writes=0;let accessCalls=0;
 const env={STAGING_ENABLED:'D1_CANDIDATE',AMENDMENT_V061_ENABLED:'OFFLINE_FIXTURE_ONLY',ACCESS_AUD:'b'.repeat(64),ACCESS_ACCOUNT:'a'.repeat(32),IDENTITY_HMAC_KEY:'c'.repeat(64),
  CONTRIBUTORS_GENERATION:'d'.repeat(32),CONTRIBUTORS_JOURNAL_PIN:'e'.repeat(64),
  CONTRIBUTORS_RATE_LIMITER:{limit:async()=>{rateCalls++;return {success:true};}},
  CONTRIBUTORS_DB:fakeDb(db,{session:()=>{},read:(...a)=>hooks.read?.(...a), beforeWrite:(...a)=>{writes++;hooks.beforeWrite?.(...a)},afterWrite:(...a)=>hooks.afterWrite?.(...a),
    get badReadPrimary(){return hooks.badReadPrimary===true},get badWritePrimary(){return hooks.badWritePrimary===true},get unknownWrite(){return hooks.unknownWrite===true}})};
 const ctx={access:{aud:env.ACCESS_AUD,async getIdentity(){accessCalls++;return {...identities[who]};}}};
 const actors={};for(const name of ['owner','alice','bob']){who=name;actors[name]=await accessBinding(ctx,env);}who='alice';
 db.prepare('INSERT INTO lab_generation VALUES(1,?,?)').run(env.CONTRIBUTORS_GENERATION,env.CONTRIBUTORS_JOURNAL_PIN);
 db.prepare('INSERT INTO lab_owner(id,subject,email_tag) VALUES(1,?,?)').run(actors.owner.subject,actors.owner.email_tag);
 for(const [name,slot] of [['alice','friend-a'],['bob','friend-b']])db.prepare('INSERT INTO lab_identities(subject,email_tag,slot) VALUES(?,?,?)').run(actors[name].subject,actors[name].email_tag,slot);
 db.prepare('INSERT INTO lab_catalog VALUES(?,?,?,?,?,?,1)').run('EURUSD','OANDA','EURUSD','SPOT','','fixture-fx');
 db.exec('UPDATE lab_state SET write_enabled=1,read_enabled=1,recovery_enabled=1');
 const now=Date.now(),base=stamp(now-500000),anchor=stamp(now-700000),observed=stamp(now-200000);
 for(const [i,name] of [[1,'alice'],[2,'bob']]) db.prepare('INSERT INTO lab_entries(subject,request_id,market,provider,ticker,product,contract,period,kind,price,anchor_utc,observed_utc,received_utc,note,source_group) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)')
 .run(actors[name].subject,UUID+String(i).padStart(12,'0'),'EURUSD','OANDA','EURUSD','SPOT','','DAY','DELTA_PEAK','1.123',anchor,anchor,base,'fixture','fixture-fx');
 db.prepare('INSERT INTO lab_reviews(entry_id,owner,action,at_utc,reason) VALUES(?,?,?,?,?)').run(1,actors.owner.subject,'APPROVED',base,'fixture');
 const payload=(source_entry_id=1,n=3)=>({source_entry_id,request_id:UUID+String(n).padStart(12,'0'),price:'1.234',observed_utc:observed,note:'prova sintetica'});
 return {db,ctx,env,actors,payload,now,base,hooks,who:name=>{who=name;},identity:name=>identities[name],counts:()=>({rateCalls,writes,accessCalls})};
}
const denied=async f=>{await assert.rejects(f)};

test('01 valid personal amendment goes to UNREVIEWED',async t=>{const x=await fixture(t);const r=await submitAmendmentLab(x.ctx,x.env,x.payload());assert.equal(r.status,'UNREVIEWED');assert.equal(r.duplicate,false);});
test('02 same request is idempotent with no second write',async t=>{const x=await fixture(t);const p=x.payload();await submitAmendmentLab(x.ctx,x.env,p);const before=x.counts().writes;const r=await submitAmendmentLab(x.ctx,x.env,p);assert.equal(r.duplicate,true);assert.equal(x.counts().writes,before);});
test('03 same idempotency key with changed price denied',async t=>{const x=await fixture(t);const p=x.payload();await submitAmendmentLab(x.ctx,x.env,p);await denied(()=>submitAmendmentLab(x.ctx,x.env,{...p,price:'2'}));});
test('04 same key changed source denied',async t=>{const x=await fixture(t);const p=x.payload();await submitAmendmentLab(x.ctx,x.env,p);await denied(()=>submitAmendmentLab(x.ctx,x.env,{...p,source_entry_id:2}));});
test('05 Alice cannot amend Bob entry',async t=>{const x=await fixture(t);await denied(()=>submitAmendmentLab(x.ctx,x.env,x.payload(2)));});
test('06 Bob cannot amend Alice entry',async t=>{const x=await fixture(t);x.who('bob');await denied(()=>submitAmendmentLab(x.ctx,x.env,x.payload(1)));});
test('07 owner cannot impersonate contributor',async t=>{const x=await fixture(t);x.who('owner');await denied(()=>submitAmendmentLab(x.ctx,x.env,x.payload()));});
test('08 revoked Alice cannot amend',async t=>{const x=await fixture(t);x.db.prepare('UPDATE lab_identities SET revoked=1 WHERE subject=?').run(x.actors.alice.subject);await denied(()=>submitAmendmentLab(x.ctx,x.env,x.payload()));});
test('09 disabled write gate blocks',async t=>{const x=await fixture(t);x.db.exec('UPDATE lab_state SET write_enabled=0');await denied(()=>submitAmendmentLab(x.ctx,x.env,x.payload()));});
test('10 wrong generation blocks before write',async t=>{const x=await fixture(t);x.env.CONTRIBUTORS_GENERATION='f'.repeat(32);await denied(()=>submitAmendmentLab(x.ctx,x.env,x.payload()));assert.equal(x.counts().writes,0);});
test('11 disabled fixture-only switch blocks',async t=>{const x=await fixture(t);delete x.env.AMENDMENT_V061_ENABLED;await denied(()=>submitAmendmentLab(x.ctx,x.env,x.payload()));});
test('12 missing rate limiter blocks',async t=>{const x=await fixture(t);delete x.env.CONTRIBUTORS_RATE_LIMITER;await denied(()=>submitAmendmentLab(x.ctx,x.env,x.payload()));});
test('13 rate limiter denies',async t=>{const x=await fixture(t);x.env.CONTRIBUTORS_RATE_LIMITER={limit:async()=>({success:false})};await denied(()=>submitAmendmentLab(x.ctx,x.env,x.payload()));});
test('14 unknown limiter response fails closed',async t=>{const x=await fixture(t);x.env.CONTRIBUTORS_RATE_LIMITER={limit:async()=>null};await denied(()=>submitAmendmentLab(x.ctx,x.env,x.payload()));});
test('15 fake primary metadata on read denied',async t=>{const x=await fixture(t);x.hooks.badReadPrimary=true;await denied(()=>submitAmendmentLab(x.ctx,x.env,x.payload()));});
test('16 fake primary metadata on write denied with no automatic retry',async t=>{const x=await fixture(t);x.hooks.badWritePrimary=true;await denied(()=>submitAmendmentLab(x.ctx,x.env,x.payload()));assert.equal(x.counts().writes,1);});
test('17 unknown write confirmation never retried',async t=>{const x=await fixture(t);x.hooks.unknownWrite=true;await denied(()=>submitAmendmentLab(x.ctx,x.env,x.payload()));assert.equal(x.counts().writes,1);});
test('18 identity changes before dispatch must block',async t=>{const x=await fixture(t);let once=false;x.hooks.read=()=>{if(!once){once=true;x.who('bob')}};await denied(()=>submitAmendmentLab(x.ctx,x.env,x.payload()));assert.equal(x.counts().writes,0);});
test('19 identity changes after commit produces uncertainty (not retry)',async t=>{const x=await fixture(t);x.hooks.afterWrite=()=>x.who('bob');await denied(()=>submitAmendmentLab(x.ctx,x.env,x.payload()));assert.equal(x.counts().writes,1);});
test('20 client actor fields rejected even if matching',async t=>{const x=await fixture(t);await denied(()=>submitAmendmentLab(x.ctx,x.env,{...x.payload(),subject:x.actors.alice.subject}));});
test('21 malformed UUID rejected before DB',async t=>{const x=await fixture(t);await denied(()=>submitAmendmentLab(x.ctx,x.env,{...x.payload(),request_id:'bad'}));assert.equal(x.counts().rateCalls,0);});
test('22 malformed price rejected before DB',async t=>{const x=await fixture(t);await denied(()=>submitAmendmentLab(x.ctx,x.env,{...x.payload(),price:'2e6'}));});
test('23 invalid note control rejected',async t=>{const x=await fixture(t);await denied(()=>submitAmendmentLab(x.ctx,x.env,{...x.payload(),note:'a\nb'}));});
test('24 future observation time rejected',async t=>{const x=await fixture(t);await denied(()=>submitAmendmentLab(x.ctx,x.env,{...x.payload(),observed_utc:stamp(Date.now()+86400000)}));});
test('25 no cross-user receipts',async t=>{const x=await fixture(t);await submitAmendmentLab(x.ctx,x.env,x.payload());x.who('bob');const rows=await ownAmendmentsLab(x.ctx,x.env);assert.deepEqual(rows,[]);});
test('26 Alice sees only her receipt, not identity metadata',async t=>{const x=await fixture(t);await submitAmendmentLab(x.ctx,x.env,x.payload());const rows=await ownAmendmentsLab(x.ctx,x.env);assert.equal(rows.length,1);assert.equal('subject' in rows[0],false);assert.equal('email_tag' in rows[0],false);});
test('27 revoked identity loses read access',async t=>{const x=await fixture(t);await submitAmendmentLab(x.ctx,x.env,x.payload());x.db.prepare('UPDATE lab_identities SET revoked=1 WHERE subject=?').run(x.actors.alice.subject);await denied(()=>ownAmendmentsLab(x.ctx,x.env));});
test('28 owner queue cannot be seen by Alice',async t=>{const x=await fixture(t);await submitAmendmentLab(x.ctx,x.env,x.payload());await denied(()=>ownerAmendmentQueueLab(x.ctx,x.env));});
test('29 owner can see pending queue',async t=>{const x=await fixture(t);await submitAmendmentLab(x.ctx,x.env,x.payload());x.who('owner');const rows=await ownerAmendmentQueueLab(x.ctx,x.env);assert.equal(rows.length,1);assert.equal(rows[0].id,1);});
test('30 Alice cannot approve',async t=>{const x=await fixture(t);await submitAmendmentLab(x.ctx,x.env,x.payload());await denied(()=>ownerAmendmentDecisionLab(x.ctx,x.env,{id:1,action:'APPROVED',reason:'ok'}));});
test('31 owner can approve with complete history',async t=>{const x=await fixture(t);await submitAmendmentLab(x.ctx,x.env,x.payload());x.who('owner');const r=await ownerAmendmentDecisionLab(x.ctx,x.env,{id:1,action:'APPROVED',reason:'approved'});assert.equal(r.action,'APPROVED');x.who('alice');assert.equal((await ownAmendmentsLab(x.ctx,x.env))[0].status,'APPROVED');});
test('32 approved projection changes only after owner approval',async t=>{const x=await fixture(t);const p=x.payload();await submitAmendmentLab(x.ctx,x.env,p);assert.equal((await approvedLevelsLab(x.ctx,x.env))[0].price,'1.123');x.who('owner');await ownerAmendmentDecisionLab(x.ctx,x.env,{id:1,action:'APPROVED',reason:'approved'});x.who('alice');assert.equal((await approvedLevelsLab(x.ctx,x.env))[0].price,'1.234');});
test('33 non-owner sees approved-only projection, no private note',async t=>{const x=await fixture(t);const r=await approvedLevelsLab(x.ctx,x.env);assert.equal(r.length,1);assert.equal('note' in r[0],false);assert.equal('subject' in r[0],false);});
test('34 owner review with no recovery mode rejects REVOKED',async t=>{const x=await fixture(t);await submitAmendmentLab(x.ctx,x.env,x.payload());x.who('owner');await ownerAmendmentDecisionLab(x.ctx,x.env,{id:1,action:'APPROVED',reason:'yes'});x.db.exec('UPDATE lab_state SET recovery_enabled=0');await denied(()=>ownerAmendmentDecisionLab(x.ctx,x.env,{id:1,action:'REVOKED',reason:'no'}));});
test('35 owner review requires reason',async t=>{const x=await fixture(t);x.who('owner');await denied(()=>ownerAmendmentDecisionLab(x.ctx,x.env,{id:1,action:'APPROVED',reason:' '}));});
test('36 owner review with extra subject field rejects',async t=>{const x=await fixture(t);x.who('owner');await denied(()=>ownerAmendmentDecisionLab(x.ctx,x.env,{id:1,action:'APPROVED',reason:'yes',subject:x.actors.owner.subject}));});
test('37 malformed after cursor rejected',async t=>{const x=await fixture(t);await denied(()=>ownAmendmentsLab(x.ctx,x.env,-1));});
test('38 service-token Access identity blocked',async t=>{const x=await fixture(t);x.identity('alice').service_token_status=true;await denied(()=>submitAmendmentLab(x.ctx,x.env,x.payload()));x.identity('alice').service_token_status=false;});
test('39 changed Access audience blocks',async t=>{const x=await fixture(t);x.ctx.access.aud='f'.repeat(64);await denied(()=>submitAmendmentLab(x.ctx,x.env,x.payload()));});
test('40 no trusted Access identity blocks',async t=>{const x=await fixture(t);x.ctx.access=undefined;await denied(()=>submitAmendmentLab(x.ctx,x.env,x.payload()));});
