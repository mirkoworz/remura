// REMURA Contributors v0.70 LAB — 21/11/2026 13:10 CET. Private read candidate; no deploy.
import {createReadOnlyTransportV070} from './recovery_transport_v070_lab.mjs';
import {ReconciliationClientV065} from './reconciliation_client_v065_lab.mjs';
import {AmendmentClientV063} from './amendment_client_v063_lab.mjs';

const STATES=Object.freeze({
 NO_ATTEMPT:['Nessun tentativo rilevato','Nessuna prenotazione risulta nella lettura verificata. Non è un permesso di inviare: attendi indicazioni dell’OWNER.'],
 UNRESOLVED:['Esito da ricostruire','Prenotazione presente, ma inserimento non confermato. Non riprovare. Serve verifica manuale dell’OWNER.'],
 COMMITTED_UNREVIEWED:['Correzione registrata','La correzione è registrata e attende una decisione dell’OWNER. Il livello pubblico non è stato aggiornato automaticamente.'],
 COMMITTED_REVIEWED:['Esaminata dall’OWNER','La correzione è stata esaminata, ma la prenotazione è ancora aperta. Non inviare un’altra richiesta.'],
 CLOSED:['Prenotazione chiusa','Chiusura manuale registrata. CLOSED non è un’autorizzazione per riprovare o inviare un nuovo livello.']
});
const UUID=/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/;
const HEX=/^[a-f0-9]{64}$/;
const UTC=/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/;
const PRICE=/^(?:0|[1-9][0-9]{0,7})(?:\.[0-9]{1,8})?$/;
const REVIEW=new Set(['UNREVIEWED','APPROVED','REJECTED','REVOKED']);
const QUEUED=new Set(['UNRESOLVED','COMMITTED_UNREVIEWED','COMMITTED_REVIEWED']);
const bad=()=>{throw Error('REMURA_V067_NOT_ATTESTED')};
const exact=(v,keys)=>v!==null&&typeof v==='object'&&!Array.isArray(v)&&Object.getPrototypeOf(v)===Object.prototype&&Object.keys(v).length===keys.length&&keys.every(k=>Object.hasOwn(v,k));
const validStamp=s=>typeof s==='string'&&UTC.test(s)&&Number.isFinite(Date.parse(s))&&new Date(s).toISOString().slice(0,19)+'Z'===s;
const positive=n=>Number.isSafeInteger(n)&&n>0;
const requestOptions=(body)=>({method:'POST',headers:{'Content-Type':'application/json','X-Remura-CSRF':'1'},body:JSON.stringify(body),credentials:'same-origin',mode:'same-origin',redirect:'error',cache:'no-store',referrerPolicy:'no-referrer'});

