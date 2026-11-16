// REMURA Contributors v0.25 LAB — 16/11/2026 07:19 CET
import assert from "node:assert/strict";
import {CandidateClient} from "./contributors_candidate_client.mjs";
let calls=[],fail=false,malformed=false;
const res=d=>new Response(JSON.stringify({data:d}),{status:200,headers:{"Content-Type":"application/json"}});
const f=async(path,o)=>{
 calls.push({path,o});assert.equal(o.method,"POST");assert.equal(o.redirect,"error");assert.equal(o.credentials,"same-origin");assert.equal(o.cache,"no-store");
 assert.equal(o.headers["X-Remura-CSRF"],"1");
 if(path==="/api/intent"){const exp=Math.floor(Date.now()/1000)+60;return res({intent:"a".repeat(32)+"."+exp+"."+"b".repeat(64),expires_unix:exp});}
 if(path==="/api/submit"){if(fail)throw Error("transport");assert.ok(o.headers["X-Remura-Intent"]);return res(malformed?{}:{id:3,status:"UNREVIEWED",duplicate:false});}
 return res([]);
};
const c=new CandidateClient(f);
await c.read("/api/receipts",{after:0});assert.equal(calls.length,1);
await assert.rejects(c.read("https://evil.invalid/"));await assert.rejects(c.read("/api/submit"));await assert.rejects(c.read("/api/intent"));
const body={price:"1.2",request_id:"fixture"};
await c.mutate("/api/submit",body);assert.equal(calls.length,3);assert.deepEqual(JSON.parse(calls[1].o.body).body,JSON.parse(calls[2].o.body));assert.equal(c.uncertain,false);
fail=true;await assert.rejects(c.mutate("/api/submit",body));assert.equal(c.uncertain,true);
const n=calls.length;await assert.rejects(c.mutate("/api/submit",body));assert.equal(calls.length,n);
await c.read("/api/receipts",{after:0});assert.equal(calls.length,n+1);
fail=false;malformed=true;const d=new CandidateClient(f);await assert.rejects(d.mutate("/api/submit",body));assert.equal(d.uncertain,true);
const e=new CandidateClient(async()=>{throw Error("issue failed");});await assert.rejects(e.mutate("/api/submit",body));assert.equal(e.uncertain,false);
console.log("Candidate UI no-retry client checks passed");
