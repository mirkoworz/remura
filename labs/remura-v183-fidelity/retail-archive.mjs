import {buildRetailArchive} from './retail-archive-core.mjs';
const number=new Intl.NumberFormat('it-IT',{maximumFractionDigits:2});
const date=new Intl.DateTimeFormat('it-IT',{dateStyle:'short',timeStyle:'short',timeZone:'Europe/Rome'});
function node(tag,text){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;}
function chart(rows){
 const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 340 174');svg.setAttribute('role','img');svg.setAttribute('aria-label','Punti osservati: percentuali dei lotti long e short');
 const first=Date.parse(rows[0].t),last=Date.parse(rows.at(-1).t);
 const x=t=>last===first?181:34+(Date.parse(t)-first)*296/(last-first),y=v=>12+(100-v)*1.4;
 function draw(tag,attrs,text){const n=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));if(text!==undefined)n.textContent=text;svg.append(n);}
 for(const v of [0,25,50,75,100]){draw('line',{x1:34,x2:330,y1:y(v),y2:y(v),stroke:'#2d4f58'});draw('text',{x:29,y:y(v)+3,'text-anchor':'end',fill:'#a0bac0','font-size':10},v+'%');}
 for(const r of rows){draw('circle',{cx:x(r.t),cy:y(r.long),r:2,fill:'#69edca'});draw('circle',{cx:x(r.t),cy:y(r.short),r:2,fill:'#f5909c'});}
 return svg;
}
export function renderRetailArchive(root,data){
 const head=node('p',data.snapshot?'Snapshot del '+date.format(new Date(data.snapshot.t))+' · Long '+number.format(data.snapshot.long)+'% · Short '+number.format(data.snapshot.short)+'%':'Snapshot N/D per '+data.symbol);
 const view=node('div');root.replaceChildren(head,view);
 if(!data.rows.length){view.append(node('p','Storico N/D per questo strumento. Nessuna osservazione inventata.'));return;}
 const label=node('label','Periodo archivio '),select=node('select');
 for(const [value,title] of [['7','Ultimi 7 giorni rilevati'],['all','Intero archivio']]){const o=node('option',title);o.value=value;select.append(o);}select.value='7';label.append(select);
 const content=node('div');view.append(label,content);
 function update(){const all=data.rows,last=all.at(-1),rows=select.value==='all'?all:all.filter(r=>Date.parse(r.t)>=Date.parse(last.t)-604800000);
 const info=node('p',rows.length+' rilevazioni · dal '+date.format(new Date(rows[0].t))+' al '+date.format(new Date(last.t))+(data.stale?' · Storico fermo da oltre 48 ore rispetto allo snapshot.':''));
 const legend=node('p','● Long (verde)  ·  ● Short (rosa). Punti effettivi, senza interpolazione.');
 const details=node('details'),summary=node('summary','Mostra rilevazioni ('+rows.length+')'),wrap=node('div'),table=node('table');wrap.className='table-overflow';
 const tr=table.createTHead().insertRow();for(const name of ['Ora italiana','Long','Short']){const th=node('th',name);th.scope='col';tr.append(th);}
 const tb=table.createTBody();for(const r of [...rows].reverse()){const row=tb.insertRow();for(const v of [date.format(new Date(r.t)),number.format(r.long)+'%',number.format(r.short)+'%'])row.insertCell().textContent=v;}
 wrap.append(table);details.append(summary,wrap);content.replaceChildren(info,legend,chart(rows),details);
 }select.addEventListener('change',update);update();
}
async function load(path){const r=await fetch(new URL(path,import.meta.url),{mode:'same-origin'});if(!r.ok)throw Error('archive unavailable');return r.json();}
export async function mountRetailArchive(root,symbol){try{const [l,h]=await Promise.all([load('./data/myfxbook-latest.json'),load('./data/myfxbook-history.json')]);renderRetailArchive(root,buildRetailArchive(l,h,symbol));}catch{root.textContent='Archivio retail N/D. Nessun dato sostitutivo.';}}
