// REMURA v0.8.128 LAB — 17/11/2026 CET
// Offline fixture only; no files, network, deployment or real keys.
import {createCipheriv,createDecipheriv,randomBytes,timingSafeEqual} from "node:crypto";
const SCHEMA="remura.tv.level.synthetic.encrypted-backup.v1",MAX=1048576;
const hex=(x,n)=>typeof x==="string"&&x.length===n&&/^[0-9a-f]+$/.test(x);
function need(x){if(!x)throw Error("backup_fixture_denied");}
function exact(x,keys){return x!==null&&typeof x==="object"&&!Array.isArray(x)&&Object.keys(x).sort().join(",")===keys.sort().join(",");}
function ctx(c){
 need(exact(c,["anchor","generation","sequence"]));
 need(hex(c.anchor,64)&&c.anchor!=="0".repeat(64)&&hex(c.generation,32)&&c.generation!=="0".repeat(32)&&Number.isSafeInteger(c.sequence)&&c.sequence>=1&&c.sequence<=128);
 return {anchor:c.anchor,generation:c.generation,sequence:c.sequence};
}
function guard(key,witnessKey,flags){
 need(flags?.synthetic===true&&flags?.ingress_closed===true);
 need(Buffer.isBuffer(key)&&key.length===32&&Buffer.isBuffer(witnessKey)&&witnessKey.length===32&&!timingSafeEqual(key,witnessKey));
}
function aad(c){return Buffer.from(JSON.stringify({schema:SCHEMA,...ctx(c)}),"ascii");}
function binary(x,max){
 need(typeof x==="string"&&x.length<=4*Math.ceil(max/3)&&/^[A-Za-z0-9+/]*={0,2}$/.test(x));
 const b=Buffer.from(x,"base64");need(b.length<=max&&b.toString("base64")===x);return b;
}
function sqlite(b){return Buffer.isBuffer(b)&&b.length>=512&&b.length<=MAX&&b.subarray(0,16).equals(Buffer.from("SQLite format 3\0","ascii"));}
export function seal(data,context,key,witnessKey,flags){
 guard(key,witnessKey,flags);need(sqlite(data));
 const c=ctx(context),nonce=randomBytes(12);
 const cipher=createCipheriv("aes-256-gcm",key,nonce,{authTagLength:16});
 cipher.setAAD(aad(c));
 const ciphertext=Buffer.concat([cipher.update(data),cipher.final()]);
 return {schema:SCHEMA,context:c,nonce:nonce.toString("base64"),ciphertext:ciphertext.toString("base64"),tag:cipher.getAuthTag().toString("base64")};
}
export function open(envelope,expected,key,witnessKey,flags){
 guard(key,witnessKey,flags);const c=ctx(expected);
 need(exact(envelope,["schema","context","nonce","ciphertext","tag"])&&envelope.schema===SCHEMA);
 need(aad(envelope.context).equals(aad(c)));
 const nonce=binary(envelope.nonce,12),tag=binary(envelope.tag,16),ciphertext=binary(envelope.ciphertext,MAX);
 need(nonce.length===12&&tag.length===16&&ciphertext.length>=512);
 const d=createDecipheriv("aes-256-gcm",key,nonce,{authTagLength:16});d.setAAD(aad(c));d.setAuthTag(tag);
 // No plaintext is returned before the tag has been verified.
 const partial=d.update(ciphertext);
 let tail;
 try{tail=d.final();}catch{partial.fill(0);throw Error("backup_fixture_denied");}
 const plaintext=Buffer.concat([partial,tail]);partial.fill(0);tail.fill(0);
 if(!sqlite(plaintext)){plaintext.fill(0);throw Error("backup_fixture_denied");}
 return plaintext;
}
