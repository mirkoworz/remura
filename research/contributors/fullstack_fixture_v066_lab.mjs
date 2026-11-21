// REMURA Contributors v0.66 LAB — NEW integration against byte-pinned original D1 SQL & modules.
// Every module below is the exact GitHub blob from the v0.65 branch. No live Cloudflare calls.
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {webcrypto} from 'node:crypto';
import {amendmentHttpCandidateV065 as handler} from './reconciliation_composition_v065_lab.mjs';
export {handler};
import {accessBinding} from './access_binding_candidate.mjs';
globalThis.crypto ??= webcrypto;
export const origin='https://contributors.lab.invalid';
export const submit='/api/amendment/submit',intent='/api/amendment/intent',reconcile='/api/amendment/reconcile';
export const review='/owner/amendment/review',queue='/owner/amendment/reconcile-queue';
export const clock=()=>new Date().toISOString().slice(0,19)+'Z';
const secondsAgo=n=>new Date(Date.now()-n*1000).toISOString().slice(0,19)+'Z';
const sha='9ed38b6ed83755186af05f1bf28b4608cdc5f901';
export const identities={
 alice:{account_id:'a'.repeat(32),user_uuid:'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',email:'alice@example.invalid',service_token_status:false},
 bob:{account_id:'a'.repeat(32),user_uuid:'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',email:'bob@example.invalid',service_token_status:false},
 owner:{account_id:'a'.repeat(32),user_uuid:'cccccccc-cccc-4ccc-8ccc-cccccccccccc',email:'owner@example.invalid',service_token_status:false},
};
export const reqId=n=>'00000000-0000-4000-8000-'+String(n).padStart(12,'0');
const read=name=>readFileSync(new URL('./'+name,import.meta.url),'utf8');
function fullFixtureDB(t){
 const db=new DatabaseSync(':memory:');t.after(()=>db.close());
 db.exec('PRAGMA foreign_keys=ON');
 for(const n of ['d1_access_candidate.sql','d1_amendment_v059_lab.sql','d1_reconciliation_v064_lab.sql'])db.exec(read(n));
 return db;
}
export async function fixture(t){
 const db=fullFixtureDB(t);
 let who='alice',primary=true,rate=true,failOn='',afterWrite=null;
 const counts={write:0,read:0,access:0,limit:0};
 const env={
  STAGING_ORIGIN:origin,STAGING_ENABLED:'D1_CANDIDATE',
  AMENDMENT_V061_ENABLED:'OFFLINE_FIXTURE_ONLY',AMENDMENT_V062_ENABLED:'OFFLINE_FIXTURE_ONLY',
  AMENDMENT_V064_ENABLED:'OFFLINE_FIXTURE_ONLY',AMENDMENT_V065_ENABLED:'OFFLINE_FIXTURE_ONLY',
  RECONCILIATION_V064_ENABLED:'OFFLINE_FIXTURE_ONLY',ACCESS_AUD:'b'.repeat(64),ACCESS_ACCOUNT:'a'.repeat(32),
  IDENTITY_HMAC_KEY:'c'.repeat(64),INTENT_HMAC_KEY:'f'.repeat(64),
  CONTRIBUTORS_GENERATION:'d'.repeat(32),CONTRIBUTORS_JOURNAL_PIN:'e'.repeat(64),
  CONTRIBUTORS_RATE_LIMITER:{async limit(){counts.limit++;return {success:rate}}},
  CONTRIBUTORS_DB:{
    withSession(mode){
      assert.equal(mode,'first-primary');
      return { prepare(sql){
        return { bind(...args){
          return {
            async all(){
              counts.read++;
              if(failOn==='beforeRead')throw Error('synthetic read');
              const results=db.prepare(sql).all(...args);
              return {success:true,meta:{served_by_primary:primary},results};
            },
            async run(){
              counts.write++;
              if(failOn==='beforeWrite')throw Error('synthetic write');
              const r=db.prepare(sql).run(...args);
              if(typeof afterWrite==='function')afterWrite(sql,args);
              if(failOn==='afterWrite')throw Error('synthetic lost response');
              return {success:true,meta:{served_by_primary:primary,changes:r.changes}};
            }
          };
        }};
      }};
    }
  }
 };
 const ctx={access:{aud:env.ACCESS_AUD,async getIdentity(){counts.access++;return {...identities[who]};}}};
 const actors={};for(const name of Object.keys(identities)){who=name;actors[name]=await accessBinding(ctx,env);}who='alice';
 db.prepare('INSERT INTO lab_generation VALUES(1,?,?)').run(env.CONTRIBUTORS_GENERATION,env.CONTRIBUTORS_JOURNAL_PIN);
 db.prepare('INSERT INTO lab_owner(id,subject,email_tag) VALUES(1,?,?)').run(actors.owner.subject,actors.owner.email_tag);
 db.prepare('INSERT INTO lab_identities(subject,email_tag,slot) VALUES(?,?,?)').run(actors.alice.subject,actors.alice.email_tag,'friend-a');
 db.prepare('INSERT INTO lab_identities(subject,email_tag,slot) VALUES(?,?,?)').run(actors.bob.subject,actors.bob.email_tag,'friend-b');
 db.prepare('INSERT INTO lab_catalog VALUES(?,?,?,?,?,?,1)').run('EURUSD','OANDA','EURUSD','SPOT','','fixture-fx');
 db.exec('UPDATE lab_state SET write_enabled=1,read_enabled=1,recovery_enabled=1');
 const T=secondsAgo(800),before=secondsAgo(950),receive=secondsAgo(650),reviewed=secondsAgo(630);
 for(const [i,name] of [[1,'alice'],[2,'bob']]){
  db.prepare('INSERT INTO lab_entries(subject,request_id,market,provider,ticker,product,contract,period,kind,price,anchor_utc,observed_utc,received_utc,note,source_group) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)')
  .run(actors[name].subject,reqId(i),'EURUSD','OANDA','EURUSD','SPOT','','DAY','DELTA_PEAK','1.123',before,T,receive,'fixture','fixture-fx');
  db.prepare('INSERT INTO lab_reviews(entry_id,owner,action,at_utc,reason) VALUES(?,?,?,?,?)').run(i,actors.owner.subject,'APPROVED',reviewed,'fixture');
 }
 async function call(path,body={},token,opts={}){
  const h={Origin:origin,'Sec-Fetch-Site':'same-origin','X-Remura-CSRF':'1','Content-Type':'application/json',...opts.headers};
  if(token!==undefined)h['X-Remura-Intent']=token;
  const request=new Request(opts.url??origin+path,{method:'POST',headers:h,body:JSON.stringify(body)});
  return handler(request,env,ctx);
 }
 const payload=(n=3,src=1)=>({source_entry_id:src,request_id:reqId(n),price:'1.234',observed_utc:secondsAgo(500),note:'fixture'});
 const issue=async(path,body)=>{const r=await call(intent,{path,body});const j=await r.json();assert.equal(r.status,200,JSON.stringify(j));return j.data.intent};
 const submitWith=async p=>call(submit,p,await issue(submit,p));
 const reviewWith=async p=>call(review,p,await issue(review,p));
 const getState=async()=>{const r=await call(reconcile,{});return {status:r.status,data:(await r.json()).data};};
 const n=name=>db.prepare('SELECT count(*) AS total FROM '+name).get().total;
 return {db,env,ctx,actors,counts,call,payload,issue,submitWith,reviewWith,getState,n,
   setWho:x=>{who=x},setPrimary:x=>{primary=x},setRate:x=>{rate=x},setFailure:x=>{failOn=x},setAfterWrite:x=>{afterWrite=x},identity:x=>identities[x]};
}
export const json=async res=>{const j=await res.json();return {status:res.status,...j};};
