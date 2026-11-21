// REMURA Experience v0.28 LAB — 21/11/2026 CET. All keys synthetic and ephemeral.
import test from 'node:test';
import assert from 'node:assert/strict';
import {generateKeyPairSync, sign, createHash} from 'node:crypto';
import {mkdtemp,mkdir,writeFile,readFile,unlink,symlink,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,dirname} from 'node:path';
import {SCHEMA,GENESIS,contentForSignature,anchorDigest} from './anchor_proof_v026_lab.mjs';
import {RECEIPT_SCHEMA,receiptBytes} from './custody_recovery_v027_lab.mjs';
import {FLOOR_SCHEMA,KEYRING_SCHEMA,inspectOfflineSourcesV028} from './offline_source_audit_v028_lab.mjs';

const E='fixture-v028', T=Date.parse('2026-11-21T08:00:00Z');
const sha=c=>c.repeat(64),pair=()=>generateKeyPairSync('ed25519');
const O=pair(),C=pair(),A=pair(),B=pair(),FAKE=pair();
const pem=k=>k.publicKey.export({format:'pem',type:'spki'});
const keyring={schema:KEYRING_SCHEMA,chainTrust:{owner:pem(O),custodian:pem(C)},storageTrust:{alpha:pem(A),beta:pem(B)}};
const pack=x=>JSON.stringify(x)+'\n';
const fingerprint=x=>createHash('sha256').update(x).digest('hex');
function signedRecord(i,previous,disposition='PUBLISHED'){
 const entry={schema:SCHEMA,generation:E,sequence:i,previous,intent_id:'intent-'+i,candidate_digest:sha('a'),authority_digest:sha('b'),disposition,
  observed_at_ms:disposition==='PUBLISHED'?T+i*1000:T+6000,expires_at_ms:disposition==='PUBLISHED'?T+50000:T+5500};
 const bytes=Buffer.from(contentForSignature(entry));
 return {entry,signatures:{owner:sign(null,bytes,O.privateKey).toString('base64'),custodian:sign(null,bytes,C.privateKey).toString('base64')}};
}
function signedClaim(role,key,seq,digest,issued=T+9000){
 const receipt={schema:RECEIPT_SCHEMA,generation:E,custodian:role,sequence:seq,digest,issued_at_ms:issued};
 return {receipt,signature:sign(null,receiptBytes(receipt),key.privateKey).toString('base64')};
}
async function scenario(t,n=1,status='PUBLISHED'){
 const dir=await mkdtemp(join(tmpdir(),'remura-v028-'));t.after(()=>rm(dir,{recursive:true,force:true}));
 const items=['records','alpha','beta','floor','keyring']; const paths={};
 for(const name of items){const folder=join(dir,name);await mkdir(folder);paths[name]=join(folder,'artifact.json');}
 let previous=GENESIS;const records=[];for(let i=1;i<=n;i++){const r=signedRecord(i,previous,i===n?status:'PUBLISHED');records.push(r);previous=anchorDigest(r.entry);}
 const manualFloor={sequence:1,digest:anchorDigest(records[0].entry)};
 const floor={schema:FLOOR_SCHEMA,...manualFloor};
 const attestations={alpha:signedClaim('alpha',A,n,previous),beta:signedClaim('beta',B,n,previous)};
 const data={records,alpha:attestations.alpha,beta:attestations.beta,floor,keyring};
 for(const name of items)await writeFile(paths[name],pack(data[name]));
 const args={paths,expectedKeyringSha256:fingerprint(pack(keyring)),manualFloor,generation:E,nowMs:T+10000};
 const rewrite=async (name,obj)=>writeFile(paths[name],pack(obj));
 const run=()=>inspectOfflineSourcesV028(args);
 return {args,paths,data,rewrite,run,dir};
}
const review=r=>{assert.equal(r.status,'REVIEWABLE_LAB_ONLY');assert.equal(r.marketDeliveryPermitted,false);assert.equal(r.manualApprovalRequired,true);};
const block=r=>assert.deepEqual(r,{status:'BLOCKED',manualApprovalRequired:true,marketDeliveryPermitted:false});

