/* REMURA v1.18 · private read-only dashboard, no synthetic prices. */
(()=>{
"use strict";
const $=id=>document.getElementById(id);
const core=window.REMURA_MACRO_CORE;
const marketInfo=[
 {symbol:"GER30",label:"DAX 40",note:"Candele GER30: non sostituite con GER40"},
 {symbol:"DXY",label:"Dollar Index",note:"Prezzo cTrader USDX, possibile scadenza del contratto"},
 {symbol:"VIX",label:"Volatilità",note:"Contratto broker con scadenza, non indice spot CBOE"}
];
const docs={};
const stamp=t=>{const d=new Date(t||"");return Number.isFinite(d.getTime())?new Intl.DateTimeFormat("it-IT",{dateStyle:"short",timeStyle:"short",timeZone:"Europe/Rome"}).format(d):"N/D"};
function el(tag,cls,text){
 const e=document.createElement(tag);
 if(cls)e.className=cls;
 if(text!==undefined)e.textContent=text;
 return e;
}
function line(parent,label,value,cls="fact"){
 const div=el("div",cls);
 div.append(el("b",null,label+" "),document.createTextNode(value));
 parent.append(div);
}
function qualityCard(symbol,title,note,data){
 const card=el("article","market");
 const h=el("div");
 const head=el("strong",null,title+" · "+symbol);
 h.append(head);
 const quality=data?core.audit(data,Date.now()):{state:"missing",counts:{M15:0,H1:0,H4:0}};
 const labels={recent:"RECENTE",stale:"DATATO",missing:"N/D",invalid:"VERIFICA"};
 const chip=el("span","badge",labels[quality.state]||"N/D");
 chip.dataset.state=quality.state;h.append(chip);
 card.append(h,el("div","foot",note));
 line(card,"Candele:","M15 "+quality.counts.M15+" · H1 "+quality.counts.H1+" · H4 "+quality.counts.H4);
 if(quality.state==="missing"){
  line(card,"Disponibilità:","storico non ancora acquisito");
  return card;
 }
 line(card,"Ultima M15:",stamp(quality.asof)+" · "+quality.ageMinutes+" min dalla chiusura");
 line(card,"Interruzioni nelle ultime 97 M15:",String(quality.recentGaps)+" (possono essere pause di mercato)");
 line(card,"Ricostruzione H1:",quality.h1.verified+"/"+quality.h1.checked+" verificati · "+quality.h1.mismatched+" non coerenti");
 line(card,"Ricostruzione H4:",quality.h4.verified+"/"+quality.h4.checked+" verificati · "+quality.h4.mismatched+" non coerenti");
 if(quality.h1.missingInputs||quality.h4.missingInputs)
  line(card,"Copertura non verificabile:",(quality.h1.missingInputs+quality.h4.missingInputs)+" intervalli senza tutte le M15");
 if(quality.state==="invalid")card.append(el("div","warn","Anomalie di integrità: non utilizzare per conferme operative."));
 if(quality.state==="stale")card.append(el("div","warn","Prezzo datato: mercato chiuso, scadenza o raccolta da verificare."));
 if(!quality.ready)card.append(el("div","warn","Storico insufficiente per interpretazione tecnica a 55 candele H4."));
 return card;
}
async function load(symbol){
 if(Object.prototype.hasOwnProperty.call(docs,symbol))return docs[symbol];
 try{
  const r=await fetch("./private-api/prices/"+encodeURIComponent(symbol),{cache:"no-store"});
  if(!r.ok)throw Error("missing");
  const parsed=await r.json();
  const record=parsed?.schema==="remura-price-v1"?parsed?.markets?.[symbol]:null;
  if(!record||record.symbol!==symbol||record.provider!=="ctrader")throw Error("invalid");
  docs[symbol]=record;
 }catch(_){docs[symbol]=null;}
 return docs[symbol];
}
async function refresh(){
 const status=$("macro-status"),b=$("macro-refresh");b.disabled=true;
 status.dataset.error="false";status.textContent="Leggo le tre serie dalla VPS privata…";
 for(const k of Object.keys(docs))delete docs[k];
 try{
  const results=await Promise.all(marketInfo.map(m=>load(m.symbol)));
  const box=$("macro-markets");box.replaceChildren();
  for(let i=0;i<marketInfo.length;i++){
   const info=marketInfo[i];box.append(qualityCard(info.symbol,info.label,info.note,results[i]));
  }
  const pairs=[["GER30","DXY"],["GER30","VIX"],["DXY","VIX"]];
  const table=el("table"),head=el("tr");
  for(const col of ["Mercati","Pearson H1","Campioni UTC"])head.append(el("th",null,col));
  const header=el("thead");header.append(head);table.append(header);
  const body=el("tbody");
  for(const [left,right] of pairs){
   const one=docs[left],two=docs[right],row=el("tr"),c=one&&two?core.correlation(one,two):{state:"insufficient",samples:0,value:null};
   const trusted=one&&two&&core.pairEligible(one,two);
   row.append(el("td",null,left+" / "+right),
              el("td",null,c.state==="ok"&&trusted?c.value.toFixed(3):"N/D"),
              el("td",null,c.samples+" · "+(c.state==="ok"&&!trusted?"prezzi datati/anomali":c.state==="ok"?"allineati":"insufficienti")));
   body.append(row);
  }
  table.append(body);
  $("macro-pairs").replaceChildren(table);
  const n=results.filter(Boolean).length;
  status.textContent=n+"/3 serie prezzi ricevute dalla VPS · "+stamp(new Date().toISOString())+". N/D dove la verifica non è possibile.";
  if(n<3)status.textContent+=" DXY/VIX potrebbero essere ancora in fase di primo storico.";
 }catch(_){
  status.dataset.error="true";
  status.textContent="Impossibile verificare la VPS privata. Apri REMURA su .ts.net; non mostriamo dati fittizi.";
 }finally{b.disabled=false;}
}
async function selected(){
 const symbol=$("macro-symbol").value,b=$("macro-check");b.disabled=true;
 $("macro-extra").textContent="Verifico "+symbol+"…";
 try{const record=await load(symbol);$("macro-extra").replaceChildren(qualityCard(symbol,symbol,"Verifica privata su richiesta",record));}
 catch(_){$("macro-extra").textContent="Dati non disponibili.";}
 finally{b.disabled=false;}
}
const marketSymbols=window.REMURA_MARKETS?.symbols||marketInfo.map(x=>x.symbol);
for(const sym of marketSymbols){const o=el("option",null,sym);o.value=sym;$("macro-symbol").append(o);}
$("macro-symbol").value="GER30";
$("macro-refresh").addEventListener("click",refresh);
$("macro-check").addEventListener("click",selected);
refresh();
})();
