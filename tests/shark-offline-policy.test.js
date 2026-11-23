/* REMURA PWA v1.71.1 — only new offline/cache boundary tests.
 * Pure Node vm fixture; no browser, network, credentials or cloud.
 */
"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),vm=require("node:vm");
const script=fs.readFileSync(new URL("../sw.js","file://"+__filename),"utf8");
function fixture({online=false,hasShell=true}={}){
  const handlers={},matched=[],deleted=[],addAll=[];
  const cache={
    addAll:async entries=>{addAll.push([...entries]);},
    match:async(req,opts)=>{
      matched.push({url:req.url,ignoreSearch:opts.ignoreSearch});
      return hasShell?{kind:"OFFLINE_PUBLIC_SHELL"}:null;
    }
  };
  const names=["remura-shell-v85-v1.71-my-sharks-preview",
    "remura-shell-v86-v1.71-safe-offline-lab",
    "unrelated-app-cache","private-contributors-cache"];
  const cacheStorage={
    open:async name=>{assert.equal(name,"remura-shell-v86-v1.71-safe-offline-lab");return cache;},
    keys:async()=>names,
    delete:async name=>{deleted.push(name);return true;}
  };
  let waited=null,answered=null,networkCalls=0,skipped=0,claimed=0;
  const self={
    location:{origin:"https://remura.invalid"},
    registration:{scope:"https://remura.invalid/remura/"},
    addEventListener:(type,callback)=>{handlers[type]=callback;},
    skipWaiting:async()=>{skipped++;},
    clients:{claim:async()=>{claimed++;}}
  };
  const respond=(url,method="GET")=>{
    answered=null;
    handlers.fetch({
      request:{url,method},
      respondWith(p){answered=p;}
    });
    return answered;
  };
  vm.runInNewContext(script,{
    self,caches:cacheStorage,URL,Promise,Set,
    fetch:async()=>{
      networkCalls++;
      if(!online)throw Error("offline");
      return {kind:"NETWORK"};
    },
    Response:{error:()=>({kind:"NETWORK_ERROR"})}
  },{filename:"sw.js"});
  return {
    handlers,respond,matched,deleted,addAll,
    get waited(){return waited;},
    get networkCalls(){return networkCalls;},
    get skipped(){return skipped;},
    get claimed(){return claimed;},
    event:()=>({waitUntil(p){waited=p;}})
  };
}
test("01 private and unlisted endpoints are never intercepted or cached",()=>{
  const h=fixture();
  for(const p of ["/remura/owner/","/remura/owner/levels/",
    "/remura/contributors/","/remura/contributors/levels/",
    "/remura/api/receipts","/remura/private-api/health",
    "/remura/unknown","/remura/shark-cockpit.html/unknown"]){
    assert.equal(h.respond("https://remura.invalid"+p),null,p);
  }
  assert.equal(h.respond("https://outside.invalid/remura/shark-cockpit.html"),null);
  assert.equal(h.respond("https://remura.invalid/remura/shark-cockpit.html","POST"),null);
  assert.equal(h.networkCalls,0);
  assert.equal(h.matched.length,0);
});
test("02 public shell is served from exact REMURA cache only when offline",async()=>{
  const h=fixture();
  const promise=h.respond("https://remura.invalid/remura/shark-cockpit.html?v=171");
  assert.ok(promise);
  assert.equal((await promise).kind,"OFFLINE_PUBLIC_SHELL");
  assert.equal(h.matched.length,1);
  assert.equal(h.matched[0].ignoreSearch,true);
  assert.equal(h.networkCalls,1);
});
test("03 offline missing shell fails, never uses a global cross-app cache",async()=>{
  const h=fixture({hasShell:false});
  const r=await h.respond("https://remura.invalid/remura/index.html");
  assert.equal(r.kind,"NETWORK_ERROR");
  assert.equal(h.matched.length,1);
});
test("04 activation preserves cache namespaces belonging to other apps",async()=>{
  const h=fixture();
  const event=h.event();h.handlers.activate(event);await h.waited;
  assert.deepEqual(h.deleted,["remura-shell-v85-v1.71-my-sharks-preview"]);
  assert.equal(h.claimed,1);
});
test("05 installation caches the existing public files without extra API requests",async()=>{
  const h=fixture();
  const event=h.event();h.handlers.install(event);await h.waited;
  assert.equal(h.addAll.length,1);
  assert.ok(h.addAll[0].includes("./shark-cockpit.html"));
  assert.equal(h.addAll[0].some(x=>x.startsWith("./owner/")||x.startsWith("./api/")),false);
  assert.equal(h.skipped,1);
});
