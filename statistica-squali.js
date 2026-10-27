/* REMURA v1.41 — Private statistics, view only. No mock data or orders. */
(function(){
  'use strict';
  const core=window.REMURA_STAT_VALIDATION;
  if(!core)return;
  const endpoint='./private-api/signals/validation';
  const status=document.getElementById('stat-status');
  const area=document.getElementById('stat-data');
  const refresh=document.getElementById('stat-refresh');
  const buttons=[...document.querySelectorAll('[data-horizon]')];
  let model=null, horizon=1, pending=false;

  function node(tag,css,text){
    const e=document.createElement(tag);
    if(css)e.className=css;
    if(text!==undefined)e.textContent=String(text);
    return e;
  }
  function group(segment){
    return model?.items[String(horizon)+':'+segment]||null;
  }
  function integer(value){return Number(value).toLocaleString('it-IT');}
  function valueCard(label,value,hint){
    const card=node('div','stat');
    card.append(node('small','',label),node('strong','',value));
    if(hint)card.append(node('span','',hint));
    return card;
  }
  function smallTable(card,row){
    const dl=node('dl');
    for(const [label,value] of row){
      dl.append(node('dt','',label),node('dd','',value));
    }
    card.append(dl);
  }
  function subCard(label,data){
    const el=node('article','detail');
    el.append(node('h3','',label),
      node('strong','',data.samples?core.formatPercent(data.hit):'—'),
      node('div','dim','Frequenza in direzione COT'));
    el.append(node('p',data.verdict==='Campione insufficiente'?'bad small':'small',data.verdict));
    smallTable(el,[
      ['Campioni',integer(data.samples)],
      ['Settimane COT',integer(data.weeks)],
      ['Copertura coorti mature',core.formatPercent(data.coverage)],
      ['Intervallo 95%',data.samples?
        core.formatPercent(data.low)+' – '+core.formatPercent(data.high):'—'],
      ['Movimento medio verso COT',core.formatBps(data.mean)],
      ['Benchmark long',core.formatBps(data.benchmark)]
    ]);
    return el;
  }
  function render(){
    if(!model)return;
    for(const button of buttons){
      button.setAttribute('aria-pressed',String(Number(button.dataset.horizon)===horizon));
    }
    const main=group('all');
    const explain=document.getElementById('stat-interpretation');
    if(main.samples===0){
      explain.textContent=main.matured===0?
        'Non ci sono ancora finestre complete di '+horizon+' ore per il campione principale. '+
        'Zero risultati non significa zero movimenti o previsioni sbagliate.':
        integer(main.matured)+' finestre da '+horizon+' ore sono trascorse, ma nessuna '+ 
        'dispone di tutte le candele M15 contigue necessarie alla verifica.';
    }else{
      explain.textContent=integer(main.samples)+' osservazioni valutabili su '+
        integer(main.weeks)+' settimane COT distinte. I mercati possono essere '+
        'correlati: questa percentuale descrive il campione, non misura ancora '+
        'una probabilità affidabile di previsione.';
    }
    document.getElementById('main-verdict').textContent=main.verdict;
    const summary=document.getElementById('stat-overview');
    summary.replaceChildren(
      valueCard('Osservazioni valutabili',integer(main.samples),
        integer(main.weeks)+' settimane COT distinte'),
      valueCard('Prezzo nella direzione COT',core.formatPercent(main.hit),
        main.samples?'Intervallo 95%: '+core.formatPercent(main.low)+' – '+
          core.formatPercent(main.high):'Nessun risultato autentico'),
      valueCard('Movimento medio verso COT',core.formatBps(main.mean),
        'Benchmark long: '+core.formatBps(main.benchmark)),
      valueCard('Copertura coorti già mature',core.formatPercent(main.coverage),
        integer(main.samples)+' valutate su '+integer(main.matured)+
        '; '+integer(main.unevaluated)+' senza esito'),
      valueCard('Escursione favorevole',core.formatBps(main.favorable),
        'Prezzi massimi/minimi rilevati'),
      valueCard('Escursione contraria',core.formatBps(main.adverse),
        'Prezzi massimi/minimi rilevati')
    );
    document.getElementById('stat-relations').replaceChildren(
      subCard('Concordanza COT / prezzo',group('aligned')),
      subCard('Divergenza COT / prezzo',group('divergent'))
    );
    document.getElementById('stat-stages').replaceChildren(
      subCard('Prima osservazione',group('observation')),
      subCard('Conferma tecnica',group('technical_confirmation')),
      subCard('Evento qualificato',group('qualified_event'))
    );
    area.hidden=false;
  }
  async function load(){
    if(pending)return;
    pending=true;
    refresh.disabled=true;
    status.textContent='Verifico le misure autentiche sulla VPS privata…';
    status.dataset.state='loading';
    try{
      const response=await fetch(endpoint,{cache:'no-store',credentials:'same-origin'});
      if(!response.ok)throw Error('HTTP '+response.status);
      const parsed=core.read(await response.json());
      if(!parsed)throw Error('schema');
      model=parsed;
      render();
      status.dataset.state='ok';
      status.textContent='Dati aggregati dalla VPS · '+integer(model.cohorts)+
        ' coorti complessive (incluse le conferme sovrapposte).';
    }catch(_error){
      // Never retain stale results with a "live" label.
      model=null;
      area.hidden=true;
      status.dataset.state='error';
      status.textContent='Verifica statistica non disponibile o non compatibile. '+
        'La v1.40 potrebbe non essere ancora installata: nessuna statistica stimata.';
    }finally{
      pending=false;
      refresh.disabled=false;
    }
  }
  for(const button of buttons){
    button.addEventListener('click',()=>{
      horizon=Number(button.dataset.horizon);
      render();
    });
  }
  refresh.addEventListener('click',load);
  load();
  window.setInterval(()=>{if(!document.hidden)load();},5*60*1000);
})();