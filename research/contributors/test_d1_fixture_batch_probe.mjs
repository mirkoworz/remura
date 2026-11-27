// REMURA Contributors v0.49 LAB — 20/11/2026 CET
import assert from "node:assert/strict";
import {fixtureBatchProbe,SQL,MARK} from "./d1_fixture_batch_probe.mjs";
let passed=0;
function fixture({primary=true,open=false,dirty=false,error="expected",sticky=false}={}){
 const stats={reads:0,batches:0};
 let marker=dirty?1:0;
 const db={
  withSession(mode){assert.equal(mode,"first-primary");return {prepare(sql){return {bind(...args){return {async all(){
   stats.reads++;
   if(sql===SQL.marker)assert.equal(args[0],MARK);
   return {success:true,meta:{served_by_primary:primary,rows_read:1,rows_written:0},
   results:[sql===SQL.state?{write_enabled:open?1:0,read_enabled:0,recovery_enabled:0}:{n:marker}]};
  }};}};}};},
  prepare(sql){assert.equal(sql,SQL.insert);return {bind(...args){assert.equal(args.at(-1),0);return args;}};},
  async batch(list){
   stats.batches++;assert.equal(list.length,2);assert.deepEqual(list[0],list[1]);
   if(sticky)marker=1;
   if(error==="expected")throw Error("D1_ERROR: UNIQUE constraint failed: lab_catalog.market, lab_catalog.provider, lab_catalog.ticker, lab_catalog.product, lab_catalog.contract");
   if(error==="unknown")throw Error("unexpected");
   return [];
  }
 };
 return {stats,env:{FIXTURE_BATCH_MODE:"SYNTHETIC_ONLY",FIXTURE_DATABASE_NAME:"remura-contributors-fixture",CONTRIBUTORS_FIXTURE_DB:db}};
}
{
 const f=fixture();const out=await fixtureBatchProbe(f.env,true);
 assert.equal(out.status,"FIXTURE_BATCH_ROLLBACK_OBSERVED");assert.deepEqual(f.stats,{reads:4,batches:1});passed++;
}
for(const [cfg,patch,explicit,reads,batches] of [
 [{},{},false,0,0],
 [{},{FIXTURE_DATABASE_NAME:"remura-contributors-lab"},true,0,0],
 [{},{CONTRIBUTORS_DB:{}},true,0,0],
 [{primary:false},{},true,1,0],
 [{open:true},{},true,1,0],
 [{dirty:true},{},true,2,0],
 [{error:"unknown"},{},true,4,1],
 [{error:"success"},{},true,4,1],
 [{sticky:true},{},true,4,1]
]){
 const f=fixture(cfg);await assert.rejects(fixtureBatchProbe({...f.env,...patch},explicit));
 assert.deepEqual(f.stats,{reads,batches});passed++;
}
console.log("REMURA D1 fixture batch mock cases: "+passed+" PASS");
