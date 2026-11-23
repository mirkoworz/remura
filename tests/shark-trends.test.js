/* REMURA Shark COT Trends v1.70 LAB — targeted tests, no provider calls */
"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const trends=require("../shark-trends-core.js");
const row=(date,first,second)=>({date,first,second});
const history=rows=>({status:"UNATTESTED_PUBLIC_REPORT_HISTORY",rows});
test("no report or conflicting revised CFTC rows show no invented chart",()=>{
  for(const h of [null,{status:"QUARANTINE_CONFLICT",rows:[row("2026-11-17",5,-3)]},
    {status:"UNKNOWN_NO_REPORT",rows:[]}]){
    const model=trends.build(h);
    assert.equal(model.points.length,0);
    assert.equal(model.noInterpolatedPoints,true);
    assert.notEqual(model.status,"READY");
  }
});
test("two real Tuesdays produce the two separate source-defined lines",()=>{
  const m=trends.build(history([row("2026-11-10",-12,8),row("2026-11-17",-9,5)]));
  assert.equal(m.status,"READY");
  assert.equal(m.points.length,2);
  assert.equal(m.series.length,2);
  assert.equal(m.series[0].segments[0].length,2);
  assert.equal(m.series[1].segments[0].length,2);
  assert.equal(m.gaps,0);
  assert.equal(m.metric,"NET_POSITION_PCT_OPEN_INTEREST");
  assert.equal(m.tradeTimingVerified,false);
  assert.equal(m.tradingSignal,false);
});
test("missing Tuesday is a physical horizontal gap and NEVER a connecting segment",()=>{
  const m=trends.build(history([
    row("2026-10-27",10,-5),row("2026-11-03",8,-3),row("2026-11-17",2,9)
  ]));
  assert.equal(m.status,"READY");
  assert.equal(m.gaps,1);
  assert.equal(m.series[0].segments.length,2);
  assert.deepEqual(m.series[0].segments.map(s=>s.length),[2,1]);
  assert.deepEqual(m.series[1].segments.map(s=>s.length),[2,1]);
  assert.ok(m.points[2].x-m.points[1].x > m.points[1].x-m.points[0].x);
  assert.equal(m.noInterpolatedPoints,true);
});
test("axes include exact zero for positive and negative weekly net OI",()=>{
  const m=trends.build(history([row("2026-11-10",-20,33),row("2026-11-17",-12,24)]));
  assert.equal(m.status,"READY");
  assert.ok(m.axes.low<0&&m.axes.high>0);
  assert.ok(m.axes.zeroY>m.axes.top&&m.axes.zeroY<m.axes.bottom);
  assert.ok(m.series[0].segments[0][0].y>m.series[1].segments[0][0].y);
});
test("duplicated, descending or non-Tuesday reports cannot generate a trend",()=>{
  for(const rows of [
    [row("2026-11-17",1,2),row("2026-11-17",3,2)],
    [row("2026-11-17",1,2),row("2026-11-10",3,2)],
    [row("2026-11-11",1,2),row("2026-11-17",3,2)]
  ])assert.equal(trends.build(history(rows)).status,"INVALID");
});
test("invalid percentages and single-point histories remain N/D, not inferred",()=>{
  assert.equal(trends.build(history([row("2026-11-17",1,2)])).status,"INSUFFICIENT");
  for(const bad of [NaN,Infinity,101,-101,null]){
    assert.equal(trends.build(history([row("2026-11-10",3,2),row("2026-11-17",bad,2)])).status,"INVALID");
  }
});
test("iPhone chart UI uses no fetch or HTML injection, standalone includes real script bundles",()=>{
  const root=path.join(__dirname,"..");
  const html=fs.readFileSync(path.join(root,"shark-cockpit.html"),"utf8");
  const ui=fs.readFileSync(path.join(root,"shark-trends-ui.js"),"utf8");
  const page=fs.readFileSync(path.join(root,"shark-cockpit.js"),"utf8");
  const css=fs.readFileSync(path.join(root,"shark-cockpit.css"),"utf8");
  const preview=fs.readFileSync(path.join(root,"preview","REMURA-Shark-COT-Trends-v170-iPhone-STANDALONE-LAB.html"),"utf8");
  assert.ok(html.includes("v1.70 LAB")&&html.includes("23/11/2026 15:01 CET"));
  const a=html.indexOf("shark-trends-core.js?v=170"),b=html.indexOf("shark-trends-ui.js?v=170"),
    c=html.indexOf("shark-cockpit.js?v=170");
  assert.ok(a>0&&a<b&&b<c);
  assert.ok(page.includes("SHARK_TRENDS_UI.render(h,item.labels)"));
  assert.ok(css.includes(".trend-svg")&&css.includes(".trend-zero"));
  assert.ok(ui.includes("createElementNS")&&!ui.includes("fetch(")&&!ui.includes("innerHTML"));
  for(const marker of ["inline-shark-trends-core.js","inline-shark-trends-ui.js","inline-shark-cockpit.js",
      "SHARK COCKPIT v1.70 LAB"]){
    assert.ok(preview.includes(marker),marker);
  }
  assert.equal(preview.includes("<script src="),false);
});
