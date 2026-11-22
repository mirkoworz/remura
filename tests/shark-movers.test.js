// REMURA Shark Movers v1.68 LAB — new product behavior only.
const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs");
const {scan}=require("../shark-movers-core.js");
function c(code,net1,net2,opt={}){
 return {code,id:code,name:"CFTC "+code,dataset:"tff",
   status:"CURRENT_REPORT_DATE",reportDate:"2026-11-17",
   labels:["Asset Manager","Leveraged Funds"],
   deltas:{first:net1,second:net2},source:"https://publicreporting.cftc.gov",
   ...opt};
}
test("same-Tuesday CFTC subset yields honest ordered public position changes",()=>{
 const result=scan([c("099741",3,-1),c("096742",-5,1),c("097741",1,2)]);
 assert.equal(result.status,"PUBLIC_COT_MOVERS_DESCRIPTIVE");
 assert.equal(result.reportDate,"2026-11-17");
 assert.deepEqual(result.items.map(x=>x.code),["096742","099741","097741"]);
 assert.equal(result.alignedContracts,3);
});
test("comparison never combines Tuesday 17 with an earlier Tuesday 10",()=>{
 const x=scan([c("099741",2,0),c("096742",12,0,{reportDate:"2026-11-10"})]);
 assert.equal(x.reportDate,"2026-11-17");
 assert.deepEqual(x.items.map(z=>z.code),["099741"]);
 assert.equal(x.excludedOtherWeeks,1);
});
test("a contract with the biggest Leveraged Funds movement labels that category",()=>{
 const x=scan([c("099741",1,-4)]);
 assert.equal(x.items[0].category,"Leveraged Funds");
 assert.equal(x.items[0].direction,"NET_DECREASE");
 assert.equal(x.items[0].netChangePp,-4);
});
test("Asset Manager net change up does not imply new buying",()=>{
 const x=scan([c("099741",2,-0.2)]);
 assert.equal(x.items[0].direction,"NET_INCREASE");
 assert.equal(x.items[0].claim,"AGGREGATE_FUTURES_NET_POSITION_CHANGE_ONLY");
 assert.equal(x.institutionalOrderFlow,false);
 assert.equal(x.tradingSignal,false);
 assert.equal(x.sourceTimeAttested,false);
});
test("Disaggregated labels are preserved, not cast to leveraged funds",()=>{
 const x=scan([c("088691",2,-3,{dataset:"disagg",labels:["Managed Money","Producer / Merchant"]})]);
 assert.equal(x.items[0].category,"Producer / Merchant");
 assert.equal(x.items[0].dataset,"disagg");
});
test("favorites-only includes only exact selected contract codes",()=>{
 const x=scan([c("099741",3,4),c("097741",-8,-1)],{favoritesOnly:true,favorites:["099741","FAKE"]});
 assert.deepEqual(x.items.map(y=>y.code),["099741"]);
});
test("empty favorites are not market short signals and report empty state",()=>{
 const x=scan([c("099741",3,4)],{favoritesOnly:true,favorites:[]});
 assert.equal(x.status,"WATCHLIST_EMPTY");
 assert.equal(x.items.length,0);
 assert.equal(x.tradingSignal,false);
});
test("stale, quarantined and missing CFTC weekly deltas are excluded",()=>{
 const x=scan([c("099741",3,4,{status:"STALE_REPORT"}),
   c("096742",5,3,{status:"QUARANTINE_CONFLICT"}),
   c("097741",3,2,{deltas:null})]);
 assert.equal(x.status,"NO_VERIFIED_WEEKLY_INPUT");
 assert.deepEqual(x.items,[]);
});
test("zero changes are not presented as movers",()=>{
 const x=scan([c("099741",0,0)]);
 assert.equal(x.status,"NO_NET_CHANGES");
 assert.equal(x.alignedContracts,1);
 assert.equal(x.items.length,0);
});
test("future/malformed date and nonfinite values fail closed",()=>{
 const x=scan([c("099741",4,1,{reportDate:"2026-11-31"}),
  c("096742",NaN,0),c("097741",3,0,{reportDate:"BAD"})]);
 assert.equal(x.items.length,0);
});
test("bounded view returns at most six, deterministic on ties",()=>{
 const x=scan([c("099741",3,0),c("096742",3,0),c("097741",3,0)],{limit:2});
 assert.deepEqual(x.items.map(y=>y.code),["096742","097741"]);
 assert.equal(x.items.length,2);
 assert.equal(scan([c("099741",3,0)],{limit:99}).status,"NO_VERIFIED_WEEKLY_INPUT");
});
test("browser page and UI render movers from existing cards without new fetch",()=>{
 const html=fs.readFileSync("shark-cockpit.html","utf8");
 const js=fs.readFileSync("shark-cockpit.js","utf8");
 const ui=fs.readFileSync("shark-movers-ui.js","utf8");
 const sw=fs.readFileSync("sw.js","utf8");
 for(const marker of ['id="movers-list"','id="movers-status"',"shark-movers-core.js?v=168","shark-movers-ui.js?v=168"])
   assert.ok(html.includes(marker),marker);
 assert.ok(js.includes("window.REMURA_SHARK_MOVERS_UI?.render(sorted"));
 assert.ok(js.includes('r.id="shark-contract-"+item.code'));
 assert.ok(ui.includes('document.getElementById("shark-contract-"+item.code)'));
 assert.ok(ui.includes("window.REMURA_SHARK_MOVERS_UI="));
 assert.ok(!ui.includes("fetch(")&&!ui.includes("private-api/"));
 assert.ok(sw.includes("./shark-movers-core.js")&&sw.includes("./shark-movers-ui.js"));
});
