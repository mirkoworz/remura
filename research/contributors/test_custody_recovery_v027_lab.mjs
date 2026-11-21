// REMURA Experience v0.27 LAB — 21/11/2026 CET
// Completely offline, ephemeral Ed25519 keys; never handles real owner keys.
import test from 'node:test';
import assert from 'node:assert/strict';
import {generateKeyPairSync, sign} from 'node:crypto';
import {SCHEMA, GENESIS, GateDenied, contentForSignature, anchorDigest} from './anchor_proof_v026_lab.mjs';
import {RECEIPT_SCHEMA, RECEIPT_MAX_AGE_MS, receiptBytes,
  reviewCustodyRecovery, inspectRecoverySafely} from './custody_recovery_v027_lab.mjs';

const pair = () => generateKeyPairSync('ed25519');
const O = pair(), C = pair(), A = pair(), B = pair(), EVIL = pair();
const pem = p => p.publicKey.export({format:'pem',type:'spki'});
const chainTrust = {owner:pem(O),custodian:pem(C)};
const storageTrust = {alpha:pem(A),beta:pem(B)};
const G='fixture-v027';
const T = Date.parse('2026-11-21T08:00:00Z');
const h = v => v.repeat(64);
const clone = x => structuredClone(x);
const bad = fn => assert.throws(fn,GateDenied);
const record = (sequence,previous,disposition='PUBLISHED', intent='intent-'+sequence) => {
  const e = {schema:SCHEMA,generation:G,sequence,previous,intent_id:intent,
    candidate_digest:h('a'),authority_digest:h('b'),disposition,
    observed_at_ms:disposition==='PUBLISHED'?T+(sequence-1)*1000:T+2000,
    expires_at_ms:disposition==='PUBLISHED'?T+500000:T+1500};
  const bytes=Buffer.from(contentForSignature(e));
  return {entry:e,signatures:{owner:sign(null,bytes,O.privateKey).toString('base64'),
      custodian:sign(null,bytes,C.privateKey).toString('base64')}};
};
function scenario(n=1,status='PUBLISHED') {
  const records=[];let prior=GENESIS;
  for(let i=1;i<=n;i++) {const r=record(i,prior,i===n?status:'PUBLISHED');records.push(r);prior=anchorDigest(r.entry);}
  const nowMs=T+10000;
  const pin={sequence:n,digest:prior};
  const receipt=(custodian,issued_at_ms=nowMs-10) => ({schema:RECEIPT_SCHEMA,generation:G,custodian,
    sequence:n,digest:pin.digest,issued_at_ms});
  const signedReceipt=(custodian,key,issued_at_ms)=>{const r=receipt(custodian,issued_at_ms);return {
    receipt:r,signature:sign(null,receiptBytes(r),key.privateKey).toString('base64')};};
  const attestations={alpha:signedReceipt('alpha',A),beta:signedReceipt('beta',B)};
  const trustedFloor={sequence:1,digest:anchorDigest(records[0].entry)};
  const ctx={records,generation:G,chainTrust:{...chainTrust},storageTrust:{...storageTrust},attestations,trustedFloor,nowMs};
  return {ctx,pin,receipt,signedReceipt};
}

