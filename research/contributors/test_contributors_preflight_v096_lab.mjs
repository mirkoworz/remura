// REMURA Contributors v0.96 LAB — NEW pre-submit checks only (no old security suites rerun).
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {inspectLevelV096,summaryLevelV096} from "./contributors_levels_preflight_v096_lab.mjs";
import {normalize} from "./d1_lab_adapter.mjs";
const NOW_ISO="2026-11-22T21:28:00Z", NOW=Date.parse(NOW_ISO);
const REQUEST="12345678-1234-4234-9234-123456789abc";
const map=()=>({market:"XAUUSD",provider:"BROKER_A",ticker:"GOLD",product:"CFD",contract:""});
const field=(m=map())=>({...m,period:"DAY",kind:"DELTA_PEAK",price:"4050,25",
 anchor_utc:"2026-11-22T00:00:00Z",observed_utc:"2026-11-22T21:10:00Z",
 note:"Segnale di prova, non un trade"});
const check=(m=map(),f=field(m),now=NOW)=>inspectLevelV096(m,f,now);
test("same CFTC-independent D1 intake fields and order survive client preflight",()=>{
 const a=check();assert.equal(a.ok,true);
 assert.equal(a.data.price,"4050.25");
 const out=normalize({request_id:REQUEST,...a.data},NOW_ISO);
 assert.equal(out.price,"4050.25");
 assert.equal(out.market,"XAUUSD");
 assert.equal(a.requestIdGenerated,false);
 assert.equal(a.serverReceipt,false);
});
test("every server-supported candidate product maps cleanly to D1 exact schema",()=>{
 for(const product of ["SPOT","CFD","INDEX","FUTURE"]){
  const m={...map(),product,contract:product==="FUTURE"?"ESZ6":""};
  const f=field(m); const a=check(m,f);
  assert.equal(a.ok,true,product);
  assert.equal(normalize({request_id:REQUEST,...a.data},NOW_ISO).product,product);
 }
});
test("price canonicalizes comma and trailing zeros exactly as D1",()=>{
 const f={...field(),price:"4050,25000"};const a=check(map(),f);
 assert.equal(a.ok,true);assert.equal(a.data.price,"4050.25");
 assert.equal(normalize({request_id:REQUEST,...a.data},NOW_ISO).price,"4050.25");
});
test("unauthorized mapping substitution rejected before any mutation path",()=>{
 const f={...field(),provider:"BROKER_B"};
 const a=check(map(),f);
 assert.equal(a.ok,false);assert.equal(a.reason,"mapping_mismatch");
 assert.equal(a.data,null);assert.equal(a.authorizes,false);
});
test("non-catalog broker name or malformed market rejected locally",()=>{
 const m={...map(),provider:"Broker con spazi"};
 assert.equal(check(m,field(m)).reason,"catalog_mapping_invalid");
 const x={...map(),market:"XAU/USD"};
 assert.equal(check(x,field(x)).ok,false);
});
test("unlisted product and future without a specific contract denied",()=>{
 const a={...map(),product:"SPOT_CFD"};assert.equal(check(a,field(a)).ok,false);
 const b={...map(),product:"FUTURE",contract:""};assert.equal(check(b,field(b)).ok,false);
 const c={...map(),product:"FUTURE",contract:"ESZ6",ticker:"ES1!"};
 assert.equal(check(c,field(c)).ok,false);
});
test("zero, negative, exponent, leading zero or overprecision prices denied",()=>{
 for(const price of ["0","-1","1e2","01.12","1.123456789","123456789.1"]){
  assert.equal(check(map(),{...field(),price}).reason,"price_invalid",price);
 }
});
test("UTC noncanonical, reversed or future observation denied",()=>{
 assert.equal(check(map(),{...field(),anchor_utc:"2026-11-22T00:00:00+00:00"}).ok,false);
 assert.equal(check(map(),{...field(),anchor_utc:"2026-11-22T21:20:00Z"}).ok,false);
 assert.equal(check(map(),{...field(),observed_utc:"2026-11-22T21:29:00Z"}).ok,false);
});
test("notes with line break or control characters do not slip through",()=>{
 for(const note of ["Riga uno\nRiga due","a\u007fb","a".repeat(281)]){
  assert.equal(check(map(),{...field(),note}).reason,"note_invalid");
 }
});
test("pre-submit review is readable but never constitutes a receipt or authorization",()=>{
 const a=check();
 const text=summaryLevelV096(a.data);
 assert.ok(text.includes("Broker: BROKER_A"));
 assert.ok(text.includes("Prezzo: 4050.25"));
 assert.ok(text.includes("nessun dato ancora inviato"));
 assert.equal(a.authorizes,false);
 assert.equal(a.serverAccessVerified,false);
 assert.equal(a.data.request_id,undefined);
});
test("protected candidate UI preserves read server, durable state, no retry and confirmation order",()=>{
 const js=fs.readFileSync(new URL("./contributors_levels_ui_v096_lab.mjs",import.meta.url),"utf8");
 const html=fs.readFileSync(new URL("./contributors_levels_v096_lab.html",import.meta.url),"utf8");
 assert.ok(js.includes('client.read("/api/profile"'));
 assert.ok(js.includes('client.read("/api/catalog"'));
 assert.ok(js.includes("client.read('/api/level-attempt/status'"));
 assert.ok(js.includes('client.mutate("/api/submit",p,current)'));
 assert.ok(js.includes("serverBlocked=true;states()"));
 assert.ok(js.indexOf("const review=inspectLevelV096(")<js.indexOf("globalThis.confirm(confirmation)"));
 assert.ok(js.indexOf("globalThis.confirm(confirmation)")<js.indexOf("request_id:crypto.randomUUID()"));
 assert.ok(js.indexOf("request_id:crypto.randomUUID()")<js.indexOf('client.mutate("/api/submit",p,current)'));
 assert.ok(js.includes("client.uncertain"));
 assert.ok(html.includes('src="./contributors_levels_ui_v096_lab.mjs"'));
 assert.ok(html.includes("CANDIDATO LAB")&&html.includes("NON DISTRIBUITO"));
});
test("new UI variant does not change current backend assets, API security or production",()=>{
 const js=fs.readFileSync(new URL("./contributors_levels_ui_v096_lab.mjs",import.meta.url),"utf8");
 const asset=fs.readFileSync(new URL("./private_assets_v078_lab.mjs",import.meta.url),"utf8");
 assert.ok(js.includes('import {CandidateClientV076}'));
 assert.ok(!js.includes("setInterval(")&&!js.includes("setTimeout("));
 assert.ok(!asset.includes("contributors_levels_ui_v096_lab.mjs"));
});
