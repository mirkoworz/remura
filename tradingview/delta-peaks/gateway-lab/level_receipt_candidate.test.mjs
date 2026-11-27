// REMURA v0.8.118 LAB — 17/11/2026 CET
import test from "node:test";
import assert from "node:assert/strict";
import {reserveFixture,storeFixture,RESERVE_ID_SQL} from "./level_receipt_candidate.mjs";
const PIN="a".repeat(64),T=1794859200000;
test("reservation requires explicit fixture and exact clock",async()=>{
 const db={prepare(sql){assert.equal(sql,RESERVE_ID_SQL);return {bind(...args){assert.deepEqual(args,[PIN,T]);return {async first(){return {enabled:1,allowed:1,attempts:3};}};}};}};
 assert.deepEqual(await reserveFixture(db,PIN,T),{status:"UNAVAILABLE"});
 assert.deepEqual(await reserveFixture(db,PIN,T,{synthetic:true}),{status:"RESERVED",attempt:3});
});
test("invalid receipt never reaches SQL",async()=>{
 const db={prepare(){assert.fail("SQL");}};
 const r=await storeFixture(db,"{}",{synthetic:true,pin:PIN,attempt:1,receivedMs:T});
 assert.equal(r.status,"INVALID");
 assert.equal(r.receipt_authenticated,false);
});
test("storage and attempt invalid fail closed",async()=>{
 assert.equal((await reserveFixture({},PIN,T,{synthetic:true})).status,"UNAVAILABLE");
 assert.equal((await storeFixture({},"{}",{synthetic:true,pin:PIN,attempt:49})).status,"DENIED");
});
