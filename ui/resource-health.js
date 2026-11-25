/* REMURA 1.53: dati locali reali, nessun costo Oracle inventato. */
(()=>{
"use strict";
const $=id=>document.getElementById(id);
const n=v=>typeof v==="number"&&Number.isFinite(v)&&v>=0?v:null;
const count=v=>n(v)===null?"N/D":Math.round(v).toLocaleString("it-IT");
const size=v=>n(v)===null?"N/D":v<1024?count(v)+" B":v<1048576?(v/1024).toLocaleString("it-IT",{maximumFractionDigits:1})+" KB":v<1073741824?(v/1048576).toLocaleString("it-IT",{maximumFractionDigits:1})+" MB":(v/1073741824).toLocaleString("it-IT",{maximumFractionDigits:2})+" GB";
const put=(id,value)=>{if($(id))$(id).textContent=value};
function meter(id,a,b){
 const p=n(a)!==null&&n(b)!==null&&b>0?Math.min(100,100*a/b):null;
 const el=$(id);if(el){el.style.width=p===null?"0%":p+"%";el.dataset.level=p>=90?"high":p>=80?"warn":"ok";}
 return p===null?"N/D":p.toLocaleString("it-IT",{maximumFractionDigits:1})+"%";
}
async function refresh(){
 const btn=$("res-refresh");btn.disabled=true;
 try{
  const response=await fetch("./private-api/resources",{cache:"no-store",headers:{"Accept":"application/json"}});
  if(!response.ok)throw Error("private");
  const d=await response.json();if(d.schema!=="remura-resources-v1")throw Error("schema");
  const mem=d.memory||{},cpu=d.cpu||{},disk=d.disk||{},net=d.network||{},api=d.webApi||{};
  put("res-ram",size(mem.used)+" / "+size(mem.total));
  put("res-ram-sub",meter("res-ram-bar",mem.used,mem.total)+" occupata · swap "+size(mem.swapUsed));
  put("res-cpu",n(cpu.load1)===null?"N/D":cpu.load1.toLocaleString("it-IT",{maximumFractionDigits:2}));
  put("res-cpu-sub","Carico 1 minuto / "+count(cpu.logical)+" CPU logiche; non è la % istantanea");
  meter("res-cpu-bar",cpu.load1,cpu.logical);
  put("res-disk",size(disk.used)+" / "+size(disk.total));
  put("res-disk-sub",meter("res-disk-bar",disk.used,disk.total)+" del filesystem della VPS");
  put("res-network",size(net.txSinceInterfaceStart)+" ↑ / "+size(net.rxSinceInterfaceStart)+" ↓");
  put("res-network-sub","Dalla partenza dell’interfaccia, NON banda mensile Oracle");
  put("res-uptime",n(d.uptimeSeconds)===null?"N/D":Math.floor(d.uptimeSeconds/86400)+"g "+Math.floor(d.uptimeSeconds%86400/3600)+"h");
  put("res-requests",count(api.privateGet)+" private / "+count(api.allGet)+" GET");
  const t=new Date(d.sampledAt);
  put("res-time",Number.isFinite(t.getTime())?new Intl.DateTimeFormat("it-IT",{dateStyle:"short",timeStyle:"medium",timeZone:"Europe/Rome"}).format(t):"N/D");
  const st=$("res-status");st.dataset.status="ok";st.textContent="VPS raggiungibile: metriche locali aggiornate. Costi e quote Oracle non verificati.";
 }catch(e){
  const st=$("res-status");st.dataset.status="";st.textContent="N/D: metriche disponibili solo dalla REMURA privata via Tailscale, dopo l’aggiornamento del server.";
 }finally{btn.disabled=false;}
}
$("res-refresh")?.addEventListener("click",refresh);
refresh();
setInterval(()=>{if(document.visibilityState==="visible")refresh();},30000);
})();