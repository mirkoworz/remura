// REMURA TradingView v0.8.186 LAB — 21/11/2026 Europe/Rome.
// OFFLINE detached Ed25519 signature check for an optional future evidence witness.
// NOT an RFC3161 verifier. Does NOT prove timestamp accuracy, source provenance,
// independent witness operation, or that a first-seen receipt existed in time.
// No network, keys persisted, output of raw source events, Worker, or live capture.
import {createHash,createPublicKey,verify as verifySignature} from 'node:crypto';
const DOMAIN='REMURA_TV_DETACHED_WITNESS_V0186_V1';
const REQ='remura.tradingview.anchor_request.v0186.lab';
const SCHEMA='remura.tradingview.detached_witness.v0186.lab';
const HEX=/^[0-9a-f]{64}$/;
const UTC=/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$/;
const WITNESS=/^[A-Z][A-Z0-9_-]{1,31}$/;
function exact(x,fields){
 if(!x||typeof x!=='object'||Array.isArray(x)||Object.getPrototypeOf(x)!==Object.prototype)return false;
 const d=Object.getOwnPropertyDescriptors(x);
 return Object.keys(d).length===fields.length&&fields.every(k=>Object.hasOwn(d,k)&&Object.hasOwn(d[k],'value'));
}
function utc(s){
 if(typeof s!=='string'||!UTC.test(s))return false;
 const n=Date.parse(s);
 return Number.isFinite(n)&&new Date(n).toISOString().slice(0,19)+'Z'===s;
}
function result(){
 return {
  schema:SCHEMA,version:'0.8.186',mode:'OFFLINE_DETACHED_SIGNATURE_LAB',
  status:'INVALID_OR_UNVERIFIED',
  signature_verified_with_supplied_key:false,
  key_fingerprint_matched:false,
  supplied_key_independently_trusted:false,
  trusted_timestamp_authority_verified:false,
  issuer_operated_independently:false,
  timestamp_truth_verified:false,
  receipt_first_seen_authenticated:false,
  capture_ledger_independently_verified:false,
  source_or_market_coverage_attested:false,
  protocol_modified:false,network_calls:0,edge_established:false,
  holdout_eligible:false,decision:'NO_GO_LIVE'
 };
}
export function detachedWitnessMessageV0186(fields){
 if(!exact(fields,['request_digest_sha256','fold','witnessed_at','issuer'])||
    typeof fields.request_digest_sha256!=='string'||!HEX.test(fields.request_digest_sha256)||
    !['HOLDOUT_1','HOLDOUT_2'].includes(fields.fold)||!utc(fields.witnessed_at)||
    typeof fields.issuer!=='string'||!WITNESS.test(fields.issuer))throw Error('witness_payload_denied');
 return Buffer.from(JSON.stringify([
  DOMAIN,fields.fold,fields.request_digest_sha256,fields.witnessed_at,fields.issuer
 ]),'utf8');
}
export function verifyDetachedWitnessV0186({request_result,receipt,public_key_pem,pinned_spki_sha256}={}){
 const out=result();
 try{
  if(!request_result||typeof request_result!=='object'||Array.isArray(request_result)||
     Object.getPrototypeOf(request_result)!==Object.prototype||
     request_result.schema!==REQ||request_result.status!=='REQUEST_HASH_READY_UNSUBMITTED'||
     request_result.mode!=='OFFLINE_UNANCHORED'||
     request_result.capture_chain_self_consistent!==true||
     request_result.request_submitted_to_tsa!==false||
     request_result.independent_timestamp_token_verified!==false||
     request_result.trusted_anchor_established!==false||
     !['HOLDOUT_1','HOLDOUT_2'].includes(request_result.fold)||
     !Number.isSafeInteger(request_result.entries)||request_result.entries<1||
     request_result.entries>60||
     typeof request_result.request_digest_sha256!=='string'||
     !HEX.test(request_result.request_digest_sha256))return out;
  if(!exact(receipt,['schema','request_digest_sha256','fold','witnessed_at','issuer','signature_b64'])||
     receipt.schema!==SCHEMA||receipt.fold!==request_result.fold||
     receipt.request_digest_sha256!==request_result.request_digest_sha256||
     typeof receipt.signature_b64!=='string'||!/[A-Za-z0-9+/=]{80,100}/.test(receipt.signature_b64)||
     typeof public_key_pem!=='string'||public_key_pem.length>1200||
     typeof pinned_spki_sha256!=='string'||!HEX.test(pinned_spki_sha256))return out;
  const message=detachedWitnessMessageV0186({
   request_digest_sha256:receipt.request_digest_sha256,fold:receipt.fold,
   witnessed_at:receipt.witnessed_at,issuer:receipt.issuer
  });
  const key=createPublicKey(public_key_pem);
  if(key.asymmetricKeyType!=='ed25519')return out;
  const spki=key.export({type:'spki',format:'der'});
  const hash=createHash('sha256').update(spki).digest('hex');
  if(hash!==pinned_spki_sha256)return out;
  out.key_fingerprint_matched=true;
  const signature=Buffer.from(receipt.signature_b64,'base64');
  if(signature.length!==64||signature.toString('base64')!==receipt.signature_b64)return out;
  if(!verifySignature(null,message,key,signature))return out;
  out.status='DETACHED_SIGNATURE_VALID_TIME_UNATTESTED';
  out.signature_verified_with_supplied_key=true;
 }catch{
  // Fail closed; never echo a private source, signer key or malformed receipt.
 }
 return out;
}
export const V0186_DETACHED_WITNESS_CONTRACT=Object.freeze({
 type:'OFFLINE_SIGNATURE_PRIMITIVE_ONLY',version:'0.8.186',
 scheme:'ED25519_SPKI_SHA256_KEY_PIN',signatureFormat:'CANONICAL_BASE64',
 receiptSource:'EXTERNAL_BUT_NOT_INDEPENDENTLY_VERIFIED',
 rfc3161Verified:false,liveAllowed:false
});
