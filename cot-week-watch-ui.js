/* REMURA v1.49 — the COT weekly-source watch is diagnostic, not signals. */
(function(){
 'use strict';
 const api=window.REMURA_COT_WEEK_WATCH;
 const root=document.getElementById('cot-week-watch-panel');
 const status=document.getElementById('cot-week-watch-state');
 const overview=document.getElementById('cot-week-watch-overview');
 const weeks=document.getElementById('cot-week-watch-weeks');
 if(!api||!root||!status||!overview||!weeks)return;
 const create=(tag,cls,value)=>{
   const x=document.createElement(tag);
   if(cls)x.className=cls;
   if(value!==undefined)x.textContent=String(value);
   return x;
 };
 const labels={tff:'TFF — 11 contratti',disagg:'Disaggregated — 3 contratti'};
 const states={
   ok:'Archivio aggiornato',
   disabled:'Raccolta COT disabilitata',
   no_data:'Nessun report disponibile',
   incomplete:'Contratti mancanti nella settimana più recente',
   timestamp_review:'Verificare gli orari di prima acquisizione',
   source_error:'Ultimo tentativo fonte non riuscito',
   age_review:'Data COT oltre 14 giorni: verificare calendario/fonte',
   status_review:'Stato del collector da verificare'
 };
 const dl=items=>{
   const d=create('dl');
   for(const [name,val] of items){
     d.append(create('dt','',name),create('dd','',val));
   }
   return d;
 };
 const formatUtc=s=>{
   if(!s)return 'Non disponibile';
   const date=new Date(s);
   return new Intl.DateTimeFormat('it-IT',{
     timeZone:'Europe/Rome',day:'2-digit',month:'2-digit',
     year:'numeric',hour:'2-digit',minute:'2-digit',hourCycle:'h23'
   }).format(date)+' (Italia)';
 };
 function render(doc){
   overview.replaceChildren();
   weeks.replaceChildren();
   const head=create('article','detail');
   const note=doc.status==='ready'?'Raccolta presente, nessun problema rilevato nella verifica.':
     doc.status==='disabled'?'La raccolta automatica COT è disabilitata.':
     'Uno o più aspetti richiedono controllo. Non significa necessariamente report perso.';
   head.append(create('h3','','Stato monitoraggio COT'),
     create('p','small',note),
     dl([
       ['Ultima settimana completa (14 contratti)',doc.lastComplete||'Non disponibile'],
       ['Settimana completa precedente',doc.previousComplete||'Non disponibile'],
       ['Due settimane per calcolare variazione COT',
         doc.hasTwoWeeks?'Disponibili':'Non ancora disponibili'],
       ['Nuove righe dell’ultima settimana acquisite da REMURA nelle ultime 48h',
         doc.newCapture?'Sì, entrambi gli archivi':'No / non verificabile'],
       ['Raccolta programmata',doc.enabled?'Ogni 6 ore':'Disabilitata'],
     ]));
   overview.append(head);
   for(const kind of ['tff','disagg']){
     const g=doc.datasets[kind];
     const card=create('article','detail');
     card.append(create('h4','',labels[kind]),create('p','small',states[g.state]),
       dl([
         ['Settimana COT più recente',g.latestCotWeek||'Nessuna'],
         ['Copertura contratti',g.present+' / '+g.expected],
         ['Prima acquisizione tracciata',g.firstSeenKnown+' / '+g.present],
         ['Senza orario storico di prima acquisizione',g.firstSeenUnknown],
         ['Nuove righe nelle ultime 48 ore',g.recentlyCapturedRows48h],
         ['Ultimo tentativo collector',formatUtc(g.lastCollectorAttemptUtc)],
         ['Ultima raccolta riuscita',formatUtc(g.lastSuccessUtc)]
       ]));
     if(g.missingCodes.length)card.append(create('p','small',
       'Codici CFTC assenti nella settimana più recente: '+g.missingCodes.join(', ')+
       '. Verificare la fonte, non creare righe artificiali.'));
     if(g.invalidFirstSeen)card.append(create('p','small',
       'Orari di acquisizione non validi: '+g.invalidFirstSeen+
       '. Questi record non sono considerati tracciati.'));
     overview.append(card);
   }
   for(const week of doc.weeks){
     const card=create('article','detail');
     card.append(create('h4','','Settimana COT '+week.week),
       create('p','small',week.complete?
         'Copertura completa di 14 contratti nei due archivi.':
         'Copertura incompleta: non presumere un report completo.'),
       dl([
         ['TFF',week.datasets.tff.present+' / 11'],
         ['Disaggregated',week.datasets.disagg.present+' / 3'],
         ['Orari prima acquisizione TFF',week.datasets.tff.firstSeenKnown+' / '+week.datasets.tff.present],
         ['Orari prima acquisizione Disaggregated',week.datasets.disagg.firstSeenKnown+' / '+week.datasets.disagg.present]
       ]));
     weeks.append(card);
   }
   status.textContent='Le date mostrate sono quelle di riferimento COT (non di pubblicazione). '+
     '«Prima acquisizione» è il momento in cui REMURA ha archiviato per la prima volta la riga CFTC. '+
     'Il monitor non produce ordini, segnali o notifiche.';
 }
 let busy=false;
 async function refresh(){
   if(busy)return;
   busy=true;
   try{
     status.textContent='Controllo completezza dei report COT sulla VPS…';
     const response=await fetch('./private-api/cot/week-watch',{
       cache:'no-store',credentials:'same-origin'});
     if(!response.ok)throw new Error('http');
     const validated=api.read(await response.json());
     if(!validated)throw new Error('schema');
     render(validated);
   }catch(_e){
     overview.replaceChildren();weeks.replaceChildren();
     status.textContent='Monitor COT non disponibile: le statistiche precedenti restano invariate.';
   }finally{busy=false;}
 }
 const button=document.getElementById('cot-week-watch-refresh');
 if(button)button.addEventListener('click',refresh);
 refresh();
 window.setInterval(()=>{if(!document.hidden)refresh();},5*60*1000);
})();