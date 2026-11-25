import {test} from 'node:test';
import {mergeHistory} from '../tools/myfxbook-history-merge.mjs';
function runChecks(merge){
 const sha="a".repeat(40), next="b".repeat(40),source="Myfxbook Community Outlook",t=n=>`2026-11-24T0${n}:00:00Z`,row=(n,l=60)=>[t(n),l,100-l],old={schema:"remura-myfxbook-history-v1",source,sourceCommit:sha,symbols:{EURUSD:[row(0),row(1)]}}, series=(rows)=>({EURUSD:{symbol:"EURUSD",source,records:rows.map(([t,lPct,sPct])=>({t,lPct,sPct}))}});
 const assert=(v,m)=>{if(!v)throw Error(m)};const rejects=(fn)=>{let ok=false;try{fn()}catch{ok=true}assert(ok,"Expected failure")};let passed=[];
 const check=(name,fn)=>{fn();passed.push(name)};
 const input=series([row(1),row(2,70)]),saved=JSON.stringify(old);
 check("retain expired + add fresh + deduplicate",()=>{let r=merge(old,input,next);assert(r.stats.added===1&&r.stats.retained===1&&r.stats.merged===3,"counts");assert(r.archive.symbols.EURUSD[0][0]===t(0),"old retained")});
 check("no mutation",()=>{merge(old,input,next);assert(JSON.stringify(old)===saved,"mutated")});
 check("idempotence",()=>{let a=merge(old,input,next);let b=merge(a.archive,input,next);assert(b.stats.added===0&&JSON.stringify(a.archive)===JSON.stringify(b.archive),"not idempotent")});
 check("conflict rejected",()=>rejects(()=>merge(old,series([row(1,50)]),next)));
 check("missing symbols rejected",()=>rejects(()=>merge(old,{},next)));
 check("extra symbols rejected",()=>rejects(()=>merge(old,{...input,USDJPY:input.EURUSD},next)));
 check("duplicate incoming timestamp rejected",()=>rejects(()=>merge(old,series([row(1),row(1)]),next)));
 check("invalid percentage rejected",()=>rejects(()=>merge(old,series([row(2,101)]),next)));
 check("wrong source rejected",()=>rejects(()=>merge(old,{EURUSD:{...input.EURUSD,source:"other"}},next)));
 check("invalid time rejected",()=>rejects(()=>merge(old,series([["2026-02-30T00:00:00Z",50,50]]),next)));
 check("unordered input rejected",()=>rejects(()=>merge(old,series([row(2),row(1)]),next)));
 check("invalid provenance rejected",()=>rejects(()=>merge(old,input,"main")));
 return passed;
}
test('V28.1 merge checks',()=>{ const checks=runChecks(mergeHistory); if(checks.length!==12)throw Error('Unexpected test count'); });
