// REMURA Experience v0.8 LAB — 20/11/2026 CET
// Synthetic forex only. Exact contract map from forex.html source checkpoint 32188ca. No actual reads, publication inference, or institutional spot attribution.
export function forexCotFixture(pair, rows, asOf){
 const fail=()=>{throw Error("COT_FIXTURE_DENIED")};
 const code={EUR:"099741",GBP:"096742",JPY:"097741",AUD:"232741",CAD:"090741",CHF:"092741",NZD:"112741"};
 const date=x=>typeof x==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x))&&new Date(Date.parse(x)).toISOString().slice(0,10)===x;
 const stamp=x=>typeof x==="string"&&/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$/.test(x)&&Number.isFinite(Date.parse(x))&&new Date(Date.parse(x)).toISOString().replace(".000Z","Z")===x;
 if(!["EURUSD","GBPUSD","AUDUSD","NZDUSD","USDJPY","USDCAD","USDCHF","EURGBP","EURJPY","EURCHF","EURCAD","EURAUD","EURNZD","GBPJPY","GBPCHF","GBPCAD","GBPAUD","GBPNZD","AUDJPY","AUDCHF","AUDCAD","AUDNZD","NZDJPY","NZDCAD","NZDCHF","CADJPY","CADCHF","CHFJPY"].includes(pair)||!stamp(asOf)||!Array.isArray(rows))fail();
 const base=pair.slice(0,3),quote=pair.slice(3),legs=[base,quote].filter(x=>x!=="USD");
 if(base===quote||!legs.length||legs.some(x=>!Object.hasOwn(code,x))||rows.length>2)fail();
 const fields=["dataset","code","report_date","first_seen_at","oi","asset_long","asset_short","leveraged_long","leveraged_short"];
 const byCode=new Map();
 for(const r of rows){
  if(!r||Object.getPrototypeOf(r)!==Object.prototype||Object.keys(r).length!==fields.length||!fields.every(k=>Object.hasOwn(r,k))||r.dataset!=="TFF_FIXTURE"||!legs.some(x=>code[x]===r.code)||byCode.has(r.code)||!date(r.report_date)||!Number.isSafeInteger(r.oi)||r.oi<=0||r.oi>1e11)fail();
  if(!fields.slice(5).every(k=>Number.isSafeInteger(r[k])&&r[k]>=0&&r[k]<=r.oi))fail();
  if(r.report_date>asOf.slice(0,10)||!(r.first_seen_at===null||stamp(r.first_seen_at)&&r.first_seen_at<=asOf&&r.first_seen_at.slice(0,10)>=r.report_date))fail();
  byCode.set(r.code,r);
 }
 const missing=()=>({pair,status:"UNAVAILABLE",asset_gap:null,leveraged_gap:null,synthetic:true,scientific_admission:false});
 if(legs.some(x=>!byCode.has(code[x])))return missing();
 const rs=legs.map(x=>byCode.get(code[x]));if(rs.some(r=>r.report_date!==rs[0].report_date))return missing();
 const net=(ccy,group)=>{if(ccy==="USD")return 0;const r=byCode.get(code[ccy]);return 100*(r[group+"_long"]-r[group+"_short"])/r.oi};
 return {pair,status:Date.parse(asOf)-Date.parse(rs[0].report_date+"T00:00:00Z")>=15*86400000?"STALE":"FIXTURE",report_date:rs[0].report_date,legs:rs.map(r=>({code:r.code,first_seen_at:r.first_seen_at})),asset_gap:net(base,"asset")-net(quote,"asset"),leveraged_gap:net(base,"leveraged")-net(quote,"leveraged"),unit:"PERCENTAGE_POINTS_OF_OI_DIFFERENCE",usd_baseline:"MATHEMATICAL_ZERO",publication_at:null,synthetic:true,scientific_admission:false};
}
