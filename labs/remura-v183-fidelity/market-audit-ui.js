/* REMURA v1.46 — private per-market 24h research only. */
(function(){
  'use strict';
  const parser=window.REMURA_MARKET_AUDIT;
  const panel=document.getElementById('market-audit-panel');
  const select=document.getElementById('market-audit-select');
  const output=document.getElementById('market-audit-results');
  const status=document.getElementById('market-audit-state');
  const selector=document.querySelector('[data-horizon="24"]');
  if(!parser||!panel||!select||!output||!status||!selector)return;
  const node=(tag,cls,value)=>{
    const x=document.createElement(tag);
    if(cls)x.className=cls;
    if(value!==undefined)x.textContent=String(value);
    return x;
  };
  const number=x=>x==null?'—':x.toLocaleString('it-IT',{maximumFractionDigits:2});
  const pct=x=>x==null?'—':number(x)+'%';
  const bps=x=>x==null?'—':(x>0?'+':'')+number(x)+' bp';
  const metrics=['24h calendario','96 M15 negoziate'];
  let snapshot=null;
  let loading=false;
  function groupCard(title,record){
    const card=node('article','detail');
    card.append(node('h3','',title));
    card.append(node('p','small',record.matched+
      ' osservazioni abbinate su '+record.matured+
      ' coorti mature; '+record.weeks+' settimane COT distinte.'));
    if(!record.matched){
      card.append(node('p','vrd','Campione insufficiente · nessun confronto abbinato'));
      return card;
    }
    const table=node('dl');
    const pairs=[
      ['Campioni confrontabili',number(record.matched)],
      ['Finestre non confrontabili',number(record.unmatched)],
      ['Differenza media 96 M15 − calendario',bps(record.delta)]
    ];
    for(let i=0;i<2;i++){
      const item=record.values[i];
      pairs.push(
        [metrics[i]+' · direzione COT',pct(item.hit)],
        [metrics[i]+' · media verso COT',bps(item.mean)],
        [metrics[i]+' · benchmark long',bps(item.baseline)],
        [metrics[i]+' · intervallo Wilson',pct(item.low)+' – '+pct(item.high)]
      );
    }
    for(const [term,val] of pairs){
      table.append(node('dt','',term),node('dd','',val));
    }
    card.append(node('p','vrd',record.values[0].verdict),table);
    return card;
  }
  function render(){
    if(!snapshot)return;
    const value=select.value;
    if(value==='all'){
      output.replaceChildren(
        groupCard('Tutti i mercati — solo osservazioni abbinate',snapshot.total),
        groupCard('COT e prezzo concordi',snapshot.relations.aligned),
        groupCard('COT e prezzo divergenti',snapshot.relations.divergent)
      );
    }else{
      const match=snapshot.markets.find(x=>x.symbol===value);
      output.replaceChildren(...(match?[groupCard(match.symbol,match)]:[]));
    }
    const data= value==='all'?snapshot.total:snapshot.markets.find(x=>x.symbol===value);
    status.textContent=data
      ?number(data.matched)+' confronti abbinati · '+number(data.weeks)+
       ' settimane COT distinte. Stesso mercato/settimana in entrambe le misure. '+
       'I mercati possono essere correlati: non è una probabilità di profitto.'
      :'Mercato non presente nel campione.';
  }
  function sync(){
    panel.hidden=selector.getAttribute('aria-pressed')!=='true';
  }
  async function load(){
    if(loading)return;
    loading=true;
    status.textContent='Carico solo statistiche abbinate dalla VPS…';
    try{
      const response=await fetch('./private-api/signals/dual24/markets',
        {cache:'no-store',credentials:'same-origin'});
      if(!response.ok)throw new Error('http');
      const parsed=parser.read(await response.json());
      if(!parsed)throw new Error('schema');
      const old=select.value;
      snapshot=parsed;
      select.replaceChildren(new Option('Tutti · concordanze e divergenze','all'),
        ...parsed.markets.map(x=>new Option(x.symbol+' · '+x.matched+' campioni abbinati',x.symbol)));
      select.value=parsed.markets.some(x=>x.symbol===old)?old:'all';
      render();
    }catch(_err){
      snapshot=null;
      output.replaceChildren();
      status.textContent='Confronto per mercato non disponibile sulla VPS. '+
        'Le statistiche precedenti rimangono inalterate.';
    }finally{
      loading=false;
    }
  }
  for(const button of document.querySelectorAll('[data-horizon]')){
    button.addEventListener('click',sync);
  }
  select.addEventListener('change',render);
  const refresh=document.getElementById('stat-refresh');
  if(refresh)refresh.addEventListener('click',load);
  sync();
  load();
  window.setInterval(()=>{if(!document.hidden)load();},5*60*1000);
})();