// Only the OWNER can get this endpoint's rows: server-side Access/HMAC/primary rules are in v0.64/v0.65.
// This browser adapter additionally validates the exact protocol; it is never an authorization boundary.
export class OwnerRecoveryClientV067 {
 #fetch;#busy=false;
 constructor(fetcher){if(typeof fetcher!=='function')bad();this.#fetch=fetcher;}
 get busy(){return this.#busy;}
 async inspect(after=0){
  if(this.#busy||!Number.isSafeInteger(after)||after<0)bad();this.#busy=true;
  try{
   const r=await this.#fetch('/owner/amendment/reconcile-queue',requestOptions({after}));
   if(r?.status!==200||r.redirected===true||!/^application\/json\b/i.test(r.headers?.get?.('Content-Type')??'')||!/\bno-store\b/i.test(r.headers?.get?.('Cache-Control')??''))bad();
   const raw=await r.text();if(new TextEncoder().encode(raw).length>16384)bad();
   let j;try{j=JSON.parse(raw)}catch{bad()}
   if(!exact(j,['data'])||!Array.isArray(j.data)||j.data.length>20)bad();
   let last=after;
   return Object.freeze(j.data.map(d=>{
    if(!exact(d,['attempt_id','subject','request_id','status','manualApprovalRequired'])||!positive(d.attempt_id)||d.attempt_id<=last||!HEX.test(d.subject)||!UUID.test(d.request_id)||!QUEUED.has(d.status)||d.manualApprovalRequired!==true)bad();
    last=d.attempt_id;
    return Object.freeze({attempt_id:d.attempt_id,subject:d.subject,request_id:d.request_id,status:d.status,manualApprovalRequired:true});
   }));
  }finally{this.#busy=false;}
 }
}

// Validates the complete own-receipt wire contract before rendering; no actor ID is accepted from UI.
export function validateOwnReceiptsV067(list){
 if(!Array.isArray(list)||list.length>20)bad();
 let last=0;
 return Object.freeze(list.map(d=>{
  if(!exact(d,['id','source_entry_id','price','observed_utc','received_utc','note','status'])||!positive(d.id)||d.id<=last||!positive(d.source_entry_id)||typeof d.price!=='string'||!PRICE.test(d.price)||!/[1-9]/.test(d.price)||!validStamp(d.observed_utc)||!validStamp(d.received_utc)||typeof d.note!=='string'||[...d.note].length>280||!REVIEW.has(d.status))bad();
  last=d.id;
  // Deliberately discard prices, notes and other fields from the view model.
  return Object.freeze({id:d.id,source_entry_id:d.source_entry_id,received_utc:d.received_utc,status:d.status});
 }));
}

export function mountRecoveryPortalV067({doc,role='CONTRIBUTOR',fetcher=null}={}){
 if(!doc?.querySelector||!['CONTRIBUTOR','OWNER'].includes(role)||fetcher!==null&&typeof fetcher!=='function')bad();
 const el=id=>doc.querySelector('#'+id),must=id=>{const n=el(id);if(!n)bad();return n;};
 const headline=must('recoveryHeadline'),summary=must('recoverySummary'),status=must('recoveryCode'),list=must('recoveryList'),refresh=must('refreshRecovery'),leave=must('leaveRecovery'),more=must('moreRecovery'),gate=must('sendGate');
 const extra=must('recoveryExtra');
 const reader=fetcher?(role==='OWNER'?new OwnerRecoveryClientV067(fetcher):new ReconciliationClientV065(fetcher)):null;
 const receipts=fetcher&&role==='CONTRIBUTOR'?new AmendmentClientV063(fetcher):null;
 let epoch=0,busy=false,ended=false,cursor=0,all=[],hasMore=false;
 const put=(n,s)=>{n.textContent=s;};
 const clear=()=>{list.replaceChildren();all=[];cursor=0;hasMore=false;};
 const buttons=()=>{refresh.disabled=!reader||busy||ended;more.disabled=!reader||busy||ended||role!=='OWNER'||!hasMore;};
 const show=(code,heading,message)=>{put(status,code);put(headline,heading);put(summary,message);put(gate,'NUOVI INVII BLOCCATI · Nessuno stato abilita un nuovo invio.');};
 const makeRow=(label,meta)=>{
  const d=doc.createElement('li'),strong=doc.createElement('strong'),small=doc.createElement('small');
  strong.textContent=label;small.textContent=meta;d.appendChild(strong);d.appendChild(small);return d;
 };
 const next=async({append=false}={})=>{
  if(!reader||busy||ended)return;
  busy=true;const ticket=++epoch;buttons();
  if(!append){clear();show('IN VERIFICA','Lettura in corso','Nessuna conferma prima della risposta verificata.');}
  try{
   if(role==='OWNER'){
    const rows=await reader.inspect(append?cursor:0);
    if(ticket!==epoch||ended)return;
    if(!append)clear();
    for(const d of rows){if(d.attempt_id<=cursor)bad();cursor=d.attempt_id;all.push(d);list.appendChild(makeRow('Tentativo #'+d.attempt_id+' · '+d.status,'Soggetto '+d.subject.slice(0,10)+'… · richiesta '+d.request_id));}
    hasMore=rows.length===20;
    show('CODA OWNER · LETTURA',String(all.length)+' richieste elencate',rows.length===20?'Potrebbero esserci ulteriori pagine da verificare.':'Solo lettura: nessuna chiusura o approvazione automatica.');
    put(extra,'Accesso OWNER richiesto e verificato dal backend; questa schermata da sola non concede privilegi.');
   }else{
    const d=await reader.inspect();
    if(ticket!==epoch||ended)return;
    clear();
    show(d.status,...STATES[d.status]);
    if(d.status!=='NO_ATTEMPT')list.appendChild(makeRow('Tentativo personale #'+d.attempt_id,'Richiesta '+d.request_id));
    put(extra,'Le ricevute sono consultabili separatamente. Non inviare di nuovo, anche se lo stato è CLOSED.');
   }
  }catch{
   if(ticket===epoch&&!ended){clear();show('NON VERIFICATO','Stato non disponibile','Risposta mancante, non valida o accesso negato. Nessuna conferma né autorizzazione a ritentare.');}
  }finally{if(ticket===epoch){busy=false;buttons();}}
 };
 const readReceipts=async()=>{
  if(role!=='CONTRIBUTOR'||!receipts||busy||ended)return;
  busy=true;const ticket=++epoch;buttons();clear();show('IN VERIFICA','Ricevute personali','Lettura autenticata in corso, nessuna informazione ancora confermata.');
  try{
   const items=validateOwnReceiptsV067(await receipts.read('/api/amendment/mine',{after:0}));
   if(ticket!==epoch||ended)return;
   clear();for(const item of items)list.appendChild(makeRow('Ricevuta #'+item.id+' · '+item.status,'Livello #'+item.source_entry_id+' · '+item.received_utc));
   show('RICEVUTE PERSONALI',items.length+' ricevute verificate','Solo correzioni restituite dal controllo d’identità sul server. Le ricevute non autorizzano nuove scritture.');
  }catch{if(ticket===epoch&&!ended){clear();show('NON VERIFICATO','Ricevute non disponibili','Lettura negata o risposta non verificabile. Nessun dato confermato.');}}
  finally{if(ticket===epoch){busy=false;buttons();}}
 };
 const exit=()=>{epoch++;ended=true;busy=false;clear();show('VISTA CHIUSA','Dati cancellati dalla vista','Questa azione non termina una sessione Cloudflare Access: in futuro servirà logout verificato lato provider.');put(extra,'Riaprire la pagina non abilita invii.');buttons();};
 refresh.addEventListener('click',()=>{void next();});
 more.addEventListener('click',()=>{if(role==='OWNER')void next({append:true});});
 leave.addEventListener('click',exit);
 const receiptsButton=el('refreshReceipts');if(role==='CONTRIBUTOR'){if(!receiptsButton)bad();receiptsButton.addEventListener('click',()=>{void readReceipts();});receiptsButton.disabled=!receipts;}
 else if(receiptsButton)receiptsButton.disabled=true;
 show(fetcher?'STAGING CANDIDATO · LAB':'OFFLINE · LAB',role==='OWNER'?'Coda di verifica OWNER':'Recupero correzioni',fetcher?'Trasporto di sola lettura predisposto. Nessuna autenticazione o dato reale è confermato finché il server privato non viene attivato.':'Anteprima isolata, nessun account reale collegato.');
 put(extra,fetcher?'Il server dovrà validare Access, ruolo D1 e revoca a ogni richiesta; nessun invio abilitato.':'Solo le prove con trasporto sintetico iniettato possono consultare dati fixture.');buttons();
 return Object.freeze({refresh:()=>next(),receipts:()=>readReceipts(),more:()=>next({append:true}),leave:exit,get closed(){return ended;},get busy(){return busy;}});
}

// Candidate boot only. UI is NOT authentication; the server must verify Access JWT and D1 role.
if(typeof document!=='undefined'){
 let fetcher=null;
 if(document.body?.dataset?.readBridge==='STAGING_CANDIDATE'&&
    globalThis.location?.protocol==='https:'&&typeof globalThis.fetch==='function'){
  try{fetcher=createReadOnlyTransportV070({fetcher:globalThis.fetch.bind(globalThis),origin:globalThis.location.origin});}
  catch{fetcher=null;}
 }
 mountRecoveryPortalV067({doc:document,role:document.body?.dataset?.role==='OWNER'?'OWNER':'CONTRIBUTOR',fetcher});
}
