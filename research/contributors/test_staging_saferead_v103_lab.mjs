// REMURA Contributors v1.03 LAB · only new UX/security boundary tests.
// Synthetic delegate; real Access and DB read remain tested separately by v1.01.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createStagingSafeReadV103,V103_READONLY} from './private_worker_staging_saferead_v103_lab.mjs';
const BASE='https://v103-fixture.invalid';
function harness(){
 const calls={reads:0};
 let allow=true;
 const guard=async()=>{calls.reads++;return new Response(allow?'EXISTING_AUTHENTICATED_ASSET':'DENIED',{
  status:allow?200:403,headers:{'Cache-Control':'no-store',
   'Content-Type':allow?'text/html; charset=utf-8':'application/json',
   'X-Content-Type-Options':'nosniff'}
 });};
 const app=createStagingSafeReadV103({guardedGet:guard});
 return {calls,app,setAllowed:v=>{allow=v;},send:(path,opts={})=>app(new Request(BASE+path,opts),{},{} )};
}
test('01 four private pages are explicitly read-only, stamped and accessible without forms/scripts',async()=>{
 const h=harness();
 for(const p of ['/owner/','/owner/levels/','/contributors/','/contributors/levels/']){
  const res=await h.send(p);const html=await res.text();
  assert.equal(res.status,200,p);
  assert.ok(html.includes('REMURA Contributors v1.03 LAB · 23/11/2026 23:05 CET (Europe/Rome)'),p);
  assert.match(html,/<meta name="robots" content="noindex,nofollow,noarchive">/);
  assert.doesNotMatch(html,/<(form|script|button|input)\b/i);
  assert.match(html,/SOLA LETTURA/);
  assert.match(res.headers.get('cache-control'),/no-store/);
  assert.equal(res.headers.get('x-content-type-options'),'nosniff');
 }
 assert.equal(h.calls.reads,4);
});
test('02 denied Access/D1 result is never replaced with public HTML',async()=>{
 const h=harness();h.setAllowed(false);
 const result=await h.send('/contributors/levels/');
 assert.equal(result.status,403);
 assert.equal(await result.text(),'DENIED');
 assert.equal(h.calls.reads,1);
});
test('03 all JS requests are denied before even delegating Access/D1 lookups',async()=>{
 const h=harness();
 for(const p of ['/contributors/levels/contributors_levels_ui_v096_lab.mjs',
   '/owner/levels/owner_level_audit_ui_v077_lab.mjs',
   '/owner/levels/app.js']){
  const result=await h.send(p);
  assert.equal(result.status,403,p);
 }
 assert.equal(h.calls.reads,0);
});
test('04 CSS and unknown GET delegated to authenticated existing router',async()=>{
 const h=harness();
 const css=await h.send('/contributors/levels/contributors_private_levels_v076_lab.css');
 assert.equal(css.status,200);
 assert.equal(await css.text(),'EXISTING_AUTHENTICATED_ASSET');
 assert.equal(h.calls.reads,1);
});
test('05 non-GET never invokes delegate and remains denied',async()=>{
 const h=harness();
 for(const method of ['POST','PUT','PATCH','DELETE','OPTIONS']){
  const res=await h.send('/api/submit',{method,...(['POST','PUT','PATCH'].includes(method)?{body:'{}'}:{})});
  assert.equal(res.status,403,method);
 }
 assert.equal(h.calls.reads,0);
});
test('06 actual v1.02 Worker entrypoint is wired to v1.03 presentation, never bypasses it',()=>{
 const src=fs.readFileSync(new URL('./staging_readonly_entry_v102_lab.mjs',import.meta.url),'utf8');
 assert.ok(src.includes("import {privateStagingSafeReadV103}"));
 assert.ok(src.includes('return await privateStagingSafeReadV103(req,env,ctx)'));
 assert.ok(!src.includes('return await privateReadOnlyStagingV101(req,env,ctx)'));
 assert.equal(V103_READONLY.extraD1Reads,0);
 assert.equal(V103_READONLY.realAccessTested,false);
 assert.equal(V103_READONLY.deployAuthorized,false);
});