test('correct two witness signatures allow manual REVIEW only',()=>{
  const {ctx}=scenario();const x=reviewCustodyRecovery(ctx);
  assert.equal(x.status,'REVIEWABLE_LAB_ONLY'); assert.equal(x.marketDeliveryPermitted,false);
  assert.equal(x.manualApprovalRequired,true);assert.equal(Object.hasOwn(x,'market'),false);
});
test('a second signed generation with earlier independent floor can be reviewed',()=>{
  const {ctx}=scenario(2);const x=reviewCustodyRecovery(ctx);assert.equal(x.sequence,2);
  assert.equal(x.disposition,'PUBLISHED');
});
test('ABANDONED is never turned into market data or publication',()=>{
  const {ctx}=scenario(2,'ABANDONED');const x=reviewCustodyRecovery(ctx);
  assert.equal(x.disposition,'ABANDONED');assert.equal(x.marketDeliveryPermitted,false);
});
test('missing alpha witness denies',()=>{const {ctx}=scenario();ctx.attestations.alpha=null;bad(()=>reviewCustodyRecovery(ctx));});
test('missing beta witness denies',()=>{const {ctx}=scenario();ctx.attestations.beta=null;bad(()=>reviewCustodyRecovery(ctx));});
test('both missing witnesses deny',()=>{const {ctx}=scenario();ctx.attestations=null;bad(()=>reviewCustodyRecovery(ctx));});
test('unavailable or missing trusted floor denies',()=>{const {ctx}=scenario();ctx.trustedFloor=null;bad(()=>reviewCustodyRecovery(ctx));});
test('floor points to future sequence => deny',()=>{const {ctx}=scenario();ctx.trustedFloor.sequence=2;bad(()=>reviewCustodyRecovery(ctx));});
test('floor digest mismatch => deny',()=>{const {ctx}=scenario();ctx.trustedFloor.digest=h('f');bad(()=>reviewCustodyRecovery(ctx));});
test('conflicting latest witness sequence => deny',()=>{const {ctx}=scenario(2);ctx.attestations.beta.receipt.sequence=1;bad(()=>reviewCustodyRecovery(ctx));});
test('conflicting latest witness digest => deny',()=>{const {ctx}=scenario();ctx.attestations.beta.receipt.digest=h('f');bad(()=>reviewCustodyRecovery(ctx));});
test('signed but conflicting witness heads => deny',()=>{
  const s=scenario(2);s.ctx.attestations.beta=s.signedReceipt('beta',B);
  const stale={...s.ctx.attestations.beta.receipt,sequence:1,digest:s.ctx.trustedFloor.digest};
  s.ctx.attestations.beta={receipt:stale,signature:sign(null,receiptBytes(stale),B.privateKey).toString('base64')};
  bad(()=>reviewCustodyRecovery(s.ctx));
});
test('wrong alpha public key => deny',()=>{const {ctx}=scenario();ctx.storageTrust.alpha=pem(EVIL);bad(()=>reviewCustodyRecovery(ctx));});
test('wrong beta public key => deny',()=>{const {ctx}=scenario();ctx.storageTrust.beta=pem(EVIL);bad(()=>reviewCustodyRecovery(ctx));});
test('same pinned key on two witness roles => deny',()=>{const {ctx}=scenario();ctx.storageTrust.beta=ctx.storageTrust.alpha;bad(()=>reviewCustodyRecovery(ctx));});
test('storage key reused for chain owner => deny',()=>{const {ctx}=scenario();ctx.storageTrust.alpha=ctx.chainTrust.owner;bad(()=>reviewCustodyRecovery(ctx));});
test('wrong chain signing trust => deny',()=>{const {ctx}=scenario();ctx.chainTrust.custodian=pem(EVIL);bad(()=>reviewCustodyRecovery(ctx));});
test('missing pinned trust => deny',()=>{const {ctx}=scenario();ctx.storageTrust=undefined;bad(()=>reviewCustodyRecovery(ctx));});
test('forged signature of witness alpha => deny',()=>{const {ctx}=scenario();ctx.attestations.alpha.signature=ctx.attestations.beta.signature;bad(()=>reviewCustodyRecovery(ctx));});
test('wrong custodian identity even if signed => deny',()=>{
  const s=scenario();s.ctx.attestations.alpha=s.signedReceipt('beta',A);bad(()=>reviewCustodyRecovery(s.ctx));
});
test('recording witness issued in future => deny',()=>{
  const s=scenario();s.ctx.attestations.alpha=s.signedReceipt('alpha',A,s.ctx.nowMs+1);
  bad(()=>reviewCustodyRecovery(s.ctx));
});
test('stale signed witness => deny',()=>{
  const s=scenario();s.ctx.attestations.alpha=s.signedReceipt('alpha',A,s.ctx.nowMs-RECEIPT_MAX_AGE_MS-1);
  bad(()=>reviewCustodyRecovery(s.ctx));
});
test('receipt at exact age limit remains reviewable, not fresh-proof',()=>{
  const s=scenario();s.ctx.nowMs=T+RECEIPT_MAX_AGE_MS+2000;
  s.ctx.attestations.alpha=s.signedReceipt('alpha',A,T+2000);
  s.ctx.attestations.beta=s.signedReceipt('beta',B,s.ctx.nowMs-10);
  assert.equal(reviewCustodyRecovery(s.ctx).status,'REVIEWABLE_LAB_ONLY');
});
test('malformed receipt timestamp => deny',()=>{
  const {ctx}=scenario();ctx.attestations.alpha.receipt.issued_at_ms='now';bad(()=>reviewCustodyRecovery(ctx));
});
test('wrong generation in signed storage claim => deny',()=>{
  const s=scenario();s.ctx.attestations.beta.receipt.generation='legacy';bad(()=>reviewCustodyRecovery(s.ctx));
});
test('invalid base64 => deny',()=>{const {ctx}=scenario();ctx.attestations.alpha.signature='abc';bad(()=>reviewCustodyRecovery(ctx));});
test('extra in-band key or metadata => deny',()=>{const {ctx}=scenario();ctx.attestations.alpha.public_key=pem(A);bad(()=>reviewCustodyRecovery(ctx));});
test('tampered chain record => deny',()=>{const {ctx}=scenario();ctx.records[0].entry.candidate_digest=h('f');bad(()=>reviewCustodyRecovery(ctx));});
test('chain rollback with both latest storage heads, floor at 2 => deny',()=>{
  const s=scenario(2);s.ctx.trustedFloor={sequence:2,digest:s.pin.digest};
  s.ctx.records.pop();bad(()=>reviewCustodyRecovery(s.ctx));
});
test('both storage signatures for old head cannot override newer floor',()=>{
  const old=scenario(1),recent=scenario(2);
  old.ctx.trustedFloor={sequence:2,digest:recent.pin.digest};
  bad(()=>reviewCustodyRecovery(old.ctx));
});
test('two independent-looking old signed receipts plus old floor CAN replay: documented limit',()=>{
  const old=scenario(1);const state=reviewCustodyRecovery(old.ctx);
  // The verifier has no independent knowledge of any newer actual head.
  assert.equal(state.status,'REVIEWABLE_LAB_ONLY');
  assert.equal(state.marketDeliveryPermitted,false);
});
test('when complete chain is longer than both signed receipts => deny',()=>{
  const old=scenario(1),recent=scenario(2);recent.ctx.attestations=old.ctx.attestations;
  bad(()=>reviewCustodyRecovery(recent.ctx));
});
test('two signed generations cannot reuse an intent identifier',()=>{
  const s=scenario(2); const first=s.ctx.records[0];
  const duplicate=record(2,anchorDigest(first.entry),'PUBLISHED','intent-1');
  s.ctx.records[1]=duplicate;
  const digest=anchorDigest(duplicate.entry);
  for (const [role,key] of [['alpha',A],['beta',B]]) {
    const receipt={...s.ctx.attestations[role].receipt,digest};
    s.ctx.attestations[role]={receipt,signature:sign(null,receiptBytes(receipt),key.privateKey).toString('base64')};
  }
  bad(()=>reviewCustodyRecovery(s.ctx));
});
test('signed chain with observation time moving backwards is refused',()=>{
  const s=scenario(2); const first=s.ctx.records[0];
  const previous=record(2,anchorDigest(first.entry));
  const entry={...previous.entry,observed_at_ms:T-1};
  const bytes=Buffer.from(contentForSignature(entry));
  const changed={entry,signatures:{owner:sign(null,bytes,O.privateKey).toString('base64'),
    custodian:sign(null,bytes,C.privateKey).toString('base64')}};
  s.ctx.records[1]=changed;
  for(const [role,key] of [['alpha',A],['beta',B]]) {
    const receipt={...s.ctx.attestations[role].receipt,digest:anchorDigest(entry)};
    s.ctx.attestations[role]={receipt,signature:sign(null,receiptBytes(receipt),key.privateKey).toString('base64')};
  }
  bad(()=>reviewCustodyRecovery(s.ctx));
});
test('signed witness time preceding latest signed record is refused',()=>{
  const s=scenario(2);
  s.ctx.attestations.alpha=s.signedReceipt('alpha',A,T-1);
  bad(()=>reviewCustodyRecovery(s.ctx));
});
test('missing current wall-clock denies',()=>{const {ctx}=scenario();ctx.nowMs=undefined;bad(()=>reviewCustodyRecovery(ctx));});
test('negative wall-clock denies',()=>{const {ctx}=scenario();ctx.nowMs=-1;bad(()=>reviewCustodyRecovery(ctx));});
test('safe API fails closed without revealing market numbers or raw proof',()=>{
  const {ctx}=scenario();ctx.attestations.alpha=null;
  assert.deepEqual(inspectRecoverySafely(ctx),{status:'BLOCKED',manualApprovalRequired:true,marketDeliveryPermitted:false});
});
test('safe API never returns publication approval even on good proofs',()=>{
  const {ctx}=scenario();const out=inspectRecoverySafely(ctx);
  assert.equal(out.marketDeliveryPermitted,false);
  assert.equal(Object.keys(out).includes('pinPersisted'),false);
});
test('invalid custody generation does not automatically reset floor',()=>{
  const {ctx}=scenario();ctx.generation='fixture-v028';bad(()=>reviewCustodyRecovery(ctx));
});
