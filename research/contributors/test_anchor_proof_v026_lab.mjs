// REMURA Experience v0.26 LAB — tests with ephemeral Ed25519 identities.
import test from 'node:test';
import assert from 'node:assert/strict';
import {generateKeyPairSync,sign} from 'node:crypto';
import {SCHEMA,GENESIS,GateDenied,contentForSignature,anchorDigest,verifyPinnedChain,validateProposedAdvance,readDisposition} from './anchor_proof_v026_lab.mjs';
const G='fixture-v026',T=1795219000000,sha=(c)=>c.repeat(64);
const pair=()=>generateKeyPairSync('ed25519');
const OWNER=pair(),CUSTODIAN=pair(),IMPOSTOR=pair();
const trust={owner:OWNER.publicKey.export({format:'pem',type:'spki'}),custodian:CUSTODIAN.publicKey.export({format:'pem',type:'spki'})};
const genesis={sequence:0,digest:GENESIS};
const clone=x=>structuredClone(x);
function entry(seq=1,previous=GENESIS,disposition='PUBLISHED',intent='intent-1'){
 return {schema:SCHEMA,generation:G,sequence:seq,previous,intent_id:intent,candidate_digest:sha('a'),authority_digest:sha('b'),disposition,observed_at_ms:disposition==='PUBLISHED'?T:T+1001,expires_at_ms:T+1000};
}
function signed(e,owner=OWNER,custodian=CUSTODIAN){const b=Buffer.from(contentForSignature(e));return {entry:e,signatures:{owner:sign(null,b,owner.privateKey).toString('base64'),custodian:sign(null,b,custodian.privateKey).toString('base64')}};}
function chain(status='PUBLISHED') {const a=signed(entry(1,GENESIS,status));return {records:[a],pin:{sequence:1,digest:anchorDigest(a.entry)}};}
function request(records,pin,other={}){return {records,externalPin:pin,trust,generation:G,...other};}
const rejected=fn=>assert.throws(fn,GateDenied);

