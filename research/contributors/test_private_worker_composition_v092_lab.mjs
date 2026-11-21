// REMURA Contributors v0.92 LAB: only NEW real-composition integration checks.
// No live provider calls, no secrets, and no legacy suite reruns.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {privateWorkerCandidateV092 as candidate,V092_COMPOSITION} from './private_worker_composition_v092_lab.mjs';
import * as surface from './private_worker_composition_v092_lab.mjs';

const ORIGIN='https://fixture.remura.invalid';
const ACCOUNT='b'.repeat(32), AUD='a'.repeat(64);
const ID={account_id:ACCOUNT,user_uuid:'12345678-1234-1234-1234-123456789abc',
 email:'offline@invalid.test',service_token_status:false,service_token_id:null};
function harness(role='CONTRIBUTOR',flags={}){
 const state={profileReads:0,genReads:0,identityReads:0,primarySessions:0,rateCalls:0};
 const db={
  withSession(mode){
   assert.equal(mode,'first-primary');state.primarySessions++;
   return {prepare(sql){return {bind(...args){return {async all(){
    if(sql.includes("SELECT 'OWNER' AS role")){
     state.profileReads++;
     if(flags.revoked)return {success:true,meta:{served_by_primary:true},results:[]};
     const row={role,slot:role==='OWNER'?'owner':'friend-a',
      read_enabled:flags.read===false?0:1,
      write_enabled:role==='OWNER'?0:(flags.write===false?0:1),
      recovery_enabled:role==='OWNER'?(flags.recover===false?0:1):0};
     return {success:true,meta:{served_by_primary:true},results:[row]};
    }
    if(sql.includes('SELECT id FROM lab_generation')){
     state.genReads++;return {success:true,meta:{served_by_primary:true},results:[{id:1}]};
    }
    return {success:true,meta:{served_by_primary:true},results:[]};
   }}}}}};
  }
 };
 const env={STAGING_ORIGIN:ORIGIN,STAGING_ENABLED:'D1_CANDIDATE',
  PRIVATE_WORKER_V078:'OFFLINE_FIXTURE_ONLY',ACCESS_AUD:AUD,ACCESS_ACCOUNT:ACCOUNT,
  IDENTITY_HMAC_KEY:'c'.repeat(64),INTENT_HMAC_KEY:'d'.repeat(64),
  LEVEL_HTTP_V074:'OFFLINE_FIXTURE_ONLY',HTTP_CANDIDATE_ENABLED:'LAB_ONLY',
  LEVEL_JOURNAL_V076:'OFFLINE_FIXTURE_ONLY',
  CONTRIBUTORS_GENERATION:'e'.repeat(32),CONTRIBUTORS_JOURNAL_PIN:'f'.repeat(64),
  CONTRIBUTORS_DB:db,CONTRIBUTORS_RATE_LIMITER:{async limit(){state.rateCalls++;return {success:true}}}};
 const ctx={access:{aud:AUD,async getIdentity(){state.identityReads++;return flags.badIdentity?{...ID,service_token_status:true}:ID}}};
 return {env,ctx,state};
}
function req(path,method='GET',headers={}){
 return new Request(ORIGIN+path,{method,...(method==='POST'?{body:'{}'}:{}),
 headers:method==='POST'?{'Origin':ORIGIN,'Sec-Fetch-Site':'same-origin',
 'Content-Type':'application/json','X-Remura-CSRF':'1',...headers}:headers});
}
async function send(h,path,method='GET',headers={}){
 return candidate(req(path,method,headers),h.env,h.ctx);
}
test('01 no default deployable Worker exported',()=>{
 assert.equal(Object.hasOwn(surface,'default'),false);
 assert.deepEqual(Object.keys(surface).sort(),['V092_COMPOSITION','privateWorkerCandidateV092'].sort());
 assert.equal(V092_COMPOSITION.pilotAllowed,false);
});
test('02 real dependencies serve authorized Contributor HTML',async()=>{
 const h=harness();const r=await send(h,'/contributors/');
 assert.equal(r.status,200);assert.match(await r.text(),/REMURA Contributors v0.78 LAB/);
 assert.ok(h.state.profileReads>=1);assert.ok(h.state.identityReads>=1);
});
test('03 real dependencies deny OWNER access to Contributor HTML',async()=>{
 assert.equal((await send(harness('OWNER'),'/contributors/')).status,403);
});
test('04 OWNER can read its private HTML only with recovery permission',async()=>{
 const h=harness('OWNER');const r=await send(h,'/owner/');
 assert.equal(r.status,200);assert.match(await r.text(),/OWNER DESK/);
 assert.equal(h.state.profileReads,1); // one primary profile read on OWNER GET
});
test('05 OWNER recovery revocation closes privileged GET even with read enabled',async()=>{
 const h=harness('OWNER',{recover:false});
 const r=await send(h,'/owner/');assert.equal(r.status,403);
 assert.equal(h.state.profileReads,1);
});
test('06 Contributor cannot view OWNER HTML',async()=>{
 assert.equal((await send(harness(),'/owner/')).status,403);
});
test('07 OWNER JS asset also requires recovery permission',async()=>{
 const h=harness('OWNER',{recover:false});
 assert.equal((await send(h,'/owner/levels/owner_level_integrity_ui_v078_lab.mjs')).status,403);
});
test('08 revoked D1 identity cannot read Contributor HTML',async()=>{
 const h=harness('CONTRIBUTOR',{revoked:true});
 assert.equal((await send(h,'/contributors/')).status,403);
});
test('09 non-human Access service token identity fails before D1 profile',async()=>{
 const h=harness('OWNER',{badIdentity:true});
 assert.equal((await send(h,'/owner/')).status,403);
 assert.equal(h.state.profileReads,0);
});
test('10 real composed POST path resolves own profile via HMAC, primary D1 and generation',async()=>{
 const h=harness();
 const r=await send(h,'/api/profile','POST');
 assert.equal(r.status,200);
 const body=await r.json();
 assert.equal(body.data.role,'CONTRIBUTOR');
 assert.equal(body.data.can_recover,false);
 assert.ok(h.state.profileReads>=2);
 assert.equal(h.state.genReads,1);
 assert.equal(h.state.rateCalls,1);
});
test('11 forged role header denied before D1 read',async()=>{
 const h=harness();const r=await send(h,'/api/profile','POST',{'X-Remura-Role':'OWNER'});
 assert.equal(r.status,403);assert.equal(h.state.profileReads,0);
});
test('12 cross-origin GET cannot leak OWNER area even with authorized identity',async()=>{
 const h=harness('OWNER');
 const r=await candidate(new Request('https://elsewhere.invalid/owner/'),h.env,h.ctx);
 assert.equal(r.status,403);assert.equal(h.state.profileReads,0);
});
test('13 no provider availability or pilot claim from offline composition',()=>{
 assert.equal(V092_COMPOSITION.realD1Tested,false);
 assert.equal(V092_COMPOSITION.liveAccessJwtVerified,false);
 assert.equal(V092_COMPOSITION.freeQuotaAttested,false);
});

test('14 OWNER recovery-disabled cannot even query generic own profile',async()=>{
 const h=harness('OWNER',{recover:false});
 const r=await send(h,'/api/profile','POST');
 assert.equal(r.status,403);
 assert.equal(h.state.profileReads,1);
 assert.equal(h.state.genReads,0);
});
test('15 OWNER with recovery can query profile through existing backend',async()=>{
 const h=harness('OWNER');const r=await send(h,'/api/profile','POST');
 assert.equal(r.status,200);
 const body=await r.json();
 assert.equal(body.data.role,'OWNER');
 assert.equal(body.data.can_recover,true);
 assert.equal(h.state.genReads,1);
 assert.ok(h.state.profileReads>=2);
});
