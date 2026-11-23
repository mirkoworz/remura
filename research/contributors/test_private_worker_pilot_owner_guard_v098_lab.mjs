// REMURA Contributors v0.98 LAB — 23/11/2026 Europe/Rome
// New regression tests ONLY, synthetic identity and D1 profile, no external calls.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createPilotOwnerGuardV098,V098_PILOT,privateWorkerPilotV098}
  from './private_worker_pilot_owner_guard_v098_lab.mjs';
import {privateAssetFilesV096} from './private_assets_v096_lab.mjs';

const ORIGIN='https://pilot-v098-fixture.invalid';
const ENV={PRIVATE_WORKER_V078:'OFFLINE_FIXTURE_ONLY',STAGING_ENABLED:'D1_CANDIDATE',
  STAGING_ORIGIN:ORIGIN,ACCESS_AUD:'synthetic-audience'};
const id='a'.repeat(64),tag='b'.repeat(64);
function setup(){
  const users={
    owner:{role:'OWNER',can_read:true,can_write:false,can_recover:true},
    a:{role:'CONTRIBUTOR',can_read:true,can_write:true,can_recover:false},
    b:{role:'CONTRIBUTOR',can_read:true,can_write:true,can_recover:false}
  };
  const metrics={auth:0,profiles:0,reads:0,levels:0,audit:0};
  const authenticate=async(ctx)=>{
    metrics.auth++;
    if(ctx.access.blocked)throw Error('provider_revoked');
    return {subject:id,email_tag:tag};
  };
  const profileRead=async(ctx)=>{
    metrics.profiles++;
    if(ctx.access.dbRevoked)throw Error('d1_revoked');
    return {...users[ctx.access.fixtureUser]};
  };
  const app=createPilotOwnerGuardV098({
    authenticate,profileRead,
    protectedRead:async()=>{metrics.reads++;return new Response('{"data":"READ"}',
      {headers:{'Content-Type':'application/json','Cache-Control':'no-store'}});},
    levelApi:async()=>{metrics.levels++;return new Response('{"data":"LEVEL"}',
      {headers:{'Content-Type':'application/json','Cache-Control':'no-store'}});},
    ownerAudit:async()=>{metrics.audit++;return new Response('{"data":"AUDIT"}',
      {headers:{'Content-Type':'application/json','Cache-Control':'no-store'}});},
    assetFiles:privateAssetFilesV096
  });
  const context=(who)=>({access:{
    fixtureUser:who,aud:ENV.ACCESS_AUD,async getIdentity(){return {synthetic:true}}}});
  const get=(path)=>new Request(ORIGIN+path);
  const post=(path,options={})=>new Request(ORIGIN+path,{method:'POST',
    body:options.body??'{}',headers:{Origin:ORIGIN,'Sec-Fetch-Site':'same-origin',
    'X-Remura-CSRF':'1','Content-Type':'application/json',...(options.headers??{})}});
  return {users,metrics,app,context,get,post};
}
test('01 OWNER with recovery access can load owner page',async()=>{
 const h=setup(),r=await h.app(h.get('/owner/'),ENV,h.context('owner'));
 assert.equal(r.status,200);assert.equal(h.metrics.profiles,1);
});
test('02 OWNER recovery revocation denies previously available owner GET, on fresh lookup',async()=>{
 const h=setup(),ctx=h.context('owner');
 assert.equal((await h.app(h.get('/owner/'),ENV,ctx)).status,200);
 h.users.owner.can_recover=false;
 assert.equal((await h.app(h.get('/owner/'),ENV,ctx)).status,403);
 assert.equal((await h.app(h.get('/owner/levels/'),ENV,ctx)).status,403);
 assert.equal(h.metrics.profiles,3);
});
test('03 OWNER can_read alone cannot access owner script after revocation',async()=>{
 const h=setup();h.users.owner.can_recover=false;
 const r=await h.app(h.get('/owner/levels/owner_level_integrity_ui_v078_lab.mjs'),
   ENV,h.context('owner'));
 assert.equal(r.status,403);assert.match(r.headers.get('Cache-Control'),/no-store/);
});
test('04 revoked OWNER denied generic profile POST, not just /owner routes',async()=>{
 const h=setup();h.users.owner.can_recover=false;
 assert.equal((await h.app(h.post('/api/profile'),ENV,h.context('owner'))).status,403);
 assert.equal(h.metrics.levels,0);
});
test('05 revoked OWNER denied queue, history and review POST before downstream',async()=>{
 const h=setup();h.users.owner.can_recover=false;
 for(const path of ['/owner/queue','/owner/history','/owner/review']){
  assert.equal((await h.app(h.post(path),ENV,h.context('owner'))).status,403,path);
 }
 assert.equal(h.metrics.levels,0);
});
test('06 revoked OWNER denied append-only audit POST before downstream',async()=>{
 const h=setup();h.users.owner.can_recover=false;
 assert.equal((await h.app(h.post('/owner/new-level/attest'),ENV,h.context('owner'))).status,403);
 assert.equal(h.metrics.audit,0);
});
test('07 active OWNER may reach owner queue and audit delegates, not contributor submit',async()=>{
 const h=setup(),ctx=h.context('owner');
 assert.equal((await h.app(h.post('/owner/queue'),ENV,ctx)).status,200);
 assert.equal((await h.app(h.post('/owner/new-level/pending'),ENV,ctx)).status,200);
 assert.equal((await h.app(h.post('/api/submit'),ENV,ctx)).status,403);
 assert.equal(h.metrics.levels,1);assert.equal(h.metrics.audit,1);
});
test('08 contributor can see own protected intake and cannot see OWNER pages',async()=>{
 const h=setup(),ctx=h.context('a');
 assert.equal((await h.app(h.get('/contributors/levels/'),ENV,ctx)).status,200);
 assert.equal((await h.app(h.get('/owner/'),ENV,ctx)).status,403);
});
test('09 contributor cannot reach OWNER queue/review/audit through POST',async()=>{
 const h=setup(),ctx=h.context('a');
 for(const p of ['/owner/queue','/owner/review','/owner/new-level/integrity'])
   assert.equal((await h.app(h.post(p),ENV,ctx)).status,403);
 assert.equal(h.metrics.levels+h.metrics.audit,0);
});
test('10 contributor with read/write can reach delegated intake; no self-approval',async()=>{
 const h=setup(),ctx=h.context('a');
 assert.equal((await h.app(h.post('/api/profile'),ENV,ctx)).status,200);
 assert.equal((await h.app(h.post('/api/submit'),ENV,ctx)).status,200);
 assert.equal((await h.app(h.post('/owner/review'),ENV,ctx)).status,403);
 assert.equal(h.metrics.levels,2);
});
test('11 contributor read-only can view receipts but cannot submit or catalog',async()=>{
 const h=setup();h.users.a.can_write=false;const ctx=h.context('a');
 assert.equal((await h.app(h.post('/api/receipts'),ENV,ctx)).status,200);
 assert.equal((await h.app(h.post('/api/submit'),ENV,ctx)).status,403);
 assert.equal((await h.app(h.post('/api/catalog'),ENV,ctx)).status,403);
});
test('12 D1 profile revoked denies GET and POST even when Access fixture remains',async()=>{
 const h=setup(),ctx=h.context('a');ctx.access.dbRevoked=true;
 assert.equal((await h.app(h.get('/contributors/'),ENV,ctx)).status,403);
 assert.equal((await h.app(h.post('/api/profile'),ENV,ctx)).status,403);
 assert.equal(h.metrics.levels,0);
});
test('13 Access blocked denies POST before a D1 lookup',async()=>{
 const h=setup(),ctx=h.context('a');ctx.access.blocked=true;
 assert.equal((await h.app(h.post('/api/profile'),ENV,ctx)).status,403);
 assert.equal(h.metrics.profiles,0);
});
test('14 forged role header, missing CSRF and cross-origin POST rejected before DB',async()=>{
 const h=setup(),ctx=h.context('a');
 assert.equal((await h.app(h.post('/api/profile',{headers:{'X-Remura-Role':'OWNER'}}),ENV,ctx)).status,403);
 assert.equal((await h.app(h.post('/api/profile',{headers:{'X-Remura-CSRF':'0'}}),ENV,ctx)).status,403);
 assert.equal((await h.app(h.post('/api/profile',{headers:{Origin:'https://else.invalid'}}),ENV,ctx)).status,403);
 assert.equal(h.metrics.profiles,0);
});
test('15 large/malformed body, unknown route and disabled staging always deny',async()=>{
 const h=setup(),ctx=h.context('a');
 assert.equal((await h.app(h.post('/api/submit',{body:'x'.repeat(4097)}),ENV,ctx)).status,403);
 assert.equal((await h.app(h.post('/api/submit',{body:'not json'}),ENV,ctx)).status,403);
 assert.equal((await h.app(h.post('/owner/secrets'),ENV,ctx)).status,403);
 assert.equal((await h.app(h.post('/api/profile'),{...ENV,STAGING_ENABLED:'OFF'},ctx)).status,403);
 assert.equal(h.metrics.levels,0);
});
test('16 v0.98 is an inert extension of genuine v0.96 composition; no runtime activation',()=>{
 assert.equal(typeof privateWorkerPilotV098,'function');
 assert.equal(V098_PILOT.realPilotAllowed,false);
 assert.equal(V098_PILOT.deployAuthorized,false);
 const source=fs.readFileSync(new URL('./private_worker_pilot_owner_guard_v098_lab.mjs',import.meta.url),'utf8');
 assert.ok(source.includes("createPrivateWorkerRouterV096"));
 assert.ok(source.includes("private_levels_composition_v096_lab.mjs"));
 assert.ok(!source.includes('export default'));
 assert.ok(!source.includes('fetch('));
 assert.ok(!source.includes('wrangler '));
});
