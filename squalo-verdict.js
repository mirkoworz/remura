/* REMURA v1.24 — private, read-only integration of existing verified feeds. */
(()=>{
"use strict";
const core=window.REMURA_SQUALO_VERDICT_CORE;
const macroCore=window.REMURA_PRICE_STATUS_CORE?.macro;
const cfg=window.REMURA_MARKETS;
const host=document.getElementById("squalo-verdict");
if(!core||!host||!cfg)return;
const requested=(new URLSearchParams(location.search).get("symbol")||"XAUUSD").toUpperCase();
const symbol=cfg.symbols.includes(requested)?requested:"XAUUSD";
const $=id=>document.getElementById(id);
const text=(tag,cls,v)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(v!==undefined)e.textContent=v;return e;};
const feeds={price:null,myfxbook:null,capital:null,macro:null};
function readCot(){return window.REMURA_INSIGHTS?.getAnalysis?.()||null;}
function row(label,entry){
 const card=text("div","sv-factor");
 const headline=text("strong",null,label+" · "+entry.title);
 headline.dataset.status=entry.status;
 card.append(headline,text("p",null,entry.detail));
 return card;
}
function render(){
 const result=core.evaluate({symbol,cot:readCot(),price:feeds.price,myfxbook:feeds.myfxbook,
  capital:feeds.capital,macro:feeds.macro,now:Date.now()});
 host.dataset.state=result.state;
 $("sv-title").textContent=result.title;
 $("sv-subtitle").textContent=result.narrative;
 const container=$("sv-factors");container.replaceChildren();
 for(const [label,k] of [["COT settimanale","cot"],["Prezzo H4/H1/M15","price"],
   ["Myfxbook · lotti","myfxbook"],["Capital.com · clienti","capital"],["Contesto DXY/VIX","macro"]]){
  container.append(row(label,result.items[k]));
 }
 const note=$("sv-retail-note");note.replaceChildren();
 for(const line of result.retailNotes)note.append(text("p",null,line));
 $("sv-footnote").textContent=result.note;
}
function accept(event,key){
 const d=event.detail;
 if(d?.symbol!==symbol)return;
 feeds[key]={current:d.current||null,fresh:d.fresh===true};
 render();
}
window.addEventListener("remura:cot",render);
window.addEventListener("remura:retail",e=>accept(e,"myfxbook"));
window.addEventListener("remura:capital",e=>accept(e,"capital"));
window.addEventListener("remura:price",e=>{
 if(e.detail?.symbol!==symbol)return;
 feeds.price=e.detail.result||null;
 render();
});
async function macro(){
 if(!macroCore){render();return;}
 const controller=new AbortController();
 const timeout=setTimeout(()=>controller.abort(),12000);
 try{
  const price=async symbol=>{
   const response=await fetch("./private-api/prices/"+symbol,{cache:"no-store",signal:controller.signal});
   if(!response.ok)throw Error("feed_unavailable");
   const doc=await response.json();
   const data=doc?.schema==="remura-price-v1"?doc?.markets?.[symbol]:null;
   if(data?.provider!=="ctrader"||data?.symbol!==symbol)throw Error("invalid");
   return data;
  };
  const [dxy,vix]=await Promise.all([price("DXY"),price("VIX")]);
  const info=macroCore.context(dxy,vix);
  const today=Date.now();
  const historical=[dxy,vix].some(x=>macroCore.audit(x,today).state==="weekend");
  feeds.macro={...info,historical};
 }catch(_){feeds.macro=null;}
 finally{clearTimeout(timeout);render();}
}
window.addEventListener("visibilitychange",()=>{
 if(document.visibilityState==="visible"){render();macro();}
});
render();
macro();
})();
