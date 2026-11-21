// REMURA TV v0.8.186 LAB: 14 NEW offline detached witness cases only.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {generateKeyPairSync,createHash,sign} from 'node:crypto';
import {verifyDetachedWitnessV0186 as review,
 detachedWitnessMessageV0186 as message,V0186_DETACHED_WITNESS_CONTRACT as contract
} from './detached_witness_v0186_lab.mjs';
import * as module from './detached_witness_v0186_lab.mjs';
const SCHEMA='remura.tradingview.detached_witness.v0186.lab';
const kp=generateKeyPairSync('ed25519');
const pem=kp.publicKey.export({type:'spki',format:'pem'});
const hash=createHash('sha256').update(kp.publicKey.export({type:'spki',format:'der'})).digest('hex');
const original={
 schema:'remura.tradingview.anchor_request.v0186.lab',status:'REQUEST_HASH_READY_UNSUBMITTED',
 mode:'OFFLINE_UNANCHORED',request_digest_sha256:'a'.repeat(64),
 fold:'HOLDOUT_1',entries:3,capture_chain_self_consistent:true,
 request_submitted_to_tsa:false,independent_timestamp_token_verified:false,
 trusted_anchor_established:false
};
const signed={
 schema:SCHEMA,request_digest_sha256:original.request_digest_sha256,
 fold:'HOLDOUT_1',witnessed_at:'2026-11-23T00:12:00Z',issuer:'SYNTHETIC_WITNESS'
};
function copy(x){return JSON.parse(JSON.stringify(x));}
function signFields(fields=signed,privateKey=kp.privateKey){
 return {...fields,signature_b64:sign(null,message({
  request_digest_sha256:fields.request_digest_sha256,fold:fields.fold,
  witnessed_at:fields.witnessed_at,issuer:fields.issuer
 }),privateKey).toString('base64')};
}
function check({req=original,receipt=signFields(),key=pem,pin=hash}={}){
 return review({request_result:req,receipt,public_key_pem:key,pinned_spki_sha256:pin});
}
test('01 matching detached Ed25519 proof accepted only as a signature, never clock attestation',()=>{
 const r=check();assert.equal(r.status,'DETACHED_SIGNATURE_VALID_TIME_UNATTESTED');
 assert.equal(r.signature_verified_with_supplied_key,true);
 for(const x of ['trusted_timestamp_authority_verified','timestamp_truth_verified',
 'receipt_first_seen_authenticated','capture_ledger_independently_verified',
 'holdout_eligible','edge_established','supplied_key_independently_trusted']){
  assert.equal(r[x],false,x);
 }
});
test('02 mismatched source digest rejected',()=>{
 const receipt=signFields({...signed,request_digest_sha256:'b'.repeat(64)});
 assert.equal(check({receipt}).status,'INVALID_OR_UNVERIFIED');
});
test('03 mismatched fold rejected even when message signature is mathematically valid',()=>{
 const receipt=signFields({...signed,fold:'HOLDOUT_2'});
 assert.equal(check({receipt}).status,'INVALID_OR_UNVERIFIED');
});
test('04 post-signature timestamp manipulation rejected',()=>{
 const receipt=signFields();receipt.witnessed_at='2026-11-23T00:12:01Z';
 assert.equal(check({receipt}).signature_verified_with_supplied_key,false);
});
test('05 post-signature witness identity manipulation rejected',()=>{
 const receipt=signFields();receipt.issuer='FAKE_ANCHOR';
 assert.equal(check({receipt}).status,'INVALID_OR_UNVERIFIED');
});
test('06 different Ed25519 signer rejected by pinned expected key',()=>{
 const other=generateKeyPairSync('ed25519');
 const receipt=signFields(signed,other.privateKey);
 assert.equal(check({receipt}).signature_verified_with_supplied_key,false);
});
test('07 incorrect public-key fingerprint never verifies signature',()=>{
 const r=check({pin:'0'.repeat(64)});
 assert.equal(r.status,'INVALID_OR_UNVERIFIED');assert.equal(r.key_fingerprint_matched,false);
});
test('08 malformed or noncanonical base64 signature rejected',()=>{
 const receipt=signFields();receipt.signature_b64=receipt.signature_b64.slice(0,-1); // remove required Base64 padding, same bytes but NON-canonical
 const r=check({receipt});assert.equal(r.signature_verified_with_supplied_key,false);
});
test('09 missing receipt stays unknown, never interpreted as no market activity',()=>{
 const r=check({receipt:null});
 assert.equal(r.status,'INVALID_OR_UNVERIFIED');assert.equal(r.source_or_market_coverage_attested,false);
});
test('10 invalid purported local capture chain never inherits valid signer authority',()=>{
 const req={...original,capture_chain_self_consistent:false};
 assert.equal(check({req}).signature_verified_with_supplied_key,false);
});
test('11 alleged already submitted external timestamp proof not accepted through offline schema',()=>{
 const req={...original,independent_timestamp_token_verified:true};
 assert.equal(check({req}).status,'INVALID_OR_UNVERIFIED');
});
test('12 unexpected private source fields fail closed and are never echoed',()=>{
 const receipt={...signFields(),actor_email:'private@example.test'};
 const r=check({receipt});assert.equal(r.status,'INVALID_OR_UNVERIFIED');
 assert.equal(JSON.stringify(r).includes('private@example.test'),false);
});
test('13 fake or invalid UTC witness timestamp rejected before signature',()=>{
 const receipt={...signed,witnessed_at:'2026-02-30T00:12:00Z'};
 assert.throws(()=>message({request_digest_sha256:receipt.request_digest_sha256,
  fold:receipt.fold,witnessed_at:receipt.witnessed_at,issuer:receipt.issuer}),/witness_payload_denied/);
});
test('14 no deployable default export, no external calls or live privilege',()=>{
 assert.equal(Object.hasOwn(module,'default'),false);
 assert.equal(contract.liveAllowed,false);assert.equal(contract.rfc3161Verified,false);
 assert.equal(check().network_calls,0);assert.equal(check().decision,'NO_GO_LIVE');
});
