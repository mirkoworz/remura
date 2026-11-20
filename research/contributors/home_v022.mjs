// REMURA Experience v0.22 LAB — 20/11/2026 CET
// Local Home adapter. No network, actual authorization or persistent session.
const INFO=new Set(['Stato prezzi','COT & Sentiment','Mercati']);
const HOME_TTL=900000;
export function createHomeV2({session,clock,role,panel,renderInfo,renderStatus,onDenied,schedule,cancel}){
 if(!session||!['read','refresh','close'].every(k=>typeof session[k]==='function')||![clock,role,panel,renderInfo,renderStatus,onDenied,schedule,cancel].every(f=>typeof f==='function'))throw Error('HOME_FIXTURE_ONLY');
 let timer=null,epoch=0,closed=false,busy=false;
 function unschedule(){if(timer!==null){cancel(timer);timer=null;}}
 function close(){if(closed)return;closed=true;epoch++;busy=false;unschedule();session.close();}
 function sync(){
  unschedule();if(closed)return null;
  if(role()!=='CONTRIBUTOR'){close();onDenied();return null;}
  try{
   const v=session.read(),now=clock();
   if(!Number.isSafeInteger(now)||now<0)throw Error('clock');
   renderStatus(v,busy);
   const current=panel();if(INFO.has(current))renderInfo(current,v);
   if(v){
    const deadlines=[Date.parse(v.as_of)+HOME_TTL+1,...v.prices.filter(p=>p.price!==null).map(p=>Date.parse(p.observed_at)+HOME_TTL+1)];
    const next=Math.min(...deadlines.filter(t=>t>now));
    if(Number.isFinite(next))timer=schedule(()=>{timer=null;sync();},Math.max(1,next-now));
   }
   return v;
  }catch{close();onDenied();return null;}
 }
 async function refresh(){
  if(closed||role()!=='CONTRIBUTOR')return 'CANCELLED';
  const id=++epoch;busy=true;
  try{
   const pending=session.refresh();sync();const outcome=await pending;
   if(closed||id!==epoch)return 'CANCELLED';
   if(role()!=='CONTRIBUTOR'){close();onDenied();return 'CANCELLED';}
   busy=false;if(outcome==='DENIED'||outcome==='CANCELLED'){close();onDenied();return outcome;}
   sync();return outcome;
  }catch{if(closed||id!==epoch)return 'CANCELLED';busy=false;close();onDenied();return 'UNAVAILABLE';}
 }
 return Object.freeze({sync,refresh,close});
}
