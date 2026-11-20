// REMURA Experience v0.7 LAB — 20/11/2026 CET
import {projectApproved} from './approved_projection_v07.mjs';
function runChecks(projectApproved){
 const now=Date.parse("2026-11-20T16:00:00Z"), base=()=>({schema:"REMURA_APPROVED_FIXTURE_V1",as_of:"2026-11-20T15:59:00Z",prices:[{instrument:"EURUSD",price:1,observed_at:"2026-11-20T15:55:00Z",source:"FIXTURE_PRICE"}],cot:[{instrument:"EURUSD",long:100,short:80,report_at:"2026-11-17T00:00:00Z",published_at:"2026-11-20T15:30:00Z",source:"FIXTURE_COT"}]});
 let count=0;const check=v=>{if(!v)throw Error("test_failed");count++};
 const p=projectApproved(base(),now);check(p.synthetic===true&&p.scientific_admission===false&&p.cot[0].net===20);check(p.prices[0].freshness==="WITHIN_DEMO_WINDOW");
 const stale=base();stale.prices[0].observed_at="2026-11-20T14:00:00Z";check(projectApproved(stale,now).prices[0].freshness==="STALE");
 const empty=base();empty.prices=[];empty.cot=[];check(projectApproved(empty,now).prices.length===0);
 for(const mutate of [x=>x.secret="fake",x=>x.prices[0].url="fake",x=>x.cot[0].raw_json="fake",x=>x.prices[0].instrument="OTHER",x=>x.prices[0].price=NaN,x=>x.prices[0].price=-1,x=>x.prices[0].observed_at="2026-11-20T16:00:00Z",x=>x.cot[0].published_at="2026-11-21T00:00:00Z",x=>x.cot[0].long=1.2,x=>x.prices.push({...x.prices[0]}),x=>x.cot.push({...x.cot[0]}),x=>x.as_of="2026-02-30T00:00:00Z",x=>x.cot[0].source="OTHER",x=>x.schema="LIVE",x=>x.prices[0].source="OTHER",x=>x.cot[0].report_at="2026-11-20T15:45:00Z"]){
  const x=base();mutate(x);let denied=false;try{projectApproved(x,now)}catch(e){denied=e.message==="PROJECTION_DENIED"}check(denied);
 }
 return count;
}
console.log('REMURA_PROJECTION_TESTS_PASS='+runChecks(projectApproved));
