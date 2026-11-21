// REMURA Experience v0.28 LAB — 21/11/2026 CET
// Portable, read-only rehearsal. Path separation is NOT independent custody.
import {constants} from 'node:fs';
import {open, realpath, stat} from 'node:fs/promises';
import {dirname} from 'node:path';
import {createHash} from 'node:crypto';
import {inspectRecoverySafely} from './custody_recovery_v027_lab.mjs';

export const FLOOR_SCHEMA='REMURA_OFFLINE_FLOOR_V028_FIXTURE';
export const KEYRING_SCHEMA='REMURA_OFFLINE_KEYRING_V028_FIXTURE';
const HEX=/^[a-f0-9]{64}$/;
const NAME=/^[A-Za-z0-9_.:-]{1,64}$/;
const MAX={records:262144,alpha:4096,beta:4096,floor:4096,keyring:16384};
const deny=()=>{throw Error('OFFLINE_AUDIT_BLOCKED');};
const exact=(x,keys)=>x!==null&&typeof x==='object'&&!Array.isArray(x)&&Object.getPrototypeOf(x)===Object.prototype&&Object.keys(x).length===keys.length&&keys.every(k=>Object.hasOwn(x,k));
const samePin=(a,b)=>a.sequence===b.sequence&&a.digest===b.digest;
const validPin=p=>exact(p,['sequence','digest'])&&Number.isSafeInteger(p.sequence)&&p.sequence>=1&&p.sequence<=64&&typeof p.digest==='string'&&HEX.test(p.digest);
const blocked=()=>Object.freeze({status:'BLOCKED',manualApprovalRequired:true,marketDeliveryPermitted:false});

async function readStrict(path,maxBytes){
 if(typeof path!=='string'||!path||path.length>4096)deny();
 let handle;
 try{
  handle=await open(path,constants.O_RDONLY|constants.O_NOFOLLOW|constants.O_NONBLOCK);
  const before=await handle.stat();
  if(!before.isFile()||before.size<2||before.size>maxBytes)deny();
  const bytes=await handle.readFile();
  const after=await handle.stat();
  if(bytes.length!==before.size||after.size!==before.size||after.mtimeMs!==before.mtimeMs||after.ctimeMs!==before.ctimeMs||after.ino!==before.ino)deny();
  const str=bytes.toString('utf8');
  if(!Buffer.from(str,'utf8').equals(bytes))deny();
  const data=JSON.parse(str);
  // Exact canonical JSON plus LF rejects duplicate keys, hidden fields and non-finite encodings.
  if(JSON.stringify(data)+'\n'!==str)deny();
  return {data,bytes,real:await realpath(path)};
 }catch{deny();}finally{if(handle)await handle.close();}
}

/** All five artifacts must come from distinct resolved directories.
 * That's merely a local misconfiguration check, NOT physical/admin independence.
 * expectedKeyringSha256 and manualFloor must come from independently checked
 * OWNER knowledge, not from source files or a companion manifest.
 */
export async function inspectOfflineSourcesV028({paths,expectedKeyringSha256,manualFloor,generation,nowMs}={}){
 try{
  if(!exact(paths,['records','alpha','beta','floor','keyring'])||typeof expectedKeyringSha256!=='string'||!HEX.test(expectedKeyringSha256)||!validPin(manualFloor)||typeof generation!=='string'||!NAME.test(generation)||!Number.isSafeInteger(nowMs)||nowMs<0)deny();
  const loaded=await Promise.all(Object.keys(MAX).map(async k=>[k,await readStrict(paths[k],MAX[k])]));
  const files=Object.fromEntries(loaded);
  const roots=await Promise.all(Object.values(files).map(async f=>realpath(dirname(f.real))));
  if(new Set(roots).size!==roots.length)deny();
  if(!exact(files.floor.data,['schema','sequence','digest'])||files.floor.data.schema!==FLOOR_SCHEMA)deny();
  const floor={sequence:files.floor.data.sequence,digest:files.floor.data.digest};
  if(!validPin(floor)||!samePin(floor,manualFloor))deny();
  if(!exact(files.keyring.data,['schema','chainTrust','storageTrust'])||files.keyring.data.schema!==KEYRING_SCHEMA)deny();
  const fingerprint=createHash('sha256').update(files.keyring.bytes).digest('hex');
  if(fingerprint!==expectedKeyringSha256)deny();
  const result=inspectRecoverySafely({records:files.records.data,
    attestations:{alpha:files.alpha.data,beta:files.beta.data},
    trustedFloor:floor,chainTrust:files.keyring.data.chainTrust,
    storageTrust:files.keyring.data.storageTrust,generation,nowMs});
  // NEVER promote witness state or allow market payloads.
  if(result.status!=='REVIEWABLE_LAB_ONLY'||result.marketDeliveryPermitted!==false)deny();
  return Object.freeze({status:'REVIEWABLE_LAB_ONLY',manualApprovalRequired:true,marketDeliveryPermitted:false,
    auditedSequence:result.sequence,headMatchesTwoSigners:true});
 }catch{return blocked();}
}
