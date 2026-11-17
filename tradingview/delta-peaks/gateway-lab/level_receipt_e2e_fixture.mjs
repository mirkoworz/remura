// REMURA v0.8.119 LAB — 17/11/2026 CET
// Finite synthetic script, exact SQL via local Python sqlite3 subprocess.
import {spawnSync} from "node:child_process";
import {fileURLToPath} from "node:url";
import {reserveFixture,storeFixture} from "./level_receipt_candidate.mjs";
import {STOP_SQL} from "./level_admission_candidate.mjs";
const helper=fileURLToPath(new URL("./level_receipt_sqlite_fixture.py",import.meta.url));
const path=process.argv[2];
let input="";for await(const chunk of process.stdin){input+=chunk;if(input.length>300000)throw Error("fixture bound");}
const spec=JSON.parse(input);
if(spec.synthetic!==true||!Array.isArray(spec.actions)||spec.actions.length>48)throw Error("fixture only");
const db={prepare(sql){return {bind(...args){return {async first(){
 const out=spawnSync("python3",[helper,path],{input:JSON.stringify({sql,args}),encoding:"utf8",timeout:5000,maxBuffer:65536});
 if(out.status!==0)throw Error("fixture failure");
 return JSON.parse(out.stdout);
}};}};}};
const attempts=new Map();const results=[];
for(const a of spec.actions){
 if(a.kind==="reserve"){
  const r=await reserveFixture(db,a.pin??spec.pin,a.now,{synthetic:true});
  if(r.status==="RESERVED")attempts.set(a.id,r.attempt);
  results.push(r.status);
 }else if(a.kind==="store"){
  const r=await storeFixture(db,a.raw,{synthetic:true,pin:a.pin??spec.pin,attempt:attempts.get(a.id),
   expected:a.expected??spec.expected,receivedMs:a.now,afterCloseMs:spec.cutoff});
  if(r.synthetic!==true||r.receipt_authenticated!==false||r.scientific_admission!==false||r.operational_signal!==false)throw Error("unsafe result");
  results.push(r.status);
 }else if(a.kind==="stop"){
  const r=await db.prepare(STOP_SQL).bind(spec.pin).first();results.push(r?.enabled===0?"STOPPED":"UNAVAILABLE");
 }else throw Error("unknown fixture action");
}
console.log(JSON.stringify(results));
