// REMURA Experience v0.21 LAB — 20/11/2026 CET
// Offline V2 consumer; no network, server authentication or persistent session.
import {validateSharedFixture} from './validate_shared_fixture_v011.mjs';
const V2='REMURA_SHARED_VIEW_FIXTURE_V2', TTL=900000;
function fail(){throw Error('VIEW_V2_REJECTED')}
export function validateV2(x,now){
 if(!x||Object.getPrototypeOf(x)!==Object.prototype||x.schema!==V2||!Number.isSafeInteger(x.revision)||x.revision<1||x.revision>32||!Array.isArray(x.prices)||x.prices.length>5)fail();
 const prices=x.prices.map(r=>{
  if(!r||Object.getPrototypeOf(r)!==Object.prototype)fail();
  if(r.freshness==='STALE'){if(r.price!==null)fail();return {...r,price:1};}
  if(r.freshness!=='WITHIN_DEMO_WINDOW'||typeof r.price!=='number')fail();
  return r;
 });
 // Placeholder is confined to legacy structural validation, never exposed or retained.
 const checked=validateSharedFixture({...x,schema:'REMURA_SHARED_VIEW_FIXTURE_V1',prices},now);
 return {...checked,schema:V2,prices:checked.prices.map(r=>({...r,price:r.freshness==='STALE'?null:r.price}))};
}
function metadata(v){return JSON.stringify({...v,prices:v.prices.map(({price,freshness,...r})=>r)});}
function age(v,now){return {...v,prices:v.prices.map(r=>r.price===null||now-Date.parse(r.observed_at)>TTL?{...r,price:null,freshness:'STALE'}:r)};}
export function makeConsumerV2({request,clock}){
 if(typeof request!=='function'||typeof clock!=='function')fail();
 let epoch=0,closed=false,visible=false,known=null,lastTime=-1;
 function close(){closed=true;epoch++;visible=false;known=null;}
 function sample(){const t=clock();if(!Number.isSafeInteger(t)||t<0||t<lastTime){close();fail();}lastTime=t;return t;}
 function prune(t){if(known)known=age(known,t);if(known&&t-Date.parse(known.as_of)>TTL)visible=false;}
 async function refresh(){
  if(closed)return 'CANCELLED';
  const id=++epoch;visible=false;
  try{
   prune(sample());const r=await request();if(closed||id!==epoch)return 'CANCELLED';
   const now=sample();prune(now);
   if(r?.status===401||r?.status===403){close();return 'DENIED';}
   if(r?.status!==200||r.headers?.['Cache-Control']!=='no-store, max-age=0'||typeof r.body!=='string'||r.body.length>16384||new TextEncoder().encode(r.body).length>16384)return 'UNAVAILABLE';
   const v=validateV2(JSON.parse(r.body),now);
   if(known){
    if(v.revision<known.revision||v.as_of<known.as_of)return 'UNAVAILABLE';
    if(v.revision===known.revision){
     if(metadata(v)!==metadata(known))return 'UNAVAILABLE';
     for(let i=0;i<v.prices.length;i++){
      const a=known.prices[i].price,b=v.prices[i].price;
      if(b!==null&&(a===null||a!==b))return 'UNAVAILABLE';
     }
    }
   }
   known=v;visible=true;return 'READY';
  }catch{return closed||id!==epoch?'CANCELLED':'UNAVAILABLE';}
 }
 function read(){
  if(closed)return null;
  try{prune(sample());return visible&&known?structuredClone(known):null;}
  catch{close();return null;}
 }
 return Object.freeze({refresh,read,close});
}
