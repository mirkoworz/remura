// REMURA Experience v0.29 LAB — 21/11/2026 CET
// Two-signature offline handoff verification; NO actual independent custodian or storage.
import {createHash,createPublicKey,verify as edVerify} from 'node:crypto';
import {verifyPinnedChain,anchorDigest} from './anchor_proof_v026_lab.mjs';
export const SCHEMA='REMURA_OFFLINE_HANDOFF_V029_FIXTURE';
export const ACK_SCHEMA='REMURA_OFFLINE_HANDOFF_ACK_V029_FIXTURE';
const SHA=/^[a-f0-9]{64}$/,B64=/^[A-Za-z0-9+/]{86}==$/,ID=/^[A-Za-z0-9_.:-]{1,64}$/;
const fields=['schema','generation','sequence','digest','nonce','source','target','issued_at_ms','expires_at_ms'];
const afields=['schema','handoff_digest','nonce','receiver','received_at_ms'];
const exact=(x,f)=>x&&Object.getPrototypeOf(x)===Object.prototype&&Object.keys(x).length===f.length&&f.every(k=>Object.hasOwn(x,k));
const validTime=x=>Number.isSafeInteger(x)&&x>=0;
const deny=()=>{throw Error('HANDOFF_BLOCKED');};
function bytes(x,f){return Buffer.from(JSON.stringify(Object.fromEntries(f.map(k=>[k,x[k]]))));}
function key(p){try{if(typeof p!=='string'||p.length>2048)deny();const x=createPublicKey(p);if(x.asymmetricKeyType!=='ed25519')deny();return x;}catch{deny();}}
function sig(data,s,pub){if(typeof s!=='string'||!B64.test(s))deny();const b=Buffer.from(s,'base64');if(b.length!==64||b.toString('base64')!==s||!edVerify(null,data,pub,b))deny();}
export function manifestBytes(m){
 if(!exact(m,fields)||m.schema!==SCHEMA||![m.generation,m.nonce,m.source,m.target].every(x=>typeof x==='string'&&ID.test(x))||m.source===m.target||!Number.isSafeInteger(m.sequence)||m.sequence<1||m.sequence>64||typeof m.digest!=='string'||!SHA.test(m.digest)||!validTime(m.issued_at_ms)||!validTime(m.expires_at_ms)||m.issued_at_ms>=m.expires_at_ms||m.expires_at_ms-m.issued_at_ms>3600000)deny();
 return bytes(m,fields);
}
export function ackBytes(a){
 if(!exact(a,afields)||a.schema!==ACK_SCHEMA||typeof a.handoff_digest!=='string'||!SHA.test(a.handoff_digest)||typeof a.nonce!=='string'||!ID.test(a.nonce)||typeof a.receiver!=='string'||!ID.test(a.receiver)||!validTime(a.received_at_ms))deny();
 return bytes(a,afields);
}
export function reviewHandoffV029({records,manifest,ownerSig,ack,receiverSig,chainTrust,ownerPublicKey,receiverPublicKey,manualFloor,generation,nowMs}){
 const owner=key(ownerPublicKey),receiver=key(receiverPublicKey);
 if(owner.export({type:'spki',format:'der'}).equals(receiver.export({type:'spki',format:'der'})))deny();
 const handoff=manifestBytes(manifest),ackRaw=ackBytes(ack);
 if(!ID.test(generation)||manifest.generation!==generation||!validTime(nowMs)||nowMs<manifest.issued_at_ms||nowMs>manifest.expires_at_ms||ack.received_at_ms<manifest.issued_at_ms||ack.received_at_ms>nowMs||ack.received_at_ms>manifest.expires_at_ms||ack.receiver!==manifest.target||ack.nonce!==manifest.nonce)deny();
 sig(handoff,ownerSig,owner);sig(ackRaw,receiverSig,receiver);
 const mh=createHash('sha256').update(handoff).digest('hex');
 if(ack.handoff_digest!==mh)deny();
 if(!exact(manualFloor,['sequence','digest'])||!Number.isSafeInteger(manualFloor.sequence)||manualFloor.sequence<1||manualFloor.sequence>manifest.sequence||typeof manualFloor.digest!=='string'||!SHA.test(manualFloor.digest))deny();
 const v=verifyPinnedChain({records,trust:chainTrust,externalPin:{sequence:manifest.sequence,digest:manifest.digest},generation});
 if(!records[manualFloor.sequence-1]||anchorDigest(records[manualFloor.sequence-1].entry)!==manualFloor.digest)deny();
 // Passing a proof means only that two synthetic cryptographic acknowledgments agree.
 return Object.freeze({status:'REVIEWABLE_LAB_ONLY',manualApprovalRequired:true,marketDeliveryPermitted:false,sequence:v.sequence});
}
export function safeHandoffV029(input){try{return reviewHandoffV029(input)}catch{return Object.freeze({status:'BLOCKED',manualApprovalRequired:true,marketDeliveryPermitted:false})}}
