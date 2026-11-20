// REMURA Experience v0.11 LAB — 20/11/2026 17:13 CET
import {makePublisher,makeConsumer} from './snapshot_lifecycle_v011.mjs';
import {validateSharedFixture} from './validate_shared_fixture_v011.mjs';
import {buildDistributor} from './shared_distributor_v010.mjs';
import {projectApproved} from './approved_projection_v07.mjs';
import {forexCotFixture} from './forex_cot_projection_v08.mjs';
async function suite(makePublisher,makeConsumer,validate,build,projectPrices,projectForex){
 let now=Date.parse("2026-11-20T16:13:00Z"),approve=()=>true;
 const origin="https://contributors.fixture.invalid",req={method:"POST",url:origin+"/api/approved-snapshot",origin,body:null};
 const profile={role:"CONTRIBUTOR",can_read:true,generation:"g1",subject:"fixture-a"};
 const input=()=>({schema:"REMURA_PUBLISH_FIXTURE_V1",as_of:"2026-11-20T16:12:00Z",prices:[{instrument:"EURUSD",price:1,observed_at:"2026-11-20T16:10:00Z",source:"FIXTURE_PRICE"}],forex_rows:[{dataset:"TFF_FIXTURE",code:"099741",report_date:"2026-11-17",first_seen_at:null,oi:1000,asset_long:300,asset_short:100,leveraged_long:100,leveraged_short:300}]});
 let count=0;const ok=v=>{if(!v)throw Error("CHECK_"+count);count++};
 const p=makePublisher({approve:(...args)=>approve(...args),priceProjection:projectPrices,forexProjection:projectForex,clock:()=>now});
 const h=build({origin,clock:()=>now,authorize:async()=>profile,readSnapshot:p.readSnapshot,projectPrices,projectForex});
 let responseOverride=null;const c=makeConsumer({request:()=>responseOverride?responseOverride():h(req,{}),validate,clock:()=>now});
 ok(await c.refresh()==="UNAVAILABLE"&&c.read()===null);
 ok(await p.publish(JSON.stringify(input()),0,{})==="PUBLISHED");
 ok(await c.refresh()==="READY"&&c.read().revision===1);
 ok(c.read().cot.find(x=>x.pair==="EURUSD").asset_gap===20);
 const copy=c.read();copy.prices[0].price=999;ok(c.read().prices[0].price===1);
 const saved=await h(req,{});ok(saved.status===200);
 ok(await p.publish(JSON.stringify(input()),0,{})==="CONFLICT");
 approve=()=>false;ok(await p.publish(JSON.stringify(input()),1,{})==="DENIED");
 ok(JSON.parse(p.readSnapshot()).revision===1);
 approve=()=>true;
 for(const change of [s=>s.secret="no",s=>s.as_of="2026-11-20T16:11:00Z",s=>s.prices[0].source="LIVE",s=>s.forex_rows[0].oi=0,s=>s.forex_rows.push({...s.forex_rows[0]})]){
  const s=input();change(s);ok(await p.publish(JSON.stringify(s),1,{})==="REJECTED");
 }
 let release;approve=()=>new Promise(resolve=>release=resolve);
 const pending=p.publish(JSON.stringify(input()),1,{});
 approve=()=>true;ok(await p.publish(JSON.stringify(input()),1,{})==="PUBLISHED");release(true);
 ok(await pending==="CONFLICT");ok(JSON.parse(p.readSnapshot()).revision===2);
 ok(await c.refresh()==="READY"&&c.read().revision===2);
 responseOverride=()=>saved;ok(await c.refresh()==="UNAVAILABLE"&&c.read()===null);
 responseOverride=null;ok(await c.refresh()==="READY");
 const latest=await h(req,{});
 const bad=JSON.parse(latest.body);bad.prices[0].price=2;
 responseOverride=()=>({...latest,body:JSON.stringify(bad)});
 ok(await c.refresh()==="UNAVAILABLE"&&c.read()===null);
 for(const alter of [x=>x.extra="no",x=>x.cot.pop(),x=>x.cot[0].asset_gap=201,x=>x.cot[0].legs[0].code="097741",x=>x.cot[0].publication_at=x.as_of,x=>x.sentiment.capital="LIVE",x=>x.prices[0].observed_at="2026-11-20T16:14:00Z",x=>x.scientific_admission=true]){
  const b=JSON.parse(latest.body);alter(b);responseOverride=()=>({...latest,body:JSON.stringify(b)});ok(await c.refresh()==="UNAVAILABLE"&&c.read()===null);
 }
 responseOverride=()=>({...latest,headers:{}});ok(await c.refresh()==="UNAVAILABLE");
 responseOverride=()=>new Promise(resolve=>release=resolve);
 const inflight=c.refresh();c.close();release(latest);ok(await inflight==="CANCELLED"&&c.read()===null);
 responseOverride=null;ok(await c.refresh()==="READY");
 now+=13*60000;ok(c.read().prices[0].freshness==="STALE");
 now+=3*60000;ok(c.read()===null);
 ok(await c.refresh()==="UNAVAILABLE");
 return count;
}
console.log('REMURA_LIFECYCLE_PASS='+await suite(makePublisher,makeConsumer,validateSharedFixture,buildDistributor,projectApproved,forexCotFixture));
