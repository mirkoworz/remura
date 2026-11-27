/* REMURA Shark Cockpit v1.68 LAB — 22/11/2026 22:10 CET.
 * Official public weekly CFTC futures, with retail archived separately.
 * No new backend, no chart scraping, no institution identities, no signals.
 */
(function(root,factory){
  const api=factory();
  if(typeof module==="object"&&module.exports)module.exports=api;
  root.REMURA_SHARK_CORE=api;
})(typeof window!=="undefined"?window:globalThis,function(){
  "use strict";
  const DAY=86400000,WEEK=7*DAY;
  const CONTRACTS=Object.freeze([
    {code:"099741",id:"EUR",name:"Euro FX",family:"Valute",dataset:"tff"},
    {code:"096742",id:"GBP",name:"Sterlina britannica",family:"Valute",dataset:"tff"},
    {code:"097741",id:"JPY",name:"Yen giapponese",family:"Valute",dataset:"tff"},
    {code:"232741",id:"AUD",name:"Dollaro australiano",family:"Valute",dataset:"tff"},
    {code:"090741",id:"CAD",name:"Dollaro canadese",family:"Valute",dataset:"tff"},
    {code:"092741",id:"CHF",name:"Franco svizzero",family:"Valute",dataset:"tff"},
    {code:"112741",id:"NZD",name:"Dollaro neozelandese",family:"Valute",dataset:"tff"},
    {code:"13874A",id:"US500",name:"S&P 500 · E-mini",family:"Indici",dataset:"tff"},
    {code:"209742",id:"NAS100",name:"Nasdaq 100 · E-mini",family:"Indici",dataset:"tff"},
    {code:"124603",id:"US30",name:"Dow Jones · E-mini",family:"Indici",dataset:"tff"},
    {code:"098662",id:"DXY",name:"US Dollar Index",family:"Indici",dataset:"tff"},
    {code:"088691",id:"XAUUSD",name:"Oro · COMEX",family:"Metalli",dataset:"disagg"},
    {code:"084691",id:"XAGUSD",name:"Argento · COMEX",family:"Metalli",dataset:"disagg"},
    {code:"067651",id:"USOIL",name:"WTI · NYMEX",family:"Energia",dataset:"disagg"}
  ]);
  const FIELDS=Object.freeze({
    tff:["report_date_as_yyyy_mm_dd","cftc_contract_market_code","open_interest_all",
         "asset_mgr_positions_long","asset_mgr_positions_short",
         "lev_money_positions_long","lev_money_positions_short"],
    disagg:["report_date_as_yyyy_mm_dd","cftc_contract_market_code","open_interest_all",
            "m_money_positions_long_all","m_money_positions_short_all",
            "prod_merc_positions_long","prod_merc_positions_short"]
  });
  const DATASETS=Object.freeze({tff:"gpe5-46if",disagg:"72hh-3qpy"});
  const SOURCES=Object.freeze({
    tff:"https://publicreporting.cftc.gov/Commitments-of-Traders/TFF-Futures-Only/gpe5-46if",
    disagg:"https://publicreporting.cftc.gov/Commitments-of-Traders/Disaggregated-Futures-Only/72hh-3qpy"
  });
  const FX_RETAIL=Object.freeze(["EURUSD","GBPUSD","AUDUSD","NZDUSD","USDJPY","USDCAD","USDCHF"]);
  function strictDate(v){
    if(typeof v!=="string"||! /^\d{4}-\d{2}-\d{2}/.test(v))return null;
    const date=v.slice(0,10),ms=Date.parse(date+"T00:00:00Z");
    if(!Number.isFinite(ms)||new Date(ms).toISOString().slice(0,10)!==date)return null;
    return {date,ms};
  }
  function amount(v){
    if(v===null||v===undefined||v==="")return null;
    if(typeof v!=="number"&&typeof v!=="string")return null;
    const n=Number(v);
    return Number.isFinite(n)&&n>=0?n:null;
  }
  function normalized(row,dataset,now){
    if(!row||typeof row!=="object"||Array.isArray(row)||!FIELDS[dataset])return null;
    const stamp=strictDate(row.report_date_as_yyyy_mm_dd);
    const code=String(row.cftc_contract_market_code||"").toUpperCase().padStart(6,"0");
    const contract=CONTRACTS.find(c=>c.code===code&&c.dataset===dataset);
    if(!contract||!stamp||stamp.ms>now||new Date(stamp.ms).getUTCDay()!==2||((now-stamp.ms)>180*DAY))return null;
    const fields=dataset==="tff"?
      ["asset_mgr_positions_long","asset_mgr_positions_short","lev_money_positions_long","lev_money_positions_short"]:
      ["m_money_positions_long_all","m_money_positions_short_all","prod_merc_positions_long","prod_merc_positions_short"];
    const nums=fields.map(k=>amount(row[k])),oi=amount(row.open_interest_all);
    if(oi===null||oi<=0||nums.some(x=>x===null))return null;
    const a=100*(nums[0]-nums[1])/oi,b=100*(nums[2]-nums[3])/oi;
    if(!Number.isFinite(a)||!Number.isFinite(b)||Math.abs(a)>100.00001||Math.abs(b)>100.00001)return null;
    return {code,dataset,date:stamp.date,at:stamp.ms,oi,first:{long:nums[0],short:nums[1],net:a},
            second:{long:nums[2],short:nums[3],net:b}};
  }
  function same(a,b){
    return a.date===b.date&&a.oi===b.oi&&
      ["first","second"].every(k=>a[k].long===b[k].long&&a[k].short===b[k].short);
  }
  function parseRows(records,dataset,now=Date.now()){
    if(!FIELDS[dataset]||!Array.isArray(records)||records.length>3500||!Number.isFinite(now))throw Error("CFTC_BATCH_INVALID");
    const map=new Map(),conflicts=new Set();let valid=0,invalid=0;
    for(const raw of records){
      const row=normalized(raw,dataset,now);
      if(!row){invalid++;continue;}
      valid++;
      const key=row.code+"|"+row.date;
      if(map.has(key)&&!same(map.get(key),row))conflicts.add(row.code);
      else if(!map.has(key))map.set(key,row);
    }
    const byCode=new Map();
    for(const c of CONTRACTS.filter(c=>c.dataset===dataset)){
      const rows=[...map.values()].filter(r=>r.code===c.code).sort((a,b)=>b.at-a.at).slice(0,12);
      byCode.set(c.code,{rows,conflict:conflicts.has(c.code)});
    }
    return {dataset,byCode,valid,invalid,source:SOURCES[dataset],provenance:"CFTC_PUBLIC_BROWSER_FETCH_UNATTESTED_FIRST_SEEN"};
  }
  function round(n){return Number.isFinite(n)?Math.round(n*100)/100:null;}
  function changeSign(n){return n>0?"UP":n<0?"DOWN":"FLAT";}
  function card(c,parsed,now=Date.now()){
    const item=parsed&&parsed.byCode instanceof Map?parsed.byCode.get(c.code):null;
    const rows=item?.rows||[],cur=rows[0]||null,prev=rows[1]||null;
    const age=cur?Math.floor((now-cur.at)/DAY):null;
    let status=!cur?"UNKNOWN_NO_REPORT":item.conflict?"QUARANTINE_CONFLICT":
      age>14?"STALE_REPORT":"CURRENT_REPORT_DATE";
    const consecutive=!!(cur&&prev&&cur.at-prev.at===WEEK);
    let deltas=null,comparison="UNKNOWN",fourWeek=null;
    if(status==="CURRENT_REPORT_DATE"&&consecutive){
      deltas={first:round(cur.first.net-prev.first.net),second:round(cur.second.net-prev.second.net)};
      const sides=[changeSign(deltas.first),changeSign(deltas.second)];
      comparison=sides.includes("FLAT")?"FLAT_OR_MIXED":sides[0]===sides[1]?"CO_MOVING":"DIVERGENT";
      if(rows.length>=5&&rows.slice(0,5).every((r,i)=>i===0||rows[i-1].at-r.at===WEEK)){
        fourWeek={first:round(cur.first.net-rows[4].first.net),
                  second:round(cur.second.net-rows[4].second.net)};
      }
    } else if(status==="CURRENT_REPORT_DATE"&&!consecutive)status="UNKNOWN_WEEKLY_COMPARISON";
    return {
      id:c.id,code:c.code,name:c.name,family:c.family,dataset:c.dataset,
      labels:c.dataset==="tff"?["Asset Manager","Leveraged Funds"]:["Managed Money","Producer / Merchant"],
      source:SOURCES[c.dataset],reportDate:cur?.date||null,ageDays:age,status,
      first:cur?round(cur.first.net):null,second:cur?round(cur.second.net):null,
      openInterest:cur?cur.oi:null,deltas,fourWeek,comparison,
      availableWeeks:rows.length,publicationTimeVerified:false,
      independentlyWitnessed:false,individualInstitutionsKnown:false,
      realTimeMarketFlow:false,spotPairMappingVerified:false,tradingSignal:false
    };
  }
  /*
   * Weekly anatomy: changes in reported LONG/SHORT positions in contracts,
   * NOT proof of new buy/sell orders. CFTC first-publication time unknown.
   * Derivation uses exactly the two Tuesday snapshots already admitted by card().
   */
  function anatomyFor(contract,parsed,now=Date.now()){
    if(!contract||!CONTRACTS.some(c=>c.code===contract.code&&c.dataset===contract.dataset))
      return {status:"UNKNOWN_CONTRACT",categories:[],orderFlowVerified:false};
    const status=card(contract,parsed,now);
    if(status.status!=="CURRENT_REPORT_DATE"||status.deltas===null)
      return {status:status.status,categories:[],orderFlowVerified:false};
    const item=parsed?.byCode instanceof Map?parsed.byCode.get(contract.code):null;
    if(!item||item.conflict||!Array.isArray(item.rows)||item.rows.length<2)
      return {status:"UNKNOWN_SOURCE_HISTORY",categories:[],orderFlowVerified:false};
    const [cur,prev]=item.rows;
    if(!cur||!prev||cur.at-prev.at!==WEEK||cur.date!==status.reportDate)
      return {status:"UNKNOWN_WEEK_BOUNDARY",categories:[],orderFlowVerified:false};
    const groups=["first","second"].map((key,index)=>{
      const a=cur[key],b=prev[key];
      if(!a||!b||![a.long,a.short,b.long,b.short].every(Number.isFinite))return null;
      const longDelta=a.long-b.long,shortDelta=a.short-b.short;
      const netCurrent=a.long-a.short,netPrevious=b.long-b.short;
      return {label:status.labels[index],key,
        currentLong:a.long,currentShort:a.short,
        previousLong:b.long,previousShort:b.short,
        longDelta,shortDelta,
        netContracts:netCurrent,netDeltaContracts:netCurrent-netPrevious,
        netPpChange:status.deltas[key],
        /* Not possible to infer actual orders/openings/closings from two reports. */
        opensVerified:false,closesVerified:false,actorIdentityVerified:false};
    });
    if(groups.some(x=>x===null))return {status:"UNKNOWN_GROUP_COUNTS",categories:[],orderFlowVerified:false};
    return {status:"WEEKLY_GROSS_POSITIONS_COMPARABLE",
      reportDate:cur.date,previousDate:prev.date,
      currentOpenInterest:cur.oi,openInterestDelta:cur.oi-prev.oi,
      categories:groups,
      source:SOURCES[contract.dataset],sourceType:contract.dataset,
      firstSeenVerified:false,orderFlowVerified:false,causalTradeAttribution:false,
      tradingSignal:false};
  }
  function prepare(tff,disagg,now=Date.now()){
    const reports={tff,disagg};
    return CONTRACTS.map(c=>card(c,reports[c.dataset],now));
  }
  /* Watchlist stores only public CFTC contract codes on this iPhone. */
  function parseFavorites(raw){
    if(typeof raw!=="string"||raw.length>512)return [];
    let arr;
    try{arr=JSON.parse(raw);}catch{return [];}
    if(!Array.isArray(arr)||arr.length>CONTRACTS.length)return [];
    const valid=new Set(CONTRACTS.map(c=>c.code));
    return [...new Set(arr.filter(v=>typeof v==="string"&&valid.has(v)))];
  }
  function toggleFavorite(values,code){
    const allowed=new Set(CONTRACTS.map(c=>c.code));
    if(typeof code!=="string"||!allowed.has(code))return [...parseFavorites(JSON.stringify(values))];
    const clean=parseFavorites(JSON.stringify(values));
    return clean.includes(code)?clean.filter(x=>x!==code):[...clean,code];
  }
  function historyFor(c,parsed){
    const item=parsed&&parsed.byCode instanceof Map?parsed.byCode.get(c.code):null;
    if(!item||!Array.isArray(item.rows)||!item.rows.length)
      return {status:"UNKNOWN_NO_REPORT",rows:[],firstSeenVerified:false};
    if(item.conflict)
      return {status:"QUARANTINE_CONFLICT",rows:[],firstSeenVerified:false};
    const ordered=item.rows.slice(0,12).reverse();
    const rows=ordered.map((r,i)=>{
      const prev=i>0?ordered[i-1]:null,consecutive=!!prev&&r.at-prev.at===WEEK;
      return {date:r.date,first:round(r.first.net),second:round(r.second.net),
        firstChange:consecutive?round(r.first.net-prev.first.net):null,
        secondChange:consecutive?round(r.second.net-prev.second.net):null,
        openInterest:r.oi,priorWeekMissing:!!prev&&!consecutive};
    });
    return {status:"UNATTESTED_PUBLIC_REPORT_HISTORY",rows,firstSeenVerified:false,
      cftcTuesdayOnly:true,spotMappingVerified:false,tradingSignal:false};
  }
  function filterCards(cards,{family="Tutte",search="",mode="Movimento",favoritesOnly=false,favorites=[]}={}){
    if(!Array.isArray(cards))return [];
    const s=String(search).trim().toUpperCase();
    const fav=new Set(parseFavorites(JSON.stringify(favorites)));
    const out=cards.filter(x=>(family==="Tutte"||x.family===family)&&
      (!favoritesOnly||fav.has(x.code))&&
      (!s||(x.id+" "+x.name+" "+x.code).toUpperCase().includes(s)));
    const ready=x=>x.status==="CURRENT_REPORT_DATE"&&x.deltas!==null;
    const weight=x=>ready(x)?Math.max(Math.abs(x.deltas.first),Math.abs(x.deltas.second)):-1;
    return out.sort((a,b)=>{
      if(mode==="Divergenze"){
        const pr=x=>x.comparison==="DIVERGENT"?0:x.comparison==="CO_MOVING"?1:2;
        return pr(a)-pr(b)||weight(b)-weight(a)||a.id.localeCompare(b.id);
      }
      if(mode==="Data"){
        return (b.reportDate||"").localeCompare(a.reportDate||"")||a.id.localeCompare(b.id);
      }
      return weight(b)-weight(a)||a.id.localeCompare(b.id);
    });
  }
  function summarizeRetail(doc,now=Date.now()){
    if(!doc||doc.status!=="ok"||doc.source!=="Myfxbook Community Outlook"||
       !doc.symbols||typeof doc.symbols!=="object")return [];
    return FX_RETAIL.map(pair=>{
      const v=doc.symbols[pair],stamp=Date.parse(v?.t||""),
            lots=amount(v?.lLots),shortLots=amount(v?.sLots),
            positions=amount(v?.lPos),shortPos=amount(v?.sPos);
      const age=Number.isFinite(stamp)?now-stamp:null;
      const valid=age!==null&&age>=-5*60000&&lots!==null&&shortLots!==null&&
        lots+shortLots>0&&positions!==null&&shortPos!==null&&positions+shortPos>=30;
      const fresh=valid&&age<=3*3600000;
      return {pair,status:!valid?"UNKNOWN":fresh?"RECENT_RETAIL":"ARCHIVED_RETAIL",
        observedAt:valid?new Date(stamp).toISOString():null,
        longLotsPct:valid?round(100*lots/(lots+shortLots)):null,
        samplePositions:valid?positions+shortPos:null,
        separatePopulation:"MYFXBOOK_RETAIL_LOTS",
        cotComparableAsInstitutional:false};
    });
  }
  return Object.freeze({CONTRACTS,FIELDS,DATASETS,SOURCES,FX_RETAIL,DAY,WEEK,
                        parseRows,card,anatomyFor,prepare,filterCards,parseFavorites,toggleFavorite,historyFor,summarizeRetail,round});
});