test('good separate paths are REVIEWABLE LAB only',async t=>review(await (await scenario(t)).run()));
test('two generations verify with first external floor',async t=>{const x=await scenario(t,2);const r=await x.run();review(r);assert.equal(r.auditedSequence,2);});
test('ABANDONED never gains publication or prices',async t=>{const x=await scenario(t,2,'ABANDONED');const r=await x.run();review(r);assert.equal(Object.hasOwn(r,'market'),false);});
test('missing manual floor blocks',async t=>{const x=await scenario(t);x.args.manualFloor=null;block(await x.run());});
test('stale manually entered digest blocks',async t=>{const x=await scenario(t);x.args.manualFloor={...x.args.manualFloor,digest:sha('f')};block(await x.run());});
test('older floor file and known newer manual floor block',async t=>{const x=await scenario(t,2);x.args.manualFloor={sequence:2,digest:anchorDigest(x.data.records[1].entry)};block(await x.run());});
test('floor file alteration blocks with manual floor unchanged',async t=>{const x=await scenario(t);await x.rewrite('floor',{...x.data.floor,digest:sha('f')});block(await x.run());});
test('missing keyring fingerprint blocks',async t=>{const x=await scenario(t);x.args.expectedKeyringSha256=undefined;block(await x.run());});
test('wrong keyring fingerprint blocks',async t=>{const x=await scenario(t);x.args.expectedKeyringSha256=sha('f');block(await x.run());});
test('keyring mutation with original fingerprint blocks',async t=>{const x=await scenario(t);await x.rewrite('keyring',{...x.data.keyring,storageTrust:{...x.data.keyring.storageTrust,alpha:pem(FAKE)}});block(await x.run());});
test('even a recomputed untrusted fingerprint cannot forge valid signatures',async t=>{const x=await scenario(t);const keyring2={...x.data.keyring,storageTrust:{...x.data.keyring.storageTrust,alpha:pem(FAKE)}};await x.rewrite('keyring',keyring2);x.args.expectedKeyringSha256=fingerprint(pack(keyring2));block(await x.run());});
test('missing alpha blocks',async t=>{const x=await scenario(t);await unlink(x.paths.alpha);block(await x.run());});
test('missing beta blocks',async t=>{const x=await scenario(t);await unlink(x.paths.beta);block(await x.run());});
test('damaged alpha signature blocks',async t=>{const x=await scenario(t);await x.rewrite('alpha',{...x.data.alpha,signature:x.data.beta.signature});block(await x.run());});
test('mismatched signed beta head blocks',async t=>{const x=await scenario(t,2);const floor=x.data.floor;await x.rewrite('beta',signedClaim('beta',B,1,floor.digest));block(await x.run());});
test('both old signed receipts against newer chain block',async t=>{const x=await scenario(t,2);const floor=x.data.floor;await x.rewrite('alpha',signedClaim('alpha',A,1,floor.digest));await x.rewrite('beta',signedClaim('beta',B,1,floor.digest));block(await x.run());});
test('old signed snapshot and old manually supplied floor are replayable: documented LIMIT',async t=>{const x=await scenario(t);review(await x.run());});
test('duplicate JSON field rejected by canonical parse',async t=>{const x=await scenario(t);const str=pack(x.data.floor).replace('"sequence":1,','"sequence":1,"sequence":1,');await writeFile(x.paths.floor,str);block(await x.run());});
test('JSON whitespace or extra line rejected',async t=>{const x=await scenario(t);await writeFile(x.paths.floor,JSON.stringify(x.data.floor,null,2)+'\n');block(await x.run());});
test('malformed JSON rejected',async t=>{const x=await scenario(t);await writeFile(x.paths.alpha,'{invalid');block(await x.run());});
test('invalid UTF-8 rejected',async t=>{const x=await scenario(t);await writeFile(x.paths.beta,Buffer.from([0xff,0xfe]));block(await x.run());});
test('extra field in floor rejected',async t=>{const x=await scenario(t);await x.rewrite('floor',{...x.data.floor,bonus:true});block(await x.run());});
test('unexpected keyring schema rejected',async t=>{const x=await scenario(t);const kr={...x.data.keyring,schema:'BAD'};await x.rewrite('keyring',kr);x.args.expectedKeyringSha256=fingerprint(pack(kr));block(await x.run());});
test('symlink to keyring rejected',async t=>{const x=await scenario(t);const original=join(x.dir,'real-keys.json');await writeFile(original,pack(x.data.keyring));await unlink(x.paths.keyring);await symlink(original,x.paths.keyring);block(await x.run());});
test('same actual directory for two files rejected',async t=>{const x=await scenario(t);x.args.paths.beta=x.paths.alpha;block(await x.run());});
test('symlinked directory alias rejected on resolved directories',async t=>{const x=await scenario(t);const alias=join(x.dir,'alias-alpha');await symlink(dirname(x.paths.alpha),alias);x.args.paths.beta=join(alias,'artifact.json');block(await x.run());});
test('oversized alpha artifact blocked without allocation',async t=>{const x=await scenario(t);await writeFile(x.paths.alpha,'x'.repeat(5000));block(await x.run());});
test('missing full records file blocks',async t=>{const x=await scenario(t);await unlink(x.paths.records);block(await x.run());});
test('records array tampering blocks even when other artifacts valid',async t=>{const x=await scenario(t);const rec=structuredClone(x.data.records);rec[0].entry.intent_id='tampered';await x.rewrite('records',rec);block(await x.run());});
test('invalid wall clock blocks',async t=>{const x=await scenario(t);x.args.nowMs=NaN;block(await x.run());});
test('wrong generation blocks without fallback',async t=>{const x=await scenario(t);x.args.generation='legacy';block(await x.run());});
test('audit never mutates source artifacts',async t=>{const x=await scenario(t);const before=await Promise.all(Object.values(x.paths).map(p=>readFile(p)));review(await x.run());const after=await Promise.all(Object.values(x.paths).map(p=>readFile(p)));assert.ok(after.every((b,i)=>b.equals(before[i])));});
