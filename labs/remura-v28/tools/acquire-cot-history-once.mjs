import {cotHistoryCore} from './cot-history-core.mjs';
import {createHash} from 'node:crypto';
const core=cotHistoryCore();
const consent='ALLOW_2_PUBLIC_CFTC_HISTORY_GETS_NO_PRIVATE_DATA';
if(process.argv.length!==3||process.argv[2]!==consent)throw Error('Separate explicit consent required');
const MAX_BYTES=2000000;
const rows=[],proof=[];
for(const dataset of ['tff','disagg']){
 const startedAtUtc=new Date().toISOString();
 const response=await fetch(core.query(dataset),{method:'GET',redirect:'error',signal:AbortSignal.timeout(20000),headers:{Accept:'application/json'}});
 if(!response.ok||!response.body)throw Error('Official public CFTC response unavailable');
 const reader=response.body.getReader(),chunks=[];let n=0;
 while(true){const {value,done}=await reader.read();if(done)break;n+=value.byteLength;if(n>MAX_BYTES){await reader.cancel();throw Error('Response too large');}chunks.push(value);}
 const bytes=Buffer.concat(chunks);const receivedAtUtc=new Date().toISOString();
 const incoming=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
 rows.push(...core.parse(dataset,incoming));proof.push({dataset,startedAtUtc,receivedAtUtc,bytes:n,rawSha256:createHash('sha256').update(bytes).digest('hex'),rawBase64:bytes.toString('base64')});
}
const coverage=core.describe(rows);
const digest=createHash('sha256').update(JSON.stringify(rows)).digest('hex');
if(!coverage.complete){console.error(JSON.stringify({state:'INCOMPLETE_NO_ARCHIVE',coverage}));process.exitCode=2;}else{console.log(JSON.stringify({schema:'remura-cftc-history-v1',source:'official_public_cftc_socrata',captureClock:'actual_read_not_historical_first_seen',start:core.start,end:core.end,coverage,normalizedSha256:digest,rows,proof}));}
