const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs");
const core=require("../squalo-verdict-core.js");
const NOW=Date.parse("2026-10-24T10:00:00Z");
const fresh=stamp=>new Date(stamp).toISOString();
const market=(state="confirmed",side=1,latest="2026-10-23T20:45:00Z")=>({
 state,side,metrics:{M15:{latest}}
});
const cot=(bias=1,state="trend")=>({state,bias,sustained:state==="trend",stale:false,conflict:false});
const mfb=(pct=20)=>({fresh:true,current:{t:fresh(NOW-1e5),lLots:pct,sLots:100-pct,lPos:80,sPos:80}});
const capital=(pct=80)=>({fresh:true,current:{t:fresh(NOW-1e5),lPct:pct,sPct:100-pct}});
test("Concordant COT and broker price are labelled traces, never trade signals",()=>{
 const result=core.evaluate({symbol:"EURUSD",cot:cot(),price:market(),myfxbook:mfb(),capital:capital(),macro:{state:"easing",label:"Volatilità in calo",historical:true},now:NOW});
 assert.equal(result.state,"aligned");assert.equal(result.side,1);
 assert.match(result.title,/Tracce concordi/);
 assert.match(result.retailNotes.join(" "),/Myfxbook presenta un estremo retail opposto/);
 assert.match(result.retailNotes.join(" "),/Capital.com presenta un estremo retail nella stessa direzione/);
 assert.equal(result.items.macro.status,"historical");
 assert.match(result.note,/Nessuna probabilità/);
});
test("Divergence between COT and H4/H1 is explicit without directional verdict",()=>{
 const r=core.evaluate({symbol:"EURUSD",cot:cot(-1),price:market("watch",1),now:NOW});
 assert.equal(r.state,"divergent");assert.equal(r.side,0);
 assert.match(r.narrative,/in contrasto|mentre/);
});
test("DAX and VIX with no matching COT cannot be promoted to institutional trend",()=>{
 const r=core.evaluate({symbol:"GER30",cot:null,price:market(),myfxbook:mfb(15),now:NOW});
 assert.equal(r.state,"incomplete");assert.equal(r.side,0);
 assert.equal(r.items.cot.status,"missing");
 assert.match(r.items.cot.detail,/Nessuna posizione istituzionale/);
});
test("Weekend candles can be historic, but expired price, stale COT and stale retail never vote",()=>{
 const week=core.evaluate({symbol:"XAUUSD",cot:cot(),price:market("confirmed",1,"2026-10-23T20:45:00Z"),now:NOW});
 assert.equal(week.state,"aligned");
 const expired=core.evaluate({symbol:"XAUUSD",cot:cot(),price:market("confirmed",1,"2026-10-19T20:45:00Z"),now:NOW});
 assert.equal(expired.state,"stale");assert.equal(expired.side,0);
 assert.equal(core.retailEvidence({fresh:true,current:{t:"2026-10-22T09:00:00Z",lLots:75,sLots:25,lPos:80,sPos:60}},"Myfxbook",NOW).status,"stale");
 const c=core.evaluate({symbol:"EURUSD",cot:{...cot(),stale:true,state:"stale"},price:market(),now:NOW});
 assert.equal(c.state,"stale");assert.equal(c.side,0);
});
test("Neutral, conflict and malformed retail inputs do not produce false institutional evidence",()=>{
 assert.equal(core.evaluate({cot:cot(),price:market("conflict",0),now:NOW}).state,"mixed");
 assert.equal(core.retailEvidence({fresh:true,current:{t:fresh(NOW),lLots:50,sLots:50,lPos:2,sPos:4}},"Myfxbook",NOW).status,"missing");
 assert.equal(core.retailEvidence({fresh:true,current:{t:fresh(NOW),lPct:160}},"Capital.com",NOW).status,"missing");
 assert.equal(core.macroEvidence({state:"unavailable"}).status,"missing");
});
test("All market pages use the same combined renderer without exposing credentials",()=>{
 const html=fs.readFileSync("asset.html","utf8"),script=fs.readFileSync("squalo-verdict.js","utf8");
 assert.ok(html.includes('id="squalo-verdict"'));
 assert.ok(html.includes('squalo-verdict-core.js'));
 assert.ok(html.includes('squalo-verdict.js'));
 for(const name of ["remura:cot","remura:price","remura:retail","remura:capital"])
  assert.ok(script.includes(name),name);
 assert.ok(script.includes("window.REMURA_PRICE_STATUS_CORE"));
 assert.ok(script.includes("REMURA_VERDICT_SNAPSHOTS"));
 assert.ok(html.includes("window.REMURA_VERDICT_SNAPSHOTS=Object.create(null)"));
 assert.ok(!script.includes("api_key")&&!script.includes("Bearer "));
});
