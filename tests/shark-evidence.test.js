/* REMURA Shark Evidence v1.69 LAB — tests for new UI provenance only.
 * No CFTC/Myfxbook calls, no production or Filone A tests repeated.
 */
"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const {summarize}=require("../shark-evidence-core.js");
const sample=[
  {dataset:"tff",reportDate:"2026-11-17",status:"CURRENT_REPORT_DATE",deltas:{first:1,second:-2}},
  {dataset:"tff",reportDate:"2026-11-17",status:"QUARANTINE_CONFLICT",deltas:null},
  {dataset:"disagg",reportDate:"2026-11-03",status:"STALE_REPORT",deltas:null}
];
const report=r=>r.sources.find(x=>x.id==="tff");
test("N/D without successful CFTC fetch; CVD never improvised",()=>{
  const r=summarize({cards:sample,loaded:{tff:false,disagg:false},readAt:null});
  assert.equal(report(r).state,"NON_DISPONIBILE");
  assert.equal(r.sources.find(x=>x.id==="cvd").state,"NON_COLLEGATO");
  assert.equal(r.publicationTimeVerified,false);
  assert.equal(r.independentFirstSeen,false);
  assert.equal(r.readAt,null);
});
test("CFTC conflicting contracts take precedence over partly recent ones",()=>{
  const r=summarize({cards:sample,loaded:{tff:true,disagg:true},readAt:1795440000000});
  assert.equal(report(r).state,"DA_VERIFICARE");
  assert.match(report(r).detail,/1 variazioni WoW confrontabili/);
  assert.equal(report(r).reference,"2026-11-17");
  assert.equal(r.sources.find(x=>x.id==="disagg").state,"OBSOLETO");
  assert.ok(r.readAt.endsWith("Z"));
});
test("recent but nonconsecutive weekly reports cannot be called comparable",()=>{
  const cards=[{dataset:"tff",reportDate:"2026-11-17",status:"UNKNOWN_WEEKLY_COMPARISON",deltas:null}];
  const r=summarize({cards,loaded:{tff:true}});
  assert.equal(report(r).state,"RECENTE");
  assert.match(report(r).detail,/0 variazioni WoW confrontabili/);
});
test("retail sample remains separate from institutional futures",()=>{
  const r=summarize({retail:[
    {status:"RECENT_RETAIL",observedAt:"2026-11-23T12:00:00Z"},
    {status:"ARCHIVED_RETAIL",observedAt:"2026-11-21T12:00:00Z"}
  ]});
  const retail=r.sources.find(x=>x.id==="retail");
  assert.equal(retail.state,"PARZIALE");
  assert.equal(retail.reference,"2026-11-23T12:00:00Z");
  assert.match(retail.note,/non rappresenta posizioni istituzionali/);
});
test("single updated HTML is stamped at top, modules load before cockpit, with iPhone jump links",()=>{
  const html=fs.readFileSync(path.join(__dirname,"..","shark-cockpit.html"),"utf8");
  const tag=html.indexOf("v1.70 LAB");
  assert.ok(tag>0&&tag<html.indexOf('<section class="hero"'));
  assert.match(html,/23\/11\/2026 13:30 CET \(Europe\/Rome\)/);
  const iCore=html.indexOf("shark-evidence-core.js?v=169");
  const iUi=html.indexOf("shark-evidence-ui.js?v=169");
  const iCockpit=html.indexOf("shark-cockpit.js?v=170");
  assert.ok(iCore<iUi&&iUi<iCockpit);
  for(const name of ['id="evidence"','id="contracts"','id="retail"','#institutional-movers'])assert.ok(html.includes(name));
  const ui=fs.readFileSync(path.join(__dirname,"..","shark-evidence-ui.js"),"utf8");
  assert.equal(ui.includes("fetch("),false);
  assert.equal(ui.includes("innerHTML"),false);
  const preview=fs.readFileSync(path.join(__dirname,"..","preview",
    "REMURA-Shark-Evidence-v169-iPhone-STANDALONE-LAB.html"),"utf8");
  for(const marker of ["inline-shark-evidence-core.js","inline-shark-evidence-ui.js",
    "inline-shark-cockpit.js",'id="evidence"',"v1.69 LAB"]){
    assert.ok(preview.includes(marker),marker);
  }
  assert.ok(!preview.includes("<script src="));
  assert.ok(!preview.includes("/private-api/"));
});
