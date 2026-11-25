// REMURA V28.1 LAB — pure offline merge; no network, no credentials, no writes.
export function mergeHistory(previous,incoming,sourceCommit){
  const schema="remura-myfxbook-history-v1",source="Myfxbook Community Outlook";
  const validCommit=x=>typeof x==="string"&&/^[a-f0-9]{40}$/.test(x);
  const obj=x=>x!==null&&typeof x==="object"&&!Array.isArray(x);
  const fail=m=>{throw new Error(m)};
  if(!obj(previous)||previous.schema!==schema||previous.source!==source||!validCommit(previous.sourceCommit)||!validCommit(sourceCommit)||!obj(previous.symbols)||!obj(incoming))fail("Invalid archive or provenance");
  const names=Object.keys(previous.symbols).sort();
  if(!names.length||JSON.stringify(names)!==JSON.stringify(Object.keys(incoming).sort())||names.some(s=>!/^[A-Z0-9]{3,8}$/.test(s)))fail("Unexpected symbol coverage");
  const lineage=previous.sourceCommits??[previous.sourceCommit];
  if(!Array.isArray(lineage)||!lineage.every(validCommit)||!lineage.includes(previous.sourceCommit))fail("Invalid source lineage");
  function read(rows){
    if(!Array.isArray(rows)||!rows.length)fail("Empty series");
    const out=new Map();let last=-Infinity;
    for(const r of rows){
      if(!Array.isArray(r)||r.length!==3)fail("Invalid row");
      const [t,l,s]=r;const ms=Date.parse(t);
      if(typeof t!=="string"||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(t)||!Number.isFinite(ms)||new Date(ms).toISOString()!==t.replace("Z",".000Z")||ms<=last||![l,s].every(v=>typeof v==="number"&&Number.isFinite(v)&&v>=0&&v<=100))fail("Invalid or unordered observation");
      last=ms;out.set(t,[t,l,s]);
    }return out;
  }
  const symbols={},stats={old:0,incoming:0,added:0,retained:0,merged:0},perSymbol={};
  for(const name of names){
    const series=incoming[name];
    if(!obj(series)||series.symbol!==name||series.source!==source||!Array.isArray(series.records))fail("Invalid incoming source: "+name);
    const a=read(previous.symbols[name]),b=read(series.records.map(r=>[r?.t,r?.lPct,r?.sPct]));
    const rows=new Map(a);let added=0,retained=0;
    for(const [t,r] of b){if(rows.has(t)){const old=rows.get(t);if(old[1]!==r[1]||old[2]!==r[2])fail("Conflicting observation: "+name+" "+t);}else{rows.set(t,r);added++;}}
    for(const t of a.keys())if(!b.has(t))retained++;
    symbols[name]=[...rows.values()].sort((x,y)=>x[0].localeCompare(y[0]));
    const counts={old:a.size,incoming:b.size,added,retained,merged:rows.size};perSymbol[name]=counts;
    for(const k of Object.keys(stats))stats[k]+=counts[k];
  }
  return {archive:{schema,source,sourceCommit,sourceCommits:[...new Set([...lineage,sourceCommit])],symbols},stats,perSymbol};
}
