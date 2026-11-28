import {CATALOG,LABELS,KINDS,PERIODS,normalizeProposal,pricesFromText,formatGrouped} from "./proposal-core.mjs";
const el=id=>document.getElementById(id),key="remura-v3019-preview-selection";
const defaults={mode:"CFD",category:"Forex",asset:"EURUSD",provider:"OANDA",kind:"DELTA_PEAK",period:"DAY"};
let choice={...defaults},saved;
try{saved=JSON.parse(localStorage.getItem(key)||"null");}catch{}
if(saved&&typeof saved==="object"){const match=CATALOG.find(x=>x.mode===saved.mode&&x.category===saved.category&&x.asset===saved.asset&&x.provider===saved.provider);if(match)choice={mode:match.mode,category:match.category,asset:match.asset,provider:match.provider,kind:Object.hasOwn(KINDS,saved.kind)?saved.kind:defaults.kind,period:Object.hasOwn(PERIODS,saved.period)?saved.period:defaults.period};}
let requestId=crypto.randomUUID(),sequence=0;
function remember(){try{localStorage.setItem(key,JSON.stringify(choice));}catch{}}
function buttonGroup(id,items,selected,change){const node=el(id);node.replaceChildren(...items.map(([value,label])=>{const b=document.createElement("button");b.type="button";b.textContent=label;b.setAttribute("aria-pressed",String(value===selected));b.onclick=()=>change(value);return b;}));}
function resetDraft(){el("prices").value="";el("note").value="";requestId=crypto.randomUUID();el("status").textContent="";}
function current(){return CATALOG.find(x=>x.mode===choice.mode&&x.category===choice.category&&x.asset===choice.asset&&x.provider===choice.provider);}
function render(){
 const rows=CATALOG.filter(x=>x.mode===choice.mode),cats=[...new Set(rows.map(x=>x.category))];
 if(!cats.includes(choice.category))choice.category=cats[0];
 const assets=[...new Set(rows.filter(x=>x.category===choice.category).map(x=>x.asset))];
 if(!assets.includes(choice.asset))choice.asset=assets[0];
 const providers=rows.filter(x=>x.category===choice.category&&x.asset===choice.asset).map(x=>x.provider);
 if(!providers.includes(choice.provider))choice.provider=providers[0];
 document.querySelectorAll("[data-mode]").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.mode===choice.mode)));
 buttonGroup("categories",cats.map(x=>[x,x]),choice.category,v=>{if(v!==choice.category){choice.category=v;resetDraft();render();}});
 el("assetLabel").textContent=choice.category==="Forex"?"Pair":"Asset";
 el("asset").replaceChildren(...assets.map(v=>new Option(v+(LABELS[v]?" — "+LABELS[v]:""),v)));el("asset").value=choice.asset;
 el("providerLabel").textContent=choice.mode==="CFD"?"Fonte":"Feed dati";
 buttonGroup("providers",providers.map(x=>[x,x==="DXFEED"?"dxFeed":x]),choice.provider,v=>{if(v!==choice.provider){choice.provider=v;resetDraft();render();}});
 el("continuous").hidden=choice.mode!=="FUTURES";
 el("availability").textContent=current().availability==="V3018_EXISTING"?"Alias già predisposto nella V30.18":"Candidato LAB · disponibilità fonte da verificare";
 buttonGroup("kinds",Object.entries(KINDS),choice.kind,v=>{choice.kind=v;render();});
 buttonGroup("periods",Object.entries(PERIODS).filter(([k])=>k!=="PREVIOUS_MONTH"),choice.period,v=>{choice.period=v;render();});
 remember();update();
}
function body(){return {request_id:requestId,mapping_id:current().id,kind:choice.kind,period:choice.period,prices:el("prices").value,note:el("note").value};}
function now(){return new Date().toISOString().slice(0,19)+"Z";}
function update(){try{const proposal=normalizeProposal(body());const n=pricesFromText(proposal.prices).length;el("count").textContent=n+" livelli distinti";el("message").textContent=formatGrouped({proposal,received_utc:now()},{preview:true});el("submit").disabled=false;el("status").textContent="";}catch{el("count").textContent="—";el("message").textContent="In attesa di prezzi validi…";el("submit").disabled=true;el("status").textContent=el("prices").value.trim()?"Controlla prezzi e note: un prezzo positivo per riga, massimo 20.":"";}}
document.querySelectorAll("[data-mode]").forEach(b=>b.onclick=()=>{if(b.dataset.mode!==choice.mode){choice.mode=b.dataset.mode;choice.category=choice.mode==="CFD"?"Forex":"Indici";resetDraft();render();}});
el("asset").onchange=()=>{choice.asset=el("asset").value;resetDraft();render();};
el("prices").oninput=el("note").oninput=update;
el("form").onsubmit=e=>{e.preventDefault();try{const proposal=normalizeProposal(body()),received_utc=now();const card=document.createElement("div");card.className="receipt";card.textContent="PROVA P"+(++sequence)+" · "+current().asset+" · "+proposal.prices.split("\n").join(" / ")+" · "+new Date(received_utc).toLocaleString("it-IT",{timeZone:"Europe/Rome"});el("receipts").prepend(card);resetDraft();update();el("status").textContent="Proposta simulata. Nessun dato inviato.";}catch{update();}};
render();
