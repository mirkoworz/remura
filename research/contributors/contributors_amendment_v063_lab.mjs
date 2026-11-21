// REMURA Contributors v0.63 LAB — 21/11/2026 CET
// Browser defaults to OFFLINE PREVIEW only. Real data transport is NOT instantiated here.
const PRICE=/^(?:0|[1-9][0-9]{0,7})(?:\.[0-9]{1,8})?$/;
const UTC=/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/;
function parsePrice(v){if(typeof v!=='string')return null;const p=v.trim().replace(',','.');return PRICE.test(p)&&/[1-9]/.test(p)?p:null;}
function parseTime(v,now){return typeof v==='string'&&UTC.test(v)&&Number.isFinite(Date.parse(v))&&new Date(v).toISOString().slice(0,19)+'Z'===v&&Date.parse(v)<=now?v:null;}
function text(el,value){if(el)el.textContent=value;}
export function mountAmendmentUIV063({doc,client=null,newId=()=>globalThis.crypto?.randomUUID?.(),now=()=>Date.now()}={}){
 if(!doc?.querySelector)throw Error('REMURA_UI_UNAVAILABLE');
 const get=s=>doc.querySelector(s),form=get('#amendmentForm'),state=get('#state'),feedback=get('#feedback'),
   proposed=get('#proposed'),when=get('#when'),status=get('.status'),send=get('#submitToLab'),receipts=get('#checkReceipts'),receiptsText=get('#receiptStatus');
 if(!form||!state||!feedback||!proposed||!when||!status||!send||!receipts||!receiptsText)throw Error('REMURA_UI_UNAVAILABLE');
 let draft=null,revision=0,disconnected=false,inFlight=false,locked=false;
 const enabled=!!client&&typeof client.mutate==='function'&&typeof client.read==='function';
 const buttons=()=>{send.disabled=!enabled||!draft||inFlight||locked||client?.uncertain===true;receipts.disabled=!enabled||inFlight;};
 const clear=()=>{
  revision++;draft=null;text(state,'NESSUNA RICHIESTA');text(feedback,'Questa è un’anteprima offline: nessun livello è stato inviato.');
  text(proposed,'—');text(when,'—');status.classList.remove('pending');buttons();
 };
 const preview=e=>{
  e?.preventDefault?.();
  if(inFlight||locked||client?.uncertain)return;
  revision++;const price=parsePrice(form.elements.price.value),observed_utc=parseTime(form.elements.observed.value,now()),note=form.elements.note.value;
  const source=Number(form.elements.sourceId.value);
  if(!price||!observed_utc||!Number.isSafeInteger(source)||source<1||typeof note!=='string'||[...note].length>280||/[\u0000-\u001f\u007f-\u009f\uD800-\uDFFF]/u.test(note)){
   draft=null;status.classList.remove('pending');text(state,'DATI NON VALIDI');text(feedback,'Controlla prezzo, data UTC e nota. Nessun invio.');buttons();return;
  }
  draft=Object.freeze({source_entry_id:source,price,observed_utc,note});
  text(state,'PENDING · ANTEPRIMA NON INVIATA');text(feedback,'Anteprima nel browser. Servirà una conferma reale e l’approvazione OWNER.');
  text(proposed,price.replace('.',','));text(when,observed_utc);status.classList.add('pending');buttons();
 };
 async function submit(){
  if(!enabled||!draft||inFlight||locked||client.uncertain){buttons();return;}
  const version=revision,confirmed={...draft};const request_id=newId();
  if(typeof request_id!=='string'||!(/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/).test(request_id)){
    locked=true;text(state,'INVIO BLOCCATO');text(feedback,'Impossibile preparare una richiesta sicura. Nessun invio effettuato.');buttons();return;
  }
  inFlight=true;buttons();text(state,'INVIO IN VERIFICA');text(feedback,'Richiesta sintetica in verifica. Non ripetere l’invio.');
  try{
    const ack=await client.mutate('/api/amendment/submit',{...confirmed,request_id},{stillCurrent:()=>!disconnected&&version===revision});
    if(disconnected||version!==revision)return;
    locked=true;status.classList.add('pending');
    text(state,'RICEVUTA CONFERMATA · '+String(ack.status));
    text(feedback,'Correzione registrata in LAB con ID '+String(ack.id)+'. Il prezzo condiviso NON cambia senza approvazione OWNER.');
  }catch{
    locked=client.uncertain===true;
    text(state,locked?'ESITO INCERTO · INVIO BLOCCATO':'INVIO NON CONFERMATO');
    text(feedback,locked?'Il server potrebbe aver registrato la correzione. Non ritentare: verifica le ricevute e consulta l’OWNER.':'La richiesta non è stata confermata. Non è stata mostrata alcuna ricevuta.');
  }finally{inFlight=false;buttons();}
 }
 async function checkReceipts(){
  if(!enabled||inFlight)return;
  inFlight=true;buttons();text(receiptsText,'Verifica delle sole ricevute personali…');
  try{
   const items=await client.read('/api/amendment/mine',{after:0});
   text(receiptsText,'Ricevute personali disponibili: '+String(items.length)+'. '+(client.uncertain?'L’esito dell’ultimo invio resta incerto.':'Nessuna autorizzazione automatica di pubblicazione.'));
  }catch{text(receiptsText,'Ricevute non verificabili. Nessun dato confermato.');}
  finally{inFlight=false;buttons();}
 }
 form.addEventListener('submit',preview);
 form.addEventListener('reset',()=>queueMicrotask(clear));
 send.addEventListener('click',()=>submit());
 receipts.addEventListener('click',()=>checkReceipts());
 clear();
 return Object.freeze({disconnect:()=>{disconnected=true;locked=true;buttons();},isLocked:()=>locked,hasDraft:()=>!!draft});
}
// DO NOT instantiate an HTTP fetcher in the real document. Preview-only is the safe default.
if(typeof document!=='undefined')mountAmendmentUIV063({doc:document});
