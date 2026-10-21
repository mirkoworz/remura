/* Offline tests of the compact multi-source iPhone dashboard. */
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const script=fs.readFileSync(path.join(__dirname,"../quicklook.js"),"utf8");
function run(symbol="EURUSD"){
  const elements=new Map();
  const events=new Map();
  function node(id,text=""){
    const item={id,textContent:text,className:"",setAttribute(){}};
    elements.set(id,item);
    return item;
  }
  const alert=node("alert");
  alert.insertAdjacentElement=(position,item)=>{
    assert.equal(position,"afterend");
    elements.set(item.id,item);
  };
  const document={
    getElementById:id=>elements.get(id)||null,
    createElement:()=>({
      setAttribute(){},
      set innerHTML(html){
        this.html=html;
        for(const [,id] of html.matchAll(/id="([^"]+)"/g))node(id);
      }
    })
  };
  const window={
    location:{search:"?symbol="+symbol},
    REMURA_MARKETS:{symbols:["EURUSD","XAUUSD"]},
    addEventListener:(name,fn)=>events.set(name,fn),
    setTimeout:fn=>fn()
  };
  vm.runInNewContext(script,{document,window,URLSearchParams});
  const send=(name,market=symbol)=>events.get(name)({detail:{symbol:market}});
  const read=id=>elements.get(id)?.textContent;
  return {node,read,send,elements};
}

test("quicklook creates a separate, accessible summary and deep links",()=>{
  const {read,elements}=run();
  assert.equal(read("rq-symbol"),"EURUSD");
  const view=elements.get("remura-quicklook");
  assert.match(view.html,/href="#rm-insights"/);
  assert.match(view.html,/href="#remura-price-engine"/);
  assert.match(view.html,/href="#retail-module"/);
  assert.match(view.html,/href="#remura-multisource"/);
  assert.match(view.html,/quote/i);
  assert.match(read("rq-retail-main"),/N\/D/);
});

test("quicklook updates on source events without creating trading signals",()=>{
  const {node,read,send}=run();
  node("rm-state","Dati discordanti");
  node("rm-title","Asset Manager e Leveraged Funds non allineati");
  node("r-status","Myfxbook · rilevato");
  node("r-lp","82,5%");
  node("r-sp","17,5%");
  node("r-updated","21/10/2026, 18:24");
  node("rp-state","Segnali discordanti");
  node("rp-h4","Rialzista");
  node("rp-h1","Neutrale");
  node("rp-m15","Ribassista");
  node("rp-last","Ultima M15 chiusa: 21/10/2026, 18:00");

  send("remura:cot");
  send("remura:retail");
  send("remura:price");
  assert.equal(read("rq-cot-main"),"Dati discordanti");
  assert.match(read("rq-retail-main"),/82,5% long · 17,5% short/);
  assert.match(read("rq-price-main"),/H4 Rialzista · H1 Neutrale · M15 Ribassista/);
  assert.match(read("rq-retail-details"),/Quote lotti, non posizioni istituzionali/);
  send("remura:retail","XAUUSD"); // Ignore an update for another market.
  assert.equal(read("rq-retail-main"),"82,5% long · 17,5% short");
});

test("stale retail must remain labeled; missing feed suppresses percentages",()=>{
  const {node,read,send}=run();
  node("r-lp","80%");
  node("r-sp","20%");
  node("r-status","Myfxbook · datato");
  send("remura:retail");
  assert.match(read("rq-retail-details"),/datato/);
  node("r-status","Myfxbook non collegato");
  send("remura:retail");
  assert.equal(read("rq-retail-main"),"Sentiment N/D");
});

test("quicklook rejects simulated/invalid percentage text",()=>{
  const {node,read,send}=run();
  node("r-status","Myfxbook · rilevato");
  node("r-lp","—");
  node("r-sp","100%");
  send("remura:retail");
  assert.equal(read("rq-retail-main"),"Sentiment N/D");
});
