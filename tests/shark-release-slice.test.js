/* REMURA v1.72 MAINLINE SLICE — new integration-only gates.
 * Prior LAB unit suites remain attested; avoid retesting untouched COT maths.
 */
"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs");
const html=fs.readFileSync("shark-cockpit.html","utf8");
const nav=fs.readFileSync("nav.js","utf8");
const sw=fs.readFileSync("sw.js","utf8");
const scriptPaths=["shark-cockpit-core.js","shark-movers-core.js","shark-movers-ui.js",
"shark-evidence-core.js","shark-evidence-ui.js","shark-trends-core.js",
"shark-trends-ui.js","shark-focus-core.js","shark-focus-ui.js","shark-cockpit.js"];
test("01 new page and only new page has current v1.72 candidate stamp at its top",()=>{
 assert.match(html,/SHARK COCKPIT v1\.72 RELEASE CANDIDATE LAB · 23\/11\/2026 21:17 CET \(Europe\/Rome\)/);
 assert.ok(html.indexOf('class="build-stamp"')<html.indexOf('class="site-top"'));
 assert.match(nav,/Aggiornamento v1\.72 LAB · 23\/11\/2026 21:17 CET/);
});
test("02 every local script exists and dependency order is complete",()=>{
 for(const p of scriptPaths)assert.equal(fs.existsSync(p),true,p);
 let prev=-1;for(const p of scriptPaths){const at=html.indexOf('src="./'+p+'?v=');assert.ok(at>prev,p);prev=at}
 assert.ok(html.indexOf('src="./nav.js?v=172')>prev);
 assert.equal(fs.existsSync("shark-cockpit.css"),true);
});
test("03 mainline menu genuinely links back to CFTC dashboard",()=>{
 assert.ok(nav.includes('href="./shark-cockpit.html" data-main="cockpit"'));
 assert.ok(nav.includes('isCockpit=page==="shark-cockpit.html"'));
 assert.ok(nav.includes('isHome||isCockpit||isScanner'));
 assert.ok(html.includes('href="./mercati.html#institutional-scanner"'));
});
test("04 retail read uses existing PUBLIC Myfxbook snapshot and no private endpoint",()=>{
 const app=fs.readFileSync("shark-cockpit.js","utf8");
 assert.ok(app.includes('fetch("./data/myfxbook/latest.json"'));
 assert.ok(fs.existsSync("data/myfxbook/latest.json"));
 assert.ok(!app.includes("/private-api/"));
});
test("05 new PWA shell caches all new public modules only and not APIs",()=>{
 const prefix=sw.match(/const CACHE="([^"]+)"/);
 assert.equal(prefix?.[1],"remura-shell-v87-v1.72-mainline-slice-lab");
 for(const p of scriptPaths)assert.ok(sw.includes('"./'+p+'"'),p);
 assert.ok(sw.includes('"./shark-cockpit.html"'));
 assert.ok(!sw.includes('"./private-api/'));
 assert.ok(!sw.includes('"./api/'));
 assert.ok(sw.includes("PUBLIC_SHELL_PATHS.has(url.pathname)"));
 assert.ok(sw.includes('name.startsWith("remura-shell-")'));
});
test("06 no production switch, external SDK, Cloudflare mutation or COT guessing added",()=>{
 const app=fs.readFileSync("shark-cockpit.js","utf8");
 assert.ok(app.includes('cache:"no-store"'));
 assert.ok(app.includes('REMURA_SHARK_CORE'));
 assert.ok(!app.includes("wrangler deploy"));
 assert.ok(!app.includes("Cloudflare D1"));
 assert.ok(!app.includes("ORDER_EXECUTE"));
});
