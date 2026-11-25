// REMURA V28.6 — local import of the two authorized public CFTC downloads; zero network.
import {readFileSync,statSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {cotHistoryCore} from './cot-history-core.mjs';
const core=cotHistoryCore();
if(process.argv.length!==4)throw Error('Usage: node import-cot-history.mjs TFF.json DISAGG.json');
const args=process.argv.slice(2);
const proof=[],rows=[];
for(const [i,dataset] of ['tff','disagg'].entries()){
 const path=args[i],size=statSync(path).size;
 if(size<2||size>2000000)throw Error('Unexpected input size');
 const bytes=readFileSync(path);
 if(bytes.length!==size)throw Error('Input changed during read');
 const payload=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
 rows.push(...core.parse(dataset,payload));
 proof.push({dataset,expectedSourceUrl:core.query(dataset),rawSha256:createHash('sha256').update(bytes).digest('hex'),bytes:size,rawBase64:bytes.toString('base64')});
}
const coverage=core.describe(rows);
if(!coverage.complete){console.error(JSON.stringify({state:'INCOMPLETE_NO_ARCHIVE',coverage}));process.exitCode=2;}
else console.log(JSON.stringify({schema:'remura-cftc-history-v1',source:'user_supplied_public_cftc_downloads',captureClock:'download_time_not_independently_attested',importedAtUtc:new Date().toISOString(),start:core.start,end:core.end,coverage,normalizedSha256:createHash('sha256').update(JSON.stringify(rows)).digest('hex'),rows,proof}));
