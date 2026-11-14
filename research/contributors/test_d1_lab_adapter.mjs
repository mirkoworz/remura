// REMURA Contributors v0.16 LAB — 14/11/2026 23:56 CET
import assert from "node:assert/strict";
import {SQL,normalize,submit,receipts} from "./d1_lab_adapter.mjs";
const now="2026-11-14T22:56:00Z";
const actor={subject:"fixture-a",role:"CONTRIBUTOR"};
const payload={request_id:"00000000-0000-0000-0000-000000000001",market:"EURUSD",provider:"OANDA",ticker:"EURUSD",product:"SPOT",contract:"",period:"WEEK",kind:"DELTA_PEAK",price:"1,085400",anchor_utc:"2026-11-09T00:00:00Z",observed_utc:now,note:"synthetic"};
assert.equal(normalize(payload,now).price,"1.0854");
for(const change of [{price:"0.000"},{price:"1e3"},{note:"x\n"},{role:"OWNER"},{observed_utc:"2026-02-30T12:00:00Z"},{observed_utc:"2026-11-15T00:00:00Z"},{product:"FUTURE",contract:"NQ!",ticker:"NQ1!"}]){
 assert.throws(()=>normalize({...payload,...change},now));
}
let allowed=true,stored=null,queries=[];
const db={prepare(sql){
 return {bind(...args){
  queries.push({sql,args});
  assert.equal(args[0],actor.subject);
  return {
   async first(){
    if(sql===SQL.gate)return allowed?{slot:"friend-a"}:null;
    assert.equal(sql,SQL.existing);
    assert.equal(args[1],payload.request_id);
    return allowed?stored:null;
   },
   async run(){
    assert.equal(sql,SQL.insert);
    assert.equal(args.length,18);
    assert.equal(args[9],"1.0854");
    assert.equal(args[12],now);
    stored={id:1,...normalize(payload,now)};
    return {success:true,meta:{changes:1}};
   },
   async all(){
    assert.equal(sql,SQL.receipts);
    return {success:true,results:stored?[stored]:[]};
   }
  }
 }};
}};
assert.deepEqual(await submit(db,actor,payload,{now,synthetic:true}),{id:1,status:"UNREVIEWED",duplicate:false});
assert.equal((await submit(db,actor,payload,{now,synthetic:true})).duplicate,true);
await assert.rejects(submit(db,actor,{...payload,price:"2"},{now,synthetic:true}));
assert.equal((await receipts(db,actor,{synthetic:true})).length,1);
const count=queries.length;
await assert.rejects(submit(db,{subject:"fixture-a",role:"OWNER"},payload,{now,synthetic:true}));
await assert.rejects(submit(db,actor,payload,{now}));
await assert.rejects(receipts(db,actor,{after:-1,synthetic:true}));
assert.equal(queries.length,count);
allowed=false;
await assert.rejects(receipts(db,actor,{synthetic:true}));
await assert.rejects(submit(db,actor,payload,{now,synthetic:true}));
assert.equal(queries.filter(x=>x.sql===SQL.insert).length,1);
console.log("synthetic D1 adapter checks passed");
