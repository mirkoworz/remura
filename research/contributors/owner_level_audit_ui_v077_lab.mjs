// REMURA Contributors v0.77 LAB — 21/11/2026 16:44 CET.
// OWNER evidence desk: no auto retries, no ability to clear a RESERVED slot.
const $=id=>document.getElementById(id);
const pending=$('ownerLevelPending'),history=$('ownerLevelAuditHistory');
const select=$('ownerLevelAttemptSelect'),reason=$('ownerLevelReason');
const status=$('ownerLevelAuditStatus'),attest=$('ownerLevelAttest');
const load=$('ownerLevelLoad'),reloadHistory=$('ownerLevelAuditLoad');
let items=[],busy=false,locked=false,epoch=0;
const tell=s=>{status.textContent=s};
function controls(){for(const b of [load,reloadHistory,attest])b.disabled=busy||(b===attest&&locked);}
function put(list,itemsToShow){
 list.replaceChildren();
 if(!itemsToShow.length){const el=document.createElement('li');el.textContent='Nessuna voce in questa pagina.';list.append(el);return;}
 for(const text of itemsToShow){const li=document.createElement('li');li.textContent=text;list.append(li);}
}
function label(a){
 return 'ID '+a.attempt_id+' · Identità '+a.subject.slice(0,12)+'… · Richiesta '+a.request_id.slice(-12)+
  ' · '+(a.evidence==='RECEIPT_FOUND'?'Ricevuta presente #'+a.receipt_id:'Ricevuta non osservata')+
  (a.audit_id?' · Audit #'+a.audit_id:'');
}
async function post(path,body,token){
 const options={method:'POST',headers:{'Content-Type':'application/json','X-Remura-CSRF':'1',...(token?{'X-Remura-Intent':token}:{})},
  credentials:'same-origin',mode:'same-origin',redirect:'error',cache:'no-store',
  referrerPolicy:'no-referrer',body:JSON.stringify(body)};
 const response=await fetch(path,options);
 if(response.redirected||!/^application\/json\b/i.test(response.headers.get('Content-Type')??'')||
  !/\bno-store\b/i.test(response.headers.get('Cache-Control')??''))throw Error('invalid_response');
 const data=await response.text();
 if(data.length>100000)throw Error('large_response');
 let result;try{result=JSON.parse(data)}catch{throw Error('invalid_json')}
 if(!response.ok||!result||typeof result!=='object'||!('data' in result))throw Error('not_confirmed');
 return result.data;
}
async function action(fn){
 if(busy)return;
 const current=++epoch;busy=true;controls();
 try{await fn(()=>epoch===current);}
 catch{if(current===epoch)tell('Impossibile confermare: non ritentare la firma. Rileggi prima lo storico OWNER.');}
 finally{busy=false;controls();}
}
load.addEventListener('click',()=>action(async current=>{
 const result=await post('/owner/new-level/pending',{after:0});
 if(!current())return;
 if(!Array.isArray(result.rows)||result.rows.length>20||typeof result.has_more!=='boolean')throw Error('invalid_queue');
 items=result.rows;
 select.replaceChildren();
 for(let i=0;i<items.length;i++){const option=document.createElement('option');option.value=String(i);option.textContent=label(items[i]);select.append(option);}
 put(pending,items.map(label));
 controls(); // Never clear an uncertain signed action lock by refreshing queue.
 tell(items.length?'Stati letti dal database primario. Nessun tentativo viene sbloccato.':'Nessun tentativo in sospeso.');
}));
reloadHistory.addEventListener('click',()=>action(async current=>{
 const result=await post('/owner/new-level/history',{after:0});
 if(!current())return;
 if(!Array.isArray(result.rows)||result.rows.length>20)throw Error('invalid_history');
 put(history,result.rows.map(r=>'Audit #'+r.id+' · '+r.classification+' · '+r.request_id.slice(-12)+' · '+r.at_utc));
 tell('Storico append-only aggiornato. La verifica non riapre il diritto di invio.');
}));
attest.addEventListener('click',()=>action(async current=>{
 if(locked||!items.length)throw Error('locked');
 const index=Number(select.value),item=items[index];if(!Number.isSafeInteger(index)||!item)throw Error('selection');
 const note=reason.value.trim();
 if(!note||note.length>280)throw Error('reason');
 const evidence=item.evidence==='RECEIPT_FOUND'?'RECEIPT_FOUND':'RECEIPT_NOT_OBSERVED';
 const draft={subject:item.subject,request_id:item.request_id,classification:evidence,
  receipt_id:evidence==='RECEIPT_FOUND'?item.receipt_id:null,reason:note};
 if(!globalThis.confirm('Confermi di registrare una osservazione OWNER irreversibile? NON sblocca invii né approva il livello.'))return;
 // Explicit no-retry boundary starts BEFORE the signed HMAC is requested.
 locked=true;controls();
 const intent=await post('/owner/new-level/audit-intent',{body:draft});
 if(!current()||typeof intent.intent!=='string')throw Error('intent');
 const recorded=await post('/owner/new-level/attest',draft,intent.intent);
 if(!current()||recorded.recorded!==true||recorded.attempt_still_locked!==true)throw Error('status');
 tell('Osservazione salvata. Tentativo ancora BLOCCATO. Apri lo storico per verificare.');
 reason.value='';
}));
controls();
