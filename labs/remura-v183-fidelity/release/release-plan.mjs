// Pure release planning; never deploys, reads secrets, requests data or authorizes a release.
export const DATA_PATHS=Object.freeze(['data/cot-history-public.json','data/myfxbook-history.json','data/myfxbook-latest.json']);
const SENSITIVE=new Set(['_headers','manifest.webmanifest','sw.js','preview-network-guard.js','capital-cloud-config.js','capital-cloud.js','impostazioni.js','resource-health.js','price.js','price-core.js','price-status-core.js','retail.js','sources.js','squalincome-diagnostics.js','squalincome-freshness-core.js','stato-prezzi.js','statistica-squali.js','nav.js']);
const UI=/^(?:[A-Za-z0-9_-]+\.css|[A-Za-z0-9_-]+\.html|assets\/experience\/(?:frame-[0-8]\.webp|smf\.webp|intro\.css)|splash-mascot\.webp|icon\.svg)$/;
export function validateInventory(m){
 if(m?.schema!=='remura-release-inventory-v1'||m.channel!=='public-lab'||!/^\d+\.\d+\.\d+$/.test(m.version)||!Array.isArray(m.files)||!m.files.length||m.files.length>150)throw Error('invalid inventory');
 const out=new Map();
 for(const f of m.files){
  if(!f||typeof f.path!=='string'||! /^[A-Za-z0-9_][A-Za-z0-9_.\/-]*$/.test(f.path)||f.path.split('/').some(s=>!s||s==='.'||s==='..')||out.has(f.path)||! /^[a-f0-9]{40}$/.test(f.gitBlob)||!Number.isSafeInteger(f.bytes)||f.bytes<0||f.bytes>25000000)throw Error('invalid file');
  out.set(f.path,f);
 }
 for(const p of ['index.html','nav.js','sw.js','collaboratori.html',...DATA_PATHS])if(!out.has(p))throw Error('required file missing');
 return out;
}
export function planRelease(current,candidate){
 const a=validateInventory(current),b=validateInventory(candidate);
 const changes=[];
 for(const path of [...new Set([...a.keys(),...b.keys()])].sort()){
  const x=a.get(path),y=b.get(path);
  if(x&&y&&x.gitBlob===y.gitBlob&&x.bytes===y.bytes)continue;
  const kind=!x||!y?'inventory-change':DATA_PATHS.includes(path)?'public-data':SENSITIVE.has(path)?'sensitive':UI.test(path)?'ui':'unclassified';
  changes.push({path,kind});
 }
 const kinds=new Set(changes.map(x=>x.kind));
 const channel=changes.length===0?'no-change':kinds.size===1&&kinds.has('ui')?'ui-only':kinds.size===1&&kinds.has('public-data')?'public-data-only':'manual-review';
 const versionParts=v=>v.split('.').map(BigInt);
 const av=versionParts(current.version),bv=versionParts(candidate.version);
 const i=av.findIndex((x,i)=>x!==bv[i]);const forward=i>=0&&bv[i]>av[i];
 return Object.freeze({channel,changes,publicArchivesChanged:changes.some(x=>DATA_PATHS.includes(x.path)),needsVersionIncrease:changes.length>0&&!forward,requiresManualReview:channel==='manual-review'||changes.length>0&&!forward,activationAuthorized:false,providerRequests:0,privateWrites:0,serverRestart:false});
}
