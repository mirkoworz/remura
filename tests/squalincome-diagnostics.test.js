const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
require("../squalincome-diagnostics.js");
const diagnostics=globalThis.REMURA_SQUAL_DIAGNOSTICS;
const payload=(d,baselines=0,eventsTotal=0)=>({
  schema:"remura-squalincome-monitor-v1",enabled:true,baselines,eventsTotal,
  lastEvents:[],diagnostics:d
});
const valid=()=>({
  lastScanAt:"2026-10-25T08:26:00+00:00",trackedMarkets:34,analyzed:0,excluded:34,
  outcome:"data_insufficient",newBaselines:0,newEvents:0,
  exclusionReasons:{market_closed:34,cot_group_conflict:13,cot_no_direction:4},
  exclusions:Array.from({length:34},(_,i)=>({symbol:"XAU"+String(i).padStart(3,"0"),
    reasons:["market_closed",...(i<13?["cot_group_conflict"]:i<17?["cot_no_direction"]:[])]}))
});
test("never confuse first unscanned VPS with zero meaningful events",()=>{
  assert.equal(diagnostics.read(payload(null)).kind,"not_scanned");
  const legacy=payload(null); delete legacy.diagnostics;
  assert.equal(diagnostics.read(legacy).kind,"legacy");
  assert.equal(diagnostics.read(payload(valid())).outcome,"data_insufficient");
  assert.equal(diagnostics.read(payload(valid())).displayOutcome,"market_closed");
  const scan={...valid(),analyzed:34,excluded:0,exclusionReasons:{},exclusions:[],
    outcome:"no_significant_event"};
  const view=diagnostics.read(payload(scan,34));
  assert.equal(view.outcome,"no_significant_event");
  assert.equal(view.displayOutcome,"no_significant_event");
  assert.equal(view.analyzed,34);
  assert.equal(view.baselines,34);
});
test("diagnostics show real rejection reasons without treating them as distinct markets",()=>{
  const view=diagnostics.read(payload(valid(),0,0));
  assert.equal(view.excluded,34);
  assert.equal(view.reasons.reduce((n,r)=>n+r.count,0),51);
  assert.equal(view.reasons[0].code,"market_closed");
  assert.ok(view.date.includes("25/10/2026"));
  assert.equal(view.exclusions.length,34);
});
test("reject inconsistent counters and unknown schema rather than guessing",()=>{
  assert.equal(diagnostics.read(payload({...valid(),analyzed:1})).kind,"invalid");
  assert.equal(diagnostics.read({...payload(valid()),schema:"unknown"}),null);
});
test("only whitelisted codes are displayed, never leak diagnostic free text",()=>{
  const scan=valid();
  scan.exclusionReasons={scan_error:1,secret_api_token:15};
  scan.exclusions=[...scan.exclusions.slice(0,33),{symbol:"EURUSD",reasons:["scan_error","secret_api_token"]}];
  const view=diagnostics.read(payload(scan));
  assert.equal(view.reasons.length,1);
  assert.equal(view.exclusions.at(-1).labels.length,1);
  assert.ok(!JSON.stringify(view).includes("secret_api_token"));
});
test("weekend alone is clearly separated from genuine data gaps",()=>{
  const closed=valid();
  assert.equal(diagnostics.read(payload(closed)).displayOutcome,"market_closed");
  const cotMissing=structuredClone(closed);
  cotMissing.exclusionReasons.cot_missing=1;
  cotMissing.exclusions[0].reasons.push("cot_missing");
  assert.equal(diagnostics.read(payload(cotMissing)).displayOutcome,"data_insufficient");
  const barsBroken=structuredClone(closed);
  barsBroken.exclusionReasons.price_error=1;
  barsBroken.exclusions[0].reasons.push("price_error");
  assert.equal(diagnostics.read(payload(barsBroken)).displayOutcome,"data_insufficient");
  const unknown=structuredClone(closed);
  unknown.exclusionReasons.unrecognized_error=1;
  unknown.exclusions[0].reasons.push("unrecognized_error");
  assert.equal(diagnostics.read(payload(unknown)).displayOutcome,"data_insufficient");
});
test("open or mixed markets cannot be reported as wholly closed",()=>{
  const mixed=valid();
  mixed.analyzed=1;
  mixed.excluded=33;
  mixed.exclusions.pop();
  assert.equal(diagnostics.read(payload(mixed)).displayOutcome,"data_insufficient");
  const notClosed=valid();
  notClosed.exclusions[0].reasons=["cot_group_conflict"];
  assert.equal(diagnostics.read(payload(notClosed)).displayOutcome,"data_insufficient");
  const clean=valid();
  clean.analyzed=34;
  clean.excluded=0;
  clean.exclusions=[];
  clean.exclusionReasons={};
  clean.outcome="no_significant_event";
  assert.equal(diagnostics.read(payload(clean)).displayOutcome,"no_significant_event");
});
test("v1.36 shows real distinct timeframe stamps and seven stored observations",()=>{
  const snapshot=valid();
  snapshot.markets=snapshot.exclusions.map((row,i)=>({
    symbol:row.symbol,analyzed:false,
    timeframes:{
      M15:{lastClosedAt:"2026-10-26T10:45:00+00:00",ageMinutes:15,bars:1657},
      H1:{lastClosedAt:"2026-10-26T10:00:00+00:00",ageMinutes:60,bars:414},
      H4:{lastClosedAt:"2026-10-26T08:00:00+00:00",ageMinutes:180,bars:99}
    }
  }));
  snapshot.updatedObservations=2;
  const base=payload(snapshot,7,0);
  base.observations=Array.from({length:7},(_,i)=>({
    symbol:"EUR"+String(i).padStart(3,"0"),state:"aligned",priceState:"watch",
    reportDate:"2026-10-20",priceTime:"2026-10-26T10:45:00+00:00",
    observedAt:"2026-10-26T11:00:00+00:00"
  }));
  const view=diagnostics.read(base);
  assert.equal(view.markets.length,34);
  assert.equal(view.markets[0].frames.M15.ageMinutes,15);
  assert.equal(view.markets[0].frames.H1.ageMinutes,60);
  assert.equal(view.markets[0].frames.H4.ageMinutes,180);
  assert.equal(view.updatedObservations,2);
  assert.equal(view.observations.length,7);
  assert.equal(view.baselines,7);
});
test("v1.36 refuses fabricated frames and clearly separates trend from OHLC errors",()=>{
  assert.match(diagnostics.REASONS.ohlc_mismatch,/candele/);
  assert.match(diagnostics.REASONS.trend_disagreement,/tendenze/i);
  const snapshot=valid();
  snapshot.exclusions[0].reasons=["ohlc_mismatch"];
  snapshot.exclusionReasons={ohlc_mismatch:1};
  const view=diagnostics.read(payload(snapshot));
  assert.equal(view.displayOutcome,"data_insufficient");
  assert.match(view.exclusions[0].labels[0],/H1\/H4/);
  const legacy=diagnostics.read(payload(valid()));
  assert.equal(legacy.markets.length,0);
  assert.equal(legacy.observations.length,0);
  snapshot.markets=[{symbol:"BAD",analyzed:true,timeframes:{}}];
  assert.equal(diagnostics.read(payload(snapshot)).kind,"invalid");
});
test("v1.37 interprets verified directional history without inventing older samples",()=>{
  const p=payload(valid(),13,0);
  p.historyTotal=2;
  p.history=[
    {symbol:"NZDJPY",state:"divergent",cotSide:-1,priceSide:1,h4Side:1,h1Side:1,m15Side:0,
     priceState:"watch",reportDate:"2026-10-20",priceTime:"2026-10-27T05:15:00+00:00",
     observedAt:"2026-10-27T05:20:00+00:00",cotWeekly:-8.4,cotSustained:1,
     origin:"first_after_upgrade",eventType:null},
    {symbol:"NZDJPY",state:"aligned",cotSide:-1,priceSide:-1,h4Side:-1,h1Side:-1,m15Side:-1,
     priceState:"confirmed",reportDate:"2026-10-20",priceTime:"2026-10-27T05:30:00+00:00",
     observedAt:"2026-10-27T05:35:00+00:00",cotWeekly:-8.4,cotSustained:1,
     origin:"update",eventType:"new_convergence"}
  ];
  const out=diagnostics.read(p);
  assert.equal(out.historyTotal,2);
  assert.equal(out.history.length,2);
  assert.equal(out.history[0].origin,"first_after_upgrade");
  assert.equal(out.history[0].h4Side,1);
  assert.equal(out.history[1].priceSide,-1);
  assert.equal(out.history[1].eventType,"new_convergence");
  assert.equal(out.baselines,13);
});
test("v1.37 never displays unsanitized or guessed directions or sentiment",()=>{
  const p=payload(valid());
  p.historyTotal=2;
  p.history=[
    {symbol:"EURUSD",state:"divergent",cotSide:1,priceSide:-1,
     h4Side:9,h1Side:null,m15Side:null,priceState:"watch",
     reportDate:"2026-10-20",priceTime:"2026-10-27T04:00:00+00:00",
     observedAt:"2026-10-27T05:00:00+00:00",cotWeekly:NaN,cotSustained:0,
     origin:"baseline",eventType:"secret_token"},
    {symbol:"MY_SECRET",state:"aligned",cotSide:1,priceSide:1,
     priceState:"confirmed",reportDate:"2026-10-20",
     priceTime:"2026-10-27T05:30:00+00:00",observedAt:"2026-10-27T05:40:00+00:00",
     origin:"update",eventType:"new_convergence"}
  ];
  const out=diagnostics.read(p);
  assert.equal(out.history.length,1);
  assert.equal(out.history[0].h4Side,null);
  assert.equal(out.history[0].cotWeekly,null);
  assert.equal(out.history[0].eventType,null);
  assert.ok(!JSON.stringify(out.history).includes("secret"));
  const old=payload(valid(),13);
  assert.equal(diagnostics.read(old).history.length,0);
  assert.equal(diagnostics.read(old).historyTotal,null);
});
test("v1.38 models discrete observed changes, not synthetic continuous movement",()=>{
  const p=payload(valid(),13);
  p.historyTotal=3;
  const base={symbol:"GBPNZD",state:"divergent",cotSide:1,priceSide:-1,
    h4Side:-1,h1Side:-1,m15Side:-1,reportDate:"2026-10-20",
    cotWeekly:11.03,cotSustained:1,origin:"update",eventType:null};
  p.history=[
    {...base,priceState:"partial",priceTime:"2026-10-27T10:15:00+00:00",
      observedAt:"2026-10-27T10:24:00+00:00"},
    {...base,priceState:"watch",origin:"first_after_upgrade",priceTime:"2026-10-27T08:15:00+00:00",
      observedAt:"2026-10-27T08:24:00+00:00"},
    {...base,priceState:"confirmed",priceTime:"2026-10-27T12:15:00+00:00",
      observedAt:"2026-10-27T12:24:00+00:00"}
  ];
  const view=diagnostics.read(p);
  const m=diagnostics.evolutionModel(view.history);
  assert.equal(m.length,1);
  assert.equal(m[0].symbol,"GBPNZD");
  assert.equal(m[0].points.length,3); // no synthetic intermediate bars
  assert.equal(m[0].changes.length,2);
  assert.equal(m[0].verifiedEvents,0); // technical confirmations are NOT events
  assert.equal(m[0].divergentSamples,3);
  assert.deepEqual(m[0].changes[1].labels,["conferma tecnica parziale → conferma tecnica"]);
  assert.equal(m[0].last.priceTime,"2026-10-27T12:15:00+00:00");
});
test("v1.38 honors only backend-qualified events and keeps weekly COT separate",()=>{
  const p=payload(valid());
  p.historyTotal=2;
  p.history=[
    {symbol:"EURGBP",state:"aligned",cotSide:-1,priceSide:-1,h4Side:-1,h1Side:-1,m15Side:0,
     priceState:"watch",reportDate:"2026-10-20",priceTime:"2026-10-27T08:15:00+00:00",
     observedAt:"2026-10-27T08:25:00+00:00",cotWeekly:-5.71,cotSustained:1,
     origin:"baseline",eventType:null,token:"PRIVATE"},
    {symbol:"EURGBP",state:"divergent",cotSide:-1,priceSide:1,h4Side:1,h1Side:1,m15Side:1,
     priceState:"confirmed",reportDate:"2026-10-20",priceTime:"2026-10-27T10:15:00+00:00",
     observedAt:"2026-10-27T10:25:00+00:00",cotWeekly:-5.71,cotSustained:1,
     origin:"update",eventType:"new_divergence"}
  ];
  const view=diagnostics.read(p);
  assert.equal(view.history.length,2);
  assert.ok(!JSON.stringify(view.history).includes("PRIVATE"));
  const model=diagnostics.evolutionModel(view.history);
  assert.equal(model[0].verifiedEvents,1);
  assert.ok(model[0].changes[0].labels.includes("concordanza → divergenza"));
  assert.ok(model[0].changes[0].labels.some(x=>x.includes("EVENTO verificato")));
  assert.equal(model[0].changes[0].labels.some(x=>x.includes("nuova osservazione COT")),false);
});
test("v1.38 filter buttons really filter markets, without inventing signals",()=>{
  class Node {
    constructor(tag){this.tag=tag;this.children=[];this.attributes={};this.handlers={};this.style={};this.textContent="";this.className="";}
    append(...nodes){this.children.push(...nodes);}
    replaceChildren(...nodes){this.children=[...nodes];}
    setAttribute(key,val){this.attributes[key]=val;}
    addEventListener(key,fn){this.handlers[key]=fn;}
  }
  const doc=globalThis.document;
  globalThis.document={createElement:tag=>new Node(tag)};
  try {
    const scan=valid();scan.exclusions=scan.exclusions.slice(2);scan.analyzed=2;scan.excluded=32;
    scan.outcome="no_significant_event";
    const p=payload(scan,13);
    p.historyTotal=2;
    const template={h4Side:1,h1Side:1,m15Side:1,priceState:"confirmed",
       reportDate:"2026-10-20",priceTime:"2026-10-27T11:15:00+00:00",
       observedAt:"2026-10-27T11:25:00+00:00",cotWeekly:4.79,
       cotSustained:1,origin:"update",eventType:null};
    p.history=[
      {...template,symbol:"GBPAUD",cotSide:1,priceSide:-1,h4Side:-1,h1Side:-1,m15Side:-1,state:"divergent"},
      {...template,symbol:"EURGBP",cotSide:1,priceSide:1,state:"aligned"}
    ];
    const host=new Node("div");
    assert.equal(diagnostics.render(p,host),true);
    const walk=(node)=>[node,...node.children.flatMap(walk)];
    const radar=walk(host).find(x=>x.className==="monitor-evolution radar-evolution");
    assert.ok(radar);
    const results=walk(radar).find(x=>x.className==="radar-evolution-results");
    const buttons=walk(radar).filter(x=>x.className==="radar-filter");
    assert.equal(buttons.length,4);
    assert.deepEqual(buttons.map(x=>x.textContent),["Tutti (2)","Divergenti (1)","Concordi (1)","Eventi verificati (0)"]);
    assert.equal(buttons[0].attributes["aria-pressed"],"true");
    assert.equal(results.children.length,2);
    const cells=walk(results).filter(x=>x.className==="radar-matrix-cell");
    assert.equal(cells.length,14); // 2 source-backed samples, 7 lanes per sample
    const scroll=walk(results).filter(x=>x.className==="radar-matrix-scroll");
    assert.equal(scroll.length,2);
    assert.ok(scroll.every(x=>x.tabIndex===0 && x.attributes.role==="region"));
    assert.ok(walk(results).some(x=>x.className==="radar-stamp-date"));
    assert.ok(walk(results).some(x=>x.className==="radar-legend"));
    buttons[1].handlers.click();
    assert.equal(buttons[1].attributes["aria-pressed"],"true");
    assert.equal(results.children.length,1);
    assert.equal(walk(results).filter(x=>x.className==="radar-evolution-name")[0].textContent,"GBPAUD");
    buttons[3].handlers.click();
    assert.equal(results.children.length,1);
    assert.ok(walk(results).some(x=>x.textContent.includes("Nessun evento COT/prezzo qualificato")));
    assert.ok(!walk(host).some(x=>String(x.textContent).includes("PRIVATE")));
  } finally {
    globalThis.document=doc;
  }
});
test("v1.39 CSS constrains every ancestor of the scrollable radar and keeps filters readable on iPhone",()=>{
  const html=fs.readFileSync("mercati.html","utf8");
  const css=html.split("<style>")[1].split("</style>")[0];
  assert.match(css,/\.monitor-diagnostics,\.radar-evolution,\.radar-evolution-results\{grid-template-columns:minmax\(0,1fr\)\}/);
  assert.match(css,/\.radar-evolution-card\{width:100%;overflow:hidden\}/);
  assert.match(css,/\.radar-matrix-scroll\{[\s\S]*?overflow-x:auto;/);
  assert.match(css,/\.radar-evolution-top\{display:grid;grid-template-columns:minmax\(0,1fr\)/);
  assert.match(css,/@media\(max-width:650px\)\{[\s\S]*?\.radar-filters\{grid-template-columns:repeat\(2,minmax\(0,1fr\)\)/);
  assert.match(css,/\.radar-filter\[aria-pressed="true"\]/);
  assert.match(css,/\.radar-state\{max-width:100%;min-width:0;overflow-wrap:anywhere/);
  assert.match(css,/\.radar-stamp-date/);
  assert.ok(!css.includes("overflow-x:visible"));
});
test("v1.39 never equates a weekly COT delta with a net short position or technical confirmation with an institutional trade",()=>{
  const js=fs.readFileSync("squalincome-diagnostics.js","utf8");
  assert.match(js,/Δ COT settimanale/);
  assert.match(js,/NON equivale necessariamente a posizione netta long\/short/);
  assert.match(js,/non conferma un'operazione istituzionale/);
  assert.match(js,/Idonei nella scansione corrente/);
  assert.match(js,/Il Radar storico può contenerne più/);
  assert.match(js,/Nessun evento COT\/prezzo qualificato/);
  assert.match(js,/scroll\.tabIndex=0/);
});
test("v1.39 preserves truthful radar totals from 11 market histories independent of scan eligibility",()=>{
  const basis={h4Side:1,h1Side:1,m15Side:1,priceState:"watch",
    reportDate:"2026-10-20",priceTime:"2026-10-27T12:15:00+00:00",
    observedAt:"2026-10-27T12:25:00+00:00",cotWeekly:-2.12,
    origin:"update",cotSustained:1,eventType:null};
  const p=payload({...valid(),analyzed:6,excluded:28,
    exclusions:valid().exclusions.slice(0,28),outcome:"no_significant_event"},13,0);
  p.historyTotal=11;
  p.history=Array.from({length:11},(_,i)=>{
    const divergent=i<7;
    return {...basis,symbol:"EUR"+String(i).padStart(3,"0"),
      cotSide:-1,priceSide:divergent?1:-1,
      state:divergent?"divergent":"aligned"};
  });
  const view=diagnostics.read(p),models=diagnostics.evolutionModel(view.history);
  assert.equal(view.tracked,34);
  assert.equal(view.analyzed,6);
  assert.equal(view.excluded,28);
  assert.equal(models.length,11);
  assert.equal(models.filter(x=>x.last.state==="divergent").length,7);
  assert.equal(models.filter(x=>x.last.state==="aligned").length,4);
  assert.equal(models.filter(x=>x.verifiedEvents>0).length,0);
  assert.equal(models.reduce((n,x)=>n+x.points.length,0),11);
});
test("Radar Squali wires only private endpoint and same-origin script",()=>{
  const html=fs.readFileSync("mercati.html","utf8");
  assert.ok(html.includes('id="monitor-diagnostics"'));
  assert.ok(html.includes('squalincome-diagnostics.js?v=139'));
  assert.ok(html.includes("./private-api/signals/status"));
});
