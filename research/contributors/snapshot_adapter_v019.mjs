// REMURA Experience v0.19 LAB — 20/11/2026 CET
// Offline subprocess adapter; no network or production identity.
import {readFileSync} from 'node:fs';
import {buildDistributor} from './shared_distributor_v010.mjs';
import {projectApproved} from './approved_projection_v07.mjs';
import {forexCotFixture} from './forex_cot_projection_v08.mjs';
const origin='https://contributors.fixture.invalid';
try {
 const raw=readFileSync(0,'utf8');
 if(Buffer.byteLength(raw)>8192)throw Error('size');
 const now=Number(process.argv[2]);
 const handle=buildDistributor({authorize:async()=>({role:'CONTRIBUTOR',can_read:true,generation:'fixture-v019',subject:'local-fixture'}),readSnapshot:async()=>raw,projectPrices:projectApproved,projectForex:forexCotFixture,origin,clock:()=>now});
 const result=await handle({method:'POST',url:origin+'/api/approved-snapshot',origin,body:null},{});
 process.stdout.write(JSON.stringify(result));
} catch {process.exitCode=1;}
