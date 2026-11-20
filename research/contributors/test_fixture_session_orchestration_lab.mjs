// REMURA Contributors v0.53 LAB — offline only
import assert from "node:assert/strict";
import {fixtureConfigGate} from "./fixture_proxy_config_gate.mjs";
import {fixtureBatchProbe,SQL,MARK} from "./d1_fixture_batch_probe.mjs";
import {makeSyntheticSession} from "./fixture_session_orchestration_lab.mjs";
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
for(const kind of ["success","config","open_error","extra_binding","missing_binding","missing_dispose","unknown_batch","sticky","dirty","dispose_error","concurrent","snapshot"]){
 const f=fixture(kind==="unknown_batch"?{error:"unknown"}:kind==="sticky"?{sticky:true}:kind==="dirty"?{dirty:true}:{});
 let opened=0,disposed=0,seen;
 const cfg=structuredClone(config);
 const run=makeSyntheticSession(fixtureConfigGate,fixtureBatchProbe,async c=>{
  opened++;seen=c;
  if(kind==="open_error")throw Error("mock_open");
  if(kind==="snapshot")cfg.d1_databases[0].database_id=evidence.lab_uuid;
  return {env:kind==="extra_binding"?{CONTRIBUTORS_FIXTURE_DB:f.env.CONTRIBUTORS_FIXTURE_DB,CONTRIBUTORS_DB:{}}:kind==="missing_binding"?{}:{CONTRIBUTORS_FIXTURE_DB:f.env.CONTRIBUTORS_FIXTURE_DB},dispose:kind==="missing_dispose"?undefined:async()=>{disposed++;if(kind==="dispose_error")throw Error("mock_dispose");}};
 });
 if(kind==="config")cfg.workers_dev=true;
 const a=run(cfg,evidence,true);
 if(kind==="concurrent")await assert.rejects(run(cfg,evidence,true),/fixture_session_denied/);
 const ok=["success","concurrent","snapshot"].includes(kind);
 if(ok){const x=await a;assert.equal(x.status,"SYNTHETIC_SESSION_OBSERVED");assert.equal(x.remote_session_closed_verified,false);}
 else await assert.rejects(a,/fixture_session_blocked_no_retry/);
 await assert.rejects(run(config,evidence,true),/fixture_session_denied/);
 assert.equal(opened,kind==="config"?0:1);
 assert.equal(disposed,["config","open_error","missing_dispose"].includes(kind)?0:1);
 assert.equal(f.stats.batches,["success","concurrent","snapshot","unknown_batch","sticky","dispose_error"].includes(kind)?1:0);
 if(kind==="snapshot")assert.equal(seen.d1_databases[0].database_id,evidence.fixture_uuid);
 passed++;
}
{let n=0;const run=makeSyntheticSession(fixtureConfigGate,fixtureBatchProbe,async()=>{n++;throw Error("unexpected");});await assert.rejects(run(config,evidence,false),/fixture_session_denied/);assert.equal(n,0);passed++;}
console.log("REMURA synthetic fixture session cases: "+passed+" PASS");
