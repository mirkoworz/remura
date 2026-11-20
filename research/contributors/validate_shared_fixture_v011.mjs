// REMURA Experience v0.11 LAB — 20/11/2026 17:13 CET
// Client-side fixture envelope validation; does not authenticate the server or establish market provenance.
export function validateSharedFixture(x,now){
 const deny=()=>{throw Error("VIEW_REJECTED")};
 const keys=(o,k)=>o!==null&&typeof o==="object"&&Object.getPrototypeOf(o)===Object.prototype&&Object.keys(o).length===k.length&&k.every(p=>Object.hasOwn(o,p));
 const stamp=s=>typeof s==="string"&&/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$/.test(s)&&Number.isFinite(Date.parse(s))&&new Date(Date.parse(s)).toISOString().replace(".000Z","Z")===s;
 const day=s=>typeof s==="string"&&/^\d{4}-\d\d-\d\d$/.test(s)&&stamp(s+"T00:00:00Z");
 const pairs=["EURUSD","GBPUSD","AUDUSD","NZDUSD","USDJPY","USDCAD","USDCHF","EURGBP","EURJPY","EURCHF","EURCAD","EURAUD","EURNZD","GBPJPY","GBPCHF","GBPCAD","GBPAUD","GBPNZD","AUDJPY","AUDCHF","AUDCAD","AUDNZD","NZDJPY","NZDCAD","NZDCHF","CADJPY","CADCHF","CHFJPY"];
 const codes={EUR:"099741",GBP:"096742",JPY:"097741",AUD:"232741",CAD:"090741",CHF:"092741",NZD:"112741"};
 if(!keys(x,["schema","revision","as_of","synthetic","scientific_admission","prices","cot","sentiment","delta"])||x.schema!=="REMURA_SHARED_VIEW_FIXTURE_V1"||!Number.isSafeInteger(x.revision)||x.revision<1||x.synthetic!==true||x.scientific_admission!==false||!stamp(x.as_of)||!Number.isSafeInteger(now)||now<Date.parse(x.as_of)||now-Date.parse(x.as_of)>15*60000||!Array.isArray(x.prices)||x.prices.length>5||!Array.isArray(x.cot)||x.cot.length!==28||!keys(x.sentiment,["myfxbook","capital"])||x.sentiment.myfxbook!=="UNAVAILABLE"||x.sentiment.capital!=="UNAVAILABLE"||x.delta!=="UNAVAILABLE")deny();
 const seen=new Set();
 const prices=x.prices.map(r=>{
  if(!keys(r,["instrument","price","observed_at","source","freshness"])||!["EURUSD","GBPUSD","USDJPY","XAUUSD","NAS100"].includes(r.instrument)||seen.has(r.instrument)||typeof r.price!=="number"||!Number.isFinite(r.price)||r.price<0.000001||r.price>1e7||!stamp(r.observed_at)||r.observed_at>x.as_of||r.source!=="FIXTURE_PRICE"||!["STALE","WITHIN_DEMO_WINDOW"].includes(r.freshness))deny();
  seen.add(r.instrument);
  return {instrument:r.instrument,price:r.price,observed_at:r.observed_at,source:r.source,freshness:r.freshness==="STALE"||now-Date.parse(r.observed_at)>15*60000?"STALE":"WITHIN_DEMO_WINDOW"};
 });
 const cot=x.cot.map((r,i)=>{
  const common=["pair","status","asset_gap","leveraged_gap","synthetic","scientific_admission"];
  if(!r||r.pair!==pairs[i]||r.synthetic!==true||r.scientific_admission!==false)deny();
  if(r.status==="UNAVAILABLE"){
   if(!keys(r,common)||r.asset_gap!==null||r.leveraged_gap!==null)deny();
   return {pair:r.pair,status:r.status,asset_gap:null,leveraged_gap:null,synthetic:true,scientific_admission:false};
  }
  const expected=[r.pair.slice(0,3),r.pair.slice(3)].filter(c=>c!=="USD").map(c=>codes[c]);
  if(!keys(r,[...common,"report_date","legs","unit","usd_baseline","publication_at"])||!["STALE","FIXTURE"].includes(r.status)||!day(r.report_date)||r.report_date>x.as_of.slice(0,10)||r.status!==(Date.parse(x.as_of)-Date.parse(r.report_date+"T00:00:00Z")>=15*86400000?"STALE":"FIXTURE")||![r.asset_gap,r.leveraged_gap].every(v=>typeof v==="number"&&Number.isFinite(v)&&Math.abs(v)<=100*expected.length)||r.unit!=="PERCENTAGE_POINTS_OF_OI_DIFFERENCE"||r.usd_baseline!=="MATHEMATICAL_ZERO"||r.publication_at!==null||!Array.isArray(r.legs)||r.legs.length!==expected.length)deny();
  const legs=r.legs.map((l,j)=>{if(!keys(l,["code","first_seen_at"])||l.code!==expected[j]||!(l.first_seen_at===null||stamp(l.first_seen_at)&&l.first_seen_at<=x.as_of&&l.first_seen_at.slice(0,10)>=r.report_date))deny();return {code:l.code,first_seen_at:l.first_seen_at}});
  return {pair:r.pair,status:r.status,asset_gap:r.asset_gap,leveraged_gap:r.leveraged_gap,report_date:r.report_date,legs,unit:r.unit,usd_baseline:r.usd_baseline,publication_at:null,synthetic:true,scientific_admission:false};
 });
 return {schema:x.schema,revision:x.revision,as_of:x.as_of,synthetic:true,scientific_admission:false,prices,cot,sentiment:{myfxbook:"UNAVAILABLE",capital:"UNAVAILABLE"},delta:"UNAVAILABLE"};
}
