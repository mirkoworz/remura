// REMURA Contributors v0.75 LAB — fresh immutable asset integrity / Worker safety tests.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {privateAssetFilesV075} from './private_assets_v075_lab.mjs';
import {render,names} from './build_private_assets_v075_lab.mjs';
import {REMURA_V075_ALLOWED_STATIC} from './private_worker_router_v075_lab.mjs';
const load=n=>readFileSync(new URL('./'+n,import.meta.url),'utf8');
for(const name of names)test('asset source byte-identical '+name,()=>{
 assert.equal(privateAssetFilesV075[name],load(name));
}); // 13 truly distinct assets, not a test loop over multiple versions.
test('14 manifest builder determinism without mutation',()=>{
 assert.equal(render(),load('private_assets_v075_lab.mjs'));
});
test('15 generated runtime module never imports filesystem or Node crypto',()=>{
 const s=load('private_assets_v075_lab.mjs');assert.doesNotMatch(s,/\b(?:from|import)\s*['"]node:/);
 const c=load('private_levels_composition_v075_lab.mjs');assert.doesNotMatch(c,/\bnode:/);
});
test('16 all pages first visible version and date 21/11/2026',()=>{
 const files=names.filter(n=>n.endsWith('.html'));assert.equal(files.length,4);
 for(const n of files){
  const s=load(n);
  assert.match(s,/REMURA (?:Contributors )?v0\.75 LAB · 21\/11\/2026 15:48 CET/);
  const pos=s.indexOf('v0.75 LAB · 21/11/2026 15:48 CET');
  assert.ok(pos>0 && pos<s.indexOf('<main'));
 }
});
test('17 all HTML JS and CSS references are area-allowlisted',()=>{
 for(const n of names.filter(n=>n.endsWith('.html'))){
  const s=load(n),area=n.includes('levels')?'LEVELS':'RECOVERY';
  const references=[...s.matchAll(/(?:href|src)="\.\/([a-z0-9_.-]+)"/g)].map(m=>m[1]);
  assert.ok(references.length>=2,n);
  for(const ref of references)assert.ok(REMURA_V075_ALLOWED_STATIC.areas[area].includes(ref),n+': '+ref);
 }
});
test('18 relative JS import closure is area-allowlisted',()=>{
 for(const area of ['RECOVERY','LEVELS']){
  for(const n of REMURA_V075_ALLOWED_STATIC.areas[area].filter(n=>n.endsWith('.mjs'))){
   for(const m of load(n).matchAll(/\bfrom\s*['"]\.\/([a-z0-9_.-]+)['"]/g)){
    assert.ok(REMURA_V075_ALLOWED_STATIC.areas[area].includes(m[1]),area+': '+n+' -> '+m[1]);
   }
  }
 }
});
test('19 sidebar exits lock immediately and cannot claim provider revoked',()=>{
 const s=load('contributors_levels_ui_v075_lab.mjs');
 assert.match(s,/closed=true;reset\(\);states\(\)/);
 assert.match(s,/createExitCoordinatorV072/);
 assert.match(s,/non è attestata/);
 for(const n of ['contributors_levels_v075_lab.html','owner_levels_v075_lab.html']){
  assert.match(load(n),/id="leaveLevels"/);
 }
});
test('20 private asset manifest whitelist matches embedded file keys exactly',()=>{
 const expected=[...REMURA_V075_ALLOWED_STATIC.files,
  'contributors_recovery_v075_private_lab.html','contributors_owner_recovery_v075_private_lab.html','contributors_levels_v075_lab.html','owner_levels_v075_lab.html'];
 assert.deepEqual(Object.keys(privateAssetFilesV075).sort(),[...expected].sort());
 assert.equal(new Set(expected).size,expected.length);
});
