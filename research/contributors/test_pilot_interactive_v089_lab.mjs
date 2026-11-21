// REMURA Contributors v0.89 LAB — ONLY new interactive pilot tests
import {test} from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {runInNewContext,Script} from "node:vm";
const html=readFileSync(new URL("./contributors_pilot_interactive_v089_lab.html",import.meta.url),"utf8");
const matched=html.match(/<script id="pilot-simulator">([\s\S]*?)<\/script>/);
assert.ok(matched);
const script=matched[1];
new Script(script);
const ids=[
"currentRole","contributorActions","ownerActions","roleContributor","roleOwner","submitDemo",
"uncertainDemo","amendDemo","approveDemo","rejectDemo","approveAmendDemo","rejectAmendDemo",
"observeReservedDemo","resetDemo","originalsList","amendmentsList","auditList",
"originalCount","amendCount","liveStatus"
];
function demo(){
 const nodes=new Map(ids.map(id=>[id,{
  value:"",textContent:"",disabled:false,hidden:false,attrs:{},handlers:{},
  setAttribute(k,v){this.attrs[k]=v},
  addEventListener(k,v){this.handlers[k]=v}
 }]));
 const ctx={document:{getElementById:id=>{
  assert.ok(nodes.has(id),"only declared DOM IDs "+id);return nodes.get(id)
 }},String,Array,Object,Number};
 runInNewContext(script,ctx);
 return {nodes,run:src=>runInNewContext(src,ctx),get:id=>nodes.get(id)};
}
test("01 version and Rome datetime at the very top",()=>{
 assert.ok(html.indexOf('id="version"')<html.indexOf("<main"));
 assert.match(html,/Contributors v0\.89 LAB · 21\/11\/2026 19:03 CET/);
});
test("02 no network allowed by CSP",()=>{
 assert.match(html,/connect-src 'none'/);assert.match(html,/form-action 'none'/);
});
test("03 no external assets",()=>{
 assert.doesNotMatch(html,/<(?:iframe|img|link)\b/i);
});
test("04 no fetch or storage operations",()=>{
 assert.doesNotMatch(script,/\bfetch\s*\(/);
 assert.doesNotMatch(script,/\blocalStorage\b|\bsessionStorage\b|\bXMLHttpRequest\b/);
});
test("05 no HTML injection or text field accepting user data",()=>{
 assert.doesNotMatch(script,/\.innerHTML\b|\bcreateElement\b/);
 assert.doesNotMatch(html,/<(?:input|textarea|form)\b/i);
});
test("06 initial demo starts contributor without data",()=>{
 const d=demo();
 assert.match(d.get("currentRole").textContent,/CONTRIBUTOR/);
 assert.equal(d.get("originalCount").textContent,"0");
 assert.equal(d.get("amendCount").textContent,"0");
});
test("07 contributor can submit only synthetic",()=>{
 const d=demo();assert.equal(d.run("submitDemo()"),true);
 assert.match(d.get("originalsList").textContent,/DEMO:EURUSD · UNREVIEWED/);
});
test("08 unique original IDs, bounded list",()=>{
 const d=demo();assert.equal(d.run("submitDemo()"),true);
 assert.equal(d.run("submitDemo()"),true);
 assert.match(d.get("originalsList").textContent,/#1/);
 assert.match(d.get("originalsList").textContent,/#2/);
});
test("09 role switch only changes demo UI",()=>{
 const d=demo();assert.equal(d.run("setRole('OWNER')"),true);
 assert.equal(d.get("contributorActions").hidden,true);
 assert.equal(d.get("ownerActions").hidden,false);
});
test("10 invalid role refused",()=>{
 const d=demo();assert.equal(d.run("setRole('ADMIN')"),false);
 assert.match(d.get("currentRole").textContent,/CONTRIBUTOR/);
});
test("11 owner cannot submit",()=>{
 const d=demo();d.run("setRole('OWNER')");assert.equal(d.run("submitDemo()"),false);
});
test("12 contributor cannot approve original",()=>{
 const d=demo();d.run("submitDemo()");
 assert.equal(d.run("reviewOriginal('APPROVED')"),false);
});
test("13 owner can approve first unreviewed",()=>{
 const d=demo();d.run("submitDemo()");d.run("setRole('OWNER')");
 assert.equal(d.run("reviewOriginal('APPROVED')"),true);
 assert.match(d.get("originalsList").textContent,/APPROVED/);
});
test("14 owner can reject original",()=>{
 const d=demo();d.run("submitDemo()");d.run("setRole('OWNER')");
 assert.equal(d.run("reviewOriginal('REJECTED')"),true);
 assert.match(d.get("originalsList").textContent,/REJECTED/);
});
test("15 original cannot be reviewed twice",()=>{
 const d=demo();d.run("submitDemo()");d.run("setRole('OWNER')");
 d.run("reviewOriginal('APPROVED')");
 assert.equal(d.run("reviewOriginal('REJECTED')"),false);
});
test("16 amendment needs approved original",()=>{
 const d=demo();d.run("submitDemo()");
 assert.equal(d.run("amendDemo()"),false);
});
test("17 amendment separate from approved original",()=>{
 const d=demo();d.run("submitDemo()");d.run("setRole('OWNER')");
 d.run("reviewOriginal('APPROVED')");d.run("setRole('CONTRIBUTOR')");
 assert.equal(d.run("amendDemo()"),true);
 assert.match(d.get("originalsList").textContent,/ORIG #1.*APPROVED/);
 assert.match(d.get("amendmentsList").textContent,/AMEND #1 → ORIG #1 · UNREVIEWED/);
});
test("18 contributor cannot approve amendment",()=>{
 const d=demo();d.run("submitDemo()");d.run("setRole('OWNER')");
 d.run("reviewOriginal('APPROVED')");d.run("setRole('CONTRIBUTOR')");d.run("amendDemo()");
 assert.equal(d.run("reviewAmendment('APPROVED')"),false);
});
test("19 owner approves amendment preserving original",()=>{
 const d=demo();d.run("submitDemo()");d.run("setRole('OWNER')");
 d.run("reviewOriginal('APPROVED')");d.run("setRole('CONTRIBUTOR')");d.run("amendDemo()");
 d.run("setRole('OWNER')");
 assert.equal(d.run("reviewAmendment('APPROVED')"),true);
 assert.match(d.get("originalsList").textContent,/ORIG #1.*APPROVED/);
 assert.match(d.get("amendmentsList").textContent,/APPROVED/);
});
test("20 owner rejects amendment preserving original",()=>{
 const d=demo();d.run("submitDemo()");d.run("setRole('OWNER')");
 d.run("reviewOriginal('APPROVED')");d.run("setRole('CONTRIBUTOR')");d.run("amendDemo()");
 d.run("setRole('OWNER')");
 assert.equal(d.run("reviewAmendment('REJECTED')"),true);
 assert.match(d.get("originalsList").textContent,/ORIG #1.*APPROVED/);
});
test("21 lost response creates RESERVED",()=>{
 const d=demo();
 assert.equal(d.run("uncertainDemo()"),true);
 assert.match(d.get("originalsList").textContent,/RESERVED/);
});
test("22 reserved locks new submissions",()=>{
 const d=demo();d.run("uncertainDemo()");
 assert.equal(d.run("submitDemo()"),false);
 assert.equal(d.get("submitDemo").disabled,true);
});
test("23 reserved locks amendments",()=>{
 const d=demo();d.run("submitDemo()");d.run("setRole('OWNER')");
 d.run("reviewOriginal('APPROVED')");d.run("setRole('CONTRIBUTOR')");
 d.run("uncertainDemo()");
 assert.equal(d.run("amendDemo()"),false);
});
test("24 owner observation does not unlock RESERVED",()=>{
 const d=demo();d.run("uncertainDemo()");d.run("setRole('OWNER')");
 assert.equal(d.run("observeReserved()"),true);
 assert.match(d.get("originalsList").textContent,/RESERVED/);
 d.run("setRole('CONTRIBUTOR')");
 assert.equal(d.run("submitDemo()"),false);
});
test("25 RESERVED cannot be owner-approved",()=>{
 const d=demo();d.run("uncertainDemo()");d.run("setRole('OWNER')");
 assert.equal(d.run("reviewOriginal('APPROVED')"),false);
});
test("26 audit strictly appends observations",()=>{
 const d=demo();d.run("submitDemo()");d.run("setRole('OWNER')");
 d.run("reviewOriginal('APPROVED')");
 assert.match(d.get("auditList").textContent,/01 · ORIGINAL_SUBMITTED · #1\n02 · ORIGINAL_APPROVED · #1/);
});
test("27 reset clears only in-memory demo",()=>{
 const d=demo();d.run("uncertainDemo()");d.run("resetDemo()");
 assert.equal(d.get("originalCount").textContent,"0");
 assert.equal(d.get("auditList").textContent,"Nessun evento.");
});
test("28 sample instruments and market placeholders explicitly synthetic",()=>{
 assert.match(html,/SEGNAPOSTO LAB/);
 assert.match(script,/DEMO:EURUSD/);
 assert.match(html,/nessuna misura live/i);
});
test("29 UI doesn't claim actual access validation",()=>{
 assert.match(html,/NON È UN LOGIN O UNA PROVA DI SICUREZZA/);
 assert.match(html,/STAGING REALE NO-GO/);
});
test("30 list capacity is bounded",()=>{
 const d=demo();
 for(let i=0;i<12;i++)assert.equal(d.run("submitDemo()"),true);
 assert.equal(d.run("submitDemo()"),false);
});
