// REMURA Experience v0.13 LAB — 20/11/2026 CET
import {makeReadBridge} from './snapshot_read_bridge_v013.mjs';
import {buildDistributor} from './shared_distributor_v010.mjs';
import {projectApproved} from './approved_projection_v07.mjs';
import {forexCotFixture} from './forex_cot_projection_v08.mjs';
async function test(makeReadBridge,buildDistributor,projectPrices,projectForex){
 const origin="https://contributors.fixture.invalid",req={method:"POST",url:origin+"/api/approved-snapshot",origin,site:"same-origin",csrf:"1",contentType:"application/json",body:"{}",encoding:"identity"};
 const env=()=>({mode:"SYNTHETIC_ONLY",CONTRIBUTORS_GENERATION:"a".repeat(32),CONTRIBUTORS_JOURNAL_PIN:"b".repeat(64)});
 const actor={subject:"c".repeat(64),email_tag:"d".repeat(64)};
 let count=0;const ok=v=>{if(!v)throw Error("CHECK_"+count);count++};
 function harness({identity=()=>actor,gen=()=>true,role=()=>({role:"CONTRIBUTOR",can_read:true}),lim=()=>({success:true}),duringRead=()=>{}}={}){
  let reads=0,auth=0,profiles=0,limits=0,gens=0;
  const h=makeReadBridge({accessBinding:async(c,e,x)=>{auth++;return identity(auth,x)},verifyGeneration:async e=>{gens++;if(!gen(gens,e))throw Error("generation")},profile:async(c,e,x)=>{profiles++;return role(profiles,x)},rateLimit:async()=>{limits++;return lim()},distributor:authorize=>buildDistributor({origin,authorize,clock:()=>Date.parse("2026-11-20T16:18:00Z"),readSnapshot:async()=>{reads++;duringRead();return JSON.stringify({schema:"REMURA_SHARED_FIXTURE_V1",revision:1,as_of:"2026-11-20T16:17:00Z",prices:[],forex_rows:[]})},projectPrices,projectForex})});
  return {h,counts:()=>({reads,auth,profiles,limits,gens})};
 }
 let h=harness(),r=await h.h(req,env(),{});ok(r.status===200);ok(h.counts().reads===1&&h.counts().limits===1&&h.counts().profiles===2&&h.counts().gens===4);
 ok(!r.body.includes(actor.subject)&&!r.body.includes(actor.email_tag));ok(r.headers["Cache-Control"].includes("no-store"));
 for(const change of [{method:"GET"},{url:req.url+"?x=1"},{origin:"https://other.invalid"},{site:"cross-site"},{csrf:"0"},{contentType:"text/plain"},{body:'{"role":"OWNER"}'},{body:null},{encoding:"gzip"},{url:origin+"/owner/queue"}]){
  h=harness();r=await h.h({...req,...change},env(),{});ok(r.status===403&&h.counts().auth===0&&h.counts().reads===0);
 }
 for(const e of [{...env(),mode:"LIVE"},{...env(),CONTRIBUTORS_GENERATION:"bad"},{...env(),CONTRIBUTORS_JOURNAL_PIN:"bad"}]){h=harness();r=await h.h(req,e,{});ok(r.status===403&&h.counts().auth===0)}
 for(const identity of [()=>null,()=>({subject:"bad",email_tag:actor.email_tag}),()=>{throw Error("fake")}]){h=harness({identity});r=await h.h(req,env(),{});ok(r.status===403&&h.counts().reads===0)}
 h=harness({lim:()=>({success:false})});r=await h.h(req,env(),{});ok(r.status===429&&h.counts().reads===0);
 h=harness({lim:()=>null});r=await h.h(req,env(),{});ok(r.status===403&&h.counts().reads===0);
 for(const role of [()=>({role:"OWNER",can_read:true}),()=>({role:"VIEWER",can_read:true}),()=>({role:"CONTRIBUTOR",can_read:false}),()=>({role:"CONTRIBUTOR",can_read:"true"})]){
  h=harness({role});r=await h.h(req,env(),{});ok(r.status!==200&&h.counts().reads===0);
 }
 h=harness({gen:()=>false});r=await h.h(req,env(),{});ok(r.status!==200&&h.counts().reads===0);
 h=harness({identity:i=>i===1?actor:{...actor,email_tag:"e".repeat(64)}});r=await h.h(req,env(),{});ok(r.status!==200&&h.counts().reads===0);
 for(const role of [i=>({role:"CONTRIBUTOR",can_read:i===1}),i=>({role:i===1?"CONTRIBUTOR":"OWNER",can_read:true})]){
  h=harness({role});r=await h.h(req,env(),{});ok(r.status!==200&&h.counts().reads===1);
 }
 h=harness({identity:i=>i<3?actor:{...actor,subject:"e".repeat(64)}});r=await h.h(req,env(),{});ok(r.status!==200&&h.counts().reads===1);
 for(const key of ["CONTRIBUTORS_GENERATION","CONTRIBUTORS_JOURNAL_PIN"]){const e=env();h=harness({duringRead:()=>{e[key]="f".repeat(e[key].length)}});r=await h.h(req,e,{});ok(r.status!==200&&h.counts().reads===1)}
 h=harness({gen:i=>i<3});r=await h.h(req,env(),{});ok(r.status!==200&&h.counts().reads===1);
 return count;
}
console.log('REMURA_READ_BRIDGE_PASS='+await test(makeReadBridge,buildDistributor,projectApproved,forexCotFixture));
