// REMURA Shark Anatomy v1.68 LAB — product-specific cases only.
const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs");
const core=require("../shark-cockpit-core.js");
const NOW=Date.parse("2026-11-22T21:10:00Z");
const eur=core.CONTRACTS.find(c=>c.code==="099741");
const gold=core.CONTRACTS.find(c=>c.code==="088691");
function fx(date="2026-11-17",fields={}){
  return {report_date_as_yyyy_mm_dd:date,cftc_contract_market_code:"099741",
    open_interest_all:"1000",asset_mgr_positions_long:"120",
    asset_mgr_positions_short:"40",lev_money_positions_long:"60",
    lev_money_positions_short:"80",...fields};
}
function disagg(date="2026-11-17",fields={}){
  return {report_date_as_yyyy_mm_dd:date,cftc_contract_market_code:"088691",
    open_interest_all:"2000",m_money_positions_long_all:"500",
    m_money_positions_short_all:"200",prod_merc_positions_long:"400",
    prod_merc_positions_short:"550",...fields};
}
function anatomy(rows,ds="tff",c=eur,now=NOW){
  return core.anatomyFor(c,core.parseRows(rows,ds,now),now);
}
test("Anatomy shows both categories' exact reported long/short current counts",()=>{
  const a=anatomy([fx(),fx("2026-11-10",{asset_mgr_positions_long:"100",
     asset_mgr_positions_short:"65",lev_money_positions_long:"75",lev_money_positions_short:"70"})]);
  assert.equal(a.status,"WEEKLY_GROSS_POSITIONS_COMPARABLE");
  assert.deepEqual(a.categories.map(c=>c.label),["Asset Manager","Leveraged Funds"]);
  assert.equal(a.categories[0].currentLong,120);
  assert.equal(a.categories[0].currentShort,40);
  assert.equal(a.categories[1].currentLong,60);
  assert.equal(a.categories[1].currentShort,80);
});
test("Weekly net decomposition longDelta minus shortDelta equals net contracts delta",()=>{
  const a=anatomy([fx(),fx("2026-11-10",{asset_mgr_positions_long:"100",
    asset_mgr_positions_short:"65",lev_money_positions_long:"75",
    lev_money_positions_short:"70"})]);
  const m=a.categories[0],l=a.categories[1];
  assert.deepEqual([m.longDelta,m.shortDelta,m.netContracts,m.netDeltaContracts,m.netPpChange],
    [20,-25,80,45,4.5]);
  assert.deepEqual([l.longDelta,l.shortDelta,l.netDeltaContracts],[-15,10,-25]);
  for(const v of a.categories)assert.equal(v.netDeltaContracts,v.longDelta-v.shortDelta);
});
test("Net position can rise on fewer shorts with no increase in longs",()=>{
 const a=anatomy([fx(),fx("2026-11-10",{asset_mgr_positions_long:"120",
  asset_mgr_positions_short:"60"})]);
 assert.equal(a.categories[0].longDelta,0);
 assert.equal(a.categories[0].shortDelta,-20);
 assert.equal(a.categories[0].netDeltaContracts,20);
 assert.equal(a.categories[0].opensVerified,false);
 assert.equal(a.categories[0].closesVerified,false);
});
test("Long and short reported positions may both rise while net exposure falls",()=>{
 const a=anatomy([fx("2026-11-17",{asset_mgr_positions_long:"110",asset_mgr_positions_short:"120"}),
                  fx("2026-11-10",{asset_mgr_positions_long:"100",asset_mgr_positions_short:"90"})]);
 const m=a.categories[0];
 assert.equal(m.longDelta,10);
 assert.equal(m.shortDelta,30);
 assert.equal(m.netDeltaContracts,-20);
 assert.equal(m.netPpChange,-2);
});
test("OI changes do not get confused with gross contract changes or net percentage points",()=>{
 const a=anatomy([fx("2026-11-17",{open_interest_all:"2000",
  asset_mgr_positions_long:"170",asset_mgr_positions_short:"60"}),
  fx("2026-11-10",{open_interest_all:"1000",asset_mgr_positions_long:"120",
  asset_mgr_positions_short:"70"})]);
 assert.equal(a.currentOpenInterest,2000);
 assert.equal(a.openInterestDelta,1000);
 assert.equal(a.categories[0].netDeltaContracts,60);
 assert.equal(a.categories[0].netPpChange,0.5);
});
test("Disaggregated gold uses Managed Money and Producer/Merchant without TFF mislabeling",()=>{
 const a=anatomy([disagg(),disagg("2026-11-10",{
  m_money_positions_long_all:"450",prod_merc_positions_short:"500"})],"disagg",gold);
 assert.equal(a.status,"WEEKLY_GROSS_POSITIONS_COMPARABLE");
 assert.deepEqual(a.categories.map(c=>c.label),["Managed Money","Producer / Merchant"]);
 assert.equal(a.categories[0].longDelta,50);
 assert.equal(a.categories[1].shortDelta,50);
});
test("No week-before CFTC report means no gross-position anatomy",()=>{
 const a=anatomy([fx()]);
 assert.equal(a.status,"UNKNOWN_WEEKLY_COMPARISON");
 assert.deepEqual(a.categories,[]);
});
test("Two Tuesdays separated by two weeks cannot masquerade as one-week changes",()=>{
 const a=anatomy([fx(),fx("2026-11-03",{asset_mgr_positions_long:"70"})]);
 assert.equal(a.status,"UNKNOWN_WEEKLY_COMPARISON");
 assert.deepEqual(a.categories,[]);
});
test("A stale CFTC report cannot be shown as current anatomy",()=>{
 const late=Date.parse("2026-12-13T19:00:00Z");
 const a=anatomy([fx(),fx("2026-11-10")],"tff",eur,late);
 assert.equal(a.status,"STALE_REPORT");
 assert.deepEqual(a.categories,[]);
});
test("Same Tuesday conflicting revisions stay quarantined rather than cherry-picked",()=>{
 const a=anatomy([fx(),fx("2026-11-17",{asset_mgr_positions_long:"90"}),fx("2026-11-10")]);
 assert.equal(a.status,"QUARANTINE_CONFLICT");
 assert.equal(a.categories.length,0);
});
test("Wrong dataset/contract or unverifiable actor identity fails closed",()=>{
 const wrong=anatomy([fx()],"disagg",eur);
 assert.equal(wrong.status,"UNKNOWN_NO_REPORT");
 const spoof=core.anatomyFor({code:"BOGUS",dataset:"tff"},null,NOW);
 assert.equal(spoof.status,"UNKNOWN_CONTRACT");
 const valid=anatomy([fx(),fx("2026-11-10")]);
 assert.equal(valid.firstSeenVerified,false);
 assert.equal(valid.orderFlowVerified,false);
 assert.equal(valid.causalTradeAttribution,false);
 assert.equal(valid.tradingSignal,false);
 assert.ok(valid.categories.every(c=>!c.actorIdentityVerified));
});
test("Real iPhone UI renders anatomy from existing CFTC snapshots and adds no fetch",()=>{
 const html=fs.readFileSync("shark-cockpit.html","utf8");
 const ui=fs.readFileSync("shark-cockpit.js","utf8");
 const css=fs.readFileSync("shark-cockpit.css","utf8");
 assert.ok(html.includes("v1.70 LAB")&&html.includes("shark-cockpit.js?v=170"));
 assert.ok(html.includes("Radiografia settimanale:"));
 assert.ok(ui.includes("core.anatomyFor("));
 assert.ok(ui.includes("r.append(anatomyPanel(item))"));
 assert.ok(ui.includes("shortDelta")&&ui.includes("longDelta"));
 assert.ok(css.includes(".anatomy-details")&&css.includes(".anatomy-positions"));
 assert.ok(!ui.includes("cloudflare.com")&&!ui.includes("private-api/"));
});
