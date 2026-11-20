// REMURA Experience v0.10 LAB — 20/11/2026 17:09 CET
import {buildDistributor} from './shared_distributor_v010.mjs';
import {projectApproved} from './approved_projection_v07.mjs';
import {forexCotFixture} from './forex_cot_projection_v08.mjs';
async function suite(build,projectPrices,projectForex){
 const origin="https://contributors.fixture.invalid",now=Date.parse("2026-11-20T16:09:00Z"),req={method:"POST",url:origin+"/api/approved-snapshot",origin,body:null};
 const profile={role:"CONTRIBUTOR",can_read:true,generation:"g1",subject:"fixture-a"};
 const snap=()=>({schema:"REMURA_SHARED_FIXTURE_V1",revision:1,as_of:"2026-11-20T16:08:00Z",prices:[{instrument:"EURUSD",price:1,observed_at:"2026-11-20T16:02:00Z",source:"FIXTURE_PRICE"}],forex_rows:[{dataset:"TFF_FIXTURE",code:"099741",report_date:"2026-11-17",first_seen_at:null,oi:1000,asset_long:300,asset_short:100,leveraged_long:100,leveraged_short:300}]});
 let n=0;const ok=x=>{if(!x)throw Error("CHECK_"+n);n++};
 function harness({auth=()=>({...profile}),snapshot=()=>JSON.stringify(snap()),time=()=>now}={}){
  let ac=0,reads=0;
  const handler=build({origin,clock:time,authorize:async ctx=>{ac++;return auth(ctx,ac)},readSnapshot:async()=>{reads++;return snapshot()},projectPrices,projectForex});
  return {handler,counts:()=>[ac,reads]};
 }
 let h=harness(),r=await h.handler(req,{}),j=JSON.parse(r.body);
 ok(r.status===200&&j.synthetic&&j.scientific_admission===false);
 ok(j.cot.length===28&&j.cot.find(x=>x.pair==="EURUSD").asset_gap===20);
 ok(j.cot.find(x=>x.pair==="CADJPY").asset_gap===null);
 ok(j.sentiment.capital==="UNAVAILABLE"&&j.delta==="UNAVAILABLE");
 ok(!r.body.includes("fixture-a")&&!r.body.includes('"generation"')&&!r.body.includes('"forex_rows"'));
 ok(r.headers["Cache-Control"].includes("no-store")&&h.counts().join()==="2,1");
 for(const q of [{...req,method:"GET"},{...req,url:req.url+"?x=1"},{...req,url:origin+"/owner/queue"},{...req,origin:"https://other.invalid"},{...req,body:"{}"},{...req,subject:"fixture-a"}]){
  h=harness();r=await h.handler(q,{});ok(r.status===403&&h.counts().join()==="0,0");
 }
 for(const p of [null,{...profile,role:"OWNER"},{...profile,role:"VIEWER"},{...profile,can_read:false},{...profile,can_read:"true"},{...profile,subject:""},{...profile,extra:"fake"}]){
  h=harness({auth:()=>p});r=await h.handler(req,{});ok(r.status===403&&h.counts().join()==="1,0");
 }
 h=harness({auth:()=>{throw Error("fixture")}});r=await h.handler(req,{});ok(r.status!==200&&h.counts().join()==="1,0"&&!r.body.includes("fixture"));
 for(const change of [s=>s.as_of="2026-11-20T15:00:00Z",s=>s.as_of="2026-11-20T16:10:00Z",s=>s.revision=0,s=>s.schema="LIVE",s=>s.secret="fixture-secret",s=>s.prices[0].source="LIVE",s=>s.forex_rows.push({...s.forex_rows[0]}),s=>s.forex_rows[0].code="999999",s=>s.forex_rows[0].asset_long=1001,s=>s.forex_rows[0].first_seen_at="2026-11-20T16:10:00Z"]){
  h=harness({snapshot:()=>{const s=snap();change(s);return JSON.stringify(s)}});r=await h.handler(req,{});ok(r.status===503&&h.counts().join()==="1,1"&&!r.body.includes("fixture-secret"));
 }
 for(const snapshot of [()=>"{",()=>null,()=>"x".repeat(8193),()=>'"'+"é".repeat(4096)+'"',()=>{throw Error("mock store failure")}]){h=harness({snapshot});r=await h.handler(req,{});ok(r.status===503&&h.counts().join()==="1,1")}
 for(const altered of [{...profile,generation:"g2"},{...profile,subject:"fixture-b"},{...profile,can_read:false},null]){
  h=harness({auth:(ctx,i)=>i===1?profile:altered});r=await h.handler(req,{});ok(r.status===403&&h.counts().join()==="2,1"&&r.body==='{"error":"UNAVAILABLE"}');
 }
 h=harness();const first=await h.handler(req,{}),second=await h.handler(req,{});ok(first.body===second.body&&h.counts().join()==="4,2");
 h=harness({snapshot:()=>JSON.stringify({...snap(),prices:[],forex_rows:[]})});r=await h.handler(req,{});ok(r.status===200&&JSON.parse(r.body).cot.every(x=>x.status==="UNAVAILABLE"));
 let badOrigin=false;try{build({origin:"https://production.invalid",clock:()=>now,authorize:async()=>profile,readSnapshot:async()=>"",projectPrices,projectForex})}catch{badOrigin=true}ok(badOrigin);
 return n;
}
console.log('REMURA_DISTRIBUTOR_FIXTURE_PASS='+await suite(buildDistributor,projectApproved,forexCotFixture));
