/* REMURA Filone B v20.8 LAB — 23/11/2026 Europe/Rome.
 * Pure CFTC weekly watchlist and coverage gates; offline only.
 * Independent lanes and deterministic ordering, NO prediction/price engine.
 */
(function(root){"use strict";
const core=typeof module!=="undefined"&&module.exports?require("./cot-intelligence-core.js"):root.REMURA_COT_INTELLIGENCE;
const api=(function watchFactory(core){
 "use strict";
 const EXPECTED={
  tff:[...new Set([...Object.values(core.FX),...Object.values(core.DIRECT).filter(x=>x[0]==="tff").map(x=>x[1])])].sort(),
  disagg:[...new Set(Object.values(core.DIRECT).filter(x=>x[0]==="disagg").map(x=>x[1]))].sort()
 };
 const GROUPS=[
  {id:"fx_relative",dataset:"tff",symbols:[...core.PAIRS],label:"Cross Forex sintetici"},
  {id:"tff_futures",dataset:"tff",symbols:Object.keys(core.DIRECT).filter(s=>core.DIRECT[s][0]==="tff").sort(),label:"Futures finanziari"},
  {id:"disagg_futures",dataset:"disagg",symbols:Object.keys(core.DIRECT).filter(s=>core.DIRECT[s][0]==="disagg").sort(),label:"Futures fisici"}
 ];
 const UNSUPPORTED=["GER30","VIX","UKOIL"];
 const stamp=x=>typeof x==="string"&&/(Z|[+-]\d{2}:\d{2})$/.test(x)&&Number.isFinite(Date.parse(x))?Date.parse(x):null;
 const days=(a,b)=>(Date.parse(a+"T00:00:00Z")-Date.parse(b+"T00:00:00Z"))/86400000;
 function build(snapshot,options={}){
  const now=stamp(options.nowUtc);
  if(now===null)throw TypeError("NOW_UTC_REQUIRED");
  const asOf=options.observedAt==null?null:stamp(options.observedAt);
  if(options.observedAt!=null&&asOf===null)throw TypeError("INVALID_OBSERVED_AT");
  if(asOf!==null&&asOf>now)throw RangeError("FUTURE_OBSERVATION");
  const window=options.window??52;
  if(![26,52,156,260].includes(window))throw RangeError("INVALID_COT_WINDOW");
  if(!snapshot||snapshot.schema!=="remura-cot-intelligence-snapshot-v1"||
     snapshot.source!=="existing_private_cftc_cache"||
     snapshot.captureClock!=="first_local_capture_not_official_publication"||
     !Array.isArray(snapshot.rows)||snapshot.rowCount!==snapshot.rows.length||
     snapshot.truncated!==false)throw TypeError("INVALID_OR_TRUNCATED_SNAPSHOT");
  const checked=core.parseRows(snapshot.rows,asOf);
  if(checked.rejected>0)throw Error("INVALID_CFTC_ROWS:"+checked.rejected);
  if(checked.valid===0) return {
   schema:"remura-cot-watchlist-v1",state:"no_data",mode:asOf===null?"descriptive_only":"capture_asof",
   nowUtc:new Date(now).toISOString(),observedAt:asOf===null?null:new Date(asOf).toISOString(),
   source:"CFTC Futures Only (existing offline cache)",periods:{},groups:[],unsupported:UNSUPPORTED,
   notes:["Nessun dato CFTC utilizzabile; nessuna classifica"]
  };
  const all=core.parseRows(snapshot.rows,null);
  for(const table of all.indexed.values()){
   for(const row of table.values()){
    const report=Date.parse(row.date+"T00:00:00Z");
    if(report>now||row.seen!==null&&row.seen>now+5*60000)
       throw Error("CFTC_FUTURE_CLOCK");
   }
  }
  const periods={};
  for(const dataset of Object.keys(EXPECTED)){
   const expected=EXPECTED[dataset],byWeek=new Map();
   for(const code of expected){
    const items=checked.indexed.get(dataset+"|"+code);
    if(!items)continue;
    for(const date of items.keys()){
     if(!byWeek.has(date))byWeek.set(date,new Set());
     byWeek.get(date).add(code);
    }
   }
   const sorted=[...byWeek.keys()].sort().reverse();
   const latest=sorted[0]??null,previous=sorted[1]??null;
   const have=latest?[...byWeek.get(latest)]:[];
   const prevHave=previous?[...byWeek.get(previous)]:[];
   const missingLatest=expected.filter(code=>!have.includes(code));
   const missingPrevious=expected.filter(code=>!prevHave.includes(code));
   const reportAgeDays=latest?days(new Date(now).toISOString().slice(0,10),latest):null;
   const intervalDays=latest&&previous?days(latest,previous):null;
   let state;
   if(!latest)state="no_data";
   else if(missingLatest.length)state="incomplete_latest";
   else if(!previous||missingPrevious.length)state="incomplete_previous";
   else if(intervalDays<5||intervalDays>9)state="cadence_review";
   else if(reportAgeDays>14)state="stale";
   else state="complete";
   periods[dataset]={state,latest,previous,expected:expected.length,
    latestPresent:have.length,previousPresent:prevHave.length,
    missingLatest,missingPrevious,reportAgeDays,intervalDays};
  }
  const groupResults=[];
  for(const group of GROUPS){
   const period=periods[group.dataset];
   if(period.state!=="complete"){
    groupResults.push({id:group.id,label:group.label,dataset:group.dataset,
     state:"blocked",reason:period.state,entries:[],considered:group.symbols.length});
    continue;
   }
   const entries=[],issues=[];
   for(const symbol of group.symbols){
    const r=core.evaluate(snapshot.rows,symbol,{window,...(asOf===null?{}:{observedAt:options.observedAt})});
    if(r.state!=="ready"||r.reportDate!==period.latest){
     issues.push({symbol,state:r.state});continue;
    }
    if(!r.weeklyChange||!Number.isFinite(r.weeklyChange.aPp)){
     issues.push({symbol,state:"invalid_weekly_change"});continue;
    }
    const change=r.weeklyChange.aPp;
    const exposures=group.id==="fx_relative"?
      [symbol.slice(0,3),symbol.slice(3)].filter(x=>x!=="USD"):
      ["US500","NAS100","US30"].includes(symbol)?["US_equity"]:
      symbol==="DXY"?["US_dollar_index"]:
      ["XAUUSD","XAGUSD"].includes(symbol)?["precious_metals"]:["energy_WTI"];
    entries.push({
     symbol,reportDate:r.reportDate,referenceType:r.type,
     dataset:r.dataset,codes:r.codes,
     categoryA:r.labels[0],categoryB:r.labels[1],
     netA_Pp:r.netPercentOI.a,netB_Pp:r.netPercentOI.b,
     deltaA_Pp:change,deltaB_Pp:r.weeklyChange.bPp,
     categoryGapPp:r.categoryGapPp,deltaGapPp:r.weeklyChange.gapPp,
     relationship:r.categoryRelationship,
     historicalIndex52:window===52&&r.relative?.state==="ok"?{
       a:r.relative.values?.a?.value??null,
       b:r.relative.values?.b?.value??null,
       gap:r.relative.values?.gap?.value??null}:null,
     relativeStatus:r.relative.state,firstLocalCaptureUtc:r.provenance.map(p=>p.firstLocalCaptureUtc),
     exposureTags:exposures,
     observationMode:r.mode,
     evidence:"CFTC aggregated futures positioning (weekly), not price or executed flows"
    });
   }
   entries.sort((a,b)=>Math.abs(b.deltaA_Pp)-Math.abs(a.deltaA_Pp)||a.symbol.localeCompare(b.symbol));
   groupResults.push({id:group.id,label:group.label,dataset:group.dataset,
    state:asOf===null?"descriptive":"capture_asof",
    ordering:"|weekly change net% OI of category A| descending; NOT prediction",
    entries,issues,considered:group.symbols.length});
  }
  const nonempty=groupResults.some(g=>g.entries.length);
  return {schema:"remura-cot-watchlist-v1",
    state:nonempty?"descriptive_ready":"insufficient",
    mode:asOf===null?"descriptive_only":"first_local_capture_asof",
    nowUtc:new Date(now).toISOString(),
    observedAt:asOf===null?null:new Date(asOf).toISOString(),
    source:"CFTC Futures Only via existing private offline cache",
    contractCoverage:EXPECTED,periods,groups:groupResults,unsupported:UNSUPPORTED,
    notes:[
     "Ordine descrittivo per ampiezza, NON segnale di acquisto/vendita né stima di rendimento",
     "Gruppi futures e cross FX tenuti separati: nessuna classifica unica",
     "Cross Forex derivati da due futures USD, non posizionamento spot diretto",
     "28 coppie FX condividono 7 futures valutari: osservazioni NON indipendenti",
     "As-of basato solo su prima acquisizione locale; non prova l'orario ufficiale CFTC",
     "Una futura pubblicazione CFTC bisettimanale attiva deve essere riconosciuta prima di adattare la definizione del confronto"
    ]
  };
 }
 return {build,EXPECTED,GROUPS,UNSUPPORTED};
})(core);
if(typeof module!=="undefined"&&module.exports)module.exports=api;
if(root)root.REMURA_COT_WATCHLIST=api;
})(typeof window!=="undefined"?window:null);
