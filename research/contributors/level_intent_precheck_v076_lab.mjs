// REMURA Contributors v0.76 LAB — 21/11/2026 15:57 CET.
// Read-only HMAC prevalidation BEFORE reserving durable original-level slot.
// It MUST NOT replace the original one-use burn inside candidateRequest.
const TOKEN=/^([a-f0-9]{32})\.([0-9]{10})\.([a-f0-9]{64})$/;
const HEX=/^[a-f0-9]{64}$/;
const bad=()=>{throw Error('REMURA_V076_BAD_INTENT')};
const bytes=h=>Uint8Array.from(h.match(/../g),c=>parseInt(c,16));
export async function verifyLevelIntentBeforeClaimV076(env,actor,raw,token){
 if(typeof token!=='string'||!TOKEN.test(token)||!actor||!HEX.test(actor.subject)||!HEX.test(actor.email_tag)||
    !/^[a-f0-9]{32}$/.test(env?.CONTRIBUTORS_GENERATION??'')||
    !HEX.test(env?.CONTRIBUTORS_JOURNAL_PIN??'')||!HEX.test(env?.INTENT_HMAC_KEY??'')||
    /^0+$/.test(env.INTENT_HMAC_KEY)||env.INTENT_HMAC_KEY===env.IDENTITY_HMAC_KEY)bad();
 const [nonce,expText,mac]=token.split('.'),exp=Number(expText),now=Math.floor(Date.now()/1000);
 if(!Number.isSafeInteger(exp)||exp<now||exp>now+90||!raw||Object.getPrototypeOf(raw)!==Object.prototype)bad();
 if(typeof crypto?.subtle?.importKey!=='function')bad();
 const payload=JSON.stringify(Object.keys(raw).sort().map(k=>[k,raw[k]]));
 const msg=new TextEncoder().encode(JSON.stringify(['remura-intent-v1',env.CONTRIBUTORS_GENERATION,env.CONTRIBUTORS_JOURNAL_PIN,
  actor.subject,actor.email_tag,'/api/submit','CONTRIBUTOR','WRITE',payload,nonce,exp]));
 const key=await crypto.subtle.importKey('raw',bytes(env.INTENT_HMAC_KEY),{name:'HMAC',hash:'SHA-256'},false,['verify']);
 if(await crypto.subtle.verify('HMAC',key,bytes(mac),msg)!==true)bad();
 return true;
}
