// REMURA Contributors v0.62 LAB — browser-only preview. No fetch, storage or publishing.
const form=document.querySelector('#amendmentForm');
const state=document.querySelector('#state');
const feedback=document.querySelector('#feedback');
const proposed=document.querySelector('#proposed');
const when=document.querySelector('#when');
const status=document.querySelector('.status');
const PRICE=/^(?:0|[1-9][0-9]{0,7})(?:\.[0-9]{1,8})?$/;
const UTC=/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/;
function parsePrice(v){const normalized=v.trim().replace(',','.');if(!PRICE.test(normalized)||!/[1-9]/.test(normalized))return null;return normalized;}
function parseUtc(v){if(!UTC.test(v)||!Number.isFinite(Date.parse(v))||new Date(v).toISOString().slice(0,19)+'Z'!==v||Date.parse(v)>Date.now())return null;return v;}
function resetPreview(){state.textContent='NESSUNA RICHIESTA';feedback.textContent='Compila la correzione: vedrai qui soltanto un’anteprima locale.';proposed.textContent='—';when.textContent='—';status.classList.remove('pending');}
form?.addEventListener('submit',event=>{
 event.preventDefault();const p=parsePrice(form.elements.price.value);const utc=parseUtc(form.elements.observed.value);
 const note=form.elements.note.value;
 if(!p||!utc||[...note].length>280||/[\u0000-\u001f\u007f-\u009f\uD800-\uDFFF]/u.test(note)){
  state.textContent='DATI NON VALIDI';feedback.textContent='Controlla prezzo e timestamp UTC. Nessun dato è stato inviato.';status.classList.remove('pending');return;
 }
 state.textContent='PENDING · SOLO SIMULAZIONE';feedback.textContent='Anteprima generata nel browser. Non esiste alcuna richiesta inviata né una correzione registrata.';
 proposed.textContent=p.replace('.',',');when.textContent=utc;status.classList.add('pending');
});
form?.addEventListener('reset',()=>queueMicrotask(resetPreview));
