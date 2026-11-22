// REMURA v1.65 LAB — NEW Shark Cockpit product tests, not past research suites.
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const core=require("../shark-cockpit-core.js");
const NOW=Date.parse("2026-11-22T16:32:00Z");
function row(date="2026-11-17",opt={}){
  return {report_date_as_yyyy_mm_dd:date,cftc_contract_market_code:"099741",
    open_interest_all:"1000",asset_mgr_positions_long:"120",asset_mgr_positions_short:"40",
    lev_money_positions_long:"60",lev_money_positions_short:"80",...opt};
}
function parsed(records,ds="tff",now=NOW){return core.parseRows(records,ds,now);}
function find(records,now=NOW){
  const p=parsed(records,"tff",now);
  return core.card(core.CONTRACTS.find(x=>x.code==="099741"),p,now);
}
test("14 CFTC contracts exactly; forex contracts never presumed spot orders",()=>{
  assert.equal(core.CONTRACTS.length,14);
  assert.equal(core.CONTRACTS.filter(x=>x.family==="Valute").length,7);
  assert.equal(core.CONTRACTS.filter(x=>x.dataset==="disagg").length,3);
  assert.ok(core.CONTRACTS.every(c=>c.code&&c.name&&c.dataset));
  assert.equal(new Set(core.CONTRACTS.map(c=>c.code)).size,14);
  assert.equal(find([row()]).spotPairMappingVerified,false);
});
test("real CFTC fields: Asset Manager and Leveraged Funds remain separate",()=>{
  const x=find([row("2026-11-17"),row("2026-11-10",
    {asset_mgr_positions_long:"100",lev_money_positions_long:"90"})]);
  assert.equal(x.status,"CURRENT_REPORT_DATE");
  assert.equal(x.first,8);
  assert.equal(x.second,-2);
  assert.deepEqual(x.deltas,{first:2,second:-3});
  assert.equal(x.comparison,"DIVERGENT");
  assert.equal(x.tradingSignal,false);
});
test("Co-moving two TFF categories is descriptive, not positive alpha",()=>{
  const x=find([row(),row("2026-11-10",
    {asset_mgr_positions_long:"100",lev_money_positions_long:"50"})]);
  assert.equal(x.comparison,"CO_MOVING");
  assert.equal(x.independentlyWitnessed,false);
  assert.equal(x.publicationTimeVerified,false);
  assert.equal(x.individualInstitutionsKnown,false);
  assert.equal(x.realTimeMarketFlow,false);
});
test("missing prior COT Tuesday is N/D, never compares two weeks apart",()=>{
  const x=find([row(),row("2026-11-03")]);
  assert.equal(x.status,"UNKNOWN_WEEKLY_COMPARISON");
  assert.equal(x.deltas,null);
  assert.equal(x.fourWeek,null);
});
test("latest COT report older than 14 days is stale",()=>{
  const later=Date.parse("2026-12-13T16:32:00Z");
  const x=find([row("2026-11-17"),row("2026-11-10")],later);
  assert.equal(x.status,"STALE_REPORT");
  assert.equal(x.deltas,null);
});
test("four-week change only on five consecutive Tuesday reports",()=>{
  const rows=["2026-11-17","2026-11-10","2026-11-03","2026-10-27","2026-10-20"]
     .map((date,i)=>row(date,{asset_mgr_positions_long:String(120-i*10)}));
  const x=find(rows);
  assert.deepEqual(x.fourWeek,{first:4,second:0});
  const gapped=find([rows[0],rows[1],rows[2],rows[4]]);
  assert.equal(gapped.fourWeek,null);
});
test("conflicting report revision for same Tuesday quarantined, not averaged",()=>{
  const x=find([row(),row("2026-11-17",{asset_mgr_positions_long:"190"}),row("2026-11-10")]);
  assert.equal(x.status,"QUARANTINE_CONFLICT");
  assert.equal(x.deltas,null);
});
test("identical duplicate CFTC row does not fabricate movement",()=>{
  const x=find([row(),row(),row("2026-11-10",{asset_mgr_positions_long:"100",lev_money_positions_long:"90"})]);
  assert.equal(x.status,"CURRENT_REPORT_DATE");
  assert.equal(x.availableWeeks,2);
  assert.equal(x.deltas.first,2);
});
test("negative, missing, blank and nonfinite CFTC volumes are excluded",()=>{
  for(const bad of [-3,"","abc",null,Infinity]){
    const x=find([row("2026-11-17",{open_interest_all:bad})]);
    assert.equal(x.status,"UNKNOWN_NO_REPORT");
    assert.equal(x.first,null);
  }
});
test("future, wrong weekday and invalid calendar date are excluded",()=>{
  const result=parsed([row("2026-11-24"),row("2026-11-18"),row("2026-11-31")]);
  assert.equal(result.valid,0);
  assert.equal(result.invalid,3);
});
test("TFF response cannot be re-used as Disaggregated data",()=>{
  const r=parsed([row()],"disagg");
  assert.equal(r.valid,0);
  assert.equal(core.card(core.CONTRACTS[0],r,NOW).status,"UNKNOWN_NO_REPORT");
});
test("full list preserves 14 contracts with unknowns for unavailable dataset",()=>{
  const p=parsed([row(),"",row("2026-11-10")]);
  const list=core.prepare(p,null,NOW);
  assert.equal(list.length,14);
  assert.equal(list.find(c=>c.id==="XAUUSD").status,"UNKNOWN_NO_REPORT");
  assert.ok(list.every(c=>c.tradingSignal===false));
});
test("filtering and ordering are functional on exact categories and codes",()=>{
  const p=parsed([row(),row("2026-11-10",{asset_mgr_positions_long:"100",lev_money_positions_long:"90"})]);
  const list=core.prepare(p,null,NOW);
  const fx=core.filterCards(list,{family:"Valute",search:"099741",mode:"Movimento"});
  assert.equal(fx.length,1);
  assert.equal(fx[0].id,"EUR");
  assert.equal(core.filterCards(list,{family:"Energia",search:"EUR"}).length,0);
  assert.equal(core.filterCards(list,{mode:"Movimento"})[0].id,"EUR");
});
test("retail Myfxbook pct comes from lots not a guessed CFTC field",()=>{
  const obj={status:"ok",source:"Myfxbook Community Outlook",symbols:{
    EURUSD:{t:"2026-11-22T16:22:00Z",lLots:30,sLots:70,lPct:99,lPos:40,sPos:70}
  }};
  const r=core.summarizeRetail(obj,NOW).find(x=>x.pair==="EURUSD");
  assert.equal(r.longLotsPct,30);
  assert.equal(r.status,"RECENT_RETAIL");
  assert.equal(r.cotComparableAsInstitutional,false);
  assert.equal(r.separatePopulation,"MYFXBOOK_RETAIL_LOTS");
});
test("weekend retail data over 3h remains ARCHIVED, never labeled live",()=>{
  const obj={status:"ok",source:"Myfxbook Community Outlook",symbols:{
    EURUSD:{t:"2026-11-22T08:50:44Z",lLots:30,sLots:70,lPos:40,sPos:70}
  }};
  assert.equal(core.summarizeRetail(obj,NOW)[0].status,"ARCHIVED_RETAIL");
});
test("wrong Myfxbook schema or insufficient positions yields unknown",()=>{
  assert.deepEqual(core.summarizeRetail({},NOW),[]);
  const z=core.summarizeRetail({status:"ok",source:"Myfxbook Community Outlook",
    symbols:{EURUSD:{t:"2026-11-22T16:22:00Z",lLots:3,sLots:2,lPos:4,sPos:2}}},NOW);
  assert.equal(z[0].status,"UNKNOWN");
  assert.equal(z[0].longLotsPct,null);
});
test("actual browser page wires CFTC and existing static retail with no new backend",()=>{
  const html=fs.readFileSync("shark-cockpit.html","utf8");
  const js=fs.readFileSync("shark-cockpit.js","utf8");
  const nav=fs.readFileSync("nav.js","utf8");
  const sw=fs.readFileSync("sw.js","utf8");
  for(const name of ["shark-cockpit-core.js?v=165","shark-cockpit.js?v=165","nav.js?v=165","shark-cockpit.css?v=165"])assert.ok(html.includes(name));
  for(const name of ["id=\"cards\"","id=\"refresh\"","id=\"family\"","id=\"sort\"","id=\"retail-list\""])assert.ok(html.includes(name));
  for(const path of ["./shark-cockpit.html","./shark-cockpit.js","./shark-cockpit.css","./shark-cockpit-core.js"])assert.ok(sw.includes(path));
  assert.ok(nav.includes('data-main="cockpit"'));
  assert.ok(js.includes("./data/myfxbook/latest.json"));
  assert.ok(js.includes("publicreporting.cftc.gov"));
  assert.ok(!js.includes("private-api/")&&!js.includes("localStorage.setItem"));
});
