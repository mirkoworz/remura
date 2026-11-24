// REMURA v1.78 LAB — fixed B archive. No CFTC requests.
import {makePrivateRetailReader,createRetailSession} from './private-retail-v177.mjs';
const OWNER_ORIGIN=null; // Deliberately disabled until separately authorized.
const read=makePrivateRetailReader({ownerOrigin:OWNER_ORIGIN,pageOrigin:location.origin,fetchFn:window.fetch.bind(window)});
const session=createRetailSession(),core=window.REMURA_SHARK_CORE;
const status=document.getElementById("retail-status"),list=document.getElementById("retail-list"),button=document.getElementById("retail-refresh");
let active=null;
function draw(){
 const s=session.snapshot(),rows=core.summarizeRetail(s.doc,Date.now());
 list.replaceChildren();
 status.textContent=!rows.length?(s.state==="DENIED"?"Accesso negato · N/D":s.state==="CLEARED"?"Sessione rimossa · N/D":"Feed privato non disponibile o non configurato · N/D"):rows.filter(r=>r.status==="RECENT_RETAIL").length+" / "+rows.length+" campioni recenti (entro 3 ore) · fonte VPS privata. Non sono segnali.";
 for(const r of rows){const card=document.createElement("div");card.className="retail-item";const parts=[r.pair,Number.isFinite(r.longLotsPct)?r.longLotsPct.toLocaleString("it-IT")+"% long":"N/D",r.status==="RECENT_RETAIL"?"Recente":r.status==="ARCHIVED_RETAIL"?"Archivio":"N/D",r.observedAt?new Date(r.observedAt).toLocaleString("it-IT",{timeZone:"Europe/Rome"}):"Data N/D"];for(const part of parts){const el=document.createElement("span");el.textContent=part;card.append(el)}list.append(card)}
}
async function refresh(){
 if(active||!OWNER_ORIGIN)return;
 const ctrl=new AbortController();active=ctrl;button.disabled=true;const ticket=session.begin(),timer=setTimeout(()=>ctrl.abort(),6500);
 try{session.accept(ticket,await read(ctrl.signal))}finally{clearTimeout(timer);if(active===ctrl)active=null;button.disabled=!OWNER_ORIGIN;draw()}
}
button.disabled=!OWNER_ORIGIN;if(OWNER_ORIGIN)button.textContent="Aggiorna snapshot VPS";
button.addEventListener("click",refresh);
document.addEventListener("visibilitychange",()=>{if(!document.hidden)draw()});
window.addEventListener("pageshow",draw);
window.addEventListener("pagehide",()=>{active?.abort();session.clear();draw()});
setInterval(()=>{if(!document.hidden)draw()},60000);
draw();
