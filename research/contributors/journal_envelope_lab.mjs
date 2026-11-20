// REMURA Contributors v0.29 LAB — 16/11/2026 08:24 CET
// Synthetic-only local subprocess. Never use production keys or data.
// No network or file writes; one bounded stdin message, one stdout response; no diagnostic details.
import {createCipheriv,createDecipheriv,randomBytes} from "node:crypto";
const deny=()=>{throw Error("envelope_denied");};
const hex=(s,n)=>typeof s==="string"&&s.length===n&&/^[a-f0-9]+$/.test(s);
const shape=(x,keys)=>x&&Object.getPrototypeOf(x)===Object.prototype&&Object.keys(x).length===keys.length&&keys.every(k=>Object.hasOwn(x,k));
function processMessage(p){
 if(!shape(p,["synthetic","mode","key","journal","seq","data"])||p.synthetic!==true||
    !hex(p.key,64)||/^0+$/.test(p.key)||!hex(p.journal,32)||!Number.isInteger(p.seq)||p.seq<1||p.seq>6)deny();
 const key=Buffer.from(p.key,"hex");
 const aad=Buffer.from(JSON.stringify(["remura-contributors-journal-lab-v1",p.journal,p.seq]));
 try{
  if(p.mode==="seal"){
   if(typeof p.data!=="string"||!p.data.length||p.data.length>2048||p.data.length%2!==0||!hex(p.data,p.data.length))deny();
   const nonce=randomBytes(12);
   const c=createCipheriv("aes-256-gcm",key,nonce,{authTagLength:16});c.setAAD(aad);
   const ct=Buffer.concat([c.update(Buffer.from(p.data,"hex")),c.final()]);
   return {v:1,nonce:nonce.toString("hex"),ct:ct.toString("hex"),tag:c.getAuthTag().toString("hex")};
  }
  if(p.mode==="open"){
   const e=p.data;
   if(!shape(e,["v","nonce","ct","tag"])||e.v!==1||!hex(e.nonce,24)||!hex(e.tag,32)||
    typeof e.ct!=="string"||!e.ct.length||e.ct.length>2048||e.ct.length%2!==0||!hex(e.ct,e.ct.length))deny();
   const d=createDecipheriv("aes-256-gcm",key,Buffer.from(e.nonce,"hex"),{authTagLength:16});
   d.setAAD(aad);d.setAuthTag(Buffer.from(e.tag,"hex"));
   const raw=Buffer.concat([d.update(Buffer.from(e.ct,"hex")),d.final()]);
   return {plaintext:raw.toString("hex")};
  }
  deny();
 }finally{key.fill(0);}
}
try{
 const chunks=[];let total=0;
 for await(const ch of process.stdin){total+=ch.length;if(total>4096)deny();chunks.push(ch);}
 const p=JSON.parse(new TextDecoder("utf-8",{fatal:true}).decode(Buffer.concat(chunks)));
 process.stdout.write(JSON.stringify(processMessage(p)));
}catch{process.exitCode=1;}