test('genesis requires matching explicit external pin',()=>{const h=verifyPinnedChain(request([],genesis));assert.equal(h.disposition,'EMPTY');});
test('genesis without pin denied',()=>rejected(()=>verifyPinnedChain(request([],undefined))));
test('valid two-signature anchor matches pinned latest',()=>{const c=chain(),h=verifyPinnedChain(request(c.records,c.pin));assert.equal(h.sequence,1);assert.equal(h.disposition,'PUBLISHED');});
test('only published fresh event admits status, no market data',()=>{const c=chain();const r=readDisposition({...request(c.records,c.pin),clock:()=>T+1});assert.deepEqual(r,{status:'PUBLISHED',revision:1});assert.equal(Object.hasOwn(r,'market'),false);});
test('expired event denied',()=>{const c=chain();assert.equal(readDisposition({...request(c.records,c.pin),clock:()=>T+1001}),null);});
test('before observation denied',()=>{const c=chain();assert.equal(readDisposition({...request(c.records,c.pin),clock:()=>T-1}),null);});
test('ABANDONED event always denied even with clock reversal',()=>{const c=chain('ABANDONED');assert.equal(readDisposition({...request(c.records,c.pin),clock:()=>T}),null);assert.equal(readDisposition({...request(c.records,c.pin),clock:()=>T+2000}),null);});
test('missing pin fail closed even when signatures correct',()=>{const c=chain();rejected(()=>verifyPinnedChain(request(c.records,undefined)));assert.equal(readDisposition({...request(c.records,null),clock:()=>T}),null);});
test('rolled back chain cannot match externally pinned new head',()=>{const c=chain();const more=signed(entry(2,c.pin.digest,'PUBLISHED','intent-2'));const pin2={sequence:2,digest:anchorDigest(more.entry)};rejected(()=>verifyPinnedChain(request(c.records,pin2)));});
test('same-length anchor substitution rejected by pin',()=>{const c=chain();const altered=signed({...c.records[0].entry,intent_id:'different'});rejected(()=>verifyPinnedChain(request([altered],c.pin)));});
test('wrong pinned owner key rejected',()=>{const c=chain();const other={...trust,owner:IMPOSTOR.publicKey.export({format:'pem',type:'spki'})};rejected(()=>verifyPinnedChain(request(c.records,c.pin,{trust:other})));});
test('wrong pinned custodian key rejected',()=>{const c=chain();const other={...trust,custodian:IMPOSTOR.publicKey.export({format:'pem',type:'spki'})};rejected(()=>verifyPinnedChain(request(c.records,c.pin,{trust:other})));});
test('two identical pinned keys rejected',()=>{const c=chain();rejected(()=>verifyPinnedChain(request(c.records,c.pin,{trust:{owner:trust.owner,custodian:trust.owner}})));});
test('untrusted public keys embedded in receipt rejected',()=>{const c=chain();c.records[0].public_keys=trust;rejected(()=>verifyPinnedChain(request(c.records,c.pin)));});
test('wrong generation denied',()=>{const c=chain();rejected(()=>verifyPinnedChain(request(c.records,c.pin,{generation:'legacy'})));});
test('tampered payload with old signature denied',()=>{const c=chain();c.records[0].entry.candidate_digest=sha('f');rejected(()=>verifyPinnedChain(request(c.records,c.pin)));});
test('tampered signature rejected',()=>{const c=chain();c.records[0].signatures.owner=signed(entry(1,GENESIS,'PUBLISHED','other')).signatures.owner;rejected(()=>verifyPinnedChain(request(c.records,c.pin)));});
test('invalid base64 signature rejected',()=>{const c=chain();c.records[0].signatures.owner='AAAA';rejected(()=>verifyPinnedChain(request(c.records,c.pin)));});
test('malformed timestamp rejected',()=>rejected(()=>contentForSignature({...entry(),observed_at_ms:'1'})));
test('late PUBLISHED signature cannot be accepted',()=>rejected(()=>contentForSignature({...entry(),observed_at_ms:T+1001})));
test('premature ABANDONED signature cannot be accepted',()=>rejected(()=>contentForSignature({...entry(1,GENESIS,'ABANDONED'),observed_at_ms:T})));
test('wrong revision or non-contiguous chain denied',()=>{const c=chain(),e=signed(entry(3,c.pin.digest,'PUBLISHED','intent-3'));rejected(()=>verifyPinnedChain(request([...c.records,e],{sequence:2,digest:anchorDigest(e.entry)})));});
test('previous digest mismatch denied',()=>{const c=chain(),e=signed(entry(2,sha('e'),'PUBLISHED','intent-2'));rejected(()=>verifyPinnedChain(request([...c.records,e],{sequence:2,digest:anchorDigest(e.entry)})));});
test('new candidate is proposed only; old external pin still blocks read',()=>{const c=chain(),p=signed(entry(2,c.pin.digest,'ABANDONED','intent-2'));const proposed=validateProposedAdvance({...request(c.records,c.pin),proposed:p});assert.equal(proposed.sequence,2);assert.equal(readDisposition({...request([...c.records,p],c.pin),clock:()=>T}),null);});
test('after explicit external pin update new ABANDONED head blocks read',()=>{const c=chain(),p=signed(entry(2,c.pin.digest,'ABANDONED','intent-2'));const proposed=validateProposedAdvance({...request(c.records,c.pin),proposed:p});const fresh=verifyPinnedChain(request([...c.records,p],proposed));assert.equal(fresh.disposition,'ABANDONED');assert.equal(readDisposition({...request([...c.records,p],proposed),clock:()=>T}),null);});
test('cannot propose new entry with duplicate intent id',()=>{const c=chain(),p=signed(entry(2,c.pin.digest,'PUBLISHED','intent-1'));rejected(()=>validateProposedAdvance({...request(c.records,c.pin),proposed:p}));});
test('cannot propose with incorrect previous hash',()=>{const c=chain(),p=signed(entry(2,sha('f'),'PUBLISHED','intent-2'));rejected(()=>validateProposedAdvance({...request(c.records,c.pin),proposed:p}));});
test('single owner signer cannot masquerade as custodian',()=>{const c=chain();const hacked=signed(c.records[0].entry,OWNER,OWNER);rejected(()=>verifyPinnedChain(request([hacked],c.pin)));});
test('clock invalid prevents delivery',()=>{const c=chain();assert.equal(readDisposition({...request(c.records,c.pin),clock:()=>NaN}),null);});
test('missing trusted store fails closed',()=>{const c=chain();rejected(()=>verifyPinnedChain(request(c.records,c.pin,{trust:undefined})));});
test('empty genesis never delivers numeric content',()=>assert.equal(readDisposition({...request([],genesis),clock:()=>T}),null));
test('external pin cannot be inferred from in-band receipt',()=>{const c=chain();rejected(()=>verifyPinnedChain(request(c.records,c.records[0].external_pin)));});
test('key algorithm type rejected',()=>{const c=chain();const {publicKey}=generateKeyPairSync('rsa',{modulusLength:2048});rejected(()=>verifyPinnedChain(request(c.records,c.pin,{trust:{...trust,owner:publicKey.export({format:'pem',type:'spki'})}})));});
