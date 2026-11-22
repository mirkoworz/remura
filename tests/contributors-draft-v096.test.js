// REMURA Contributors v0.96 LAB — server-contract intake alignment only.
const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs");
const core=require("../preview/contributors-draft-v096-core.js");
const NOW=Date.parse("2026-11-22T21:28:00Z");
const f=()=>({market:"XAUUSD",provider:"BROKER_A",ticker:"GOLD",product:"CFD",contract:"",
  period:"DAY",kind:"DELTA_PEAK",price:"4050,25000",anchor_utc:"2026-11-22T00:00:00Z",
  observed_utc:"2026-11-22T21:10:00Z",note:"Livello prova"});
const check=x=>core.validate({...f(),...x},NOW);
test("products mirror exact D1 catalog values, no SPOT_CFD or OTHER",()=>{
 assert.deepEqual(core.PRODUCTS,["SPOT","CFD","INDEX","FUTURE"]);
 assert.equal(check({product:"SPOT_CFD"}).ok,false);
 assert.equal(check({product:"OTHER"}).ok,false);
});
test("valid local proposal cannot falsely claim a server receipt or mapping",()=>{
 const r=check({});assert.equal(r.ok,true);
 assert.equal(r.draft.price,"4050.25");
 assert.equal(r.draft.schema,"remura.contributors.local_draft.v096");
 for(const k of ["sent_to_server","received_by_owner","approved","identity_verified","mapping_verified"])
 assert.equal(r.draft[k],false);
 assert.equal(r.draft.request_id,undefined);
});
test("all four valid product classes permitted without invented contract",()=>{
 for(const product of ["SPOT","CFD","INDEX"]){
  const a=check({product});assert.equal(a.ok,true,product);assert.equal(a.draft.contract,"");
 }
 const future=check({product:"FUTURE",contract:"GCZ6",ticker:"GC"});
 assert.equal(future.ok,true);assert.equal(future.draft.contract,"GCZ6");
});
test("future continuous ticker and missing contract denied like D1",()=>{
 assert.equal(check({product:"FUTURE",contract:""}).ok,false);
 assert.equal(check({product:"FUTURE",ticker:"GC1!",contract:"GCZ6"}).ok,false);
 assert.equal(check({product:"CFD",contract:"GCZ6"}).ok,false);
});
test("provider is actual server catalog identifier, not free-text brand",()=>{
 assert.equal(check({provider:"Broker Prova"}).ok,false);
 assert.equal(check({provider:"BROKER_A"}).ok,true);
 assert.equal(check({provider:" broker_a "}).draft.provider,"BROKER_A");
 assert.equal(check({provider:"TOO_LONG_PROVIDER_123"}).ok,false);
});
test("price uses strict D1 bounds and normalizes comma/trailing zeroes",()=>{
 assert.equal(core.canonicalPrice("1,23000"),"1.23");
 for(const p of ["0","-5","01.2","123456789","1e5","1.123456789","1,2,3"]){
  assert.equal(check({price:p}).ok,false,p);
 }
});
test("timestamp requires exact canonical UTC Z, not local offsets",()=>{
 for(const t of ["2026-11-22T21:10:00+01:00","2026-11-31T21:10:00Z",
   "2026-11-22T21:10:00.123Z","2026-11-22 21:10:00Z"]){
  assert.equal(check({observed_utc:t}).ok,false,t);
 }
});
test("future and reversed chronology fail closed",()=>{
 assert.equal(check({observed_utc:"2026-11-22T21:30:00Z"}).ok,false);
 assert.equal(check({anchor_utc:"2026-11-22T21:20:00Z"}).ok,false);
});
test("multi-line notes disallowed as they are in D1 server normalization",()=>{
 assert.equal(check({note:"abc\nxyz"}).ok,false);
 assert.equal(check({note:"X".repeat(281)}).ok,false);
 assert.equal(check({note:"ok"}).ok,true);
});
test("malformed fields or invalid methods fail with no JSON export",()=>{
 assert.equal(check({ticker:"EUR/JPY"}).ok,false);
 assert.equal(check({kind:"UNKNOWN"}).ok,false);
 assert.equal(check({period:"YEAR"}).ok,false);
 assert.equal(core.validate([],NOW).ok,false);
 assert.equal(core.exportJSON({...f(),price:"bad"},NOW).json,null);
});
test("new standalone iPhone page contains exact client rules, no network calls",()=>{
 const html=fs.readFileSync("preview/REMURA-Contributors-v096-iPhone-SERVER-CONTRACT-LAB.html","utf8");
 for(const p of ["SPOT","CFD","INDEX","FUTURE"])
   assert.ok(html.includes('<option value="'+p+'">'));
 assert.ok(html.includes("remura.contributors.local_draft.v096"));
 assert.ok(html.includes("v1.70 LAB"));
 assert.ok(html.includes("connect-src 'none'")&&html.includes("form-action 'none'"));
 assert.ok(!html.includes("fetch(")&&!html.includes("<script src="));
 assert.ok(html.includes("id=\"copy-json\"")&&html.includes('id="clear-all"'));
});
