// REMURA Contributors v0.19 LAB — 16/11/2026 01:16 CET
import assert from "node:assert/strict";
import {SQL,queue,history,review} from "./d1_lab_review.mjs";
const owner={role:"OWNER",subject:"fixture-owner"}, contributor={role:"CONTRIBUTOR",subject:"fixture-a"};
const opts={synthetic:true,now:"2026-11-16T00:16:00Z",reason:"synthetic"};
let allowed=true,calls=[],write={success:true,meta:{changes:1}},rows=[];
const db={prepare(sql){return {bind(...args){calls.push({sql,args});return {
 async first(){assert.equal(sql,SQL.ownerGate);assert.deepEqual(args,[owner.subject]);return allowed?{id:1}:null;},
 async all(){assert.ok([SQL.queue,SQL.history].includes(sql));assert.equal(args[1],owner.subject);return {success:true,results:rows};},
 async run(){assert.equal(sql,SQL.decision);assert.equal(args[1],owner.subject);return write;}
};}};}};
assert.deepEqual(await review(db,owner,1,"APPROVED",opts),{id:1,action:"APPROVED",at_utc:opts.now});
assert.deepEqual(calls.at(-1).args,[1,owner.subject,"APPROVED",opts.now,"synthetic"]);
assert.deepEqual(await queue(db,owner,{synthetic:true}),[]);
assert.deepEqual(await history(db,owner,1,{synthetic:true}),[]);
const n=calls.length;
for(const actor of [contributor,{role:"OWNER",subject:"fixture-a"},{role:"OWNER",subject:"real-user"}]){
 await assert.rejects(review(db,actor,1,"APPROVED",opts));
 await assert.rejects(queue(db,actor,{synthetic:true}));
 await assert.rejects(history(db,actor,1,{synthetic:true}));
}
for(const change of [{synthetic:false},{reason:" "},{reason:"x\n"},{reason:"x".repeat(281)},{now:"2026-02-30T00:00:00Z"}]){
 await assert.rejects(review(db,owner,1,"APPROVED",{...opts,...change}));
}
await assert.rejects(review(db,owner,0,"APPROVED",opts));
await assert.rejects(review(db,owner,1,"UNREVIEWED",opts));
await assert.rejects(queue(db,owner,{synthetic:true,after:-1}));
assert.equal(calls.length,n);
allowed=false; await assert.rejects(review(db,owner,1,"APPROVED",opts));await assert.rejects(queue(db,owner,{synthetic:true}));
allowed=true;write={success:true,meta:{changes:0}};await assert.rejects(review(db,owner,1,"APPROVED",opts));
rows=Array(21).fill({});await assert.rejects(queue(db,owner,{synthetic:true}));
rows=Array(3).fill({});await assert.rejects(history(db,owner,1,{synthetic:true}));
console.log("D1 synthetic owner review checks passed");
