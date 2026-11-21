// REMURA Contributors v0.88 LAB — ONLY new offline iPhone checker tests
import {test} from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {runInNewContext,Script} from "node:vm";
const html=readFileSync(new URL("./contributors_free_local_v088_lab.html",import.meta.url),"utf8");
const found=html.match(/<script id="local-free-checker">([\s\S]*?)<\/script>/);
assert.ok(found,"one inline self-contained script required");
const js=found[1];
new Script(js);
const ids=[
 "reads","writes","requests","dbs","storage","largest","seatsUsed","seatsTotal",
 "observed","verdict","explain","seatsState","clockState","analyze","clear",
 ...["reads","writes","requests","dbs","storage","largest"].map(s=>s+"State")
];
function env(){
 const elements=new Map(ids.map(id=>[id,{value:"",textContent:"",handlers:{},addEventListener(type,cb){this.handlers[type]=cb;}}]));
 const context={document:{getElementById:id=>elements.get(id)},Date,Number,Object,RegExp};
 runInNewContext(js,context);
 const set=(x)=>{for(const [key,value] of Object.entries(x))elements.get(key).value=String(value)};
 const get=(id)=>elements.get(id).textContent;
 const calc=()=>runInNewContext("calculate()",context);
 const clear=()=>runInNewContext("clearAll()",context);
 return {elements,set,get,calc,clear};
}
function fresh(){
 return new Date(Date.now()-60000).toISOString().slice(0,19)+"Z";
}
function full(){
 return {reads:"12",writes:"1",requests:"199",dbs:"4",storage:"6557696",largest:"6266880",seatsUsed:"1",seatsTotal:"50",observed:fresh()};
}
test("01 header top version and Rome date",()=>{
 assert.ok(html.indexOf('id="version"')<html.indexOf("<main"));
 assert.match(html,/Contributors v0\.88 LAB · 21\/11\/2026 18:56 CET/);
});
test("02 restrictive CSP no network",()=>{
 assert.match(html,/connect-src 'none'/);assert.match(html,/form-action 'none'/);
});
test("03 HTML contains no external resources",()=>{
 assert.doesNotMatch(html,/<(?:img|iframe|link)\b/i);
});
test("04 missing all counters remains NO-GO",()=>{
 const e=env();const r=e.calc();assert.equal(r.decision,"NO_GO");assert.match(e.get("readsState"),/SCONOSCIUTO/);
});
test("05 valid values remain NO-GO",()=>{
 const e=env();e.set(full());const r=e.calc();assert.equal(r.invalid,0);assert.equal(r.missing,0);assert.equal(r.decision,"NO_GO");assert.match(e.get("explain"),/non dimostrano/);
});
test("06 missing D1 reads never converted to zero",()=>{
 const e=env();const o=full();delete o.reads;e.set(o);e.calc();assert.equal(e.get("readsState"),"SCONOSCIUTO");
});
test("07 explicit zero is manual estimate",()=>{
 const e=env();e.set({...full(),reads:"0"});e.calc();assert.match(e.get("readsState"),/STIMA/);
});
test("08 D1 reads at limit",()=>{
 const e=env();e.set({...full(),reads:"5000000"});const r=e.calc();assert.equal(r.over,1);
});
test("09 D1 writes at limit",()=>{
 const e=env();e.set({...full(),writes:"100000"});const r=e.calc();assert.equal(r.over,1);
});
test("10 Workers at limit",()=>{
 const e=env();e.set({...full(),requests:"100000"});const r=e.calc();assert.equal(r.over,1);
});
test("11 D1 databases at limit",()=>{
 const e=env();e.set({...full(),dbs:"10"});const r=e.calc();assert.equal(r.over,1);
});
test("12 storage account at limit",()=>{
 const e=env();e.set({...full(),storage:"5000000000"});const r=e.calc();assert.ok(r.over>=1);
});
test("13 one D1 DB at limit",()=>{
 const e=env();e.set({...full(),largest:"500000000"});const r=e.calc();assert.equal(r.over,1);
});
test("14 D1 warning threshold 70pct",()=>{
 const e=env();e.set({...full(),reads:"3500000"});const r=e.calc();assert.equal(r.caution,1);
});
test("15 negative values invalid",()=>{
 const e=env();e.set({...full(),writes:"-1"});assert.ok(e.calc().invalid>=1);
});
test("16 fractional values invalid",()=>{
 const e=env();e.set({...full(),requests:"3.5"});assert.ok(e.calc().invalid>=1);
});
test("17 leading zero invalid to avoid ambiguity",()=>{
 const e=env();e.set({...full(),reads:"007"});assert.ok(e.calc().invalid>=1);
});
test("18 largest bigger than total rejected",()=>{
 const e=env();e.set({...full(),largest:"6557697"});assert.ok(e.calc().invalid>=1);
});
test("19 Access seats used over total rejected",()=>{
 const e=env();e.set({...full(),seatsUsed:"51",seatsTotal:"50"});assert.ok(e.calc().invalid>=1);
});
test("20 Access no free seats not attested",()=>{
 const e=env();e.set({...full(),seatsUsed:"50",seatsTotal:"50"});e.calc();assert.match(e.get("seatsState"),/NON ATTESTATO/);
});
test("21 old UTC day is stale",()=>{
 const e=env();e.set({...full(),observed:"2026-11-20T17:00:00Z"});const r=e.calc();assert.ok(r.missing>=1);
});
test("22 reset empties all local fields",()=>{
 const e=env();e.set(full());e.calc();e.clear();assert.equal(e.elements.get("writes").value,"");assert.match(e.get("verdict"),/NO-GO/);
});
