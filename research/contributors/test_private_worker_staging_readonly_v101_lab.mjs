// REMURA Contributors v1.01 LAB — seven NEW GET-only staging contract tests.
// Synthetic identities and D1 handles, no external network, Cloudflare, writes or credentials.
import test from 'node:test';
import assert from 'node:assert/strict';
import {createStagingReadOnlyV101,V101_STATE} from './private_worker_staging_readonly_v101_lab.mjs';
import {privateAssetFilesV096} from './private_assets_v096_lab.mjs';
const ORIGIN='https://remura-v101-fixture.invalid';
function rig(){
 const env={STAGING_ENABLED:'D1_CANDIDATE',
   PRIVATE_WORKER_V078:'STAGING_AUTHENTICATED_READONLY',
   CONTRIBUTORS_STAGE_READONLY:'EXPLICIT_STAGING_ONLY',
   STAGING_ORIGIN:ORIGIN,ACCESS_AUD:'fixture',
   CONTRIBUTORS_DB:{prepare:()=>({})}};
 const states={
   OWNER:{role:'OWNER',can_read:true,can_write:false,can_recover:false},
   A:{role:'CONTRIBUTOR',can_read:true,can_write:false,can_recover:false}
 };
 const count={auth:0,read:0};
 const worker=createStagingReadOnlyV101({
   authenticate:async ctx=>{count.auth++;return {
     subject:(ctx.access.principal==='OWNER'?'a':'b').repeat(64),
     email_tag:(ctx.access.principal==='OWNER'?'c':'d').repeat(64)};},
   profileRead:async ctx=>{count.read++;return states[ctx.access.principal];},
   assetFiles:privateAssetFilesV096
 });
 const send=(who,path='/',opts={},override={})=>{
   const ctx={access:{principal:who,aud:env.ACCESS_AUD,getIdentity:async()=>null}};
   return worker(new Request(ORIGIN+path,opts),{...env,...override},ctx);
 };
 return {env,states,count,send,worker};
}
test('01 valid OWNER / CONTRIBUTOR GET only on role-bound private pages',async()=>{
 const r=rig();
 for(const [who,path] of [['OWNER','/owner/'],['OWNER','/owner/levels/'],
   ['A','/contributors/'],['A','/contributors/levels/']]){
   const response=await r.send(who,path);
   assert.equal(response.status,200,who+' '+path);
   assert.match(response.headers.get('content-type'),/^text\/html/);
   assert.match(response.headers.get('cache-control'),/no-store/);
   assert.equal(response.headers.get('x-content-type-options'),'nosniff');
 }
 assert.equal(r.count.auth,4);assert.equal(r.count.read,4);
});
test('02 cross-role pages / assets denied at backend, not just hidden UI',async()=>{
 const r=rig();
 for(const [who,path] of [
   ['A','/owner/'],['A','/owner/levels/'],
   ['A','/owner/levels/owner_level_audit_ui_v077_lab.mjs'],
   ['OWNER','/contributors/'],['OWNER','/contributors/levels/']]){
   assert.equal((await r.send(who,path)).status,403,who+' '+path);
 }
});
test('03 static CSS/JS of own area works, but unknown assets and query strings fail closed',async()=>{
 const r=rig();
 assert.equal((await r.send('A','/contributors/levels/contributors_private_levels_v076_lab.css')).status,200);
 assert.equal((await r.send('A','/contributors/levels/contributors_levels_ui_v096_lab.mjs')).status,200);
 assert.equal((await r.send('A','/contributors/levels/owner_level_audit_ui_v077_lab.mjs')).status,403);
 for(const p of ['/admin/','/api/profile','/private-api/health','/owner/nonsense.js',
   '/contributors/?next=x','/contributors/%2e%2e/owner/'])
   assert.equal((await r.send('A',p)).status,403,p);
});
test('04 no POST, PUT, DELETE, HEAD, or OPTIONS can enter any handler',async()=>{
 const r=rig();
 for(const method of ['POST','PUT','PATCH','DELETE','HEAD','OPTIONS']){
   const opts={method,...(method==='POST'||method==='PUT'||method==='PATCH'?{body:'{}'}:{})};
   assert.equal((await r.send('A','/contributors/',opts)).status,403,method);
 }
 assert.equal(r.count.auth,0);assert.equal(r.count.read,0);
});
test('05 deployment mode must match every isolated staging gate and Direct Access context',async()=>{
 const r=rig();
 for(const o of [
   {PRIVATE_WORKER_V078:'OFFLINE_FIXTURE_ONLY'},
   {PRIVATE_WORKER_V078:undefined},
   {STAGING_ENABLED:undefined},
   {CONTRIBUTORS_STAGE_READONLY:undefined},
   {STAGING_ORIGIN:'http://remura-v101-fixture.invalid'},
   {CONTRIBUTORS_DB:null},
   {CONTRIBUTORS_DB:{}},
   {ACCESS_AUD:'other'}
 ])assert.equal((await r.send('A','/contributors/',{},o)).status,403,JSON.stringify(o));
 const noAccess=await r.worker(new Request(ORIGIN+'/contributors/'),r.env,{});
 assert.equal(noAccess.status,403);
 assert.equal(r.count.auth,0);
});
test('06 role capability contradictions and a revoked open tab must deny a fresh GET',async()=>{
 const r=rig();
 assert.equal((await r.send('A','/contributors/')).status,200);
 r.states.A.can_read=false;
 assert.equal((await r.send('A','/contributors/')).status,403);
 r.states.A.can_read=true;r.states.A.can_recover=true;
 assert.equal((await r.send('A','/contributors/levels/')).status,403);
 r.states.A.can_recover=false;r.states.A.can_write='true';
 assert.equal((await r.send('A','/contributors/')).status,403);
 assert.equal(r.count.read,4);
});
test('07 safe metadata: never claim Cloudflare login or deploy proof',()=>{
 assert.equal(V101_STATE.getOnly,true);
 assert.equal(V101_STATE.allWritesDenied,true);
 assert.equal(V101_STATE.accessRuntimeVerified,false);
 assert.equal(V101_STATE.safariVerified,false);
 assert.equal(V101_STATE.stagingAuthorized,false);
 assert.equal(V101_STATE.deployAuthorized,false);
 assert.equal(V101_STATE.pilotAllowed,false);
});

test('08 read-only pilot rejects any write or recovery capability for either role',async()=>{
 const r=rig();
 for(const [who,path] of [['OWNER','/owner/'],['A','/contributors/']]){
   assert.equal((await r.send(who,path)).status,200);
   for(const flag of ['can_write','can_recover']){
     r.states[who][flag]=true;
     assert.equal((await r.send(who,path)).status,403,who+' '+flag);
     r.states[who][flag]=false;
   }
 }
});
