// REMURA Contributors v0.55 LAB — actual local claim, mock D1 only.
import assert from "node:assert/strict";
import {mkdtemp,rm,writeFile,realpath,access} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {SQL,MARK} from "./d1_fixture_batch_probe.mjs";
import {makeDurableSyntheticSession} from "./fixture_durable_session_lab.mjs";
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
const evidence={account_id:"a".repeat(32),fixture_uuid:"00000000-0000-0000-0000-000000000002",lab_uuid:"00000000-0000-0000-0000-000000000001"};
const config={name:"remura-contributors-fixture-proxy",account_id:evidence.account_id,compatibility_date:"2026-11-15",workers_dev:false,preview_urls:false,routes:[],d1_databases:[{binding:"CONTRIBUTORS_FIXTURE_DB",database_name:"remura-contributors-fixture",database_id:evidence.fixture_uuid,remote:true}]};

let passed=0;
for(const kind of ["success","compete","open_failure","dispose_failure","bad_config","no_approval","partial_claim"]){
 const dir=await realpath(await mkdtemp(join(tmpdir(),"remura-fixture-")));
 try{
  let opened=0,disposed=0;
  const f=fixture();
  const open=async()=>{opened++;if(kind==="open_failure")throw Error("mock");return {env:{CONTRIBUTORS_FIXTURE_DB:f.env.CONTRIBUTORS_FIXTURE_DB},dispose:async()=>{disposed++;if(kind==="dispose_failure")throw Error("mock");}};};
  const mk=()=>makeDurableSyntheticSession(dir,open);
  const path=join(dir,"fixture-session-consumed-v1");
  if(kind==="partial_claim")await writeFile(path,"");
  if(kind==="compete"){
   const results=await Promise.allSettled(Array.from({length:8},()=>mk()(config,evidence,true)));
   assert.equal(results.filter(r=>r.status==="fulfilled").length,1);
  }else if(kind==="success"){
   assert.equal((await mk()(config,evidence,true)).status,"SYNTHETIC_SESSION_OBSERVED");
  }else{
   await assert.rejects(mk()(kind==="bad_config"?{...config,workers_dev:true}:config,evidence,kind!=="no_approval"));
  }
  if(["bad_config","no_approval"].includes(kind)){
   assert.equal(opened,0);await assert.rejects(access(path));
  }else{
   await access(path);await assert.rejects(mk()(config,evidence,true));
   assert.equal(opened,kind==="partial_claim"?0:1);
  }
  assert.equal(disposed,["success","compete","dispose_failure"].includes(kind)?1:0);
  assert.equal(f.stats.batches,["success","compete","dispose_failure"].includes(kind)?1:0);
  passed++;
 }finally{await rm(dir,{recursive:true,force:true});}
}
console.log("REMURA durable synthetic session cases: "+passed+" PASS");
