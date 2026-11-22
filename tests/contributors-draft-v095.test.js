// REMURA Contributors v0.95 LAB — only new local iPhone intake behavior.
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const core=require("../preview/contributors-draft-v095-core.js");
const NOW=Date.parse("2026-11-22T21:20:00Z");
const fixture=()=>({market:"XAUUSD",provider:"Broker Prova",ticker:"GOLD",
  product:"SPOT_CFD",contract:"",period:"DAY",kind:"DELTA_PEAK",
  price:"4050,25",anchor_utc:"2026-11-22T00:00:00Z",
  observed_utc:"2026-11-22T21:10:00Z",note:"Livello di prova, non un trade"});
const check=(x,now=NOW)=>core.validate({...fixture(),...x},now);
test("real candidate fields become an unverified on-device draft, not a server receipt",()=>{
 const out=check({});
 assert.equal(out.ok,true);
 assert.equal(out.draft.price,"4050.25");
 assert.equal(out.draft.schema,"remura.contributors.local_draft.v095");
 assert.equal(out.draft.status,"LOCAL_ONLY_UNVERIFIED");
 for(const f of ["identity_verified","mapping_verified","sent_to_server","received_by_owner","approved"])
   assert.equal(out.draft[f],false);
 assert.equal(out.draft.request_id,undefined);
 assert.equal(out.draft.receipt_id,undefined);
});
test("case and whitespace normalization never fabricate a broker mapping",()=>{
 const a=check({market:" eurusd ",ticker:" eurusd.fxcm ",provider:" Test Broker ",price:"1,08270"});
 assert.equal(a.ok,true);
 assert.equal(a.draft.market,"EURUSD");
 assert.equal(a.draft.ticker,"EURUSD.FXCM");
 assert.equal(a.draft.provider,"Test Broker");
 assert.equal(a.draft.price,"1.08270");
 assert.equal(a.draft.mapping_verified,false);
});
test("futures require an explicit contract identifier, without auto-mapping",()=>{
 assert.equal(check({product:"FUTURE",contract:""}).ok,false);
 const r=check({product:"FUTURE",contract:"ESZ6",ticker:"ES",market:"US500"});
 assert.equal(r.ok,true);
 assert.equal(r.draft.contract,"ESZ6");
});
test("negative, zero, exponent, super-precision or text prices rejected",()=>{
 for(const x of ["-4","0","1e5","1.000000001","x","1.2.3","1000000000",""]){
   assert.equal(check({price:x}).ok,false,x);
 }
});
test("1–8 decimals and comma locale supported but still marked not verified",()=>{
 for(const p of ["1","1.1","1,00000001","999999999.99999999"]){
   const r=check({price:p});
   assert.equal(r.ok,true,p);
   assert.equal(r.draft.approved,false);
 }
});
test("missing instrument, unrecognized product and invalid ticker rejected",()=>{
 assert.equal(check({market:""}).ok,false);
 assert.equal(check({ticker:"<script>"}).ok,false);
 assert.equal(check({product:"OPTIONS"}).ok,false);
 assert.equal(check({provider:""}).ok,false);
});
test("period and methodology match candidate server contract only",()=>{
 assert.deepEqual(core.PERIODS,["DAY","WEEK","CURRENT_MONTH","PREVIOUS_MONTH"]);
 assert.deepEqual(core.KINDS,["DELTA_PEAK","EFFORT_RESULT","OTHER_VOLUME_LEVEL"]);
 assert.equal(check({kind:"HEDGE_FUND_INSIDER"}).ok,false);
 assert.equal(check({period:"YEAR"}).ok,false);
});
test("non-UTC, malformed calendar and fractional seconds forbidden",()=>{
 for(const v of ["2026-11-22T21:10:00+01:00","2026-11-31T21:10:00Z",
   "2026-11-22T21:10:00.500Z","2026-11-22 21:10:00Z",""]){
  assert.equal(check({observed_utc:v}).ok,false,v);
 }
});
test("observation cannot predate anchor, be in the future or older than 180 days",()=>{
 assert.equal(check({anchor_utc:"2026-11-22T21:15:00Z"}).ok,false);
 assert.equal(check({observed_utc:"2026-11-23T00:00:00Z"}).ok,false);
 assert.equal(check({anchor_utc:"2026-01-01T00:00:00Z",
  observed_utc:"2026-01-02T00:00:00Z"}).ok,false);
});
test("note cannot exceed 280 chars or include controls",()=>{
 assert.equal(check({note:"z".repeat(281)}).ok,false);
 assert.equal(check({note:"injection\u0000payload"}).ok,false);
 assert.equal(check({note:"abc\nseconda riga"}).ok,true);
});
test("JSON export stable and strictly local, with no invented owner approval",()=>{
 const r=core.exportJSON(fixture(),NOW);
 assert.equal(r.ok,true);
 const out=JSON.parse(r.json);
 assert.equal(out.sent_to_server,false);
 assert.equal(out.received_by_owner,false);
 assert.equal(out.approved,false);
 assert.equal(out.note,"Livello di prova, non un trade");
 assert.equal(core.exportJSON({...fixture(),price:"nope"},NOW).json,null);
});
test("null, invalid list and invalid timestamp inputs fail closed",()=>{
 assert.equal(core.validate(null,NOW).ok,false);
 assert.equal(core.validate([],NOW).ok,false);
 assert.equal(core.validate(fixture(),NaN).ok,false);
});
test("standalone iPhone page uses the existing contributor candidate field names",()=>{
 const p=fs.readFileSync("preview/REMURA-Contributors-v095-iPhone-LOCAL-DRAFT.html","utf8");
 for(const f of ["market","provider","ticker","product","contract","period",
                 "kind","price","anchor_utc","observed_utc","note"])
   assert.ok(p.includes('id="'+f+'"'),f);
 assert.ok(p.includes("contributors.local_draft.v095"));
 assert.ok(p.includes("REMURA · Aggiornamento v1.69 LAB"));
});
test("standalone page cannot call APIs or submit forms or load remote scripts",()=>{
 const p=fs.readFileSync("preview/REMURA-Contributors-v095-iPhone-LOCAL-DRAFT.html","utf8");
 assert.ok(p.includes("connect-src 'none'"));
 assert.ok(p.includes("form-action 'none'"));
 assert.ok(!p.includes("fetch("));
 assert.ok(!p.includes("XMLHttpRequest"));
 assert.ok(!p.includes("/api/submit"));
 assert.ok(!p.includes("<script src="));
 assert.ok(!p.includes("credentials:"));
 assert.ok(p.includes("LOCAL_ONLY_UNVERIFIED"));
 assert.ok(p.includes("Copia bozza"));
});
test("no autosaved contribution: values cleared on leaving the page",()=>{
 const p=fs.readFileSync("preview/REMURA-Contributors-v095-iPhone-LOCAL-DRAFT.html","utf8");
 assert.ok(p.includes('addEventListener("pagehide"'));
 assert.ok(!p.includes("localStorage.setItem"));
 assert.ok(!p.includes("sessionStorage.setItem"));
});
