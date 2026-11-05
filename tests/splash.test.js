const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const script=fs.readFileSync('splash.js','utf8');
const page=fs.readFileSync('index.html','utf8');
const css=fs.readFileSync('splash.css','utf8');

function sandbox({referrer='',healthOk=true}={}) {
  const nodes=new Map();
  const createNode=() => {
    const attrs={},style={},classes=new Set();
    return {
      style:{setProperty(k,v){style[k]=v;},values:style},
      classList:{add(k){classes.add(k);},contains(k){return classes.has(k);}},
      setAttribute(k,v){attrs[k]=String(v);},getAttribute(k){return attrs[k];},
      textContent:'',innerHTML:'',
      remove(){this.removed=true;},
      querySelector(k){
        if(!nodes.has(k))nodes.set(k,createNode());
        return nodes.get(k);
      }
    };
  };
  const body={appended:[],append(node){this.appended.push(node);}};
  const release={textContent:'REMURA · Aggiornamento v1.62 · 03/11/2026 19:20 (Italia, preparazione)'};
  const document={
    referrer,body,readyState:'loading',createElement:createNode,
    getElementById(id){return id==='rm-release'?release:null;},
    addEventListener(event,cb){if(event==='DOMContentLoaded')cb();}
  };
  const requests=[];
  const fetch=(path,opts)=>{
    requests.push({path,opts});
    return Promise.resolve(healthOk ? {
      ok:true,headers:{get:()=> 'application/json'},
      json:async()=>({name:'REMURA Private'})
    } : {ok:false,headers:{get:()=> 'application/json'}});
  };
  vm.runInNewContext(script,{
    document,location:{origin:'https://remura.example',protocol:'https:'},URL,
    window:{matchMedia:()=>({matches:true}),addEventListener:()=>{}},
    fetch,AbortController,setTimeout,clearTimeout,
  },{timeout:1000});
  return {body,nodes,requests};
}
const sleep=(ms)=>new Promise(r=>setTimeout(r,ms));

test('splash attaches only to Home launch, uses local assets, and is offline-capable',()=>{
  assert.match(page,/splash\.css\?v=splash1/);
  assert.match(page,/<body><script src="\.\/splash\.js\?v=splash1"><\/script>/);
  assert.match(script,/splash-mascot\.webp/);
  assert.match(css,/prefers-reduced-motion/);
  assert.match(css,/safe-area-inset-top/);
  const asset=fs.readFileSync('splash-mascot.webp');
  assert.ok(asset.length>3000 && asset.length<15000);
  assert.equal(asset.subarray(0,4).toString(),'RIFF');
  assert.equal(asset.subarray(8,12).toString(),'WEBP');
  const sw=fs.readFileSync('sw.js','utf8');
  for(const path of ['splash.js','splash.css','splash-mascot.webp']) assert.ok(sw.includes(path));
});

test('health check is internal and never calls brokers or refreshes financial data',()=>{
  const endpoints=[...script.matchAll(/fetch\(\s*["'`]([^"'`]+)/g)].map(x=>x[1]);
  assert.deepEqual(endpoints,['./private-api/health']);
  assert.match(script,/credentials:"same-origin"/);
  assert.match(script,/AbortController/);
  assert.match(script,/setTimeout\(close,4500\)/);
});

test('internal Home navigation bypasses splash without GET',()=>{
  const app=sandbox({referrer:'https://remura.example/mercati.html'});
  assert.equal(app.body.appended.length,0);
  assert.equal(app.requests.length,0);
});

test('successful health check moves to 100 percent, attaches remora, then closes',async()=>{
  const app=sandbox();
  assert.equal(app.body.appended.length,1);
  assert.equal(app.requests.length,1);
  assert.equal(app.requests[0].path,'./private-api/health');
  const splash=app.body.appended[0];
  await sleep(300);
  assert.equal(app.nodes.get('[role=progressbar]').getAttribute('aria-valuenow'),'100');
  assert.equal(app.nodes.get('.rm-splash-fish').classList.contains('rm-splash-attached'),true);
  assert.match(app.nodes.get('.rm-splash-state').textContent,/Si parte/);
  assert.equal(splash.classList.contains('rm-splash-exit'),true);
});

test('unavailable backend cannot falsely claim health and does not block Home',async()=>{
  const app=sandbox({healthOk:false});
  await sleep(300);
  assert.equal(app.nodes.get('[role=progressbar]').getAttribute('aria-valuenow'),'100');
  assert.match(app.nodes.get('.rm-splash-state').textContent,/verifica la connessione/);
  assert.equal(app.body.appended[0].classList.contains('rm-splash-exit'),true);
});
