// REMURA Contributors v0.70 LAB — 21/11/2026 13:10 CET.
// Browser-only strictly READ transport for private staging candidate; never creates a session.
const DENIED='REMURA_V070_READ_ONLY';
const bad=()=>{throw new Error(DENIED)};
const routes=Object.freeze({
 '/api/amendment/reconcile':[],
 '/api/amendment/mine':['after'],
 '/owner/amendment/reconcile-queue':['after']
});
const exact=(o,ks)=>o!==null&&typeof o==='object'&&!Array.isArray(o)&&Object.getPrototypeOf(o)===Object.prototype&&Object.keys(o).length===ks.length&&ks.every(k=>Object.hasOwn(o,k));
export function createReadOnlyTransportV070({fetcher,origin}){
 if(typeof fetcher!=='function'||typeof origin!=='string')bad();
 let parsed;try{parsed=new URL(origin)}catch{bad()}
 if(parsed.protocol!=='https:'||parsed.origin!==origin||parsed.pathname!=='/'||parsed.search||parsed.hash||parsed.username||parsed.password)bad();
 return async function readOnlyFetch(path,options){
  if(typeof path!=='string'||!Object.hasOwn(routes,path)||!exact(options,['method','headers','body','credentials','mode','redirect','cache','referrerPolicy']))bad();
  const allowed=routes[path];
  if(options.method!=='POST'||!exact(options.headers,['Content-Type','X-Remura-CSRF'])||
     options.headers['Content-Type']!=='application/json'||options.headers['X-Remura-CSRF']!=='1'||
     options.credentials!=='same-origin'||options.mode!=='same-origin'||options.redirect!=='error'||
     options.cache!=='no-store'||options.referrerPolicy!=='no-referrer'||typeof options.body!=='string')bad();
  if(new TextEncoder().encode(options.body).byteLength>4096)bad();
  let data;try{data=JSON.parse(options.body)}catch{bad()}
  if(!exact(data,allowed))bad();
  if(allowed.length===1&&(!Number.isSafeInteger(data.after)||data.after<0))bad();
  // No caller-provided auth header, role, identity, request target or mutation is accepted.
  return fetcher(path,options);
 };
}
export const REMURA_V070_READ_ENDPOINTS=Object.freeze(Object.keys(routes));
