// REMURA v0.8.123 LAB — 17/11/2026 CET
import {spawnSync} from "node:child_process";
import {fileURLToPath} from "node:url";
import worker,{fixtureFetch} from "./level_permit_worker_candidate.mjs";
import {RESERVE_ID_SQL} from "./level_receipt_candidate.mjs";
import {STOP_SQL} from "./level_admission_candidate.mjs";
const helper=fileURLToPath(new URL("./level_permit_worker_sqlite_fixture.py",import.meta.url)),path=process.argv[2];
let input="";for await(const chunk of process.stdin){input+=chunk;if(input.length>300000)throw Error("fixture bound");}
const spec=JSON.parse(input);
if(spec.synthetic!==true||!Array.isArray(spec.actions)||spec.actions.length>48)throw Error("fixture only");
const key="1".repeat(64),hash=Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(key))),x=>x.toString(16).padStart(2,"0")).join("");
let reservationHook;
const db={prepare(sql){return {bind(...args){return {async first(){
 const out=spawnSync("python3",[helper,path],{input:JSON.stringify({sql,args}),encoding:"utf8",timeout:5000,maxBuffer:65536});
 if(out.status!==0)throw Error("fixture failure");
 const row=JSON.parse(out.stdout);if(sql===RESERVE_ID_SQL&&reservationHook){const hook=reservationHook;reservationHook=undefined;hook();}
 return row;
}};}};}};
function req(a,stream){
 const bytes=Array.isArray(a.bytes)?Uint8Array.from(a.bytes):new TextEncoder().encode(a.raw??"{}");
 const headers={"content-type":"application/json","content-length":String(bytes.length),...a.headers};
 const method=a.method??"POST";
 return new Request((a.url??("https://example.invalid/lab/levels/v2/"+(a.key??key))),{method,headers,...(method==="GET"||method==="HEAD"?{}:{body:stream??bytes,duplex:"half"})});
}
async function call(a,stream){
 let calls=0,dbCalls=0;
 const trap={prepare(){dbCalls++;throw Error("database must not be reached");}};
 const peer=Object.hasOwn(a,"peer")?a.peer:{synthetic:true,origin:"DIRECT_FIXTURE",ip:"192.0.2.42"};
 const config={synthetic:true,enabled:a.enabled!==false,db:a.noDb===true?trap:db,peer,pin:spec.pin,keyHash:hash,expected:a.expected??spec.expected,afterCloseMs:spec.cutoff,now:()=>{if(calls++===0)return a.now;if(a.clockThrows===true)throw Error("fixture clock");return a.done??a.now+100;}};
 const r=a.kind==="hardoff"?await worker.fetch(req(a,stream)):await fixtureFetch(req(a,stream),config);
 if(dbCalls!==0)throw Error("preflight contacted database");
 const body=await r.json();if(body.synthetic!==true||body.receipt_authenticated!==false||body.scientific_admission!==false||body.operational_signal!==false)throw Error("unsafe result");
 return [r.status,body.status];
}
const results=[];
for(const a of spec.actions){
 if(a.kind==="stop"){await db.prepare(STOP_SQL).bind(spec.pin).first();results.push([200,"STOPPED"]);}
 else if(a.kind==="overlap"){
  // Hold A's body until B has reserved and finished. Real SQL, two pending native Requests.
  let release;const bytes=new TextEncoder().encode(a.first.raw);
  const held=new ReadableStream({start(c){release=()=>{c.enqueue(bytes);c.close();};}});
  const firstReserved=new Promise(resolve=>reservationHook=resolve);
  const first=call(a.first,held);
  await firstReserved;const second=await call(a.second);release();
  results.push([await first,second]);
 }else results.push(await call(a));
}
console.log(JSON.stringify(results));
