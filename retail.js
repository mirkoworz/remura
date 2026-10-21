(()=>{"use strict";
const root=document.getElementById("retail-module");if(!root)return;
const sym=(new URLSearchParams(location.search).get("symbol")||"XAUUSD").toUpperCase();
const map={US500:"CME_MINI:ES1!",NAS100:"CME_MINI:NQ1!",US30:"CBOT_MINI:YM1!",US2000:"CME_MINI:RTY1!",DXY:"TVC:DXY"};
const ticker=map[sym]||"OANDA:"+sym;
const $=id=>document.getElementById(id);
const fmt=n=>n!==null&&n!==undefined&&n!==""&&Number.isFinite(+n)?new Intl.NumberFormat("it-IT",{maximumFractionDigits:2}).format(+n):"—";
let tf="15",mode="lots",history=[],period="7d";
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
const PERIODS={ "6h":6*3600000,"1d":24*3600000,"7d":7*86400000,"30d":30*86400000,"all":Infinity };
for(const b of $("r-windows").querySelectorAll("button")){
 b.addEventListener("click",()=>{
   period=b.dataset.window;
   for(const x of $("r-windows").querySelectorAll("button"))x.setAttribute("aria-pressed",String(x===b));
   draw();
 });
}
function localDate(timestamp,withTime=true){
 const date=new Date(timestamp);
 if(!Number.isFinite(+date))return "—";
 return new Intl.DateTimeFormat("it-IT",withTime?{day:"2-digit",month:"short",hour:"2-digit",minute:"2-digit",timeZone:"Europe/Rome"}:{day:"2-digit",month:"short",timeZone:"Europe/Rome"}).format(date);
}
function signed(n){
 return Number.isFinite(n)?(n>0?"+":"")+fmt(n):"—";
}
function draw(){
 const host=$("r-chart");host.replaceChildren();
 const keys=mode==="lots"?["lLots","sLots"]:["lPos","sPos"];
 const all=history.filter(row=>row&&row.t&&Number.isFinite(Date.parse(row.t))&&
   keys.every(k=>row[k]!==null&&row[k]!==undefined&&Number.isFinite(Number(row[k]))&&+row[k]>=0))
   .sort((a,b)=>Date.parse(a.t)-Date.parse(b.t));
 const unique=new Map(all.map(row=>[row.t,row]));
 const timeline=[...unique.values()];
 const lastTime=timeline.length?Date.parse(timeline[timeline.length-1].t):Date.now();
 const minimum=lastTime-(PERIODS[period]??Infinity);
 const records=timeline.filter(row=>Date.parse(row.t)>=minimum);
 $("r-count").textContent=records.length+" rilevazioni nel periodo";
 if(records.length<2){
   const empty=document.createElement("div");empty.className="rt-empty";
   empty.textContent=records.length===1?
     "Una rilevazione per il periodo selezionato ("+localDate(records[0].t)+"). Servono due punti per disegnare le bande.":
     "Nessuna rilevazione in questa finestra. Scegli Tutto oppure attendi nuovi dati Myfxbook.";
   host.append(empty);
   $("r-change").textContent="Andamento: servono almeno due rilevazioni reali. Il grafico non interpola dati inesistenti.";
   return;
 }
 const firstTime=Date.parse(records[0].t),last=Date.parse(records[records.length-1].t);
 const W=750,H=315,L=56,R=22,T=22,B=46;
 const maximum=Math.max(1,...records.flatMap(r=>keys.map(k=>+r[k])))*1.10;
 const X=stamp=>L+(stamp-firstTime)/Math.max(1,last-firstTime)*(W-L-R);
 const Y=value=>T+(maximum-value)/maximum*(H-T-B);
 const bottom=Y(0);
 const time=records.map(p=>Date.parse(p.t));
 const segments=[];let segment=[];
 for(let i=0;i<records.length;i++){
   if(i>0 && time[i]-time[i-1]>75*60000){if(segment.length)segments.push(segment);segment=[];}
   segment.push(i);
 }
 if(segment.length)segments.push(segment);
 const linePath=(ids,key)=>ids.map((i,n)=>(n?"L":"M")+X(time[i]).toFixed(2)+" "+Y(+records[i][key]).toFixed(2)).join(" ");
 const areaPath=(ids,key)=>{
   const path=linePath(ids,key);
   return path+" L"+X(time[ids[ids.length-1]]).toFixed(2)+" "+bottom.toFixed(2)+
     " L"+X(time[ids[0]]).toFixed(2)+" "+bottom.toFixed(2)+" Z";
 };
 let svg='<svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="Bande del sentiment: verde volume long e rosso volume short, rilevazioni reali Myfxbook">';
 for(let i=0;i<5;i++){
   const value=maximum*i/4,y=Y(value).toFixed(2);
   svg+='<line x1="'+L+'" x2="'+(W-R)+'" y1="'+y+'" y2="'+y+'" stroke="#375861" stroke-dasharray="3 5"/>';
   svg+='<text x="'+(L-7)+'" y="'+(Number(y)+4)+'" text-anchor="end" font-size="11" fill="#a4c0c6">'+fmt(value)+'</text>';
 }
 for(let i=0;i<=4;i++){
   const t=firstTime+(last-firstTime)*i/4;
   const x=X(t).toFixed(2);
   if(i>0&&i<4)svg+='<line x1="'+x+'" x2="'+x+'" y1="'+T+'" y2="'+bottom+'" stroke="#31525a" stroke-dasharray="2 7"/>';
   const timeLabel=localDate(t,period==="6h"||period==="1d");
   svg+='<text x="'+x+'" y="'+(H-15)+'" font-size="11" text-anchor="'+(i===0?"start":i===4?"end":"middle")+'" fill="#aac5c8">'+timeLabel+'</text>';
 }
 for(const ids of segments){
   // A lone isolated point must not be turned into an invented flat line.
   if(ids.length>1){
     svg+='<path class="rt-area-green" d="'+areaPath(ids,keys[0])+'"/>';
     svg+='<path class="rt-area-red" d="'+areaPath(ids,keys[1])+'"/>';
     svg+='<path class="rt-long-line" d="'+linePath(ids,keys[0])+'"/>';
     svg+='<path class="rt-short-line" d="'+linePath(ids,keys[1])+'"/>';
   }else{
     const i=ids[0];
     svg+='<circle cx="'+X(time[i])+'" cy="'+Y(+records[i][keys[0]])+'" r="3" fill="#66e2a8"/>';
     svg+='<circle cx="'+X(time[i])+'" cy="'+Y(+records[i][keys[1]])+'" r="3" fill="#fd778a"/>';
   }
 }
 const tail=records[records.length-1];
 svg+='<circle cx="'+X(last)+'" cy="'+Y(+tail[keys[0]])+'" r="4" fill="#6ee1b0" stroke="#163e3c" stroke-width="2"/>';
 svg+='<circle cx="'+X(last)+'" cy="'+Y(+tail[keys[1]])+'" r="4" fill="#ff8592" stroke="#2c242d" stroke-width="2"/>';
 svg+='<rect x="'+L+'" y="'+T+'" width="'+(W-L-R)+'" height="'+(bottom-T)+'" fill="transparent" pointer-events="all"/>';
 svg+='</svg>';
 host.innerHTML=svg;
 const prev=records[records.length-2],elapsed=(last-Date.parse(prev.t))/60000;
 const deltaLong=+tail[keys[0]]-+prev[keys[0]];
 const deltaShort=+tail[keys[1]]-+prev[keys[1]];
 const unit=mode==="lots"?" lotti":" posizioni";
 $("r-change").textContent="Ultime 2 rilevazioni ("+Math.round(elapsed)+" min): Long "+
   signed(deltaLong)+unit+" · Short "+signed(deltaShort)+unit+
   (elapsed>75?" · Dati distanti nel tempo: discontinuità segnalata nel grafico.":"")+
   " · Ultimo punto "+localDate(tail.t)+".";
 const tooltip=document.createElement("div");tooltip.className="rt-tooltip";tooltip.hidden=true;host.append(tooltip);
 const canvas=host.querySelector("svg");
 function inspect(e){
   const bounds=canvas.getBoundingClientRect();
   if(!bounds.width)return;
   const xpos=(e.clientX-bounds.left)*W/bounds.width;
   const queried=firstTime+(Math.max(L,Math.min(W-R,xpos))-L)/(W-L-R)*Math.max(1,last-firstTime);
   let low=0,high=records.length;
   while(low<high){const mid=(low+high)>>1;if(time[mid]<queried)low=mid+1;else high=mid;}
   let idx=Math.min(records.length-1,low);
   if(idx>0&&Math.abs(time[idx-1]-queried)<Math.abs(time[idx]-queried))idx--;
   const observation=records[idx];
   tooltip.textContent=localDate(observation.t)+"\nLong: "+fmt(observation[keys[0]])+unit+
     "\nShort: "+fmt(observation[keys[1]])+unit;
   tooltip.hidden=false;
   const hostBounds=host.getBoundingClientRect();
   const left=Math.max(6,Math.min(hostBounds.width-205,e.clientX-hostBounds.left-85));
   tooltip.style.left=left+"px";
   tooltip.style.top="16px";
 }
 canvas.addEventListener("pointermove",inspect);
 canvas.addEventListener("pointerdown",inspect);
 canvas.addEventListener("pointerleave",()=>{tooltip.hidden=true;});
}
let retailFetching=false;
async function retail(){
 if(retailFetching||document.visibilityState==="hidden")return;
 retailFetching=true;
 try{
 const base="./private-api/retail/",v=Date.now(); // Same-origin private collector; works when repo is private.
 const current=await fetch(base+"latest.json?ts="+v,{cache:"no-store"});
 if(!current.ok)throw Error("Feed non disponibile");
 const latest=await current.json();
 // A compact per-symbol archive avoids downloading the histories of every Myfxbook market.
 const perSymbol=await fetch(base+"history/"+encodeURIComponent(sym)+".json?ts="+v,{cache:"no-store"});
 if(perSymbol.ok){
   const archived=await perSymbol.json();
   history=Array.isArray(archived.records)?archived.records:[];
 }else{
   // Compatibility with the first snapshot collected before v0.7.
   const legacy=await fetch(base+"history.json?ts="+v,{cache:"no-store"});
   const prior=legacy.ok?await legacy.json():{};
   history=Array.isArray(prior.symbols?.[sym])?prior.symbols[sym]:[];
 }
 draw();
 const p=latest.symbols?.[sym];
 if(!p){window.dispatchEvent(new CustomEvent("remura:retail",{detail:{symbol:sym,current:null,history,status:latest.status||"missing"}}));$("r-status").textContent=latest.status==="not_configured"?"Myfxbook da attivare":"Sentiment N/D";$("r-date").textContent="Nessun dato Myfxbook verificato per "+sym+". Nessun numero simulato.";return;}
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
 const sampleCount=Number(p.lPos)+Number(p.sPos);
 if(Number.isFinite(sampleCount)&&sampleCount>=0&&sampleCount<30){$("r-date").textContent+=" ATTENZIONE: solo "+sampleCount+" posizioni censite per questo simbolo. Il sentiment è poco rappresentativo.";}
 window.dispatchEvent(new CustomEvent("remura:retail",{detail:{symbol:sym,current:p,history,status:latest.status||"ok",fresh:fresh&&(!Number.isFinite(sampleCount)||sampleCount>=30)}}));
 }catch(e){window.dispatchEvent(new CustomEvent("remura:retail",{detail:{symbol:sym,current:null,history:[],status:"error"}}));$("r-status").textContent="Myfxbook non collegato";$("r-date").textContent="Feed retail mancante o non ancora configurato. Nessuna percentuale inventata.";draw();}
 finally{retailFetching=false;}
}
price();draw();retail();
window.setInterval(retail,5*60*1000);
window.addEventListener("visibilitychange",()=>{if(document.visibilityState==="visible")retail();});
})();