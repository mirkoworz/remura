// REMURA Contributors v0.25 LAB — 16/11/2026 07:19 CET
// Same-origin browser candidate. No polling, persistence, automatic retry or role authority.
const PATHS=new Set(["/api/profile","/api/catalog","/api/receipts","/owner/queue","/owner/history","/api/intent","/api/submit","/owner/review"]);
const MUTATIONS=new Set(["/api/submit","/owner/review"]);
const TOKEN=/^[a-f0-9]{32}\.[0-9]{10}\.[a-f0-9]{64}$/;
const enc=new TextEncoder();
class CandidateClient{
 #fetch;#busy=false;#uncertain=false;
 constructor(fetcher=globalThis.fetch?.bind(globalThis)){if(typeof fetcher!=="function")throw Error("client_unavailable");this.#fetch=fetcher;}
 get uncertain(){return this.#uncertain;}
 async #request(path,body,token){
  if(!PATHS.has(path)||!body||Object.getPrototypeOf(body)!==Object.prototype)throw Error("request_denied");
  const raw=JSON.stringify(body);if(enc.encode(raw).length>4096)throw Error("request_denied");
  const headers={"Content-Type":"application/json","X-Remura-CSRF":"1"};
  if(token!==undefined){if(!TOKEN.test(token))throw Error("request_denied");headers["X-Remura-Intent"]=token;}
  const r=await this.#fetch(path,{method:"POST",headers,body:raw,credentials:"same-origin",cache:"no-store",redirect:"error",mode:"same-origin",referrerPolicy:"no-referrer"});
  if(!r||r.status!==200||!/^application\/json\b/i.test(r.headers.get("Content-Type")??""))throw Error("request_not_confirmed");
  const j=await r.json();
  if(!j||Object.getPrototypeOf(j)!==Object.prototype||!Object.hasOwn(j,"data"))throw Error("request_not_confirmed");
  return j.data;
 }
 async read(path,body={}){
  if(MUTATIONS.has(path)||path==="/api/intent"||this.#busy)throw Error("request_denied");
  this.#busy=true;try{return await this.#request(path,body);}finally{this.#busy=false;}
 }
 async mutate(path,body){
  if(!MUTATIONS.has(path)||this.#uncertain||this.#busy)throw Error("mutation_locked");
  this.#busy=true;
  try{
   const p=JSON.parse(JSON.stringify(body));
   const i=await this.#request("/api/intent",{path,body:p});
   if(!i||!TOKEN.test(i.intent??"")||!Number.isSafeInteger(i.expires_unix)||i.expires_unix<Math.floor(Date.now()/1000)||i.expires_unix>Math.floor(Date.now()/1000)+90)throw Error("intent_denied");
   this.#uncertain=true;
   const result=await this.#request(path,p,i.intent);
   if(path==="/api/submit"?(!Number.isSafeInteger(result?.id)||result.id<1||result.status!=="UNREVIEWED"||typeof result.duplicate!=="boolean"):
     (!Number.isSafeInteger(result?.id)||result.id!==p.id||result.action!==p.action||typeof result.at_utc!=="string"))throw Error("mutation_not_confirmed");
   this.#uncertain=false;return result;
  }finally{this.#busy=false;}
 }
}
export {CandidateClient};
