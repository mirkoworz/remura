// REMURA Contributors v0.90 LAB — only NEW central POST gate checks
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createPostGuardedPrivateWorkerV090 as make,V090_CONTRACT} from './private_post_guard_v090_lab.mjs';
import {REMURA_V078_ALLOWED_STATIC as paths} from './private_worker_router_v078_lab.mjs';
const ORIGIN='https://staging.remura.invalid';
const ACTOR={subject:'a'.repeat(64),email_tag:'b'.repeat(64)};
const env=()=>({PRIVATE_WORKER_V078:'OFFLINE_FIXTURE_ONLY',
 STAGING_ENABLED:'D1_CANDIDATE',STAGING_ORIGIN:ORIGIN,ACCESS_AUD:'aud-demo'});
const ctx=()=>({access:{aud:'aud-demo',getIdentity:async()=>({})}});
const c=(over={})=>({role:'CONTRIBUTOR',can_read:true,can_write:true,can_recover:false,...over});
const o=(over={})=>({role:'OWNER',can_read:true,can_write:false,can_recover:true,...over});
const assetFiles=Object.fromEntries([
 ['contributors_recovery_v078_private_lab.html','<!doctype html> contributor recovery'],
 ['contributors_owner_recovery_v078_private_lab.html','<!doctype html> owner recovery'],
 ['contributors_levels_v078_lab.html','<!doctype html> contributor levels'],
 ['owner_levels_v078_lab.html','<!doctype html> owner levels'],
 ...paths.files.map(name=>[name,'/* fixture only */'])
]);
function harness(profile=c(),authActor=ACTOR){
 let calls=0,auth=0;
 const delegate=async()=>{calls++;return new Response('{"data":{}}',{status:200,headers:{'Content-Type':'application/json'}})};
 const router=make({authenticate:async()=>{auth++;return authActor},profileRead:async()=>profile,
  protectedRead:delegate,levelApi:delegate,ownerAudit:delegate,assetFiles});
 return {router,calls:()=>calls,auth:()=>auth};
}
function req(path='/api/submit',{body='{"sample":1}',headers={},method='POST',url}={}){
 const h={'Origin':ORIGIN,'Sec-Fetch-Site':'same-origin','X-Remura-CSRF':'1',
  'Content-Type':'application/json',...headers};
 return new Request(url??ORIGIN+path,{method,headers,...(method==='GET'?{}:{body})});
}
async function denied(h,r,ee=env(),cc=ctx()){
 const v=await h.router(r,ee,cc);
 assert.equal(v.status,403);
 assert.equal(v.headers.get('Cache-Control'),'no-store, max-age=0');
 assert.equal(h.calls(),0);
}
test('01 contributor can submit within server gate',async()=>{
 const h=harness();assert.equal((await h.router(req(),env(),ctx())).status,200);
 assert.equal(h.calls(),1);
});
test('02 contributor can obtain intent',async()=>{
 const h=harness();assert.equal((await h.router(req('/api/intent'),env(),ctx())).status,200);
});
test('03 owner can review',async()=>{
 const h=harness(o());assert.equal((await h.router(req('/owner/review'),env(),ctx())).status,200);
});
test('04 owner can inspect audit',async()=>{
 const h=harness(o());assert.equal((await h.router(req('/owner/new-level/integrity'),env(),ctx())).status,200);
});
test('05 contributor cannot review owner queue',async()=>{
 const h=harness();await denied(h,req('/owner/review'));
});
test('06 contributor cannot use owner audit',async()=>{
 const h=harness();await denied(h,req('/owner/new-level/attest'));
});
test('07 owner cannot post contributor level',async()=>{
 const h=harness(o());await denied(h,req('/api/submit'));
});
test('08 contributor cannot write without permission',async()=>{
 const h=harness(c({can_write:false}));await denied(h,req('/api/submit'));
});
test('09 contributor without write cannot fetch intent',async()=>{
 const h=harness(c({can_write:false}));await denied(h,req('/api/intent'));
});
test('10 owner without recovery cannot review',async()=>{
 const h=harness(o({can_recover:false}));await denied(h,req('/owner/review'));
});
test('11 owner without recovery cannot obtain intent',async()=>{
 const h=harness(o({can_recover:false}));await denied(h,req('/api/intent'));
});
test('12 collaborator falsely claiming recovery is denied',async()=>{
 const h=harness(c({can_recover:true}));await denied(h,req('/api/profile'));
});
test('13 unknown server profile is denied',async()=>{
 const h=harness(null);await denied(h,req('/api/profile'));
});
test('14 wrong origin denied before authentication',async()=>{
 const h=harness();await denied(h,req('/api/submit',{headers:{Origin:'https://phish.invalid'}}));
 assert.equal(h.auth(),0);
});
test('15 cross-site browser fetch rejected',async()=>{
 const h=harness();await denied(h,req('/api/submit',{headers:{'Sec-Fetch-Site':'cross-site'}}));
});
test('16 missing expected CSRF value rejected',async()=>{
 const h=harness();await denied(h,req('/api/submit',{headers:{'X-Remura-CSRF':'0'}}));
});
test('17 plain text content rejected',async()=>{
 const h=harness();await denied(h,req('/api/submit',{headers:{'Content-Type':'text/plain'}}));
});
test('18 encoded body rejected',async()=>{
 const h=harness();await denied(h,req('/api/submit',{headers:{'Content-Encoding':'gzip'}}));
});
test('19 spoofed role header rejected',async()=>{
 const h=harness();await denied(h,req('/api/submit',{headers:{'X-Remura-Role':'OWNER'}}));
});
test('20 spoofed actor header rejected',async()=>{
 const h=harness();await denied(h,req('/api/submit',{headers:{'X-Remura-Subject':'f'.repeat(64)}}));
});
test('21 oversized body rejected before delegate',async()=>{
 const h=harness();await denied(h,req('/api/submit',{body:JSON.stringify({note:'x'.repeat(5000)})}));
});
test('22 mismatched Content-Length rejected',async()=>{
 const h=harness();await denied(h,req('/api/submit',{headers:{'Content-Length':'99'}}));
});
test('23 JSON array rejected',async()=>{
 const h=harness();await denied(h,req('/api/submit',{body:'[]'}));
});
test('24 invalid JSON rejected',async()=>{
 const h=harness();await denied(h,req('/api/submit',{body:'{"broken":'}));
});
test('25 prototype pollution key rejected',async()=>{
 const h=harness();await denied(h,req('/api/submit',{body:'{"__proto__":{}}'}));
});
test('26 query string rejected',async()=>{
 const h=harness();await denied(h,req('/api/submit',{url:ORIGIN+'/api/submit?x=1'}));
});
test('27 unrecognized path rejected',async()=>{
 const h=harness();await denied(h,req('/admin/destroy'));
});
test('28 malformed Access audience denied',async()=>{
 const h=harness();const cc=ctx();cc.access.aud='bad';await denied(h,req(),env(),cc);
});
test('29 invalid actor subject denied',async()=>{
 const h=harness(c(),{subject:'short',email_tag:'b'.repeat(64)});
 await denied(h,req());
});
test('30 valid cloned request still reaches handler',async()=>{
 const h=harness();const response=await h.router(req('/api/submit',{body:'{"field":"value"}'}),env(),ctx());
 assert.equal(response.status,200);assert.equal(h.calls(),1);
});
test('31 contributor can read receipt',async()=>{
 const h=harness();assert.equal((await h.router(req('/api/receipts'),env(),ctx())).status,200);
});
test('32 owner can read own profile',async()=>{
 const h=harness(o());assert.equal((await h.router(req('/api/profile'),env(),ctx())).status,200);
});
test('33 GET pages preserve pinned v0.78 behavior',async()=>{
 const h=harness();const v=await h.router(req('/contributors/',{method:'GET'}),env(),ctx());
 assert.equal(v.status,200);assert.match(await v.text(),/contributor recovery/);
});
test('34 still not a deployed auth boundary',()=>{
 assert.equal(V090_CONTRACT.defaultDeployment,'NO_GO_LAB');
 assert.equal(V090_CONTRACT.ownershipAttestedByWrapper,false);
});
