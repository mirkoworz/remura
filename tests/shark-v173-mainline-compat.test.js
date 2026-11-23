// REMURA v1.73 — new release compatibility checks only; do not mask any inherited CI.
"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs");
const index=fs.readFileSync("index.html","utf8"),cockpit=fs.readFileSync("shark-cockpit.html","utf8");
const nav=fs.readFileSync("nav.js","utf8"),sw=fs.readFileSync("sw.js","utf8");
test("01 home and Cockpit both display the accurate v1.73 update stamp",()=>{
 for(const h of [index,cockpit])assert.ok(h.includes("23/11/2026 22:20 CET (Europe/Rome)"));
 assert.ok(index.includes("Aggiornamento v1.73.1 LAB"));
 assert.ok(cockpit.includes("SHARK COCKPIT v1.73.1 WEB-FIRST CANDIDATE LAB"));
 assert.ok(index.includes('role="note"'));
});
test("02 existing main v1.64 nav and SW are NOT replaced to avoid regressions",()=>{
 assert.ok(nav.includes("Aggiornamento v1.64 · 05/11/2026 18:03 (Italia, preparazione)"));
 assert.ok(sw.includes("remura-shell-v78-v1.64-shark-cinematic"));
 assert.ok(index.includes('src="./nav.js?v=164"'));
 assert.ok(cockpit.includes('src="./nav.js?v=164"'));
});
test("03 homepage offers a real Cockpit link without altering shared menu",()=>{
 assert.ok(index.includes('href="./shark-cockpit.html"'));
 assert.ok(cockpit.includes('href="./mercati.html#institutional-scanner"'));
 for(const p of ["index.html","shark-cockpit.html"])assert.ok(fs.existsSync(p));
});
test("04 CFTC modules, real retail snapshot, iPhone UI load from mainline",()=>{
 for(const p of ["shark-cockpit-core.js","shark-cockpit.js","shark-cockpit.css",
  "shark-movers-core.js","shark-movers-ui.js","shark-focus-core.js","shark-focus-ui.js",
  "shark-evidence-core.js","shark-evidence-ui.js","shark-trends-core.js","shark-trends-ui.js"])
  assert.ok(fs.existsSync(p),p);
 assert.ok(fs.existsSync("data/myfxbook/latest.json"));
 assert.ok(fs.readFileSync("shark-cockpit.js","utf8").includes('fetch("./data/myfxbook/latest.json"'));
 assert.ok(cockpit.includes("Serve internet per i dati"));
});
test("05 no side effects to collector, authentication or PWA registration",()=>{
 assert.ok(index.includes('src="./splash.js?v=164"'));
 assert.ok(!cockpit.includes("wrangler deploy"));
 assert.ok(!cockpit.includes("IDENTITY_HMAC_KEY"));
 assert.equal(fs.readFileSync("sw.js","utf8").includes("remura-shell-v87"),false);
});
