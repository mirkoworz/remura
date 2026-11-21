// REMURA Contributors v0.92 LAB — new revocation-transition tests only.
// Uses the REAL v0.92 composed candidate with synthetic Access and primary D1.
// No provider, D1 SQL endpoint, real users, deploy, or secret retrieval.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {privateWorkerCandidateV092 as worker} from './private_worker_composition_v092_lab.mjs';

const ORIGIN='https://revocation-fixture.remura.invalid';
const ACCOUNT='b'.repeat(32),AUD='a'.repeat(64),KEY='c'.repeat(64);
const identities=Object.freeze({
 a:{account_id:ACCOUNT,user_uuid:'11111111-1111-4111-8111-111111111111',email:'a@invalid.test',service_token_status:false,service_token_id:null},
 b:{account_id:ACCOUNT,user_uuid:'22222222-2222-4222-8222-222222222222',email:'b@invalid.test',service_token_status:false,service_token_id:null},
 owner:{account_id:ACCOUNT,user_uuid:'33333333-3333-4333-8333-333333333333',email:'owner@invalid.test',service_token_status:false,service_token_id:null}
});
const bytes=Uint8Array.from(KEY.match(/../g),h=>Number.parseInt(h,16));
const hex=buf=>Array.from(new Uint8Array(buf),v=>v.toString(16).padStart(2,'0')).join('');
async function tags(identity) {
 const k=await crypto.subtle.importKey('raw',bytes,{name:'HMAC',hash:'SHA-256'},false,['sign']);
 async function h(domain,v){
  const data=new TextEncoder().encode(JSON.stringify(['remura-contributors-v1',ACCOUNT,AUD,domain,v]));
  return hex(await crypto.subtle.sign('HMAC',k,data));
 }
 return [await h('uuid',identity.user_uuid),await h('email',identity.email)];
}
async function harness(){
 const users={
  a:{role:'CONTRIBUTOR',slot:'friend-a',read:true,write:true,recover:false,revoked:false,accessBlocked:false},
  b:{role:'CONTRIBUTOR',slot:'friend-b',read:true,write:true,recover:false,revoked:false,accessBlocked:false},
  owner:{role:'OWNER',slot:'owner',read:true,write:false,recover:true,revoked:false,accessBlocked:false}
 };
 const keys=new Map();
 for(const [k,v] of Object.entries(identities))keys.set((await tags(v)).join('|'),k);
 const audit={profileReads:0,generationReads:0,primarySessions:0,accessReads:0,rateCalls:0};
 const db={
  withSession(mode){
   assert.equal(mode,'first-primary');audit.primarySessions++;
   return {prepare(sql){return {bind(...args){return {async all(){
    if(sql.includes("SELECT 'OWNER' AS role")){
     audit.profileReads++;
     const person=keys.get(args[0]+'|'+args[1]),u=users[person];
     if(args[0]!==args[2]||args[1]!==args[3]||!u||u.revoked)
      return {success:true,meta:{served_by_primary:true},results:[]};
     return {success:true,meta:{served_by_primary:u.primary!==false},results:[{
      role:u.role,slot:u.slot,read_enabled:u.read?1:0,
      write_enabled:u.write?1:0,recovery_enabled:u.recover?1:0
     }]};
    }
    if(sql.includes('SELECT id FROM lab_generation')){
     audit.generationReads++;
     return {success:true,meta:{served_by_primary:true},results:[{id:1}]};
    }
    // No synthetic D1 mutations are supported in this fixture.
    return {success:true,meta:{served_by_primary:true},results:[]};
   }}}}}};
  }
 };
 const env={
  STAGING_ORIGIN:ORIGIN,STAGING_ENABLED:'D1_CANDIDATE',
  PRIVATE_WORKER_V078:'OFFLINE_FIXTURE_ONLY',ACCESS_AUD:AUD,ACCESS_ACCOUNT:ACCOUNT,
  IDENTITY_HMAC_KEY:KEY,INTENT_HMAC_KEY:'d'.repeat(64),
  LEVEL_HTTP_V074:'OFFLINE_FIXTURE_ONLY',HTTP_CANDIDATE_ENABLED:'LAB_ONLY',
  LEVEL_JOURNAL_V076:'OFFLINE_FIXTURE_ONLY',
  CONTRIBUTORS_GENERATION:'e'.repeat(32),CONTRIBUTORS_JOURNAL_PIN:'f'.repeat(64),
  CONTRIBUTORS_DB:db,CONTRIBUTORS_RATE_LIMITER:{async limit(){audit.rateCalls++;return {success:true}}}
 };
 function context(person){
  return {access:{aud:AUD,async getIdentity(){
   audit.accessReads++;
   return users[person].accessBlocked?null:identities[person];
  }}};
 }
 async function request(person,path,method='GET',headers={}){
  const h=method==='POST'?{'Origin':ORIGIN,'Sec-Fetch-Site':'same-origin',
   'X-Remura-CSRF':'1','Content-Type':'application/json',...headers}:headers;
  return worker(new Request(ORIGIN+path,{method,headers:h,
   ...(method==='POST'?{body:'{}'}:{})}),env,context(person));
 }
 return {users,audit,env,request,context};
}
test('01 previously allowed contributor page closes after D1 revocation with same Access session',async()=>{
 const h=await harness();assert.equal((await h.request('a','/contributors/')).status,200);
 h.users.a.revoked=true;const r=await h.request('a','/contributors/');
 assert.equal(r.status,403);assert.equal(r.headers.get('Cache-Control'),'no-store, max-age=0');
});
test('02 previously allowed contributor JS is denied after server-side revocation, not cached as authorized',async()=>{
 const h=await harness();const p='/contributors/levels/contributors_levels_ui_v076_lab.mjs';
 assert.equal((await h.request('a',p)).status,200);
 h.users.a.revoked=true;
 const r=await h.request('a',p,'GET',{'If-None-Match':'"pre-revocation"','Range':'bytes=0-100'});
 assert.equal(r.status,403);assert.equal(r.headers.get('Content-Type'),'application/json; charset=utf-8');
});
test('03 revoked actor can no longer query their profile while Access identity still exists',async()=>{
 const h=await harness();assert.equal((await h.request('a','/api/profile','POST')).status,200);
 h.users.a.revoked=true;const before=h.audit.generationReads;
 assert.equal((await h.request('a','/api/profile','POST')).status,403);
 assert.equal(h.audit.generationReads,before);
});
test('04 revoking friend A never silently revokes independently authorized friend B',async()=>{
 const h=await harness();assert.equal((await h.request('a','/contributors/levels/')).status,200);
 assert.equal((await h.request('b','/contributors/levels/')).status,200);
 h.users.a.revoked=true;
 assert.equal((await h.request('a','/contributors/levels/')).status,403);
 assert.equal((await h.request('b','/contributors/levels/')).status,200);
});
test('05 removing read capability closes all contributor static pages even when write flag remains true',async()=>{
 const h=await harness();h.users.a.read=false;
 assert.equal((await h.request('a','/contributors/')).status,403);
 assert.equal((await h.request('a','/contributors/levels/')).status,403);
});
test('06 Access provider denying the session blocks identity before D1 role lookup',async()=>{
 const h=await harness();h.users.a.accessBlocked=true;
 assert.equal((await h.request('a','/contributors/')).status,403);
 assert.equal(h.audit.profileReads,0);
});
test('07 non-primary D1 profile response is never a valid authorization even with a row',async()=>{
 const h=await harness();h.users.a.primary=false;
 assert.equal((await h.request('a','/contributors/')).status,403);
});
test('08 a valid contributor is still denied access to privileged OWNER assets',async()=>{
 const h=await harness();
 assert.equal((await h.request('a','/owner/levels/owner_level_integrity_ui_v078_lab.mjs')).status,403);
 assert.equal((await h.request('b','/owner/')).status,403);
});
test('09 loss of owner recovery capability closes its previous OWNER HTML and JS access',async()=>{
 const h=await harness();assert.equal((await h.request('owner','/owner/')).status,200);
 h.users.owner.recover=false;
 assert.equal((await h.request('owner','/owner/')).status,403);
 assert.equal((await h.request('owner','/owner/levels/owner_level_audit_ui_v077_lab.mjs')).status,403);
});
test('10 revoked OWNER cannot regain privileged access via generic profile POST',async()=>{
 const h=await harness();h.users.owner.recover=false;
 const before=h.audit.generationReads;
 assert.equal((await h.request('owner','/api/profile','POST')).status,403);
 assert.equal(h.audit.generationReads,before);
});
test('11 malformed identity account never selects a D1 role (even with valid email)',async()=>{
 const h=await harness();const ctx=h.context('b');ctx.access.getIdentity=async()=>({
  ...identities.b,account_id:'0'.repeat(32)
 });
 const r=await worker(new Request(ORIGIN+'/contributors/'),h.env,ctx);
 assert.equal(r.status,403);assert.equal(h.audit.profileReads,0);
});
test('12 no profile selected if Access presents a service-token identity',async()=>{
 const h=await harness();const ctx=h.context('a');
 ctx.access.getIdentity=async()=>({...identities.a,service_token_status:true});
 const r=await worker(new Request(ORIGIN+'/contributors/'),h.env,ctx);
 assert.equal(r.status,403);assert.equal(h.audit.profileReads,0);
});
