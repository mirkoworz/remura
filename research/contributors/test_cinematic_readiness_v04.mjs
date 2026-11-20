// REMURA Experience v0.4 LAB — 20/11/2026 CET — synthetic only
import assert from "node:assert/strict";
import {createReadiness} from "./cinematic_readiness_v04.mjs";
let count=0;
const check=(v)=>{assert.ok(v);count++;};
function harness(overrides={}){
 const calls=[],steps=[];
 const c=createReadiness({shell:async()=>calls.push("shell"),
 authorize:async()=>{calls.push("auth");return {authorized:true,role:"CONTRIBUTOR"}},
 loadApproved:async role=>{calls.push("view:"+role);return {ready:true}},
 onStep:x=>steps.push(x),...overrides});
 return {c,calls,steps};
}
let h=harness(),r=await h.c.start();
check(r.state==="READY"&&r.role==="CONTRIBUTOR");
check(h.calls.join(",")==="shell,auth,view:CONTRIBUTOR");
check(h.steps.map(x=>x.completed).join(",")==="0,1,2,3");
for(const p of [null,{authorized:false,role:"OWNER"},{authorized:true,role:"ADMIN"},{authorized:"true",role:"CONTRIBUTOR"}]){
 h=harness({authorize:async()=>p});r=await h.c.start();
 check(r.state==="DENIED"&&!h.calls.some(x=>x.startsWith("view")));
}
h=harness({shell:async()=>{throw Error("synthetic")}});r=await h.c.start();check(r.state==="BLOCKED"&&h.calls.length===0);
h=harness({authorize:async()=>{throw Error("synthetic")}});r=await h.c.start();check(r.state==="BLOCKED"&&!h.calls.some(x=>x.startsWith("view")));
h=harness({loadApproved:async()=>({ready:false})});r=await h.c.start();check(r.state==="BLOCKED"&&!h.steps.some(x=>x.state==="READY"));
let release;h=harness({authorize:()=>new Promise(ok=>release=ok)});let pending=h.c.start();await Promise.resolve();await Promise.resolve();h.c.cancel();release({authorized:true,role:"OWNER"});r=await pending;check(r.state==="CANCELLED"&&!h.calls.some(x=>x.startsWith("view")));
let oldRelease;let n=0;h=harness({authorize:()=>++n===1?new Promise(ok=>oldRelease=ok):Promise.resolve({authorized:true,role:"VIEWER"})});pending=h.c.start();await Promise.resolve();await Promise.resolve();let fresh=await h.c.start();oldRelease({authorized:true,role:"OWNER"});r=await pending;check(fresh.role==="VIEWER"&&r.state==="CANCELLED"&&h.calls.filter(x=>x.startsWith("view")).join()==="view:VIEWER");
console.log("REMURA_READINESS_SYNTHETIC_PASS="+count);
