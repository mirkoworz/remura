#!/usr/bin/env node
// REMURA Experience v0.28 LAB — 21/11/2026 CET
// Read-only offline CLI. Never prints private keys, prices or receipt data.
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {inspectOfflineSourcesV028} from './offline_source_audit_v028_lab.mjs';

const DENIED=Object.freeze({status:'BLOCKED',manualApprovalRequired:true,marketDeliveryPermitted:false});
export async function runAuditCliV028(args,clock=()=>Date.now(),emit=s=>process.stdout.write(s+'\n')){
 let result=DENIED;
 try{
  if(!Array.isArray(args)||args.length!==9)throw Error('usage');
  const [records,alpha,beta,floor,keyring,fingerprint,seqText,digest,generation]=args;
  if(!/^(?:[1-9]|[1-5][0-9]|6[0-4])$/.test(seqText))throw Error('sequence');
  const nowMs=clock();
  result=await inspectOfflineSourcesV028({paths:{records,alpha,beta,floor,keyring},
    expectedKeyringSha256:fingerprint,manualFloor:{sequence:Number(seqText),digest},generation,nowMs});
 }catch{result=DENIED;}
 // The returned status never means authorized publication or independent proof.
 emit(JSON.stringify({status:result.status,manualApprovalRequired:true,marketDeliveryPermitted:false}));
 return result.status==='REVIEWABLE_LAB_ONLY'?0:3;
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const exitCode=await runAuditCliV028(process.argv.slice(2));
 process.exitCode=exitCode;
}
