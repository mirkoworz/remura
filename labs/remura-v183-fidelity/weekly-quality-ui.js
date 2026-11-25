/* REMURA v1.48 — weekly COT evidence quality, not a predictor. */
(function(){
 'use strict';
 const parser=window.REMURA_WEEKLY_QUALITY;
 const panel=document.getElementById('weekly-quality-panel');
 const status=document.getElementById('weekly-quality-state');
 const summary=document.getElementById('weekly-quality-summary');
 const rows=document.getElementById('weekly-quality-weeks');
 if(!parser||!panel||!status||!summary||!rows)return;
 let loading=false;
 const create=(tag,cls,value)=>{
   const n=document.createElement(tag);
   if(cls)n.className=cls;
   if(value!==undefined)n.textContent=String(value);
   return n;
 };
 const factor={
   USD:'Dollaro USA',
   precious_metals:'Metalli preziosi (oro/argento)',
   us_equity_indices:'Indici azionari USA',
   EUR:'Euro',GBP:'Sterlina',JPY:'Yen',CAD:'Dollaro canadese',
   AUD:'Dollaro australiano',CHF:'Franco svizzero',NZD:'Dollaro neozelandese',
   energy:'Energia'
 };
 const italian=x=>x.toLocaleString('it-IT',{maximumFractionDigits:1});
 const dl=(values)=>{
   const out=create('dl');
   for(const [k,v] of values){
     out.append(create('dt','',k),create('dd','',v));
   }
   return out;
 };
 function render(doc){
   summary.replaceChildren();
   const head=create('article','detail');
   head.append(create('h3','','Qualità delle settimane COT'),
     create('p','vrd',doc.quality),
     dl([
       ['Settimane con esiti',doc.weeks],
       ['Settimane con entrambi i gruppi',doc.both],
       ['Settimane favorevoli alle divergenze',doc.better],
       ['Settimane favorevoli alle concordanze',doc.worse],
       ['Settimane pari',doc.tie],
       ['Osservazioni studiate',doc.cases],
       ['Acquisizione tracciata prima del rilievo',doc.counts.recorded_before_observation],
       ['Storico precedente non tracciabile',doc.counts.unknown_legacy],
       ['Acquisizione successiva al rilievo',doc.counts.captured_after_observation],
       ['Riferimento COT non verificabile',doc.counts.missing_cot_reference],
     ]));
   summary.append(head);
   rows.replaceChildren();
   for(const week of doc.weekly){
     const card=create('article','detail');
     card.append(create('h4','','COT settimana '+week.week));
     const diff=week.delta==null?'Non confrontabile':
       (week.delta>0?'+':'')+italian(week.delta)+' punti percentuali';
     card.append(dl([
       ['Campioni',week.samples],
       ['Concordanze favorevoli',week.alignedHits+' / '+week.aligned],
       ['Divergenze favorevoli',week.divergentHits+' / '+week.divergent],
       ['Differenza descrittiva',diff],
       ['Acquisizioni tracciate',week.counts.recorded_before_observation],
       ['Storico non tracciabile',week.counts.unknown_legacy]
     ]));
     if(week.overlaps.length){
       card.append(create('p','small','Possibili esposizioni comuni: '+
         week.overlaps.map(x=>factor[x.factor]+' ('+x.markets+' mercati)').join(' · ')+
         '. Non sono coefficienti di correlazione.'));
     }
     rows.append(card);
   }
   status.textContent='La data COT è quella del report, non della pubblicazione. '+
      'La prima acquisizione indica quando REMURA ha visto il dato per la prima volta; '+
      'i report già archiviati prima della v1.48 restano non verificabili. '+
      'I campioni della stessa settimana possono dipendere dallo stesso evento macro.';
 }
 async function load(){
   if(loading)return;
   loading=true;
   try{
     status.textContent='Verifico settimane e disponibilità temporale del COT…';
     const resp=await fetch('./private-api/signals/weekly-quality',
       {cache:'no-store',credentials:'same-origin'});
     if(!resp.ok)throw new Error('http');
     const model=parser.read(await resp.json());
     if(!model)throw new Error('schema');
     render(model);
   }catch(_e){
     summary.replaceChildren();
     rows.replaceChildren();
     status.textContent='Audit settimanale non disponibile. '+
       'La verifica statistica precedente resta invariata.';
   }finally{loading=false;}
 }
 const refresh=document.getElementById('stat-refresh');
 if(refresh)refresh.addEventListener('click',load);
 load();
 window.setInterval(()=>{if(!document.hidden)load();},5*60*1000);
})();