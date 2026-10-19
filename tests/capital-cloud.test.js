const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");

test("Capital Firebase stays disabled until owner configures project",async()=>{
 const js=fs.readFileSync("capital-cloud.js","utf8");
 const win={REMURA_FIREBASE_CONFIG:null};
 vm.runInNewContext(js,{window:win});
 const api=win.REMURA_CAPITAL_CLOUD;
 assert.ok(api);
 assert.equal(api.enabled,false);
 assert.equal(await api.isSignedIn(),false);
 await assert.rejects(api.signIn(),/Firebase non è ancora configurato/);
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
 assert.match(config,/REMURA_FIREBASE_CONFIG = null/);
 for(const secret of ["CAPITAL_API_KEY","CAPITAL_API_PASSWORD",
                       "REMURA_FIREBASE_SERVICE_ACCOUNT","GITHUB_TOKEN"])
  for(const file of [js,ui,config])
   assert.ok(!file.includes(secret),"No private broker or service credentials allowed in browser");
});
