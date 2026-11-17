// REMURA v0.8.121 LAB — 17/11/2026 07:04 CET (session start)
// Native Request fixture only. No deployment manifest, binding or real peer attestation.
import {reserveFixture,finalizeFixture} from "./level_permit_ledger_candidate.mjs";
const MAX=15000, LIMIT=32, DEADLINE=1500;
const ROUTE=/^\/lab\/levels\/v2\/([a-f0-9]{64})$/;
function reply(status,code){return Response.json({status:code,synthetic:true,receipt_authenticated:false,scientific_admission:false,operational_signal:false},{status,headers:{"Cache-Control":"no-store","X-Content-Type-Options":"nosniff"}});}
const off=()=>reply(503,"OFF");
export default {async fetch(){return off();}};
export async function fixtureFetch(request,{synthetic=false,enabled=false,db,pin,keyHash,now,expected,afterCloseMs}={}){
 if(synthetic!==true||enabled!==true)return off();
 if(!(request instanceof Request)||typeof now!=="function"||typeof keyHash!=="string"||!/^[a-f0-9]{64}$/.test(keyHash))return reply(503,"UNAVAILABLE");
 let receivedMs;try{receivedMs=now();}catch{return reply(503,"UNAVAILABLE");}
 const permit=await reserveFixture(db,pin,receivedMs,{synthetic:true});
 if(permit.status!=="RESERVED")return reply(503,"UNAVAILABLE");
 let reader,timer,finished=false;
 try{
  const url=new URL(request.url),m=ROUTE.exec(url.pathname);
  if(request.method!=="POST")return reply(405,"METHOD");
  if(url.protocol!=="https:"||url.search||url.hash||!m)return reply(404,"NOT_FOUND");
  // A caller-controlled fixture header is NOT a production authentication method.
  if(request.headers.get("x-remura-fixture-peer")!=="SYNTHETIC_FIXTURE_PEER")return reply(403,"DENIED");
  const hash=new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(m[1])));
  let mismatch=0;for(let i=0;i<32;i++)mismatch|=hash[i]^parseInt(keyHash.slice(i*2,i*2+2),16);
  if(mismatch)return reply(403,"DENIED");
  if(request.headers.get("content-type")?.toLowerCase()!=="application/json")return reply(415,"MEDIA_TYPE");
  if(request.headers.has("content-encoding")||request.headers.has("transfer-encoding"))return reply(400,"BAD_REQUEST");
  const length=request.headers.get("content-length");
  if(!length||!/^[0-9]{1,6}$/.test(length)||Number(length)===0||!request.body)return reply(400,"BAD_REQUEST");
  if(Number(length)>MAX)return reply(413,"SIZE");
  reader=request.body.getReader();
  const deadline=new Promise((_,reject)=>{timer=setTimeout(()=>reject(new Error("deadline")),DEADLINE);});
  const bytes=new Uint8Array(Number(length));let count=0;
  for(let i=0;i<LIMIT;i++){
   const {done,value}=await Promise.race([reader.read(),deadline]);
   if(done){finished=true;break;}
   if(!(value instanceof Uint8Array)||value.length===0)return reply(400,"BAD_REQUEST");
   if(count+value.length>MAX)return reply(413,"SIZE");
   if(count+value.length>bytes.length)return reply(400,"BAD_REQUEST");
   bytes.set(value,count);count+=value.length;
  }
  if(!finished||count!==bytes.length)return reply(400,"BAD_REQUEST");
  const raw=new TextDecoder("utf-8",{fatal:true,ignoreBOM:true}).decode(bytes);
  clearTimeout(timer);
  const r=await finalizeFixture(db,raw,{synthetic:true,pin,attempt:permit.attempt,expected,receivedMs,afterCloseMs,completedMs:now()});
  const codes={STORED_SYNTHETIC:201,DUPLICATE:200,CONFLICT:409,CAPACITY_OR_ORDER:409,INVALID:400,CLOSED_USED_OR_EXPIRED:503,DENIED:503,UNAVAILABLE:503};
  return reply(codes[r.status]??503,Object.hasOwn(codes,r.status)?r.status:"UNAVAILABLE");
 }catch{return reply(400,"BAD_REQUEST");}
 finally{
  clearTimeout(timer);
  if(reader){if(!finished){try{void reader.cancel().catch(()=>{});}catch{}}try{reader.releaseLock();}catch{}}
 }
}
