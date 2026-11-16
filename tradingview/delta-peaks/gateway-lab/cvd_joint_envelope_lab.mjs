// REMURA v0.8.98 LAB — 16/11/2026 13:56 CET
// Synthetic-only bounded local subprocess. No file/network.
import {createCipheriv,createDecipheriv,randomBytes} from "node:crypto";
const MAX=17317888,B64=4*Math.ceil(MAX/3);
const deny=()=>{throw Error("joint_envelope_denied");};
const shape=(x,keys)=>x&&Object.getPrototypeOf(x)===Object.prototype&&Object.keys(x).length===keys.length&&keys.every(k=>Object.hasOwn(x,k));
const hex=(s,n)=>typeof s==="string"&&s.length===n&&/^[a-f0-9]+$/.test(s);
function decode(s){
 if(typeof s!=="string"||!s.length||s.length>B64||s.length%4!==0)deny();
 const b=Buffer.from(s,"base64");
 if(!b.length||b.length>MAX||b.toString("base64")!==s)deny();
 return b;
}
function run(p){
 if(!shape(p,["synthetic","mode","key","generation","sequence","cutoff_ms","data"])||p.synthetic!==true||
 !hex(p.key,64)||/^0+$/.test(p.key)||!hex(p.generation,32)||!Number.isSafeInteger(p.sequence)||p.sequence<1||p.sequence>96||
 !Number.isSafeInteger(p.cutoff_ms)||p.cutoff_ms<1000000000000)deny();
 const key=Buffer.from(p.key,"hex"),aad=Buffer.from(JSON.stringify(["remura-d-joint-encrypted-synthetic-v1",p.generation,p.sequence,p.cutoff_ms]));
 try{
  if(p.mode==="seal"){
   const plain=decode(p.data);
   try{
    const nonce=randomBytes(12),c=createCipheriv("aes-256-gcm",key,nonce,{authTagLength:16});c.setAAD(aad);
    const ct=Buffer.concat([c.update(plain),c.final()]);
    return {v:1,nonce:nonce.toString("hex"),ct:ct.toString("base64"),tag:c.getAuthTag().toString("hex")};
   }finally{plain.fill(0);}
  }
  if(p.mode==="open"){
   const e=p.data;
   if(!shape(e,["v","nonce","ct","tag"])||e.v!==1||!hex(e.nonce,24)||!hex(e.tag,32))deny();
   const d=createDecipheriv("aes-256-gcm",key,Buffer.from(e.nonce,"hex"),{authTagLength:16});
   d.setAAD(aad);d.setAuthTag(Buffer.from(e.tag,"hex"));
   const plain=Buffer.concat([d.update(decode(e.ct)),d.final()]);
   try{return {plaintext:plain.toString("base64")};}finally{plain.fill(0);}
  }
  deny();
 }finally{key.fill(0);}
}
try{
 const chunks=[];let n=0;
 for await(const ch of process.stdin){n+=ch.length;if(n>B64+4096)deny();chunks.push(ch);}
 const p=JSON.parse(new TextDecoder("utf-8",{fatal:true}).decode(Buffer.concat(chunks)));
 process.stdout.write(JSON.stringify(run(p)));
}catch{process.exitCode=1;}
