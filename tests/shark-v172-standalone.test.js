/* REMURA Shark Cockpit v1.72 — only NEW portable preview packaging gates.
 * No browser fetch, no synthetic COT values and no staging publication.
 */
"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs");
const source=fs.readFileSync("preview/REMURA-Shark-Cockpit-v172-iPhone-STANDALONE-LAB.html","utf8");
const bundled=[...source.matchAll(/<script id="inline-([^"]+)">([\s\S]*?)<\/script>/g)]
  .map(m=>({name:m[1],content:m[2].trim()}));
test("01 self-contained preview clearly identifies v1.72 LAB and actual timestamp at top",()=>{
 assert.ok(source.indexOf("SHARK COCKPIT v1.72 LAB · 23/11/2026 21:25 CET (Europe/Rome)")>0);
 assert.match(source,/<meta name="robots" content="noindex,nofollow,noarchive">/);
 assert.ok(source.indexOf('class="build-stamp"')<source.indexOf('class="site-top"'));
});
test("02 all nine CFTC and UI dependency modules exactly match the v1.72 mainline branch",()=>{
 const names=["shark-cockpit-core.js","shark-movers-core.js","shark-movers-ui.js",
   "shark-evidence-core.js","shark-evidence-ui.js","shark-trends-core.js",
   "shark-trends-ui.js","shark-focus-core.js","shark-focus-ui.js"];
 for(const name of names){
   const item=bundled.find(x=>x.name===name);
   assert.ok(item,name);
   assert.equal(item.content,fs.readFileSync(name,"utf8").trim(),name);
 }
 assert.ok(bundled.find(x=>x.name==="shark-cockpit.js"));
 assert.equal(bundled.length,10);
});
test("03 independent file: no external scripts, credentials or private-api links",()=>{
 assert.equal(source.includes("<script src="),false);
 assert.equal(source.includes("/private-api/"),false);
 assert.equal(source.includes("IDENTITY_HMAC_KEY"),false);
 assert.equal(source.includes("CF_Authorization"),false);
 assert.equal(source.includes("wrangler deploy"),false);
 assert.ok(source.includes("https://raw.githubusercontent.com/mirkoworz/remura/main/data/myfxbook/latest.json"));
});
test("04 CFTC data remain actual public endpoints, N/D when missing and never predicted",()=>{
 assert.ok(source.includes("gpe5-46if"));
 assert.ok(source.includes("72hh-3qpy"));
 assert.ok(source.includes("CFTC non raggiungibile"));
 assert.ok(source.includes("nessuna esposizione stimata o inventata"));
 assert.ok(source.includes("N/D"));
 assert.ok(source.includes("I miei squali"));
});
