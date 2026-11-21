// REMURA Experience v0.26 LAB — 21/11/2026 CET
// Offline verification only; pinned public keys and external monotonic pin are inputs.
// Does not store anchors, perform CAS, authenticate users or establish independent custody.
import {createHash, createPublicKey, verify as verifySignature} from 'node:crypto';

export const SCHEMA='REMURA_ANCHOR_PROOF_FIXTURE_V026';
export const GENESIS='0'.repeat(64);
const MAX=64;
const FIELDS=['schema','generation','sequence','previous','intent_id','candidate_digest','authority_digest','disposition','observed_at_ms','expires_at_ms'];
const SHA=/^[0-9a-f]{64}$/;
const B64=/^[A-Za-z0-9+/]{86}==$/;
export class GateDenied extends Error {constructor(){super('ANCHOR_GATE_DENIED');this.name='GateDenied';}}
const deny=()=>{throw new GateDenied();};
const exact=(x,keys)=>x!==null&&typeof x==='object'&&!Array.isArray(x)&&Object.getPrototypeOf(x)===Object.prototype&&Object.keys(x).length===keys.length&&keys.every(k=>Object.hasOwn(x,k));
const text=(x,max)=>typeof x==='string'&&x.length>0&&x.length<=max&&/^[a-zA-Z0-9_.:-]+$/.test(x);
const integer=x=>Number.isSafeInteger(x)&&x>=0;
function canonical(x){return JSON.stringify(x);}
export function contentForSignature(entry){
 if(!exact(entry,FIELDS)||entry.schema!==SCHEMA||!text(entry.generation,64)||!integer(entry.sequence)||entry.sequence<1||entry.sequence>MAX||!SHA.test(entry.previous)||!text(entry.intent_id,64)||!SHA.test(entry.candidate_digest)||!SHA.test(entry.authority_digest)||!['PUBLISHED','ABANDONED'].includes(entry.disposition)||!integer(entry.observed_at_ms)||!integer(entry.expires_at_ms)||!(entry.disposition==='PUBLISHED'?entry.observed_at_ms<=entry.expires_at_ms:entry.observed_at_ms>entry.expires_at_ms))deny();
 return canonical(Object.fromEntries(FIELDS.map(f=>[f,entry[f]])));
}
export function anchorDigest(entry){return createHash('sha256').update(contentForSignature(entry)).digest('hex');}
function pinnedKeys(keys){
 if(!exact(keys,['owner','custodian']))deny();
 try{
  const owner=createPublicKey(keys.owner),custodian=createPublicKey(keys.custodian);
  if(owner.asymmetricKeyType!=='ed25519'||custodian.asymmetricKeyType!=='ed25519')deny();
  const a=owner.export({format:'der',type:'spki'}),b=custodian.export({format:'der',type:'spki'});
  if(a.equals(b))deny();
  return {owner,custodian};
 }catch{deny();}
}
function signatures(record,keys){
 if(!exact(record,['entry','signatures'])||!exact(record.signatures,['owner','custodian']))deny();
 const raw=Buffer.from(contentForSignature(record.entry),'utf8');
 for(const role of ['owner','custodian']){
  const b64=record.signatures[role];
  if(typeof b64!=='string'||!B64.test(b64))deny();
  const signature=Buffer.from(b64,'base64');
  if(signature.length!==64||signature.toString('base64')!==b64||!verifySignature(null,raw,keys[role],signature))deny();
 }
}
function pinValid(pin){return exact(pin,['sequence','digest'])&&integer(pin.sequence)&&pin.sequence<=MAX&&typeof pin.digest==='string'&&SHA.test(pin.digest);}
export function verifyPinnedChain({records,trust,externalPin,generation}){
 const keys=pinnedKeys(trust);
 if(!Array.isArray(records)||records.length>MAX||!pinValid(externalPin)||!text(generation,64))deny();
 let head=GENESIS;
 for(let i=0;i<records.length;i++){
  const record=records[i];
  signatures(record,keys);
  if(record.entry.generation!==generation||record.entry.sequence!==i+1||record.entry.previous!==head)deny();
  head=anchorDigest(record.entry);
 }
 // Without an EXTERNAL, FRESH pin, even a correctly signed chain is not approved.
 if(externalPin.sequence!==records.length||externalPin.digest!==head)deny();
 return Object.freeze({sequence:records.length,digest:head,disposition:records.length?records.at(-1).entry.disposition:'EMPTY',expires_at_ms:records.length?records.at(-1).entry.expires_at_ms:null,observed_at_ms:records.length?records.at(-1).entry.observed_at_ms:null});
}
export function validateProposedAdvance({records,trust,externalPin,generation,proposed}){
 const current=verifyPinnedChain({records,trust,externalPin,generation});
 if(current.sequence>=MAX)deny();
 const keys=pinnedKeys(trust);
 signatures(proposed,keys);
 const entry=proposed.entry;
 if(entry.sequence!==current.sequence+1||entry.previous!==current.digest||entry.generation!==generation||records.some(r=>r.entry.intent_id===entry.intent_id))deny();
 // Return a proposed pin, NOT a committed pin; caller must obtain separate durable approval.
 return Object.freeze({sequence:entry.sequence,digest:anchorDigest(entry)});
}
export function readDisposition({records,trust,externalPin,generation,clock}){
 try{
  const checked=verifyPinnedChain({records,trust,externalPin,generation});
  const t=clock();
  if(!integer(t)||!checked.sequence||checked.disposition!=='PUBLISHED'||t<checked.observed_at_ms||t>checked.expires_at_ms)return null;
  return Object.freeze({status:'PUBLISHED',revision:checked.sequence});
 }catch{return null;}
}
