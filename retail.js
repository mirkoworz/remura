(()=>{"use strict";
const root=document.getElementById("retail-module");if(!root)return;
const sym=(new URLSearchParams(location.search).get("symbol")||"XAUUSD").toUpperCase();
const map={US500:"CME_MINI:ES1!",NAS100:"CME_MINI:NQ1!",US30:"CBOT_MINI:YM1!",US2000:"CME_MINI:RTY1!",DXY:"TVC:DXY"};
const ticker=map[sym]||"OANDA:"+sym;
const $=id=>document.getElementById(id);
const fmt=n=>Number.isFinite(+n)?new Intl.NumberFormat("it-IT",{maximumFractionDigits:2}).format(+n):"—";
let tf="15",mode="lots",history=[];
$("r-tradingview").href="https://www.tradingview.com/chart/?symbol="+encodeURIComponent(ticker);
$("r-myfxbook").href="https://www.myfxbook.com/community/outlook/"+encodeURIComponent(sym);
function price(){
 const node=$("r-price");node.replaceChildren();
 const wrap=document.createElement("div");wrap.className="tradingview-widget-container";wrap.style.cssText="height:100%;width:100%";
 const inside=document.createElement("div");inside.className="tradingview-widget-container__widget";wrap.append(inside);
 const script=document.createElement("script");script.async=true;script.type="text/javascript";
 script.src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
 script.text=JSON.stringify({autosize:true,symbol:ticker,interval:tf,theme:"dark",style:"1",locale:"it",timezone:"Etc/UTC",backgroundColor:"#0b1b25",hide_top_toolbar:true,hide_side_toolbar:true,hide_volume:true,allow_symbol_change:false,save_image:false});
 wrap.append(script);node.append(wrap);
}
for(const [label,value] of [["M1","1"],["M5","5"],["M15","15"],["M30","30"],["H1","60"],["H4","240"],["D1","D"]]){
 const b=document.createElement("button");b.type="button";b.textContent=label;b.setAttribute("aria-pressed",String(value===tf));
 b.addEventListener("click",()=>{if(tf===value)return;tf=value;for(const v of $("r-tf").querySelectorAll("button"))v.setAttribute("aria-pressed",String(b===v));price();});
 $("r-tf").append(b);
}
for(const b of $("r-modes").querySelectorAll("button"))b.addEventListener("click",()=>{
 mode=b.dataset.mode;for(const v of $("r-modes").querySelectorAll("button"))v.setAttribute("aria-pressed",String(b===v));draw();
});
function draw(){
 const node=$("r-chart");node.replaceChildren();
 const keys=mode==="lots"?["lLots","sLots"]:["lPos","sPos"];
 const records=history.filter(r=>r&&Number.isFinite(+r[keys[0]])&&Number.isFinite(+r[keys[1]])&&Number.isFinite(Date.parse(r.t))).slice(-360);
 $("r-count").textContent=records.length+" rilevazioni";
 if(records.length<2){let box=document.createElement("div");box.className="rt-empty";box.textContent=records.length?"Prima rilevazione acquisita: in attesa della successiva.":"Storico non disponibile. Remura non mostra dati fittizi.";node.append(box);return;}
 const W=680,H=235,L=44,R=12,T=17,B=20,peak=Math.max(1,...records.flatMap(r=>[+r[keys[0]],+r[keys[1]]]))*1.1;
 const dates=records.map(r=>Date.parse(r.t)),first=dates[0],last=Math.max(first+1,dates[dates.length-1]);
 const X=i=>L+(dates[i]-first)/(last-first)*(W-L-R),Y=n=>T+(peak-n)/peak*(H-T-B);
 const path=k=>records.map((r,i)=>(i?"L":"M")+X(i).toFixed(2)+","+Y(+r[k]).toFixed(2)).join(" ");
 let chart='<svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="Storico Myfxbook lotti e posizioni long short">';
 for(let i=0;i<5;i++){let v=peak*i/4;chart+='<line x1="'+L+'" x2="'+(W-R)+'" y1="'+Y(v)+'" y2="'+Y(v)+'" stroke="#35515b" stroke-dasharray="3 5"/><text x="'+(L-5)+'" y="'+(Y(v)+3)+'" text-anchor="end" font-size="10" fill="#9cb9bd">'+fmt(v)+'</text>';}
 chart+='<path d="'+path(keys[0])+'" fill="none" stroke="#48c78b" stroke-width="3"/><path d="'+path(keys[1])+'" fill="none" stroke="#f77885" stroke-width="2.7"/>';
 const label=t=>new Date(t).toLocaleDateString('it-IT',{day:'2-digit',month:'short',timeZone:'Europe/Rome'});
 chart+='<text x="'+L+'" y="'+(H-6)+'" fill="#a9c2c8" font-size="11">'+label(first)+'</text><text x="'+(W-R)+'" y="'+(H-6)+'" text-anchor="end" fill="#a9c2c8" font-size="11">'+label(last)+'</text></svg>';
 node.innerHTML=chart;
}
async function retail(){
 try{
 const base="https://raw.githubusercontent.com/mirkoworz/remura/main/data/myfxbook/",v=Date.now();
 const responses=await Promise.all([fetch(base+"latest.json?ts="+v,{cache:"no-store"}),fetch(base+"history.json?ts="+v,{cache:"no-store"})]);
 if(!responses.every(r=>r.ok))throw Error("Feed non disponibile");
 const [latest,archive]=await Promise.all(responses.map(r=>r.json()));
 history=Array.isArray(archive.symbols?.[sym])?archive.symbols[sym]:[];draw();
 const p=latest.symbols?.[sym];
 if(!p){$("r-status").textContent=latest.status==="not_configured"?"Myfxbook da attivare":"Sentiment N/D";$("r-date").textContent="Nessun dato Myfxbook verificato per "+sym+". Nessun numero simulato.";return;}
 const at=p.t||latest.updatedAt,age=Date.now()-Date.parse(at),fresh=Number.isFinite(age)&&age>=0&&age<3*3600000;
 $("r-status").textContent=fresh?"Myfxbook · rilevato":"Myfxbook · datato";$("r-status").className="rt-tag"+(fresh?"":" warn");
 const values=[["r-lp",fmt(p.lPct)+"%"],["r-sp",fmt(p.sPct)+"%"],["r-ll",fmt(p.lLots)+" lotti"],["r-sl",fmt(p.sLots)+" lotti"],["r-nl",fmt(p.lPos)],["r-ns",fmt(p.sPos)],["r-al","Prezzo medio "+fmt(p.avgL)],["r-as","Prezzo medio "+fmt(p.avgS)]];
 for(const [id,value] of values)$(id).textContent=value;
 const lp=+p.lPct,sp=+p.sPct,total=lp+sp;
 $("r-bar-long").style.width=Number.isFinite(total)&&total>0?Math.max(0,Math.min(100,100*lp/total))+"%":"0%";
 $("r-bar-short").style.width=Number.isFinite(total)&&total>0?Math.max(0,Math.min(100,100*sp/total))+"%":"0%";
 const text=new Date(at).toLocaleString("it-IT",{timeZone:"Europe/Rome"});
 $("r-updated").textContent=text;
 $("r-date").textContent="Myfxbook · "+text+" (ora italiana). "+(fresh?"Rilevazione recente.":"ATTENZIONE: rilevazione vecchia.");
 }catch(e){$("r-status").textContent="Myfxbook non collegato";$("r-date").textContent="Feed retail mancante o non ancora configurato. Nessuna percentuale inventata.";draw();}
}
price();draw();retail();
})();