// REMURA v0.8.128 LAB — 17/11/2026 CET
// Strictly synthetic stdin/stdout adapter for Python unittest, no real data.
import {seal,open} from "./level_encrypted_backup_lab_v1.mjs";
let chunks=[],size=0;
try{
 for await(const chunk of process.stdin){size+=chunk.length;if(size>1500000)throw Error("bound");chunks.push(chunk);}
 const s=JSON.parse(Buffer.concat(chunks).toString("utf8"));
 const key=Buffer.from(s.key,"hex"),w=Buffer.from(s.witness_key,"hex"),flags={synthetic:s.synthetic,ingress_closed:s.ingress_closed};
 if(!/^[0-9a-f]{64}$/.test(s.key)||!(/^[0-9a-f]{64}$/.test(s.witness_key)))throw Error("key");
 if(s.op==="seal"){
  const b=Buffer.from(s.data,"base64");if(b.toString("base64")!==s.data)throw Error("format");
  console.log(JSON.stringify({ok:true,envelope:seal(b,s.context,key,w,flags)}));
 }else if(s.op==="open"){
  const b=open(s.envelope,s.context,key,w,flags);
  console.log(JSON.stringify({ok:true,data:b.toString("base64")}));
 }else throw Error("op");
}catch{console.log(JSON.stringify({ok:false,error:"DENIED"}));}
