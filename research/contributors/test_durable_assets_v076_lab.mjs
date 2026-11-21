// REMURA Contributors v0.76 LAB — 14 NEW exact asset and status UX checks.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {render,names} from './build_private_assets_v076_lab.mjs';
import {privateAssetFilesV076} from './private_assets_v076_lab.mjs';
import {REMURA_V076_ALLOWED_STATIC} from './private_worker_router_v076_lab.mjs';
const file=n=>readFileSync(new URL('./'+n,import.meta.url),'utf8');
for(const name of names)test('v0.76 original asset bytes match '+name,()=>{
 assert.equal(privateAssetFilesV076[name],file(name));
 if(name.endsWith('.html')){const s=file(name);assert.match(s,/v0\.76 LAB · 21\/11\/2026 15:57 CET/);assert.ok(s.indexOf('v0.76 LAB · 21/11/2026 15:57 CET')<s.indexOf('<main'));}
 if(name==='contributors_levels_ui_v076_lab.mjs'){
  const s=file(name);assert.match(s,/client\.read\('\/api\/level-attempt\/status',\{\}\)/);assert.match(s,/serverBlocked=true;states\(\)/);assert.match(s,/serverBlocked\|\|/);
 }
 if(name==='contributors_candidate_client_v076_lab.mjs'){
  const s=file(name);assert.match(s,/\/api\/level-attempt\/status/);assert.doesNotMatch(s,/\/api\/level-attempt\/retry/);
 }
});
test('14 v0.76 deterministic manifest, import closure, and no Worker Node fs',()=>{
 assert.equal(render(),file('private_assets_v076_lab.mjs'));
 assert.equal(names.length,13);
 const actual=[...REMURA_V076_ALLOWED_STATIC.files,...names.filter(n=>n.endsWith('.html'))];
 assert.deepEqual([...new Set(actual)].sort(),[...names].sort());
 for(const area of ['RECOVERY','LEVELS'])for(const name of REMURA_V076_ALLOWED_STATIC.areas[area].filter(n=>n.endsWith('.mjs'))){
  const js=file(name);
  for(const m of js.matchAll(/\bfrom\s*['"]\.\/([a-z0-9_.-]+)['"]/g))assert.ok(REMURA_V076_ALLOWED_STATIC.areas[area].includes(m[1]),name+' -> '+m[1]);
 }
 const runtime=file('private_levels_composition_v076_lab.mjs');
 assert.doesNotMatch(runtime,/\bnode:/);
 assert.equal('default' in REMURA_V076_ALLOWED_STATIC,false);
});
