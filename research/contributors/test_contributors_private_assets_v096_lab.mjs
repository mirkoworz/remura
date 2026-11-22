// REMURA v0.96 LAB: NEW router asset integration only. No Cloudflare live API.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {privateAssetFilesV078} from "./private_assets_v078_lab.mjs";
import {privateAssetFilesV096} from "./private_assets_v096_lab.mjs";
import {createPrivateWorkerRouterV096,REMURA_V096_ALLOWED_STATIC} from "./private_worker_router_v096_lab.mjs";
import {privateWorkerCandidateV096} from "./private_levels_composition_v096_lab.mjs";

const fx=(role="CONTRIBUTOR")=>createPrivateWorkerRouterV096({
 authenticate:async()=>({subject:"a".repeat(64),email_tag:"b".repeat(64)}),
 profileRead:async()=>({role,can_read:true}),
 protectedRead:async()=>new Response("READ_FIXTURE"),
 levelApi:async()=>new Response("LEVEL_FIXTURE"),
 ownerAudit:async()=>new Response("OWNER_FIXTURE"),
 assetFiles:privateAssetFilesV096
});
const origin="https://private-fixture.invalid";
const env={PRIVATE_WORKER_V078:"OFFLINE_FIXTURE_ONLY",STAGING_ENABLED:"D1_CANDIDATE",
 STAGING_ORIGIN:origin,ACCESS_AUD:"a_fixture"};
const ctx={access:{aud:"a_fixture",getIdentity:()=>{}}};
const get=(path,method="GET")=>new Request(origin+path,{method});
test("v096 candidate asset map changes only contributor page/JS and adds pure preflight",()=>{
 const prev=Object.keys(privateAssetFilesV078),next=Object.keys(privateAssetFilesV096);
 const removed=["contributors_levels_v078_lab.html","contributors_levels_ui_v076_lab.mjs"];
 const additions=["contributors_levels_v096_lab.html","contributors_levels_ui_v096_lab.mjs",
   "contributors_levels_preflight_v096_lab.mjs"];
 assert.equal(next.length,prev.length+1);
 assert.ok(removed.every(k=>!next.includes(k)));
 assert.ok(additions.every(k=>next.includes(k)));
 for(const k of prev.filter(x=>!removed.includes(x)))assert.equal(privateAssetFilesV096[k],privateAssetFilesV078[k]);
});
test("new contributor page and module are reachable only with trusted fixture actor",async()=>{
 const app=fx(),p=await app(get("/contributors/levels/"),env,ctx);
 assert.equal(p.status,200);
 const html=await p.text();
 assert.ok(html.includes("v0.96 LAB"));
 assert.ok(html.includes('src="./contributors_levels_ui_v096_lab.mjs"'));
 assert.equal(p.headers.get("Cache-Control"),"no-store, max-age=0");
 const ui=await app(get("/contributors/levels/contributors_levels_ui_v096_lab.mjs"),env,ctx);
 assert.equal(ui.status,200);
 assert.ok((await ui.text()).includes("inspectLevelV096"));
 const preflight=await app(get("/contributors/levels/contributors_levels_preflight_v096_lab.mjs"),env,ctx);
 assert.equal(preflight.status,200);
 assert.ok((await preflight.text()).includes("CLIENT_REVIEW_ONLY"));
});
test("without explicit staging gate every private page returns deny",async()=>{
 const app=fx();
 assert.equal((await app(get("/contributors/levels/"),{},ctx)).status,403);
 assert.equal((await app(get("/contributors/levels/"),{...env,PRIVATE_WORKER_V078:"PRODUCTION"},ctx)).status,403);
});
test("without signed Access context no contributor page nor script",async()=>{
 const app=fx();
 assert.equal((await app(get("/contributors/levels/"),env,{})).status,403);
 assert.equal((await app(get("/contributors/levels/contributors_levels_preflight_v096_lab.mjs"),env,{})).status,403);
});
test("owner cannot masquerade as a contributor by requesting contributor URL",async()=>{
 const app=fx("OWNER");
 assert.equal((await app(get("/contributors/levels/"),env,ctx)).status,403);
 assert.equal((await app(get("/contributors/levels/contributors_levels_preflight_v096_lab.mjs"),env,ctx)).status,403);
});
test("contributor cannot read owner-only audit JS or private owner route",async()=>{
 const app=fx("CONTRIBUTOR");
 assert.equal((await app(get("/owner/levels/"),env,ctx)).status,403);
 assert.equal((await app(get("/contributors/levels/owner_level_integrity_ui_v078_lab.mjs"),env,ctx)).status,403);
});
test("v096 candidate static list is minimal, no old contributor entry or new API routes",()=>{
 assert.ok(REMURA_V096_ALLOWED_STATIC.pages.includes("/contributors/levels/"));
 assert.ok(REMURA_V096_ALLOWED_STATIC.files.includes("contributors_levels_preflight_v096_lab.mjs"));
 assert.ok(!REMURA_V096_ALLOWED_STATIC.files.includes("contributors_levels_ui_v076_lab.mjs"));
 const r=fs.readFileSync(new URL("./private_worker_router_v096_lab.mjs",import.meta.url),"utf8");
 assert.ok(r.includes("'/api/level-attempt/status'"));
 assert.ok(r.includes("'/api/submit'"));
 assert.ok(!r.includes("export default"));
});
test("composition remains inert without staging or deployment entrypoint",async()=>{
 assert.equal(typeof privateWorkerCandidateV096,"function");
 const res=await privateWorkerCandidateV096(get("/contributors/levels/"),{},ctx);
 assert.equal(res.status,403);
 const c=fs.readFileSync(new URL("./private_levels_composition_v096_lab.mjs",import.meta.url),"utf8");
 assert.ok(!c.includes("export default"));
 assert.ok(c.includes("createDurableLevelApiV076"));
});
