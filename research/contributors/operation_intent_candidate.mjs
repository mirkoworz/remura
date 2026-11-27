// REMURA Contributors v0.23 LAB — 16/11/2026 07:14 CET
// Candidate only; no secrets provisioned. No default Worker entrypoint.
import {normalize} from "./d1_lab_adapter.mjs";
const HEX32=/^[a-f0-9]{32}$/,HEX64=/^[a-f0-9]{64}$/;
const deny=()=>Error("intent_denied");
const hex=x=>Array.from(new Uint8Array(x),n=>n.toString(16).padStart(2,"0")).join("");
const bytes=x=>Uint8Array.from(x.match(/../g),n=>parseInt(n,16));
const enc=new TextEncoder();
const seconds=()=>Math.floor(Date.now()/1000);
const shape=(p,keys)=>p&&Object.getPrototypeOf(p)===Object.prototype&&Object.keys(p).length===keys.length&&keys.every(k=>Object.hasOwn(p,k));
const SQL=Object.freeze({
 generation:"SELECT id FROM lab_generation WHERE id=1 AND generation=? AND journal_pin=?",
 permission:"SELECT 1 AS allowed FROM lab_state s JOIN lab_generation g ON g.id=s.id WHERE s.id=1 AND g.generation=? AND g.journal_pin=? AND CASE ? WHEN 'WRITE' THEN s.write_enabled WHEN 'RECOVERY' THEN s.recovery_enabled ELSE 0 END=1 AND ((?='OWNER' AND EXISTS(SELECT 1 FROM lab_owner WHERE id=1 AND subject=? AND email_tag=? AND revoked=0)) OR (?='CONTRIBUTOR' AND EXISTS(SELECT 1 FROM lab_identities WHERE subject=? AND email_tag=? AND revoked=0)))",
 burn:"INSERT INTO lab_intent_used(nonce,subject,mode,role,expires) SELECT ?,?,?,?,? FROM lab_state s JOIN lab_generation g ON g.id=s.id WHERE s.id=1 AND g.generation=? AND g.journal_pin=? AND ? BETWEEN unixepoch() AND unixepoch()+90 AND CASE ? WHEN 'WRITE' THEN s.write_enabled WHEN 'RECOVERY' THEN s.recovery_enabled ELSE 0 END=1 AND ((?='OWNER' AND EXISTS(SELECT 1 FROM lab_owner WHERE id=1 AND subject=? AND email_tag=? AND revoked=0)) OR (?='CONTRIBUTOR' AND EXISTS(SELECT 1 FROM lab_identities WHERE subject=? AND email_tag=? AND revoked=0)))"
});
function config(env){
 if(typeof env?.CONTRIBUTORS_GENERATION!=="string"||!HEX32.test(env.CONTRIBUTORS_GENERATION)||
    typeof env.CONTRIBUTORS_JOURNAL_PIN!=="string"||!HEX64.test(env.CONTRIBUTORS_JOURNAL_PIN)||
    typeof env.INTENT_HMAC_KEY!=="string"||!HEX64.test(env.INTENT_HMAC_KEY)||/^0+$/.test(env.INTENT_HMAC_KEY)||
    env.INTENT_HMAC_KEY===env.IDENTITY_HMAC_KEY)throw deny();
 return [env.CONTRIBUTORS_GENERATION,env.CONTRIBUTORS_JOURNAL_PIN];
}
async function primary(env,sql,args,write=false){
 const s=env.CONTRIBUTORS_DB.withSession("first-primary").prepare(sql).bind(...args);
 const x=await (write?s.run():s.all());
 if(x?.success!==true||x.meta?.served_by_primary!==true)throw deny();
 if(write){if(x.meta.changes!==1)throw deny();}
 else if(!Array.isArray(x.results)||x.results.length!==1)throw deny();
 return x;
}
async function verifyGeneration(env){
 const cfg=config(env);
 const x=await primary(env,SQL.generation,cfg);
 if(x.results[0].id!==1)throw deny();
}
function operation(path,p){
 let role,mode="WRITE";
 if(path==="/api/submit"){
  normalize(p,new Date().toISOString().replace(/\.\d{3}Z$/,"Z"));role="CONTRIBUTOR";
 }else if(path==="/owner/review"){
  if(!shape(p,["id","action","reason"])||!Number.isSafeInteger(p.id)||p.id<1||!["APPROVED","REJECTED","REVOKED"].includes(p.action)||
    typeof p.reason!=="string"||!p.reason.trim()||[...p.reason].length>280||/[\u0000-\u001f\u007f-\u009f\uD800-\uDFFF]/u.test(p.reason))throw deny();
  role="OWNER";if(p.action==="REVOKED")mode="RECOVERY";
 }else throw deny();
 // Exact validated primitive fields; canonical order, no nested or client-derived identity.
 return {role,mode,body:JSON.stringify(Object.keys(p).sort().map(k=>[k,p[k]]))};
}
function args(env,b,o){return [...config(env),o.mode,o.role,b.subject,b.email_tag,o.role,b.subject,b.email_tag];}
function message(env,b,path,o,nonce,exp){
 return enc.encode(JSON.stringify(["remura-intent-v1",...config(env),b.subject,b.email_tag,path,o.role,o.mode,o.body,nonce,exp]));
}
async function key(env){
 config(env);
 return crypto.subtle.importKey("raw",bytes(env.INTENT_HMAC_KEY),{name:"HMAC",hash:"SHA-256"},false,["sign","verify"]);
}
async function issueIntent(env,b,path,p){
 const o=operation(path,p),x=await primary(env,SQL.permission,args(env,b,o));
 if(x.results[0].allowed!==1)throw deny();
 const exp=seconds()+90,nonce=hex(crypto.getRandomValues(new Uint8Array(16)));
 const sig=hex(await crypto.subtle.sign("HMAC",await key(env),message(env,b,path,o,nonce,exp)));
 return {intent:nonce+"."+exp+"."+sig,expires_unix:exp};
}
async function consumeIntent(env,b,path,p,token){
 const o=operation(path,p);
 if(typeof token!=="string"||!/^([a-f0-9]{32})\.([0-9]{10})\.([a-f0-9]{64})$/.test(token))throw deny();
 const [nonce,e,sig]=token.split("."),exp=Number(e),now=seconds();
 if(exp<now||exp>now+90||!await crypto.subtle.verify("HMAC",await key(env),bytes(sig),message(env,b,path,o,nonce,exp)))throw deny();
 const a=args(env,b,o);
 // Single insert with live role, generation, mode, expiry and unique nonce checks.
 // Do not retry if this write is ambiguous. Burn-before-effect deliberately trades availability for safety.
 await primary(env,SQL.burn,[nonce,b.subject,o.mode,o.role,exp,a[0],a[1],exp,...a.slice(2)],true);
 if(seconds()>exp)throw deny();
}
export {SQL,verifyGeneration,issueIntent,consumeIntent};
