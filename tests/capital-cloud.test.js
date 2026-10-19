const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");

test("REMURA owner Firebase Web config matches the expected project",()=>{
 const win={};
 vm.runInNewContext(fs.readFileSync("capital-cloud-config.js","utf8"),{window:win});
 const cfg=win.REMURA_FIREBASE_CONFIG;
 assert.equal(cfg.projectId,"remura-a9176");
 assert.equal(cfg.authDomain,"remura-a9176.firebaseapp.com");
 assert.ok(cfg.apiKey.startsWith("AIza"));
 assert.ok(/^1:[0-9]+:web:[0-9a-f]+$/.test(cfg.appId));
 assert.equal(Object.hasOwn(cfg,"private_key"),false);
 assert.equal(Object.hasOwn(cfg,"client_email"),false);
});
test("Capital Firebase frontend recognizes configured project",()=>{
 const js=fs.readFileSync("capital-cloud.js","utf8");
 const win={};
 vm.runInNewContext(fs.readFileSync("capital-cloud-config.js","utf8"),{window:win});
 vm.runInNewContext(js,{window:win});
 assert.ok(win.REMURA_CAPITAL_CLOUD);
 assert.equal(win.REMURA_CAPITAL_CLOUD.enabled,true);
});

test("Public REMURA uses authenticated Firestore only, with local fallback",()=>{
 const js=fs.readFileSync("capital-cloud.js","utf8");
 const ui=fs.readFileSync("sources.js","utf8");
 const html=fs.readFileSync("asset.html","utf8");
 const config=fs.readFileSync("capital-cloud-config.js","utf8");
 const sw=fs.readFileSync("sw.js","utf8");
 assert.match(js,/getDocFromServer/);
 assert.match(js,/auth\.currentUser/);
 assert.match(js,/signInWithPopup/);
 assert.match(js,/remuraPrivate/);
 assert.match(ui,/await cloud\.latest\(\)/);
 assert.match(ui,/await cloud\.history\(symbol\)/);
 assert.match(ui,/importedLatest\|\|savedLatest\(\)/);
 assert.match(html,/capital-cloud-config\.js\?v=1/);
 assert.match(html,/capital-cloud\.js\?v=1/);
 assert.match(sw,/capital-cloud-config\.js/);
 assert.ok(config.includes("window.REMURA_FIREBASE_CONFIG = {"));
 for(const secret of ["CAPITAL_API_KEY","CAPITAL_API_PASSWORD",
                       "REMURA_FIREBASE_SERVICE_ACCOUNT","GITHUB_TOKEN"])
  for(const file of [js,ui,config])
   assert.ok(!file.includes(secret),"No private broker or service credentials allowed in browser");
});
