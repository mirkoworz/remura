// REMURA Contributors v1.02 — only the new Worker entrypoint safety checks.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import worker,{V102_ENTRY} from './staging_readonly_entry_v102_lab.mjs';
const ORIGIN='https://v102-not-authorized.invalid';
test('01 missing Cloudflare authenticated context always denies, no GET delegated',async()=>{
 const req=new Request(ORIGIN+'/contributors/');
 const env={PRIVATE_WORKER_V078:'STAGING_AUTHENTICATED_READONLY',
   CONTRIBUTORS_STAGE_READONLY:'EXPLICIT_STAGING_ONLY',
   STAGING_ENABLED:'D1_CANDIDATE',STAGING_ORIGIN:ORIGIN,
   ACCESS_AUD:'a'.repeat(64),ACCESS_ACCOUNT:'b'.repeat(32),
   IDENTITY_HMAC_KEY:'c'.repeat(64),CONTRIBUTORS_DB:{prepare(){}}
 };
 const r=await worker.fetch(req,env,{});
 assert.equal(r.status,403);assert.match(r.headers.get('cache-control'),/no-store/);
 assert.equal(V102_ENTRY.authorized,false);
 assert.equal(V102_ENTRY.deployed,false);
});
test('02 all writes denied without consulting any D1 binding',async()=>{
 let dbTouches=0;
 const env={PRIVATE_WORKER_V078:'STAGING_AUTHENTICATED_READONLY',
   CONTRIBUTORS_STAGE_READONLY:'EXPLICIT_STAGING_ONLY',
   STAGING_ENABLED:'D1_CANDIDATE',STAGING_ORIGIN:ORIGIN,
   ACCESS_AUD:'a'.repeat(64),ACCESS_ACCOUNT:'b'.repeat(32),
   IDENTITY_HMAC_KEY:'c'.repeat(64),CONTRIBUTORS_DB:{prepare(){dbTouches++;}}
 };
 const ctx={access:{aud:env.ACCESS_AUD,getIdentity:async()=>null}};
 for(const method of ['POST','PUT','DELETE','PATCH']){
  const res=await worker.fetch(new Request(ORIGIN+'/api/submit',{method,body:'{}'}),env,ctx);
  assert.equal(res.status,403,method);
 }
 assert.equal(dbTouches,0);
});
test('03 template has no reachable routes, no assets or real secrets',()=>{
 const t=fs.readFileSync(new URL('./wrangler-v102-STAGING-TEMPLATE.toml',import.meta.url),'utf8');
 for(const value of ['workers_dev = false','preview_urls = false','REPLACE_ONLY_AFTER_SEPARATE_APPROVAL'])
  assert.ok(t.includes(value),value);
 assert.doesNotMatch(t,/^\s*(routes|route)\s*=/m);
 assert.doesNotMatch(t,/^\s*\[assets\]/m);
 assert.doesNotMatch(t,/^\s*IDENTITY_HMAC_KEY\s*=/m);
 assert.equal(V102_ENTRY.providerVerified,false);
});
