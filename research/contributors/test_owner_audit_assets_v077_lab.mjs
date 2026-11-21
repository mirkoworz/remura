// REMURA Contributors v0.77 LAB — 18 NEW private asset + OWNER UI checks.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {render,names} from './build_private_assets_v077_lab.mjs';
import {privateAssetFilesV077} from './private_assets_v077_lab.mjs';
import {REMURA_V077_ALLOWED_STATIC} from './private_worker_router_v077_lab.mjs';
const read=n=>readFileSync(new URL('./'+n,import.meta.url),'utf8');
for(const name of names)test('exact immutable v0.77 asset '+name,()=>{
 assert.equal(privateAssetFilesV077[name],read(name));
 if(name.endsWith('.html')){
  const s=read(name);
  assert.match(s,/v0\.77 LAB · 21\/11\/2026 16:44 CET/);
  assert.ok(s.indexOf('v0.77 LAB · 21/11/2026 16:44 CET')<s.indexOf('<main'));
 }
});
test('15 deterministic 14-file manifest exactly matches source bundle',()=>{
 assert.equal(names.length,14);
 assert.equal(render(),read('private_assets_v077_lab.mjs'));
 const expected=[...REMURA_V077_ALLOWED_STATIC.files,...names.filter(x=>x.endsWith('.html'))].sort();
 assert.deepEqual(expected,[...names].sort());
});
test('16 owner audit UI is a unique owner-only level asset',()=>{
 assert.ok(REMURA_V077_ALLOWED_STATIC.areas.LEVELS.includes('owner_level_audit_ui_v077_lab.mjs'));
 const owner=read('owner_levels_v077_lab.html');
 assert.match(owner,/src="\.\/owner_level_audit_ui_v077_lab\.mjs"/);
 assert.doesNotMatch(read('contributors_levels_v077_lab.html'),/owner_level_audit_ui_v077_lab/);
});
test('17 new owner controls never contain automatic release, retry or delete flows',()=>{
 const owner=read('owner_levels_v077_lab.html'),script=read('owner_level_audit_ui_v077_lab.mjs');
 for(const id of ['ownerLevelLoad','ownerLevelAuditLoad','ownerLevelAttest','ownerLevelPending','ownerLevelAuditHistory'])
  assert.match(owner,new RegExp('id="'+id+'"'));
 assert.match(script,/locked=true/);
 assert.match(script,/owner\/new-level\/audit-intent/);
 assert.match(script,/owner\/new-level\/attest/);
 assert.doesNotMatch(script,/(?:\/api\/level-attempt\/reset|\/owner\/new-level\/release|localStorage|sessionStorage|indexedDB)/);
});
test('18 Worker composition is node:fs free and import closure valid',()=>{
 const s=read('private_levels_composition_v077_lab.mjs');
 assert.doesNotMatch(s,/\bnode:/);
 assert.doesNotMatch(s,/export default/);
 for(const name of names.filter(x=>x.endsWith('.html'))){
  const html=read(name),area=name.includes('levels')?'LEVELS':'RECOVERY';
  for(const match of html.matchAll(/(?:src|href)="\.\/([a-z0-9_.-]+)"/g)){
   assert.ok(REMURA_V077_ALLOWED_STATIC.areas[area].includes(match[1]),name+' links '+match[1]);
  }
 }
});
