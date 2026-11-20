// REMURA Contributors v0.26 LAB — 16/11/2026 07:22 CET
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {webcrypto} from "node:crypto";
class El{
 constructor(){this.listeners={};this.children=[];this.value="";this.hidden=false;this.disabled=false;this.textContent="";}
 addEventListener(n,f){this.listeners[n]=f;}
 replaceChildren(...x){this.children=x;this.value="";}
 append(...x){this.children.push(...x);}
 reset(){}
 click(){this.listeners.click?.({preventDefault(){}});}
}
const html=readFileSync(new URL("./contributors_candidate.html",import.meta.url),"utf8");
const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(x=>x[1]);
const els=Object.fromEntries(ids.map(x=>[x,new El()]));
globalThis.document={getElementById:id=>els[id],createElement:()=>new El()};
const lifecycle={};globalThis.addEventListener=(n,f)=>{lifecycle[n]=f;};
globalThis.confirm=()=>true;
if(!globalThis.crypto)globalThis.crypto=webcrypto;
let calls=[],role="CONTRIBUTOR",fail=false,delayed=null,delayResolve;
const res=d=>new Response(JSON.stringify({data:d}),{status:200,headers:{"Content-Type":"application/json"}});
globalThis.fetch=async(path,o)=>{
 const b=JSON.parse(o.body);calls.push([path,b]);assert.equal(o.redirect,"error");
 if(path==="/api/profile")return res({role,can_write:true,can_read:true,can_recover:role==="OWNER"});
 if(path==="/api/catalog")return res([{market:"EURUSD",provider:"OANDA",ticker:"EURUSD",product:"SPOT",contract:""}]);
 if(path==="/api/receipts"){
  if(delayed){await delayed;}
  return res([{id:1,market:"EURUSD",note:"<img src=x onerror=alert(1)>",status:"UNREVIEWED"}]);
 }
 if(path==="/api/intent"){const n=Math.floor(Date.now()/1000)+60;return res({intent:"a".repeat(32)+"."+n+"."+"b".repeat(64),expires_unix:n});}
 if(path==="/api/submit"){if(fail)throw Error("uncertain");return res({id:1,status:"UNREVIEWED",duplicate:false});}
 if(path==="/owner/queue")return res([{id:2,market:"EURUSD",status:"UNREVIEWED"}]);
 if(path==="/owner/history")return res([{action:"APPROVED",reason:"private"}]);
 if(path==="/owner/review")return res({id:b.id,action:b.action,at_utc:"2026-11-16T06:22:00Z"});
 throw Error("unexpected path");
};
const flush=async()=>{for(let i=0;i<20;i++)await new Promise(r=>setImmediate(r));};
await import("./contributors_candidate_ui.mjs");
assert.equal(calls.length,0);
els.connect.click();await flush();assert.equal(els.contributor.hidden,false);assert.equal(els.owner.hidden,true);
els.market.value="EURUSD";els.market.listeners.change();els.provider.value="OANDA";els.provider.listeners.change();els.mapping.value="0";
els.price.value="1.12";els.anchor.value="2026-11-16T00:00:00Z";els.period.value="WEEK";els.kind.value="DELTA_PEAK";
els.intake.listeners.submit({preventDefault(){}});await flush();assert.deepEqual(calls.slice(-2).map(x=>x[0]),["/api/intent","/api/submit"]);
els.myLoad.click();await flush();assert.ok(els.myRows.children[0].children.some(x=>x.textContent.includes("<img")));
delayed=new Promise(r=>{delayResolve=r;});els.myLoad.click();await flush();lifecycle.pagehide();delayResolve();await flush();assert.equal(els.myRows.children.length,0);assert.equal(els.contributor.hidden,true);delayed=null;
role="OWNER";els.connect.click();await flush();assert.equal(els.owner.hidden,false);assert.equal(els.contributor.hidden,true);
els.entry.value="2";els.decision.value="APPROVED";els.reason.value="fixture";els.review.listeners.submit({preventDefault(){}});await flush();
assert.deepEqual(calls.slice(-2).map(x=>x[0]),["/api/intent","/owner/review"]);
els.clear.click();role="CONTRIBUTOR";els.connect.click();await flush();
els.market.value="EURUSD";els.market.listeners.change();els.provider.value="OANDA";els.provider.listeners.change();els.mapping.value="0";fail=true;
els.intake.listeners.submit({preventDefault(){}});await flush();assert.equal(els.send.disabled,true);assert.equal(els.contributor.hidden,true);
console.log("Candidate DOM-stub lifecycle checks passed");
