import { buildCotHistory } from './cot-history-core.mjs';
const fmt=new Intl.NumberFormat('it-IT',{maximumFractionDigits:2});
const f=x=>x===null?'N/D':fmt.format(x);
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
function graph(s){
 const NS='http://www.w3.org/2000/svg',svg=document.createElementNS(NS,'svg');
 svg.setAttribute('viewBox','0 0 340 190');svg.setAttribute('role','img');svg.setAttribute('aria-label','Serie settimanali: '+s.categories.join(' e '));svg.classList.add('cot-graph');
 const all=s.rows.flatMap(r=>[r[1],r[2]]),min=Math.min(0,...all),max=Math.max(0,...all),lo=min===max?min-1:min,hi=min===max?max+1:max;
 const x=i=>34+i*296/52,y=v=>12+(hi-v)*150/(hi-lo);
 function node(tag,attrs,txt){const n=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));if(txt!==undefined)n.textContent=txt;svg.append(n);}
 for(let i=0;i<5;i++){const v=lo+(hi-lo)*i/4;node('line',{x1:34,y1:y(v),x2:330,y2:y(v),stroke:'currentColor',opacity:.17});node('text',{x:29,y:y(v)+3,'text-anchor':'end',fill:'currentColor','font-size':9},f(v));}
 node('line',{x1:34,y1:y(0),x2:330,y2:y(0),stroke:'currentColor',opacity:.55,'stroke-dasharray':'3 3'});
 for(const [j,color] of [[1,'#64d8c5'],[2,'#f6b65a']])node('polyline',{points:s.rows.map((r,i)=>x(i)+','+y(r[j])).join(' '),fill:'none',stroke:color,'stroke-width':2,'stroke-linejoin':'round'});
 node('text',{x:34,y:181,fill:'currentColor','font-size':10},s.rows[0][0]);node('text',{x:330,y:181,fill:'currentColor','font-size':10,'text-anchor':'end'},s.rows.at(-1)[0]);
 return svg;
}
export function renderCotHistory(root,archive,{symbol='EURUSD',fixed=false}={}){
 const {series,dates}=buildCotHistory(archive);
 if(!Object.hasOwn(series,symbol)){root.replaceChildren(el('p','N/D: nessun contratto COT storico verificato per '+symbol+'.','notice'));return;}
 const controls=el('div',undefined,'history-controls'),label=el('label','Mercato o fattore'),select=el('select');select.setAttribute('aria-label','Mercato COT storico');
 for(const [kind,title] of [['currency_future','Fattori valutari'],['synthetic_fx','Cross sintetici'],['futures_reference','Riferimenti futures']]){
   const group=el('optgroup');group.label=title;for(const [sym,s] of Object.entries(series))if(s.kind===kind){const o=el('option',sym);o.value=sym;group.append(o);}select.append(group);
 }
 select.value=symbol;controls.hidden=fixed;label.append(select);controls.append(label);
 const status=el('p','53 report · 14 contratti · 28 cross sintetici. Download pubblici forniti dall’OWNER; disponibilità storica non attestata.','muted');
 const view=el('div');view.setAttribute('aria-live','polite');root.replaceChildren(status,controls,view);
 function update(){
   const s=series[select.value];if(!s)return;
   const type=s.kind==='synthetic_fx'?'Differenza tra fattori futures (USD riferimento matematico), non posizioni spot.':'Posizioni nette futures in percentuale dell’open interest.';
   const cards=el('div',undefined,'cot-index-grid');
   for(const [key,title] of [['a',s.categories[0]],['b',s.categories[1]],['gap','Gap A − B']]){
     const card=el('div',undefined,'panel cot-index-card');card.append(el('span',title,'muted'),el('strong',f(s.index52[key])),el('small','Precedente: '+f(s.previousIndex52[key]),'muted'));cards.append(card);
   }
   const legend=el('p',undefined,'cot-legend');const a=el('span',s.categories[0]),b=el('span',s.categories[1]);a.className='cot-first';b.className='cot-second';legend.append(a,b);
   const table=el('table');const header=table.createTHead().insertRow();for(const text of ['Report','Netto A','Netto B','Gap A−B']){const th=el('th',text);th.scope='col';header.append(th);}
   const tbody=table.createTBody();for(const r of [...s.rows].reverse()){const tr=tbody.insertRow();for(const val of [r[0],f(r[1]),f(r[2]),f(r[1]-r[2])])tr.insertCell().textContent=val;}
   const wrap=el('div',undefined,'table-scroll');wrap.tabIndex=0;wrap.setAttribute('role','region');wrap.setAttribute('aria-label','53 report COT');wrap.append(table);
   const details=el('details');details.append(el('summary','Mostra 53 rilevazioni settimanali'),wrap);
   view.replaceChildren(el('p',type,'muted'),cards,el('p','Ultimo report: '+dates.at(-1)+' · Δ settimanale A: '+f(s.weeklyDeltaPp[0])+' pp · B: '+f(s.weeklyDeltaPp[1])+' pp'),legend,graph(s),details,el('p','Indice min-max 0–100 sulle ultime 52 osservazioni; Gap Index sul divario netto A−B. Non sono probabilità, flussi live o segnali.','muted'));
 }
 select.addEventListener('change',update);update();
}
export async function mountCotHistory(root,options={}){
 try{const r=await fetch(new URL('./data/cot-history-public.json',import.meta.url),{mode:'same-origin'});if(!r.ok)throw Error('archive');renderCotHistory(root,await r.json(),options);return true;}catch{root.replaceChildren(el('p','Storico COT non disponibile. Nessun indice sostitutivo.','notice'));return false;}
}
