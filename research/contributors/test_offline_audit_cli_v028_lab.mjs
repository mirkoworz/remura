// REMURA Experience v0.28 LAB — CLI input/exit safety, no external services.
import test from 'node:test';
import assert from 'node:assert/strict';
import {runAuditCliV028} from './offline_audit_cli_v028_lab.mjs';
const call=async (args,clock=()=>1)=>{const sent=[];const exit=await runAuditCliV028(args,clock,s=>sent.push(s));return {exit,sent};};
const blocked=r=>{assert.equal(r.exit,3);assert.equal(r.sent.length,1);assert.deepEqual(JSON.parse(r.sent[0]),{status:'BLOCKED',manualApprovalRequired:true,marketDeliveryPermitted:false});};
test('absent args block without printing usage or market values',async()=>blocked(await call([])));
test('malformed generation number blocks',async()=>blocked(await call(['a','b','c','d','e','f','0','g','h'])));
test('synthetic incomplete inputs block without disclosing paths',async()=>{const args=['private-records','alpha','beta','floor','keyring','a'.repeat(64),'1','b'.repeat(64),'fixture-v028'];const r=await call(args);blocked(r);assert.ok(!r.sent[0].includes('private-records'));});
test('invalid caller clock fails closed',async()=>blocked(await call(['a','b','c','d','e','f','1','g','h'],()=>NaN)));
test('input errors do not emit raw keyrings',async()=>{const r=await call(null);blocked(r);assert.ok(!r.sent[0].includes('-----BEGIN'));});
