// REMURA v0.8.115 LAB — 17/11/2026 CET
// Native Request/Response fixture boundary. Default exported fetch is hard OFF.
// No receipts or payload writes. Full strict Pine validator still required.
import {reserve} from "./level_admission_candidate.mjs";
const MAX=15000, LIMIT=32, DEADLINE=1500;
const ROUTE=/^\/lab\/levels\/v1\/([a-f0-9]{64})$/;
const FIXTURE_PEER="SYNTHETIC_FIXTURE_PEER";
const off=()=>reply(503,"OFF");
function reply(status,code){return Response.json({status:code,synthetic:true,receipt_authenticated:false,operational_signal:false},{status,headers:{"Cache-Control":"no-store","X-Content-Type-Options":"nosniff"}});}
export default {async fetch(){return off();}};
export async function fixtureFetch(request,{synthetic=false,enabled=false,db,pin,keyHash,now}={}){
 if(synthetic!==true||enabled!==true)return off();
 if(!(request instanceof Request)||typeof now!=="function"||typeof keyHash!=="string"||!/^[a-f0-9]{64}$/.test(keyHash))return reply(503,"UNAVAILABLE");
 let t;try{t=now();}catch{return reply(503,"UNAVAILABLE");}
 const state=await reserve(db,pin,t);
 if(state!=="RESERVED")return reply(state==="RATE_LIMIT"?429:503,state==="RATE_LIMIT"?"RATE_LIMIT":"UNAVAILABLE");
 const url=new URL(request.url), m=ROUTE.exec(url.pathname);
 if(request.method!=="POST")return reply(405,"METHOD");
 if(url.protocol!=="https:"||url.search||!m)return reply(404,"NOT_FOUND");
 if(request.headers.get("x-remura-fixture-peer")!==FIXTURE_PEER)return reply(403,"DENIED");
 const hash=new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(m[1])));
 let mismatch=0;for(let i=0;i<32;i++)mismatch|=hash[i]^parseInt(keyHash.slice(i*2,i*2+2),16);
 if(mismatch)return reply(403,"DENIED");
 if(request.headers.get("content-type")?.toLowerCase()!=="application/json")return reply(415,"MEDIA_TYPE");
 if(request.headers.has("content-encoding")||request.headers.has("transfer-encoding"))return reply(400,"BAD_REQUEST");
 const length=request.headers.get("content-length");
 if(!length||!/^[0-9]{1,6}$/.test(length)||Number(length)===0)return reply(400,"BAD_REQUEST");
 if(Number(length)>MAX)return reply(413,"SIZE");
 if(!request.body)return reply(400,"BAD_REQUEST");
 const reader=request.body.getReader();
 let timer;
 const deadline=new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error("deadline")),DEADLINE);});
 let count=0,finished=false;
 try{
  for(let i=0;i<LIMIT;i++){
   const {done,value}=await Promise.race([reader.read(),deadline]);
   if(done){finished=true;break;}
   if(!(value instanceof Uint8Array)||value.length===0)return reply(400,"BAD_REQUEST");
   count+=value.length;
   if(count>MAX)return reply(413,"SIZE");
   if(count>Number(length))return reply(400,"BAD_REQUEST");
  }
  if(!finished||count!==Number(length))return reply(400,"BAD_REQUEST");
  // Deliberately do not buffer, parse, accept or persist unvalidated body.
  return reply(503,"VALIDATOR_NOT_CONNECTED");
 }catch{return reply(400,"BAD_REQUEST");}
 finally{
  clearTimeout(timer);
  if(!finished){try{void reader.cancel().catch(()=>{});}catch{}}
  try{reader.releaseLock();}catch{}
 }
}
