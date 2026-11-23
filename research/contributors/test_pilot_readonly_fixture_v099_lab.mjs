// REMURA Contributors v0.99 LAB — new multi-principal read-only probe tests only.
// Real v0.98 composed router, synthetic Access/D1 profiles; NO live provider or deploy.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createPilotOwnerGuardV098} from './private_worker_pilot_owner_guard_v098_lab.mjs';
import {privateAssetFilesV096} from './private_assets_v096_lab.mjs';
import {runPilotReadOnlyFixtureV099,v099FixtureCases} from './pilot_readonly_fixture_v099_lab.mjs';
const ORIGIN='https://v099-fixture.invalid';
const env={PRIVATE_WORKER_V078:'OFFLINE_FIXTURE_ONLY',
 STAGING_ENABLED:'D1_CANDIDATE',STAGING_ORIGIN:ORIGIN,ACCESS_AUD:'fixture'};
const H={'Cache-Control':'no-store, max-age=0','Content-Type':'text/html; charset=utf-8'};
function harness(){
 const principals={
  OWNER:{role:'OWNER',can_read:true,can_write:false,can_recover:true},
  A:{role:'CONTRIBUTOR',can_read:true,can_write:true,can_recover:false},
  B:{role:'CONTRIBUTOR',can_read:true,can_write:true,can_recover:false}
 };
 const observed=[];
 const app=createPilotOwnerGuardV098({
  authenticate:async(ctx)=>{
   if(!principals[ctx.access.principal])throw Error('identity_missing');
   const tags={OWNER:['a','d'],A:['b','e'],B:['c','f']}[ctx.access.principal];
   return {subject:tags[0].repeat(64),email_tag:tags[1].repeat(64)};
  },
  profileRead:async(ctx)=>({...principals[ctx.access.principal]}),
  protectedRead:async()=>new Response('{"data":[]}',{headers:{
   'Content-Type':'application/json','Cache-Control':'no-store'}}),
  levelApi:async()=>new Response('{"data":[]}',{headers:{
   'Content-Type':'application/json','Cache-Control':'no-store'}}),
  ownerAudit:async()=>new Response('{"data":[]}',{headers:{
   'Content-Type':'application/json','Cache-Control':'no-store'}}),
  assetFiles:privateAssetFilesV096
 });
 const send=async({fixturePrincipal,method,path})=>{
  observed.push({fixturePrincipal,method,path});
  assert.equal(method,'GET');
  return app(new Request(ORIGIN+path,{method}),env,
   {access:{principal:fixturePrincipal,aud:env.ACCESS_AUD,getIdentity:async()=>null}});
 };
 return {send,principals,observed};
}
test('01 1-owner + 1-contributor complete read-only route matrix',async()=>{
 const h=harness(),r=await runPilotReadOnlyFixtureV099({
  mode:'OFFLINE_FIXTURE_ONLY',send:h.send,contributors:1});
 assert.equal(r.status,'FIXTURE_MATCHES_DESIGN');
 assert.equal(r.matched,14);assert.equal(r.failed,0);
 assert.equal(h.observed.length,14);
 assert.ok(h.observed.every(x=>x.method==='GET'));
});
test('02 1-owner + 2-contributors complete 18 read-only probes',async()=>{
 const h=harness(),r=await runPilotReadOnlyFixtureV099({
  mode:'OFFLINE_FIXTURE_ONLY',send:h.send,contributors:2});
 assert.equal(r.status,'FIXTURE_MATCHES_DESIGN');
 assert.equal(r.matched,18);assert.equal(r.failed,0);
 assert.equal(h.observed.length,18);
});
test('03 fixture success is NOT login, Safari session, revocation or deploy proof',async()=>{
 const r=await runPilotReadOnlyFixtureV099({mode:'OFFLINE_FIXTURE_ONLY',
  send:harness().send});
 for(const k of ['providerVerified','safariVerified','revocationVerified','deploymentAuthorized','pilotAllowed'])
  assert.equal(r[k],false,k);
});
test('04 no implicit network transport, no mode, no selected users means fail closed',async()=>{
 for(const x of [{},{send:harness().send},
  {mode:'OFFLINE_FIXTURE_ONLY'},{mode:'PRODUCTION',send:harness().send}]){
  const r=await runPilotReadOnlyFixtureV099(x);
  assert.equal(r.status,'NOT_RUN_NO_OFFLINE_FIXTURE');
  assert.equal(r.checks,0);
 }
 const r=await runPilotReadOnlyFixtureV099({
  mode:'OFFLINE_FIXTURE_ONLY',send:harness().send,contributors:3});
 assert.equal(r.status,'NOT_RUN_INVALID_PILOT_SCOPE');
});
test('05 unexpected privilege elevation of A to OWNER fails the matrix',async()=>{
 const h=harness();h.principals.A={role:'OWNER',can_read:true,can_write:false,can_recover:true};
 const r=await runPilotReadOnlyFixtureV099({mode:'OFFLINE_FIXTURE_ONLY',send:h.send});
 assert.equal(r.status,'FIXTURE_FAIL_CLOSED');
 assert.ok(r.failed>0);
 assert.equal(r.pilotAllowed,false);
});
test('06 read capability disabled during fixture is detected instead of counted green',async()=>{
 const h=harness();h.principals.B.can_read=false;
 const r=await runPilotReadOnlyFixtureV099({mode:'OFFLINE_FIXTURE_ONLY',send:h.send});
 assert.equal(r.status,'FIXTURE_FAIL_CLOSED');
 assert.ok(r.results.some(x=>x.id==='second-contributor-home'&&x.outcome==='WRONG_HTTP_STATUS'));
});
test('07 unauthorized 200 content is never treated as denied',async()=>{
 const h=harness();
 const send=async x=>x.path==='/owner/'&&x.fixturePrincipal==='A'
  ?new Response('<h1>LEAK</h1>',{status:200,headers:H}):h.send(x);
 const r=await runPilotReadOnlyFixtureV099({mode:'OFFLINE_FIXTURE_ONLY',send});
 assert.equal(r.status,'FIXTURE_FAIL_CLOSED');
 assert.ok(r.results.some(x=>x.id==='contributor-no-owner-home'&&x.outcome==='WRONG_HTTP_STATUS'));
});
test('08 a missing no-store cache policy fails a successful authorized response',async()=>{
 const h=harness();
 const send=async x=>x.fixturePrincipal==='OWNER'&&x.path==='/owner/'
  ?new Response('<h1>OWNER</h1>',{status:200,headers:{'Content-Type':'text/html'}}):h.send(x);
 const r=await runPilotReadOnlyFixtureV099({mode:'OFFLINE_FIXTURE_ONLY',send});
 assert.ok(r.results.some(x=>x.id==='owner-home'&&x.outcome==='CACHE_NOT_BLOCKED'));
 assert.equal(r.pilotAllowed,false);
});
test('09 unexpected JSON/HTML MIME and redirects never count as valid',async()=>{
 const h=harness();
 const send=async x=>x.fixturePrincipal==='A'&&x.path==='/contributors/'
  ?new Response('{}',{status:200,headers:{'Cache-Control':'no-store','Content-Type':'application/json'}}):h.send(x);
 const r=await runPilotReadOnlyFixtureV099({mode:'OFFLINE_FIXTURE_ONLY',send});
 assert.ok(r.results.some(x=>x.id==='contributor-home'&&x.outcome==='MIME_MISMATCH'));
});
test('10 an unavailable transport is recorded once without retries',async()=>{
 const seen=new Set(),h=harness();
 const send=async x=>{
  const key=x.fixturePrincipal+'|'+x.path;
  assert.ok(!seen.has(key));seen.add(key);
  if(x.fixturePrincipal==='B'&&x.path==='/owner/')throw Error('offline_transport_failure');
  return h.send(x);
 };
 const r=await runPilotReadOnlyFixtureV099({mode:'OFFLINE_FIXTURE_ONLY',send});
 assert.equal(r.status,'FIXTURE_FAIL_CLOSED');
 assert.ok(r.results.some(x=>x.id==='second-contributor-no-owner'&&x.outcome==='TRANSPORT_UNAVAILABLE'));
});
test('11 probe is inert and restricted to exact GET routes: no credentials or payloads',()=>{
 const src=fs.readFileSync(new URL('./pilot_readonly_fixture_v099_lab.mjs',import.meta.url),'utf8');
 assert.ok(!src.includes('fetch('));
 assert.ok(!src.includes('XMLHttpRequest'));
 assert.ok(!src.includes('localStorage'));
 assert.ok(!src.includes('request_id'));
 assert.ok(v099FixtureCases(2).every(x=>['A','B','OWNER','ANON'].includes(x.who)));
 assert.ok(v099FixtureCases(2).every(x=>x.path.startsWith('/')&&!x.path.includes('://')));
});
