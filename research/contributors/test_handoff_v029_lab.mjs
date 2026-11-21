// REMURA Experience v0.29 LAB — synthetic dual-signature tests, no network.
import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash,generateKeyPairSync,sign} from 'node:crypto';
import {SCHEMA as ANCHOR,GENESIS,contentForSignature,anchorDigest} from './anchor_proof_v026_lab.mjs';
import {SCHEMA,ACK_SCHEMA,manifestBytes,ackBytes,safeHandoffV029,reviewHandoffV029} from './handoff_v029_lab.mjs';
const make=()=>generateKeyPairSync('ed25519'),A=make(),B=make(),O=make(),C=make(),BAD=make();
const pem=x=>x.publicKey.export({type:'spki',format:'pem'}),hex=x=>x.repeat(64),T=Date.parse('2026-11-21T07:30:00Z'),G='fixture-v029';
function sample(n=1){
 let prev=GENESIS;const records=[];
 for(let i=1;i<=n;i++){const entry={schema:ANCHOR,generation:G,sequence:i,previous:prev,intent_id:'intent-'+i,candidate_digest:hex('a'),authority_digest:hex('b'),disposition:'PUBLISHED',observed_at_ms:T-1000,expires_at_ms:T+3600000};const raw=Buffer.from(contentForSignature(entry));records.push({entry,signatures:{owner:sign(null,raw,O.privateKey).toString('base64'),custodian:sign(null,raw,C.privateKey).toString('base64')}});prev=anchorDigest(entry);}
 const manifest={schema:SCHEMA,generation:G,sequence:n,digest:prev,nonce:'fixture-nonce-'+n,source:'mac-test',target:'iphone-test',issued_at_ms:T,expires_at_ms:T+60000};
 const raw=manifestBytes(manifest),ownerSig=sign(null,raw,A.privateKey).toString('base64');
 const ack={schema:ACK_SCHEMA,handoff_digest:createHash('sha256').update(raw).digest('hex'),nonce:manifest.nonce,receiver:manifest.target,received_at_ms:T+1000};
 const receiverSig=sign(null,ackBytes(ack),B.privateKey).toString('base64');
 return {records,manifest,ownerSig,ack,receiverSig,chainTrust:{owner:pem(O),custodian:pem(C)},ownerPublicKey:pem(A),receiverPublicKey:pem(B),manualFloor:{sequence:1,digest:anchorDigest(records[0].entry)},generation:G,nowMs:T+2000};
}
function denials(f){assert.equal(safeHandoffV029(f).status,'BLOCKED');assert.throws(()=>reviewHandoffV029(f));}
test('two independent signatures support manual review only',()=>{const r=reviewHandoffV029(sample());assert.equal(r.status,'REVIEWABLE_LAB_ONLY');assert.equal(r.marketDeliveryPermitted,false);});
test('second generation with first known floor is reviewable',()=>assert.equal(reviewHandoffV029(sample(2)).sequence,2));
test('no owner signature blocks',()=>{let x=sample();x.ownerSig=null;denials(x)});
test('no destination acknowledgment blocks',()=>{let x=sample();x.ack=null;denials(x)});
test('no destination signature blocks',()=>{let x=sample();x.receiverSig=null;denials(x)});
test('wrong source public key blocks',()=>{let x=sample();x.ownerPublicKey=pem(BAD);denials(x)});
test('wrong receiver public key blocks',()=>{let x=sample();x.receiverPublicKey=pem(BAD);denials(x)});
test('same source and receiver key blocks',()=>{let x=sample();x.receiverPublicKey=x.ownerPublicKey;denials(x)});
test('tampered digest blocks',()=>{let x=sample();x.manifest.digest=hex('f');denials(x)});
test('reused acknowledgment for altered manifest blocks',()=>{let x=sample();x.manifest.nonce='other';denials(x)});
test('wrong target blocks',()=>{let x=sample();x.manifest.target='another';denials(x)});
test('wrong receiver blocks',()=>{let x=sample();x.ack.receiver='different';denials(x)});
test('clock before issue blocks',()=>{let x=sample();x.nowMs=T-1;denials(x)});
test('handoff expiration blocks',()=>{let x=sample();x.nowMs=T+60001;denials(x)});
test('invalid time (regression) blocks',()=>{let x=sample();x.ack.received_at_ms=T-1;denials(x)});
test('overlong validity blocks',()=>{let x=sample();x.manifest.expires_at_ms=T+4000000;denials(x)});
test('unknown generation blocks',()=>{let x=sample();x.generation='v020';denials(x)});
test('wrong out-of-band floor digest blocks',()=>{let x=sample();x.manualFloor.digest=hex('f');denials(x)});
test('floor ahead of receipt blocks',()=>{let x=sample();x.manualFloor.sequence=2;denials(x)});
test('stale chain with newer signed receipt blocks',()=>{let x=sample(2);x.records.pop();denials(x)});
test('missing trusted signer keys blocks',()=>{let x=sample();x.chainTrust=null;denials(x)});
test('invalid signature encoding blocks',()=>{let x=sample();x.ownerSig='abc';denials(x)});
test('extra field in manifest blocks',()=>{let x=sample();x.manifest.price=1.2345;denials(x)});
test('no publication action or pin persistence returned',()=>{let x=sample();let r=safeHandoffV029(x);assert.equal(r.manualApprovalRequired,true);assert.equal('price' in r,false);assert.equal('pinPersisted' in r,false)});
test('two old but valid signed copies with old floor remain reviewable (known LIMIT)',()=>{let r=safeHandoffV029(sample());assert.equal(r.status,'REVIEWABLE_LAB_ONLY');assert.equal(r.marketDeliveryPermitted,false)});
