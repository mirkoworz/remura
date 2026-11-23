// REMURA Contributors v1.00 — four NEW offline profile-integrity regressions.
// No Cloudflare sessions, user identities, network, writes or old v0.99 suite rerun.
import test from 'node:test';
import assert from 'node:assert/strict';
import {createPilotProfileIntegrityV100,V100_PILOT} from './private_worker_pilot_profile_integrity_v100_lab.mjs';
import {privateAssetFilesV096} from './private_assets_v096_lab.mjs';
const ORIGIN='https://v100-profile-fixture.invalid';
const env={PRIVATE_WORKER_V078:'OFFLINE_FIXTURE_ONLY',
  STAGING_ENABLED:'D1_CANDIDATE',STAGING_ORIGIN:ORIGIN,ACCESS_AUD:'fixture'};
function harness(){
  const profiles={
    OWNER:{role:'OWNER',can_read:true,can_write:false,can_recover:true},
    A:{role:'CONTRIBUTOR',can_read:true,can_write:true,can_recover:false}
  };
  const calls={profiles:0,delegates:0};
  const reply=async()=>{calls.delegates++;return new Response('{}',{headers:{
    'Content-Type':'application/json','Cache-Control':'no-store'}});};
  const app=createPilotProfileIntegrityV100({
    authenticate:async(ctx)=>({subject:(ctx.access.principal==='OWNER'?'a':'b').repeat(64),
      email_tag:(ctx.access.principal==='OWNER'?'c':'d').repeat(64)}),
    profileRead:async(ctx)=>{calls.profiles++;return profiles[ctx.access.principal];},
    protectedRead:reply,levelApi:reply,ownerAudit:reply,
    assetFiles:privateAssetFilesV096
  });
  const send=(principal,path,options={})=>app(
    new Request(ORIGIN+path,options),env,
    {access:{principal,aud:env.ACCESS_AUD,getIdentity:async()=>null}}
  );
  return {profiles,calls,send};
}
test('v100-01 valid contributor and owner still receive only their own private HTML',async()=>{
  const h=harness();
  assert.equal((await h.send('A','/contributors/')).status,200);
  assert.equal((await h.send('OWNER','/owner/')).status,200);
  assert.equal((await h.send('A','/owner/')).status,403);
  assert.equal(h.calls.profiles,3);
});
test('v100-02 contradictory CONTRIBUTOR can_recover=true is denied on GET',async()=>{
  const h=harness();h.profiles.A.can_recover=true;
  assert.equal((await h.send('A','/contributors/')).status,403);
  assert.equal((await h.send('A','/contributors/levels/')).status,403);
  assert.equal(h.calls.profiles,2);
});
test('v100-03 nonboolean can_write and missing recovery capability deny static assets',async()=>{
  const h=harness();h.profiles.A.can_write='true';
  assert.equal((await h.send('A','/contributors/')).status,403);
  h.profiles.A.can_write=true;delete h.profiles.A.can_recover;
  assert.equal((await h.send('A','/contributors/')).status,403);
  assert.equal(h.calls.profiles,2);
});
test('v100-04 contradictory profile rejects POST before invoking any downstream handler',async()=>{
  const h=harness();h.profiles.A.can_recover=true;
  const response=await h.send('A','/api/profile',{
    method:'POST',headers:{
      Origin:ORIGIN,'Sec-Fetch-Site':'same-origin',
      'X-Remura-CSRF':'1','Content-Type':'application/json'
    },body:'{}'
  });
  assert.equal(response.status,403);
  assert.equal(h.calls.profiles,1);
  assert.equal(h.calls.delegates,0);
  assert.equal(V100_PILOT.realPilotAllowed,false);
  assert.equal(V100_PILOT.additionalD1ProfileReads,0);
});
