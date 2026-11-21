// REMURA Contributors v0.78 LAB — 21/11/2026 16:56 CET.
// Diagnostic OWNER-only: observations NEVER release a RESERVED attempt.
// Rendering uses textContent, not HTML injection; no auto polling or hidden retries.
const list=document.getElementById('ownerLevelIntegrityRows');
const status=document.getElementById('ownerLevelIntegrityStatus');
const button=document.getElementById('ownerLevelIntegrityLoad');
const messages=Object.freeze({
 NOT_OBSERVED_UNATTESTED:'Nessuna ricevuta osservata · senza attestazione',
 ABSENCE_SNAPSHOT_ONLY:'Assenza fotografata in precedenza · NON definitiva',
 RECEIPT_FOUND_UNATTESTED:'Ricevuta presente · serve verifica OWNER',
 RECEIPT_ATTESTED_LOCKED:'Ricevuta attestata · tentativo ancora bloccato',
 EVIDENCE_CHANGED_NEEDS_OWNER:'ATTENZIONE: ricevuta comparsa dopo precedente osservazione',
 INCONSISTENT_EVIDENCE:'INCOERENZA: verificare manualmente il registro'
});
let running=false;
button.addEventListener('click',async()=>{
 if(running)return;
 running=true;button.disabled=true;list.replaceChildren();status.textContent='Verifica in sola lettura…';
 try{
  const r=await fetch('/owner/new-level/integrity',{
   method:'POST',credentials:'same-origin',mode:'same-origin',redirect:'error',cache:'no-store',
   referrerPolicy:'no-referrer',headers:{'Content-Type':'application/json','X-Remura-CSRF':'1'},
   body:JSON.stringify({after:0})
  });
  if(!r.ok||r.redirected||!/^application\/json\b/i.test(r.headers.get('Content-Type')??'')||
    !/\bno-store\b/i.test(r.headers.get('Cache-Control')??''))throw Error('response_denied');
  const text=await r.text();if(text.length>80000)throw Error('too_large');
  const body=JSON.parse(text);
  if(!body||!body.data||body.data.automatic_release!==false||
    !Array.isArray(body.data.rows)||body.data.rows.length>20||typeof body.data.has_more!=='boolean')throw Error('invalid_data');
  for(const item of body.data.rows){
   if(item.attempt_locked!==true||item.needs_owner!==true||
     !Object.hasOwn(messages,item.condition)||typeof item.subject!=='string'||typeof item.request_id!=='string')throw Error('unexpected_item');
   const li=document.createElement('li');
   li.textContent='Identità '+item.subject.slice(0,12)+'… · Richiesta '+item.request_id.slice(-12)+' · '+messages[item.condition]+' · INVIO BLOCCATO';
   list.append(li);
  }
  status.textContent=body.data.rows.length?('Verificati '+body.data.rows.length+' tentativi · nessuno sbloccato'):'Nessun tentativo riservato rilevato.';
  if(body.data.has_more)status.textContent+=' · Altri tentativi richiedono lettura paginata.';
 }catch{
  status.textContent='Verifica non confermata. Nessuna modifica e nessuna autorizzazione all’invio.';
 }finally{running=false;button.disabled=false;}
});
