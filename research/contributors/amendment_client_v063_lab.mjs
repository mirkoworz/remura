// REMURA Contributors v0.63 LAB — 21/11/2026 CET
// Client candidate: injected fetch ONLY; never auto-connect to a live endpoint.
// A mutation with unknown confirmation locks future mutation attempts in this client instance.
const MUTATIONS = new Set(['/api/amendment/submit', '/owner/amendment/review']);
const READS = new Set(['/api/amendment/mine', '/api/amendment/approved', '/owner/amendment/queue']);
const TOKEN = /^[a-f0-9]{32}\.[0-9]{10}\.[a-f0-9]{64}$/;
const UUID = /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/;
const UTC = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/;
const PRICE = /^(?:0|[1-9][0-9]{0,7})(?:\.[0-9]{1,8})?$/;
const ALLOWED_STATE = new Set(['UNREVIEWED','APPROVED','REJECTED','REVOKED']);
const same = (v, names) => v !== null && typeof v === 'object' && !Array.isArray(v) &&
  Object.getPrototypeOf(v) === Object.prototype && Object.keys(v).length === names.length &&
  names.every(k => Object.hasOwn(v,k));
function fail() { throw Error('REMURA_REQUEST_NOT_CONFIRMED'); }
function stamp(v) {
  if(typeof v !== 'string' || !UTC.test(v) || !Number.isFinite(Date.parse(v)) ||
     new Date(v).toISOString().slice(0,19)+'Z' !== v) fail();
  return v;
}
function normalizeInput(path, p) {
  if(path === '/api/amendment/submit') {
    if(!same(p,['source_entry_id','request_id','price','observed_utc','note']) ||
      !Number.isSafeInteger(p.source_entry_id) || p.source_entry_id < 1 ||
      typeof p.request_id !== 'string' || !UUID.test(p.request_id) || typeof p.price !== 'string' ||
      typeof p.note !== 'string' || [...p.note].length>280 ||
      /[\u0000-\u001f\u007f-\u009f\uD800-\uDFFF]/u.test(p.note))fail();
    const price=p.price.replace(',','.');
    if(!PRICE.test(price) || !/[1-9]/.test(price) || price.length>17)fail();
    if(Date.parse(stamp(p.observed_utc))>Date.now())fail();
    return {...p,price};
  }
  if(path === '/owner/amendment/review') {
    if(!same(p,['id','action','reason']) || !Number.isSafeInteger(p.id) || p.id<1 ||
      !['APPROVED','REJECTED','REVOKED'].includes(p.action) || typeof p.reason!=='string' ||
      !p.reason.trim() || [...p.reason].length>280 ||
      /[\u0000-\u001f\u007f-\u009f\uD800-\uDFFF]/u.test(p.reason))fail();
    return {...p};
  }
  fail();
}
function validateResponse(path,data,submitted) {
  if(path==='/api/amendment/submit') {
    if(!same(data,['id','status','duplicate']) || !Number.isSafeInteger(data.id) || data.id<1 ||
        !ALLOWED_STATE.has(data.status)||typeof data.duplicate!=='boolean')fail();
    return Object.freeze({id:data.id,status:data.status,duplicate:data.duplicate});
  }
  if(path==='/owner/amendment/review') {
    if(!same(data,['id','action','at_utc']) || data.id!==submitted.id || data.action!==submitted.action)fail();
    stamp(data.at_utc);
    return Object.freeze({id:data.id,action:data.action,at_utc:data.at_utc});
  }
  fail();
}
export class AmendmentClientV063 {
  #fetch;
  #busy=false;
  #uncertain=false;
  #now;
  constructor(fetcher,{now=()=>Date.now()}={}) {
    if(typeof fetcher!=='function'||typeof now!=='function')fail();
    this.#fetch=fetcher;
    this.#now=now;
  }
  get uncertain(){return this.#uncertain;}
  get busy(){return this.#busy;}
  async #request(path,body,token=undefined){
    if(!MUTATIONS.has(path)&&!READS.has(path)&&path!=='/api/amendment/intent')fail();
    if(!body||Object.getPrototypeOf(body)!==Object.prototype)fail();
    const raw=JSON.stringify(body);
    if(new TextEncoder().encode(raw).length>4096)fail();
    const headers={'Content-Type':'application/json','X-Remura-CSRF':'1'};
    if(token!==undefined) {if(typeof token!=='string'||!TOKEN.test(token))fail();headers['X-Remura-Intent']=token;}
    const response=await this.#fetch(path,{method:'POST',headers,body:raw,credentials:'same-origin',mode:'same-origin',redirect:'error',cache:'no-store',referrerPolicy:'no-referrer'});
    if(!response || response.status!==200 || response.redirected===true ||
      !/^application\/json\b/i.test(response.headers?.get?.('Content-Type')??'') ||
      !/\bno-store\b/i.test(response.headers?.get?.('Cache-Control')??''))fail();
    const text=await response.text();
    if(new TextEncoder().encode(text).length>32768)fail();
    let json;
    try{json=JSON.parse(text);}catch{fail()}
    if(!same(json,['data']))fail();
    return json.data;
  }
  async read(path,body={}){
    if(this.#busy || !READS.has(path))fail();
    if(path==='/api/amendment/approved') {if(!same(body,[]))fail();}
    else if(!same(body,['after'])||!Number.isSafeInteger(body.after)||body.after<0)fail();
    this.#busy=true;
    try {
      const data=await this.#request(path,body);
      if(!Array.isArray(data)||data.length>(path==='/api/amendment/approved'?100:20))fail();
      return data;
    } finally {this.#busy=false}
  }
  async mutate(path,p,{stillCurrent=()=>true}={}){
    if(this.#busy||this.#uncertain||!MUTATIONS.has(path)||typeof stillCurrent!=='function'||stillCurrent()!==true)fail();
    const body=normalizeInput(path,p);
    this.#busy=true;
    try {
      const issued=await this.#request('/api/amendment/intent',{path,body});
      if(!same(issued,['intent','expires_unix']) || typeof issued.intent!=='string'||!TOKEN.test(issued.intent)||
        !Number.isSafeInteger(issued.expires_unix)||issued.expires_unix<Math.floor(this.#now()/1000)||
        issued.expires_unix>Math.floor(this.#now()/1000)+90)fail();
      if(stillCurrent()!==true)fail();
      // After this point, even a network exception or malformed 200 may conceal a committed write.
      this.#uncertain=true;
      const response=await this.#request(path,body,issued.intent);
      const confirmed=validateResponse(path,response,body);
      if(stillCurrent()!==true)fail();
      this.#uncertain=false;
      return confirmed;
    } finally {this.#busy=false}
  }
}
