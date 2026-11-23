/* REMURA Filone B, ricerca v20.7 — 23/11/2026 (Europe/Rome).
 * Trasformazione COT Futures Only OFFLINE. Nessun fetch, DB, deploy o ordine.
 * firstSeenAt = acquisizione locale; NON data di pubblicazione CFTC.
 */
(function(root){"use strict";
const api=(function engine(){
"use strict";
const FX=Object.freeze({EUR:"099741",GBP:"096742",JPY:"097741",AUD:"232741",CAD:"090741",CHF:"092741",NZD:"112741"});
const PAIRS=Object.freeze(["EURUSD","GBPUSD","AUDUSD","NZDUSD","USDJPY","USDCAD","USDCHF","EURGBP","EURJPY","EURCHF","EURCAD","EURAUD","EURNZD","GBPJPY","GBPCHF","GBPCAD","GBPAUD","GBPNZD","AUDJPY","AUDCAD","AUDCHF","AUDNZD","NZDJPY","NZDCAD","NZDCHF","CADJPY","CADCHF","CHFJPY"]);
const DIRECT=Object.freeze({
 XAUUSD:["disagg","088691","COMEX Gold futures"],XAGUSD:["disagg","084691","COMEX Silver futures"],
 USOIL:["disagg","067651","NYMEX WTI futures"],US500:["tff","13874A","CME E-mini S&P 500 futures"],
 NAS100:["tff","209742","CME E-mini Nasdaq-100 futures"],US30:["tff","124603","CBOT E-mini Dow futures"],
 DXY:["tff","098662","ICE US Dollar Index futures"]
});
const SOURCES=Object.freeze({
 tff:{id:"gpe5-46if",labels:["Asset Manager/Institutional","Leveraged Funds"],cols:["asset_mgr_positions_long","asset_mgr_positions_short","lev_money_positions_long","lev_money_positions_short"]},
 disagg:{id:"72hh-3qpy",labels:["Managed Money","Producer/Merchant"],cols:["m_money_positions_long_all","m_money_positions_short_all","prod_merc_positions_long","prod_merc_positions_short"]}
});
const CODES=new Set([...Object.values(FX),...Object.values(DIRECT).map(v=>v[1])]);
function validDate(s){
 if(typeof s!=="string")return null;
 const d=s.slice(0,10),t=Date.parse(d+"T00:00:00Z");
 return /^\d{4}-\d{2}-\d{2}$/.test(d)&&Number.isFinite(t)&&new Date(t).toISOString().slice(0,10)===d?d:null;
}
function stamp(s){
 if(typeof s!=="string"||!/(Z|[+-]\d{2}:\d{2})$/.test(s))return null;
 const t=Date.parse(s);return Number.isFinite(t)?t:null;
}
function num(s,positive=false){
 if(s==null||typeof s==="boolean"||typeof s==="object"||typeof s==="string"&&!s.trim())return null;
 const x=Number(s);return Number.isFinite(x)&&x<=1e11&&(positive?x>0:x>=0)?x:null;
}
function market(symbol){
 if(typeof symbol!=="string")return null;
 const s=symbol.toUpperCase();
 if(Object.hasOwn(DIRECT,s)){const [dataset,code,underlying]=DIRECT[s];
  return {symbol:s,type:"futures_reference",dataset,codes:[code],underlying};}
 if(!PAIRS.includes(s))return null;
 const base=s.slice(0,3),quote=s.slice(3);
 return {symbol:s,type:"synthetic_fx_relative",dataset:"tff",base,quote,
  codes:[...new Set([FX[base],FX[quote]].filter(Boolean))],
  underlying:"Futures FX per "+base+" e "+quote+" contro USD"};
}
function parseRows(rows,asOf=null){
 if(!Array.isArray(rows)||rows.length>50000)throw new TypeError("INVALID_CFTC_BATCH");
 const all=new Map();let rejected=0;
 for(const x of rows){
  if(!x||typeof x!=="object"){rejected++;continue;}
  const dataset=x.dataset,code=String(x.code??x.cftc_contract_market_code??"").toUpperCase();
  if(!SOURCES[dataset]||!CODES.has(code))continue;
  const c=SOURCES[dataset].cols;
  const date=validDate(x.reportDate??x.report_date??x.report_date_as_yyyy_mm_dd);
  const oi=num(x.openInterest??x.oi??x.open_interest_all,true);
  const quantities=[x.aLong??x.first_long??x[c[0]],x.aShort??x.first_short??x[c[1]],
   x.bLong??x.second_long??x[c[2]],x.bShort??x.second_short??x[c[3]]].map(v=>num(v));
  const seenRaw=x.firstSeenAt??x.first_seen_at??null,seen=seenRaw===null?null:stamp(seenRaw);
  if(!date||oi===null||quantities.some(q=>q===null||q>2*oi)||(seenRaw!==null&&seen===null)){rejected++;continue;}
  const key=dataset+"|"+code+"|"+date,signature=JSON.stringify([oi,...quantities,seen]);
  if(all.has(key)){if(all.get(key).signature!==signature)throw Error("CONFLICTING_CFTC_ROWS:"+key);continue;}
  all.set(key,{date,dataset,code,oi,aLong:quantities[0],aShort:quantities[1],
   bLong:quantities[2],bShort:quantities[3],seen,signature});
 }
 const indexed=new Map();let excluded=0;
 for(const x of all.values()){
  if(asOf!==null&&(x.seen===null||x.seen>asOf||Date.parse(x.date+"T00:00:00Z")>asOf)){excluded++;continue;}
  const id=x.dataset+"|"+x.code;
  if(!indexed.has(id))indexed.set(id,new Map());
  indexed.get(id).set(x.date,x);
 }
 return {indexed,rejected,excluded,valid:all.size};
}
function net(r,side){return r?100*((side==="a"?r.aLong-r.aShort:r.bLong-r.bShort)/r.oi):0;}
function dayGap(a,b){return (Date.parse(a+"T00:00:00Z")-Date.parse(b+"T00:00:00Z"))/86400000;}
function cotIndex(values){
 if(values.length<2||values.some(v=>!Number.isFinite(v)))return null;
 const min=Math.min(...values),max=Math.max(...values),current=values.at(-1);
 return min===max?null:{value:100*(current-min)/(max-min),min,max,current,
  empiricalPercentile:100*values.filter(v=>v<=current).length/values.length};
}
function evaluate(rows,symbol,options={}){
 const m=market(symbol);
 if(!m)return {state:"unsupported",symbol:String(symbol),reason:"Mappatura futures assente"};
 const asOf=options.observedAt==null?null:stamp(options.observedAt);
 if(options.observedAt!=null&&asOf===null)throw TypeError("INVALID_OBSERVATION_TIME");
 const window=options.window??52;
 if(![26,52,156,260].includes(window))throw RangeError("INVALID_WINDOW");
 const {indexed,rejected,excluded,valid}=parseRows(rows,asOf);
 if(rejected)return {state:"invalid_rows",symbol:m.symbol,rejected,
  reason:"Input CFTC non valido; nessun riempimento automatico"};
 const get=code=>indexed.get(m.dataset+"|"+code)||new Map();
 let dates=[],legs={},build;
 if(m.type==="futures_reference"){
  legs.direct=get(m.codes[0]);dates=[...legs.direct.keys()];
  build=d=>{const r=legs.direct.get(d);return {date:d,a:net(r,"a"),b:net(r,"b"),oi:r.oi,parts:[r]};};
 } else {
  for(const c of [m.base,m.quote])if(c!=="USD")legs[c]=get(FX[c]);
  const needed=Object.keys(legs);
  if(needed.some(c=>legs[c].size===0))return {
   state:asOf===null?"missing_leg":"unverified_or_unavailable",symbol:m.symbol,
   needed:needed.map(c=>FX[c]),excluded,reason:"Gamba CFTC non disponibile e verificabile"};
  const newest=needed.map(c=>[...legs[c].keys()].sort().at(-1));
  if(new Set(newest).size!==1)return {state:"misaligned_latest",symbol:m.symbol,
   latestLegReports:Object.fromEntries(needed.map((c,i)=>[c,newest[i]])),
   reason:"Gambe valutarie non allineate nell'ultima settimana"};
  dates=[...legs[needed[0]].keys()].filter(d=>needed.every(c=>legs[c].has(d)));
  build=d=>{
   const base=m.base==="USD"?null:legs[m.base].get(d);
   const quote=m.quote==="USD"?null:legs[m.quote].get(d);
   return {date:d,a:net(base,"a")-net(quote,"a"),b:net(base,"b")-net(quote,"b"),
    oi:null,parts:[base,quote].filter(Boolean)};
  };
 }
 if(!dates.length)return {state:asOf===null?"no_data":"unverified_or_unavailable",symbol:m.symbol,
  excluded,valid,reason:"Nessun report disponibile al momento richiesto"};
 const sequence=dates.sort().map(build),now=sequence.at(-1),before=sequence.at(-2);
 const adjacent=!!before&&dayGap(now.date,before.date)>=5&&dayGap(now.date,before.date)<=9;
 const change=adjacent?{aPp:now.a-before.a,bPp:now.b-before.b,
  gapPp:(now.a-now.b)-(before.a-before.b),
  openInterestContracts:m.type==="futures_reference"?now.oi-before.oi:null}:null;
 const tail=sequence.slice(-window);
 const contiguous=sequence.length>=window&&tail.slice(1).every((r,i)=>{
  const diff=dayGap(r.date,tail[i].date);return diff>=5&&diff<=9;
 });
 const relative=contiguous?{a:cotIndex(tail.map(x=>x.a)),b:cotIndex(tail.map(x=>x.b)),
  gap:cotIndex(tail.map(x=>x.a-x.b))}:null;
 const relation=now.a*now.b<0?"categorie_opposte":now.a*now.b>0?"categorie_concordi":"neutre_o_miste";
 return {state:adjacent?"ready":"no_adjacent_week",symbol:m.symbol,
  dataset:m.dataset,datasetId:SOURCES[m.dataset].id,type:m.type,underlying:m.underlying,
  codes:m.codes,mode:asOf===null?"descriptive_only":"first_local_capture_asof",
  reportDate:now.date,previousReportDate:adjacent?before.date:null,
  labels:SOURCES[m.dataset].labels,netPercentOI:{a:now.a,b:now.b},
  categoryGapPp:now.a-now.b,categoryRelationship:relation,
  weeklyChange:change,openInterestContracts:now.oi,
  relative:{window,available:sequence.length,
   state:relative?"ok":sequence.length<window?"insufficient":"gapped_history",values:relative},
  provenance:now.parts.map(x=>({code:x.code,firstLocalCaptureUtc:x.seen===null?null:new Date(x.seen).toISOString()})),
  excludedByAsOf:excluded,
  caveats:["COT ufficiale settimanale, non flussi istituzionali live",
   "Categoria non equivale a strategia e non dimostra ordini futuri",
   m.type==="synthetic_fx_relative"?"Cross sintetico in net%/OI, non posizioni spot; USD=0 è convenzione":"Il future non è il CFD o spot del broker",
   asOf===null?"Data di pubblicazione non attestata":"La prima cattura locale non attesta la pubblicazione CFTC"]
 };
}
return {evaluate,market,parseRows,cotIndex,FX,PAIRS,DIRECT,SOURCES};
})();
if(typeof module!=="undefined"&&module.exports)module.exports=api;
if(root)root.REMURA_COT_INTELLIGENCE=api;
})(typeof window!=="undefined"?window:null);
