// REMURA v0.8.115 LAB — 17/11/2026 CET
import test from "node:test";
import assert from "node:assert/strict";
import worker,{fixtureFetch} from "./level_worker_boundary_candidate.mjs";
import {reserve,RESERVE_SQL} from "./level_admission_candidate.mjs";
import {createHash} from "node:crypto";
const KEY="1".repeat(64), HASH=createHash("sha256").update(KEY).digest("hex"), PIN="a".repeat(64), T=1794894540000;
function db(row={enabled:1,allowed:1}){return {prepare(sql){assert.equal(sql,RESERVE_SQL);return {bind(...args){assert.deepEqual(args,[PIN,T]);return {async first(){return row;}};}};}};}
const opts={synthetic:true,enabled:true,pin:PIN,keyHash:HASH,now:()=>T};
function req(body="{}",extra={},path=KEY){return new Request("https://example.invalid/lab/levels/v1/"+path,{method:"POST",body,headers:{"content-type":"application/json","content-length":"2","x-remura-fixture-peer":"SYNTHETIC_FIXTURE_PEER",...extra}});}
test("default entrypoint always off",async()=>{assert.equal((await worker.fetch(req(),{LEVEL_ENABLED:"true"})).status,503);});
test("fixture off unless explicit",async()=>{assert.equal((await fixtureFetch(req(),{...opts,synthetic:false})).status,503);});
test("D1 unavailable and denied never read body",async()=>{const r=req();assert.equal((await fixtureFetch(r,{...opts,db:db(null)})).status,503);assert.equal(r.bodyUsed,false);assert.equal(await reserve({},PIN,T),"UNAVAILABLE");});
test("rate limit before read",async()=>{const r=req();assert.equal((await fixtureFetch(r,{...opts,db:db({enabled:1,allowed:0})})).status,429);assert.equal(r.bodyUsed,false);});
test("authentication before read",async()=>{const r=req("{}",{},"2".repeat(64));assert.equal((await fixtureFetch(r,{...opts,db:db()})).status,403);assert.equal(r.bodyUsed,false);});
test("declared maximum before read",async()=>{const r=req("{}",{"content-length":"15001"});assert.equal((await fixtureFetch(r,{...opts,db:db()})).status,413);assert.equal(r.bodyUsed,false);});
test("short and trailing body",async()=>{for(const body of ["{","{}x"])assert.equal((await fixtureFetch(req(body),{...opts,db:db()})).status,400);});
test("valid body never accepted before parser port",async()=>{const r=await fixtureFetch(req(),{...opts,db:db()});assert.equal(r.status,503);assert.deepEqual(await r.json(),{status:"VALIDATOR_NOT_CONNECTED",synthetic:true,receipt_authenticated:false,operational_signal:false});});
test("thrown D1 error fails closed",async()=>{assert.equal(await reserve({prepare(){throw Error("private");}},PIN,T),"UNAVAILABLE");});
