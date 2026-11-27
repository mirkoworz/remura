// REMURA Contributors v0.27 LAB — 16/11/2026 07:24 CET
// Candidate page only; no hosting or Worker entrypoint. Every response is rendered as text.
import {CandidateClient} from "./contributors_candidate_client.mjs";
const $=id=>document.getElementById(id);
const client=new CandidateClient();
let profile=null,mappings=[],busy=false,epoch=0,cursor={my:0,queue:0};
const controls=["connect","send","myLoad","myNext","queueLoad","queueNext","reviewSend","historyLoad","clear"];
const say=x=>{$("status").textContent=x;};
function option(value,label){const o=document.createElement("option");o.value=value;o.textContent=label;return o;}
function choices(id,values){$(id).replaceChildren(option("","Seleziona"),...values.map(([v,l])=>option(v,l)));}
function states(){for(const id of controls)$(id).disabled=busy||(client.uncertain&&["send","reviewSend"].includes(id));}
async function act(fn){
 if(busy)return;busy=true;const e=epoch;states();
 const current=()=>e===epoch;
 try{await fn(current);}catch{
  if(current()){reset();say(client.uncertain?"Scrittura non confermata. Non reinviare. Verifica le ricevute o la cronologia.":"Operazione non confermata o accesso non disponibile. Verifica nuovamente.");}
 }finally{busy=false;states();}
}
function reset(){
 epoch++;profile=null;mappings=[];cursor={my:0,queue:0};
 for(const id of ["contributor","owner","clear","myRead","ownerRead","historyPanel","myNext","queueNext"])$(id).hidden=true;
 for(const id of ["intake","review"])$(id).reset();
 for(const id of ["myRows","queueRows","historyRows","market","provider","mapping","decision"])$(id).replaceChildren();
 $("historyId").value="";$("connect").hidden=false;say("");
}
function providers(){const list=mappings.filter(r=>r.market===$("market").value);choices("provider",[...new Set(list.map(r=>r.provider))].map(x=>[x,x]));symbols();}
function symbols(){choices("mapping",mappings.flatMap((r,i)=>r.market===$("market").value&&r.provider===$("provider").value?[[String(i),r.ticker+" · "+r.product+(r.contract?" · "+r.contract:"")]]:[]));}
function validProfile(p){return p&&["OWNER","CONTRIBUTOR"].includes(p.role)&&["can_read","can_write","can_recover"].every(k=>typeof p[k]==="boolean")&&!(p.role==="CONTRIBUTOR"&&p.can_recover);}
async function connect(current){
 const p=await client.read("/api/profile",{});if(!current())return;
 if(!validProfile(p))throw Error("profile");
 let list=[];
 if(p.role==="CONTRIBUTOR"&&p.can_write){
  list=await client.read("/api/catalog",{});if(!current())return;
  if(!Array.isArray(list)||list.length>256||list.some(r=>!r||["market","provider","ticker","product","contract"].some(k=>typeof r[k]!=="string")))throw Error("catalog");
 }
 profile=p;mappings=list;$("clear").hidden=false;$("connect").hidden=true;
 $("contributor").hidden=p.role!=="CONTRIBUTOR";$("owner").hidden=p.role!=="OWNER";
 $("intake").hidden=!p.can_write||!mappings.length;$("myRead").hidden=!p.can_read;
 $("ownerRead").hidden=!p.can_read;$("review").hidden=!p.can_write&&!p.can_recover;$("historyPanel").hidden=!p.can_recover;
 choices("market",[...new Set(mappings.map(r=>r.market))].map(x=>[x,x]));providers();
 choices("decision",[...(p.can_write?["APPROVED","REJECTED"]:[]),...(p.can_recover?["REVOKED"]:[])].map(x=>[x,x]));
 $("observed").value=new Date().toISOString().replace(/\.\d{3}Z$/,"Z");
 say("Autorizzazione LAB verificata · "+(p.role==="OWNER"?"Proprietario":"Collaboratore")+(p.role==="CONTRIBUTOR"&&p.can_write&&!mappings.length?" · Nessun mapping attivo":""));
}
function rowText(r,keys){const el=document.createElement("div");el.className="receipt";for(const key of keys){if(r[key]!==undefined&&r[key]!==null){const v=document.createElement("div");v.textContent=key+": "+String(r[key]);el.append(v);}}return el;}
async function page(which,resetPage,current){
 const own=which==="my",path=own?"/api/receipts":"/owner/queue";
 if(!profile?.can_read||profile.role!==(own?"CONTRIBUTOR":"OWNER"))throw Error("denied");
 const after=resetPage?0:cursor[which];
 const rows=await client.read(path,{after});if(!current())return;
 if(!Array.isArray(rows)||rows.length>20||rows.some((r,i)=>!Number.isSafeInteger(r?.id)||r.id<=(i?rows[i-1].id:after)))throw Error("page");
 $(own?"myRows":"queueRows").replaceChildren(...rows.map(r=>rowText(r,["id","market","provider","ticker","product","contract","period","kind","price","anchor_utc","observed_utc","received_utc","note","status","reviewed_utc"])));
 cursor[which]=rows.length?rows.at(-1).id:after;$(own?"myNext":"queueNext").hidden=rows.length!==20;
 say(rows.length?"Pagina ricevuta.":"Nessun record in questa pagina.");
}
$("connect").addEventListener("click",()=>act(async current=>{
 // Do not advance the lifecycle epoch merely to connect; act must see errors.
 if(profile)throw Error("already connected");
 await connect(current);
}));
$("market").addEventListener("change",providers);$("provider").addEventListener("change",symbols);
$("intake").addEventListener("submit",e=>{e.preventDefault();act(async current=>{
 if(profile?.role!=="CONTRIBUTOR"||!profile.can_write||$("mapping").value==="")throw Error("denied");
 const r=mappings[Number($("mapping").value)];if(!r||r.market!==$("market").value||r.provider!==$("provider").value)throw Error("mapping");
 const p={request_id:crypto.randomUUID(),market:r.market,provider:r.provider,ticker:r.ticker,product:r.product,contract:r.contract,period:$("period").value,kind:$("kind").value,price:$("price").value,anchor_utc:$("anchor").value,observed_utc:$("observed").value,note:$("note").value};
 const result=await client.mutate("/api/submit",p,current);if(!current())return;
 say("Ricevuta n. "+result.id+" · Non verificato. Aggiorna le ricevute manualmente.");$("price").value="";$("note").value="";
 });});
