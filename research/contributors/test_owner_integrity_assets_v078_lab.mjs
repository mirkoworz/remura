// REMURA Contributors v0.78 LAB — 20 fresh asset integrity and OWNER UI safety checks.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {render,names} from './build_private_assets_v078_lab.mjs';
import {privateAssetFilesV078} from './private_assets_v078_lab.mjs';
import {REMURA_V078_ALLOWED_STATIC} from './private_worker_router_v078_lab.mjs';
const file=n=>readFileSync(new URL('./'+n,import.meta.url),'utf8');
for(const n of names)test('byte-identical v0.78 immutable asset '+n,()=>{
 assert.equal(privateAssetFilesV078[n],file(n));
});
test('16 deterministic manifest includes only 15 vetted source files',()=>{
 assert.equal(names.length,15);
 assert.equal(render(),file('private_assets_v078_lab.mjs'));
 assert.deepEqual([...Object.keys(privateAssetFilesV078)].sort(),[...names].sort());
});
test('17 every updated private HTML page shows v0.78 CET date above main',()=>{
 const pages=names.filter(x=>x.endsWith('.html'));assert.equal(pages.length,4);
 for(const p of pages){
  const s=file(p);
  assert.match(s,/v0\.78 LAB · 21\/11\/2026 16:56 CET/);
  assert.ok(s.indexOf('v0.78 LAB · 21/11/2026 16:56 CET')<s.indexOf('<main'));
 }
});
test('18 OWNER integrity UI is linked only in OWNER page and role whitelist',()=>{
 const owner=file('owner_levels_v078_lab.html');
 assert.match(owner,/id="ownerLevelIntegrityLoad"/);
 assert.match(owner,/id="ownerLevelIntegrityRows"/);
 assert.match(owner,/src="\.\/owner_level_integrity_ui_v078_lab\.mjs"/);
 assert.ok(REMURA_V078_ALLOWED_STATIC.areas.LEVELS.includes('owner_level_integrity_ui_v078_lab.mjs'));
 assert.doesNotMatch(file('contributors_levels_v078_lab.html'),/owner_level_integrity_ui_v078_lab/);
});
test('19 all HTML module/css dependencies are declared in same-area whitelist',()=>{
 for(const p of names.filter(x=>x.endsWith('.html'))){
  const area=p.includes('levels')?'LEVELS':'RECOVERY';
  const contents=file(p);
  for(const m of contents.matchAll(/(?:src|href)="\.\/([a-z0-9_.-]+)"/g)){
   assert.ok(REMURA_V078_ALLOWED_STATIC.areas[area].includes(m[1]),p+' -> '+m[1]);
  }
 }
});
test('20 diagnostic is read-only and no module exports live Worker fetch',async()=>{
 const c=file('owner_level_integrity_ui_v078_lab.mjs');
 assert.match(c,/\/owner\/new-level\/integrity/);
 assert.match(c,/automatic_release!==false/);
 assert.doesNotMatch(c,/(?:\/owner\/new-level\/release|\/owner\/new-level\/reset|\/api\/submit|localStorage|sessionStorage)/);
 const runtime=file('private_levels_composition_v078_lab.mjs');
 assert.doesNotMatch(runtime,/\bnode:/);
 const module=await import('./private_levels_composition_v078_lab.mjs');
 assert.equal('default' in module,false);assert.equal('fetch' in module,false);
});
