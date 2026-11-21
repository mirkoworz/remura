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
export async function fixture(t){
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