$("review").addEventListener("submit",e=>{e.preventDefault();act(async current=>{
 if(profile?.role!=="OWNER")throw Error("denied");
 const id=Number($("entry").value),action=$("decision").value;
 if(!Number.isSafeInteger(id)||id<1||!(action==="REVOKED"?profile.can_recover:["APPROVED","REJECTED"].includes(action)&&profile.can_write))throw Error("denied");
 if(!globalThis.confirm("Confermi "+action+" per il contributo "+id+"?"))return;
 const r=await client.mutate("/owner/review",{id,action,reason:$("reason").value},current);if(!current())return;
 say("Decisione registrata: "+r.action+" · N. "+r.id);$("reason").value="";
 });});
$("myLoad").addEventListener("click",()=>act(c=>page("my",true,c)));$("myNext").addEventListener("click",()=>act(c=>page("my",false,c)));
$("queueLoad").addEventListener("click",()=>act(c=>page("queue",true,c)));$("queueNext").addEventListener("click",()=>act(c=>page("queue",false,c)));
$("historyLoad").addEventListener("click",()=>act(async current=>{
 if(profile?.role!=="OWNER"||!profile.can_recover)throw Error("denied");
 const id=Number($("historyId").value);if(!Number.isSafeInteger(id)||id<1)throw Error("id");
 const list=await client.read("/owner/history",{id});if(!current())return;
 if(!Array.isArray(list)||list.length>2)throw Error("history");
 $("historyRows").replaceChildren(...list.map(x=>rowText(x,["action","at_utc","reason"])));say("Cronologia aggiornata.");
 }));
$("clear").addEventListener("click",()=>{if(!busy){reset();say("Vista locale cancellata. La sessione Access non è revocata.");}});
globalThis.addEventListener("pagehide",reset);
globalThis.addEventListener("pageshow",e=>{if(e.persisted){reset();say("Verifica nuovamente l'autorizzazione.");}});
states();
