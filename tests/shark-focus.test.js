/* REMURA Shark Focus v1.71 LAB — scoped tests, no market requests */
"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const focus=require("../shark-focus-core.js");
const card=(code,status="CURRENT_REPORT_DATE",reportDate="2026-11-17",deltas={first:1.75,second:-0.2})=>({
  code,name:"Future "+code,family:"Valute",dataset:"tff",
  labels:["Asset Manager","Leveraged Funds"],reportDate,status,deltas,
  comparison:"DIVERGENT",ageDays:6
});
test("empty watchlist never promotes an institutional candidate",()=>{
  const x=focus.build([card("099741")],[]);
  assert.equal(x.state,"EMPTY");
  assert.equal(x.items.length,0);
  assert.equal(x.tradingSignal,false);
});
test("only whitelisted CFTC codes and unique favorites are shown",()=>{
  const x=focus.build([card("099741"),card("097741")],["099741","099741","FAKE","097741"]);
  assert.deepEqual(x.items.map(i=>i.code).sort(),["097741","099741"]);
  assert.equal(x.count,2);
  assert.equal(x.rankingMeaning,"DISPLAY_ORDER_ONLY");
});
test("two consecutive recent CFTC reports permit descriptive WoW only",()=>{
  const x=focus.build([card("099741")],["099741"]);
  assert.equal(x.comparable,1);
  assert.equal(x.items[0].quality,"CONFRONTABILE");
  assert.deepEqual(x.items[0].deltas,{first:1.75,second:-0.2});
  assert.equal(x.items[0].priceDirectionKnown,false);
  assert.equal(x.items[0].institutionIdentitiesKnown,false);
});
test("recent report without consecutive Tuesday must not invent weekly moves",()=>{
  const x=focus.build([card("099741","UNKNOWN_WEEKLY_COMPARISON","2026-11-17",null)],["099741"]);
  assert.equal(x.onlyReport,1);
  assert.equal(x.comparable,0);
  assert.equal(x.items[0].quality,"SOLO_REPORT");
  assert.equal(x.items[0].deltas,null);
});
test("stale and conflicting reports are quarantined from weekly delta summary",()=>{
  const x=focus.build([
    card("099741","STALE_REPORT","2026-10-27",{first:22,second:-9}),
    card("097741","QUARANTINE_CONFLICT","2026-11-17",{first:90,second:-90})
  ],["099741","097741"]);
  assert.equal(x.comparable,0);
  assert.equal(x.unavailable,2);
  assert.ok(x.items.every(i=>i.deltas===null));
});
test("quality and then report week sort before absolute magnitude, with mixed-week warning",()=>{
  const x=focus.build([
    card("099741","CURRENT_REPORT_DATE","2026-11-10",{first:10,second:9}),
    card("097741","CURRENT_REPORT_DATE","2026-11-17",{first:1,second:0.1}),
    card("096742","UNKNOWN_WEEKLY_COMPARISON","2026-11-17",null)
  ],["099741","096742","097741"]);
  assert.deepEqual(x.items.map(i=>i.code),["097741","099741","096742"]);
  assert.equal(x.differentReportWeeks,true);
  assert.deepEqual(x.distinctComparableReportDates,["2026-11-10","2026-11-17"]);
});
test("unknown source or empty cards remain N/D instead of fake exposure",()=>{
  const x=focus.build([],["099741"]);
  assert.equal(x.items[0].quality,"NON_DISPONIBILE");
  assert.equal(x.items[0].deltas,null);
  assert.equal(x.items[0].tradingSignal,false);
  assert.equal(x.measuredLiveOrders,false);
});
test("Safari DOM is wired to current favorites without API calls or HTML injection",()=>{
  const root=path.join(__dirname,"..");
  const html=fs.readFileSync(path.join(root,"shark-cockpit.html"),"utf8");
  const js=fs.readFileSync(path.join(root,"shark-cockpit.js"),"utf8");
  const ui=fs.readFileSync(path.join(root,"shark-focus-ui.js"),"utf8");
  const css=fs.readFileSync(path.join(root,"shark-cockpit.css"),"utf8");
  const sw=fs.readFileSync(path.join(root,"sw.js"),"utf8");
  const preview=fs.readFileSync(path.join(root,"preview","REMURA-Shark-Focus-v171-iPhone-STANDALONE-LAB.html"),"utf8");
  assert.match(html,/SHARK COCKPIT v1\.71 LAB · 23\/11\/2026 20:20 CET \(Europe\/Rome\)/);
  for(const token of ['id="my-sharks"','id="my-sharks-status"','id="my-sharks-list"','#my-sharks','shark-focus-core.js?v=171','shark-focus-ui.js?v=171','shark-cockpit.js?v=171'])
    assert.ok(html.includes(token),token);
  assert.ok(html.indexOf('shark-focus-core.js?v=171')<html.indexOf('shark-focus-ui.js?v=171'));
  assert.ok(html.indexOf('shark-focus-ui.js?v=171')<html.indexOf('shark-cockpit.js?v=171'));
  assert.ok(js.includes("SHARK_FOCUS_UI?.render(cards,favorites"));
  assert.ok(js.includes("toggleFavoriteCode(item.code)")&&js.includes("openFocusContract(code)"));
  assert.ok(css.includes(".focus-card")&&sw.includes("shark-focus-core.js"));
  assert.ok(ui.includes("replaceChildren")&&!ui.includes("fetch(")&&!ui.includes("innerHTML"));
  for(const token of ["inline-shark-focus-core.js","inline-shark-focus-ui.js","SHARK COCKPIT v1.71 LAB"])
    assert.ok(preview.includes(token),token);
  assert.equal(preview.includes("<script src="),false);
  assert.equal(preview.includes("/private-api/"),false);
});
