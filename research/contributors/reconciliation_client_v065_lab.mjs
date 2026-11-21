// REMURA Contributors v0.65 LAB — read-only reconciliation client; never unlocks mutation.
const STATUS=new Set(['NO_ATTEMPT','UNRESOLVED','COMMITTED_UNREVIEWED','COMMITTED_REVIEWED','CLOSED']);
const UUID=/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/;
const bad=()=>{throw Error('REMURA_RECOVERY_NOT_ATTESTED');};
const exact=(v,keys)=>v!==null&&typeof v==='object'&&!Array.isArray(v)&&Object.getPrototypeOf(v)===Object.prototype&&Object.keys(v).length===keys.length&&keys.every(k=>Object.hasOwn(v,k));
export class ReconciliationClientV065 {
 #fetch;#busy=false;
 constructor(fetcher){if(typeof fetcher!=='function')bad();this.#fetch=fetcher;}
 get busy(){return this.#busy;}
 async inspect(){
  if(this.#busy)bad();this.#busy=true;
  try{
   const r=await this.#fetch('/api/amendment/reconcile',{method:'POST',headers:{'Content-Type':'application/json','X-Remura-CSRF':'1'},body:'{}',credentials:'same-origin',mode:'same-origin',redirect:'error',cache:'no-store',referrerPolicy:'no-referrer'});
   if(r?.status!==200||r.redirected===true||!/^application\/json\b/i.test(r.headers?.get?.('Content-Type')??'')||!/\bno-store\b/i.test(r.headers?.get?.('Cache-Control')??''))bad();
   const content=await r.text();if(new TextEncoder().encode(content).length>4096)bad();
   let j;try{j=JSON.parse(content)}catch{bad()};if(!exact(j,['data']))bad();const d=j.data;
   if(!d||typeof d!=='object'||!STATUS.has(d.status)||d.mayResubmit!==false||d.manualApprovalRequired!==true)bad();
   if(d.status==='NO_ATTEMPT'){if(!exact(d,['status','mayResubmit','manualApprovalRequired']))bad();return Object.freeze({status:d.status,mayResubmit:false,manualApprovalRequired:true});}
   if(!exact(d,['status','attempt_id','request_id','mayResubmit','manualApprovalRequired'])||!Number.isSafeInteger(d.attempt_id)||d.attempt_id<1||typeof d.request_id!=='string'||!UUID.test(d.request_id))bad();
   return Object.freeze({status:d.status,attempt_id:d.attempt_id,request_id:d.request_id,mayResubmit:false,manualApprovalRequired:true});
  }finally{this.#busy=false;}
 }
}
// Does not create its own fetcher and has no write or reset/clear method.
