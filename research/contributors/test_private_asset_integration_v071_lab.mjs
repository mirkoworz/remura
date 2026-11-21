// REMURA Contributors v0.71 LAB — new asset-level tests using actual versioned UI source bytes.
// Does not call Cloudflare, does not rerun old v0.70 browser tests.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createPrivateWorkerRouterV071,REMURA_V071_ALLOWED_STATIC} from './private_worker_router_v071_lab.mjs';
const file=filename=>readFileSync(new URL('./'+filename,import.meta.url),'utf8');
const assets=Object.fromEntries([...['contributors_recovery_v071_private_lab.html','contributors_owner_recovery_v071_private_lab.html'],...REMURA_V071_ALLOWED_STATIC.files].map(name=>[name,file(name)]));
const origin='https://members.remura.example',aud='a'.repeat(64), tag='b'.repeat(64);
const env={PRIVATE_WORKER_V071:'OFFLINE_FIXTURE_ONLY',STAGING_ENABLED:'D1_CANDIDATE',STAGING_ORIGIN:origin,ACCESS_AUD:aud};
const ctx={access:{aud,async getIdentity(){return {user_uuid:'fixture-only'}}}};
let role='CONTRIBUTOR';
const gate=createPrivateWorkerRouterV071({authenticate:async()=>({subject:tag,email_tag:tag}),profileRead:async()=>({role,can_read:true}),protectedRead:async()=>new Response('{"data":{}}',{headers:{'Content-Type':'application/json','Cache-Control':'no-store'}}),assetFiles:assets});
const get=path=>gate(new Request(origin+path),env,ctx);
test('01 REAL contributor HTML is served as UTF-8 and exact bytes',async()=>{role='CONTRIBUTOR';const r=await get('/contributors/');assert.equal(r.status,200);assert.equal(await r.text(),assets['contributors_recovery_v071_private_lab.html']);assert.match(r.headers.get('Content-Type'),/text\/html/);});
test('02 REAL owner HTML served only by server OWNER',async()=>{role='OWNER';const r=await get('/owner/');assert.equal(r.status,200);assert.equal(await r.text(),assets['contributors_owner_recovery_v071_private_lab.html']);});
test('03 no browser-controlled OWNER attribute grants access',async()=>{role='CONTRIBUTOR';assert.equal((await get('/owner/')).status,403);});
test('04 every allowed friend asset resolves with original bytes',async()=>{role='CONTRIBUTOR';for(const name of REMURA_V071_ALLOWED_STATIC.files){const r=await get('/contributors/'+name);assert.equal(r.status,200,name);assert.equal(await r.text(),assets[name]);}});
test('05 every allowed owner asset resolves with original bytes',async()=>{role='OWNER';for(const name of REMURA_V071_ALLOWED_STATIC.files){const r=await get('/owner/'+name);assert.equal(r.status,200,name);assert.equal(await r.text(),assets[name]);}});
test('06 pages use v0.71 topmost version and time',()=>{for(const name of ['contributors_recovery_v071_private_lab.html','contributors_owner_recovery_v071_private_lab.html']){const s=assets[name];assert.match(s,/<div class="version">REMURA Contributors v0\.71 LAB · 21\/11\/2026 12:42 CET/);assert.ok(s.indexOf('<div class="version">')<s.indexOf('<div class="shell">'));}});
test('07 both pages retain strict same-origin CSP',()=>{for(const name of ['contributors_recovery_v071_private_lab.html','contributors_owner_recovery_v071_private_lab.html']){const s=assets[name];assert.match(s,/connect-src 'self'/);assert.match(s,/script-src 'self'/);assert.doesNotMatch(s,/script-src 'unsafe-inline'/);}});
test('08 HTML module+stylesheet links are in the allowlist',()=>{for(const n of ['contributors_recovery_v071_private_lab.html','contributors_owner_recovery_v071_private_lab.html']){const s=assets[n];for(const m of s.matchAll(/(?:src|href)="\.\/([a-z0-9_.-]+)"/g))assert.ok(REMURA_V071_ALLOWED_STATIC.files.includes(m[1]),m[1]);}});
test('09 JS relative import dependencies close over allowlist',()=>{for(const n of REMURA_V071_ALLOWED_STATIC.files.filter(x=>x.endsWith('.mjs'))){for(const m of assets[n].matchAll(/\bfrom\s+['"]\.\/([a-z0-9_.-]+)['"]/g))assert.ok(REMURA_V071_ALLOWED_STATIC.files.includes(m[1]),`${n}: ${m[1]}`);}});
test('10 no external scripts or CSS are present in either page',()=>{for(const name of ['contributors_recovery_v071_private_lab.html','contributors_owner_recovery_v071_private_lab.html'])assert.doesNotMatch(assets[name],/(?:src|href)="https?:\/\//);});
test('11 no dynamic API mutation imports are directly referenced',()=>{for(const n of ['contributors_recovery_v071_private_lab.html','contributors_owner_recovery_v071_private_lab.html'])assert.doesNotMatch(assets[n],/\/(?:api\/amendment\/submit|owner\/amendment\/review)/);});
test('12 no-store, no-CORS response headers for actual modules',async()=>{role='CONTRIBUTOR';const r=await get('/contributors/recovery_portal_v070_lab.mjs');assert.equal(r.status,200);assert.match(r.headers.get('Cache-Control'),/no-store/);assert.equal(r.headers.get('Access-Control-Allow-Origin'),null);});
