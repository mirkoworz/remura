import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';import {planRelease,validateInventory} from './release-plan.mjs';
const m=JSON.parse(readFileSync(new URL('./v1831-inventory.json',import.meta.url),'utf8'));
const copy=()=>structuredClone(m);
const next=(path)=>{const x=copy();x.version='1.83.2';const f=x.files.find(f=>f.path===path);f.gitBlob='f'.repeat(40);return x;};
assert.equal(validateInventory(m).size,82);assert.equal(planRelease(m,copy()).channel,'no-change');
for(const path of ['nav.css','collaboratori.css','index.html']){const x=planRelease(m,next(path));assert.equal(x.channel,'ui-only');assert.equal(x.publicArchivesChanged,false);assert.equal(x.activationAuthorized,false);}
for(const path of ['data/cot-history-public.json','data/myfxbook-history.json','data/myfxbook-latest.json'])assert.equal(planRelease(m,next(path)).channel,'public-data-only');
for(const path of ['sw.js','nav.js','preview-network-guard.js','capital-cloud-config.js','impostazioni.js'])assert.equal(planRelease(m,next(path)).channel,'manual-review');
const mixed=next('nav.css');mixed.files.find(f=>f.path==='data/myfxbook-latest.json').gitBlob='e'.repeat(40);assert.equal(planRelease(m,mixed).channel,'manual-review');
const added=next('nav.css');added.files.push({path:'new.html',bytes:20,gitBlob:'a'.repeat(40)});assert.equal(planRelease(m,added).channel,'manual-review');
const removed=next('nav.css');removed.files=removed.files.filter(f=>f.path!=='icon.svg');assert.equal(planRelease(m,removed).channel,'manual-review');
const old=next('nav.css');old.version='1.82.0';assert.equal(planRelease(m,old).needsVersionIncrease,true);
for(const path of ['../private/x','/absolute','data//x']){const bad=copy();bad.files.push({path,bytes:1,gitBlob:'a'.repeat(40)});assert.throws(()=>validateInventory(bad));}
const duplicate=copy();duplicate.files.push(duplicate.files[0]);assert.throws(()=>validateInventory(duplicate));
const missing=copy();missing.files=missing.files.filter(f=>f.path!=='index.html');assert.throws(()=>validateInventory(missing));
const badChannel=copy();badChannel.channel='production';assert.throws(()=>validateInventory(badChannel));
console.log('release planning: 23 scenarios passed');
