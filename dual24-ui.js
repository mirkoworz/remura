/* REMURA v1.45: optional add-on to established 1h/4h/24h statistics UI. */
(function(){
  'use strict';
  const core=window.REMURA_DUAL24;
  const panel=document.getElementById('dual24-panel');
  const output=document.getElementById('dual24-results');
  const state=document.getElementById('dual24-state');
  const legacyButton=document.querySelector('[data-horizon="24"]');
  if(!core||!panel||!output||!state||!legacyButton)return;
  const base=window.REMURA_STAT_VALIDATION;
  let busy=false;
  const node=(tag,cls,value)=>{
    const element=document.createElement(tag);
    if(cls)element.className=cls;
    if(value!==undefined)element.textContent=String(value);
    return element;
  };
  function fmt(v){return v==null?'—':v.toLocaleString('it-IT',{maximumFractionDigits:2});}
  function pct(v){return base?base.formatPercent(v):(v===null?'—':fmt(v)+'%');}
  function bps(v){return base?base.formatBps(v):(v===null?'—':fmt(v)+' bp');}
  function metricCard(name,description,item){
    const article=node('article','detail');
    article.append(node('h3','',name),node('p','small',description),
      node('strong','',item.samples?pct(item.hit):'—'),
      node('p','small',item.verdict));
    const terms=[
      ['Campioni',fmt(item.samples)],
      ['Settimane COT distinte',fmt(item.weeks)],
      ['Coorti potenzialmente mature',fmt(item.candidates)],
      ['Senza finestra verificata',fmt(item.excluded)],
      ['Quota verificata',pct(item.coverage)],
      ['Intervallo Wilson 95%',item.samples?pct(item.low)+' – '+pct(item.high):'—'],
      ['Movimento medio direzione COT',bps(item.mean)],
      ['Benchmark long',bps(item.baseline)],
      ['Escursione favorevole',bps(item.favorable)],
      ['Escursione contraria',bps(item.adverse)],
      ['Tempo effettivo trascorso',item.elapsed===null?'—':fmt(item.elapsed)+' ore'],
      ['Pause riconosciute (media)',fmt(item.pauses)],
      ['Uscite posticipate per pausa',fmt(item.delayed)]
    ];
    const list=node('dl');
    for(const [term,value] of terms)list.append(node('dt','',term),node('dd','',value));
    article.append(list);
    return article;
  }
  function render(model){
    const a=model.items['calendar24:all'];
    const b=model.items['trading96:all'];
    output.replaceChildren(
      metricCard('24 ore di calendario',
        'Apertura M15 al termine delle 24 ore trascorse. Solo per la pausa metallica verificata, eventuale prima riapertura entro 60 minuti.',a),
      metricCard('24 ore negoziate · 96 M15',
        'Apertura della 97ª candela, dopo 96 M15 effettivamente chiuse. Il tempo reale può superare le 24 ore.',b)
    );
    state.textContent='Dati autentici dalla VPS · '+fmt(model.cohorts)+
      ' coorti complessive, incluse le conferme sovrapposte. '+
      'Settimane COT distinte: '+fmt(a.weeks)+' (calendario), '+
      fmt(b.weeks)+' (negoziazione). '+
      'Queste percentuali descrivono il campione, non provano una previsione affidabile.';
  }
  function sync(){
    panel.hidden=legacyButton.getAttribute('aria-pressed')!=='true';
  }
  async function load(){
    if(busy)return;
    busy=true;
    state.textContent='Verifico gli esiti a 24 ore realmente disponibili…';
    try{
      const response=await fetch('./private-api/signals/dual24',
        {cache:'no-store',credentials:'same-origin'});
      if(!response.ok)throw Error('http');
      const data=core.read(await response.json());
      if(!data)throw Error('schema');
      render(data);
    }catch(_error){
      output.replaceChildren();
      state.textContent='Nuova verifica 24h non disponibile sulla VPS. '+
        'I risultati precedenti 1h/4h/24h rimangono validi e separati.';
    }finally{
      busy=false;
    }
  }
  for(const button of document.querySelectorAll('[data-horizon]')){
    button.addEventListener('click',()=>{sync();});
  }
  const refresh=document.getElementById('stat-refresh');
  if(refresh)refresh.addEventListener('click',load);
  sync();
  load();
  window.setInterval(()=>{if(!document.hidden)load();},5*60*1000);
})();