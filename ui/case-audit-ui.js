/* REMURA v1.47 — factual 12-week COT evidence list, not an order journal. */
(function(){
 'use strict';
 const parser=window.REMURA_CASE_AUDIT;
 const panel=document.getElementById('case-audit-panel');
 const status=document.getElementById('case-audit-state');
 const weekSelect=document.getElementById('case-audit-week');
 const relationSelect=document.getElementById('case-audit-relation');
 const marketSelect=document.getElementById('market-audit-select');
 const weekly=document.getElementById('case-audit-weekly');
 const items=document.getElementById('case-audit-items');
 if(!parser||!panel||!status||!weekSelect||!relationSelect||!marketSelect||!weekly||!items)return;
 const el=(tag,cls,val)=>{
   const n=document.createElement(tag);
   if(cls)n.className=cls;
   if(val!==undefined)n.textContent=String(val);
   return n;
 };
 const fmt=x=>x==null?'—':x.toLocaleString('it-IT',{maximumFractionDigits:2});
 const bp=x=>x==null?'—':(x>0?'+':'')+fmt(x)+' bp';
 const sideLabel=s=>s==='long'?'Rialzista':'Ribassista';
 const relLabel=r=>r==='aligned'?'Concordanza':'Divergenza';
 const isRising=s=>s==='long';
 let model=null,loading=false;
 const rows=(label,value)=>[el('dt','',label),el('dd','',value)];
 function caseCard(r){
   const box=el('article','detail');
   box.append(el('h4','',r.symbol+' · settimana COT '+r.week));
   const priceSide=r.relation==='aligned'?r.side:(isRising(r.side)?'short':'long');
   box.append(el('p','small',
      'Al primo rilievo: COT '+sideLabel(r.side)+
      ', prezzo '+sideLabel(priceSide)+' · '+relLabel(r.relation)));
   const list=el('dl');
   for(const [a,b] of [
     ['24h calendario · verso COT',bp(r.calendar24.directional)],
     ['24h calendario · prezzo long',bp(r.calendar24.benchmark)],
     ['24h calendario · esito',r.calendar24.hit?'Favorevole al COT':'Non favorevole al COT'],
     ['96 M15 · verso COT',bp(r.trading96.directional)],
     ['96 M15 · prezzo long',bp(r.trading96.benchmark)],
     ['96 M15 · esito',r.trading96.hit?'Favorevole al COT':'Non favorevole al COT'],
     ['Differenza tra misure',bp(r.delta)]
   ])list.append(...rows(a,b));
   box.append(list);
   return box;
 }
 function render(){
   if(!model)return;
   const week=weekSelect.value,rel=relationSelect.value,symbol=marketSelect.value;
   const chosen=model.cases.filter(r=>
      (week==='all'||r.week===week)&&
      (rel==='all'||r.relation===rel)&&
      (symbol==='all'||r.symbol===symbol));
   const shortList=chosen.slice(0,24);
   const wk=model.weekly.filter(r=>week==='all'||r.week===week);
   weekly.replaceChildren();
   for(const w of wk){
     const card=el('div','detail');
     card.append(el('h4','', 'Settimana COT '+w.week));
     card.append(el('p','small',w.paired+' coorti abbinate su '+
       w.matured+' potenzialmente mature. Stessa settimana: risultati correlabili.'));
     const list=el('dl');
     list.append(
       ...rows('Concordanze (casi)',w.aligned.samples),
       ...rows('Concordanze favorevoli',w.aligned.hits),
       ...rows('Divergenze (casi)',w.divergent.samples),
       ...rows('Divergenze favorevoli',w.divergent.hits));
     card.append(list);
     weekly.append(card);
   }
   items.replaceChildren(...shortList.map(caseCard));
   status.textContent=fmt(chosen.length)+' casi storici con due esiti disponibili. '+
     (chosen.length>24?'Mostrati i primi 24: seleziona una settimana e un mercato. ':'')+
     'Settimana COT = riferimento del report, non ora dell’osservazione. '+
     'Variazioni in punti base lordi, non guadagni realizzati.';
   if(chosen.length===0)items.append(el('p','small',
     'Nessuna osservazione abbinata per i filtri selezionati.'));
 }
 async function load(){
   if(loading)return;
   loading=true;
   status.textContent='Controllo il registro delle evidenze sulla VPS…';
   try{
     const res=await fetch('./private-api/signals/dual24/cases',
       {cache:'no-store',credentials:'same-origin'});
     if(!res.ok)throw new Error('http');
     const data=parser.read(await res.json());
     if(!data)throw new Error('schema');
     const old=weekSelect.value;
     model=data;
     weekSelect.replaceChildren(new Option('Tutte le settimane disponibili','all'),
       ...data.weekly.map(r=>new Option('Settimana COT '+r.week,r.week)));
     // The default deliberately shows one week; not a cherry-picked return.
     weekSelect.value=data.weekly.some(w=>w.week===old)?old:
       (data.weekly.length?data.weekly[0].week:'all');
     render();
   }catch(_e){
     model=null;
     weekly.replaceChildren();
     items.replaceChildren();
     status.textContent='Registro delle condizioni non disponibile sulla VPS. '+
       'Le analisi statistiche precedenti restano separate.';
   }finally{loading=false;}
 }
 weekSelect.addEventListener('change',render);
 relationSelect.addEventListener('change',render);
 marketSelect.addEventListener('change',render);
 const refresh=document.getElementById('stat-refresh');
 if(refresh)refresh.addEventListener('click',load);
 load();
 window.setInterval(()=>{if(!document.hidden)load();},5*60*1000);
})();