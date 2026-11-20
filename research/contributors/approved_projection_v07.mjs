// REMURA Experience v0.7 LAB — 20/11/2026 CET
// Pure fixture-only projection; no network, storage, privileges, or actual market data.
// This is a candidate data contract, not authorization or a production sanitizer.
export function projectApproved(input, nowMs) {
 const reject=()=>{throw Error("PROJECTION_DENIED")};
 const plain=o=>o!==null&&typeof o==="object"&&Object.getPrototypeOf(o)===Object.prototype;
 const keys=(o,expected)=>plain(o)&&Object.keys(o).length===expected.length&&expected.every(k=>Object.hasOwn(o,k));
 const finite=(x,min,max)=>typeof x==="number"&&Number.isFinite(x)&&x>=min&&x<=max;
 const stamp=x=>typeof x==="string"&&/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$/.test(x)&&Number.isFinite(Date.parse(x))&&new Date(Date.parse(x)).toISOString().replace(".000Z","Z")===x;
 const universe=["EURUSD","GBPUSD","USDJPY","XAUUSD","NAS100"];
 if(!Number.isSafeInteger(nowMs)||nowMs<0||!keys(input,["schema","as_of","prices","cot"])||input.schema!=="REMURA_APPROVED_FIXTURE_V1"||!stamp(input.as_of)||Date.parse(input.as_of)>nowMs)reject();
 const asOf=Date.parse(input.as_of);
 if(!Array.isArray(input.prices)||input.prices.length>universe.length||!Array.isArray(input.cot)||input.cot.length>universe.length)reject();
 let seen=new Set();
 const prices=input.prices.map(r=>{
  if(!keys(r,["instrument","price","observed_at","source"])||!universe.includes(r.instrument)||seen.has(r.instrument)||!finite(r.price,0.000001,10000000)||!stamp(r.observed_at)||Date.parse(r.observed_at)>asOf||r.source!=="FIXTURE_PRICE")reject();
  seen.add(r.instrument);
  return {instrument:r.instrument,price:r.price,observed_at:r.observed_at,source:"FIXTURE_PRICE",freshness:nowMs-Date.parse(r.observed_at)>15*60000?"STALE":"WITHIN_DEMO_WINDOW"};
 });
 seen=new Set();
 const cot=input.cot.map(r=>{
  if(!keys(r,["instrument","long","short","report_at","published_at","source"])||!["EURUSD","GBPUSD","USDJPY"].includes(r.instrument)||seen.has(r.instrument)||![r.long,r.short].every(n=>Number.isSafeInteger(n)&&finite(n,0,100000000))||!stamp(r.report_at)||!stamp(r.published_at)||Date.parse(r.report_at)>Date.parse(r.published_at)||Date.parse(r.published_at)>asOf||r.source!=="FIXTURE_COT")reject();
  seen.add(r.instrument);
  return {instrument:r.instrument,long:r.long,short:r.short,net:r.long-r.short,report_at:r.report_at,published_at:r.published_at,source:"FIXTURE_COT",freshness:nowMs-Date.parse(r.published_at)>10*86400000?"STALE":"WITHIN_DEMO_WINDOW"};
 });
 return {schema:"REMURA_PUBLIC_VIEW_FIXTURE_V1",as_of:input.as_of,prices,cot,synthetic:true,scientific_admission:false};
}
