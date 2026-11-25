// Archived public retail data only. No live status, no inference for missing records.
export function buildRetailArchive(latest,history,symbol){
 if(latest?.status!=='ok'||latest.source!=='Myfxbook Community Outlook'||history?.schema!=='remura-myfxbook-history-v1'||history.source!==latest.source)throw Error('invalid archive');
 const utc=t=>typeof t==='string'&&t.endsWith('Z')&&Number.isFinite(Date.parse(t));
 const pct=n=>Number.isFinite(n)&&n>=0&&n<=100;
 if(!utc(latest.updatedAt))throw Error('invalid snapshot time');
 const snap=latest.symbols?.[symbol]??null,raw=history.symbols?.[symbol]??[];
 if(snap&&(!utc(snap.t)||Date.parse(snap.t)>Date.parse(latest.updatedAt)||!pct(snap.lPct)||!pct(snap.sPct)))throw Error('invalid latest');
 let last=-Infinity;const rows=raw.map(r=>{
   if(!Array.isArray(r)||r.length!==3||!utc(r[0])||!pct(r[1])||!pct(r[2])||Date.parse(r[0])<=last||Date.parse(r[0])>Date.parse(latest.updatedAt))throw Error('invalid observation');
   last=Date.parse(r[0]);return {t:r[0],long:r[1],short:r[2]};
 });
 return {symbol,snapshotAt:latest.updatedAt,snapshot:snap?{t:snap.t,long:snap.lPct,short:snap.sPct}:null,rows,stale:rows.length?Date.parse(latest.updatedAt)-last>172800000:null};
}
