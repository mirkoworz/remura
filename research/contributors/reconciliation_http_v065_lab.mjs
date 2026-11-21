// REMURA Contributors v0.65 LAB — 21/11/2026 CET
// Coordinated reserved-before-write HTTP path. OFFLINE_FIXTURE_ONLY; no Worker fetch binding.
export const RESERVATION_SQL_V065 = 'INSERT INTO lab_amend_attempts_v064 (subject,request_id,source_entry_id,price,observed_utc,note,reserved_utc) SELECT ?,?,?,?,?,?,? WHERE EXISTS(SELECT 1 FROM lab_identities i CROSS JOIN lab_state s WHERE i.subject=? AND i.email_tag=? AND i.revoked=0 AND s.id=1 AND s.write_enabled=1)';
const MUTATION='/api/amendment/submit';
const LOOKUP='/api/amendment/reconcile';
const QUEUE='/owner/amendment/reconcile-queue';
const ROUTES=new Set([MUTATION,LOOKUP,QUEUE]);
const UUID=/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/;
const UTC=/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/;
const PRICE=/^(?:0|[1-9][0-9]{0,7})(?:\.[0-9]{1,8})?$/;
const CAP=4096;
const headers={'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store, max-age=0','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','X-Frame-Options':'DENY','Content-Security-Policy':"default-src 'none'; frame-ancestors 'none'"};
const respond=(status,json)=>new Response(JSON.stringify(json),{status,headers});
const deny=()=>respond(403,{error:'denied'});
const uncertain=()=>respond(409,{error:'not_confirmed',retry:false});
const exact=(o,fields)=>o!==null&&typeof o==='object'&&!Array.isArray(o)&&Object.getPrototypeOf(o)===Object.prototype&&Object.keys(o).length===fields.length&&fields.every(f=>Object.hasOwn(o,f));
function canonStamp(s){if(typeof s!=='string'||!UTC.test(s)||!Number.isFinite(Date.parse(s))||new Date(s).toISOString().slice(0,19)+'Z'!==s)throw Error('blocked');return s;}
function normalize(p,now){
 if(!exact(p,['source_entry_id','request_id','price','observed_utc','note'])||!Number.isSafeInteger(p.source_entry_id)||p.source_entry_id<1||typeof p.request_id!=='string'||!UUID.test(p.request_id)||typeof p.price!=='string'||typeof p.note!=='string'||[...p.note].length>280||/[\u0000-\u001f\u007f-\u009f\uD800-\uDFFF]/u.test(p.note))throw Error('blocked');
 let price=p.price.replace(',','.');if(!PRICE.test(price)||!/[1-9]/.test(price)||price.length>17)throw Error('blocked');
 if(price.includes('.'))price=price.replace(/0+$/,'').replace(/\.$/,'');
 const observed_utc=canonStamp(p.observed_utc);if(observed_utc>now)throw Error('blocked');
 return Object.freeze({...p,price,observed_utc});
}
function matchRequest(req,env){
 try{
  if(env?.AMENDMENT_V065_ENABLED!=='OFFLINE_FIXTURE_ONLY'||env?.AMENDMENT_V064_ENABLED!=='OFFLINE_FIXTURE_ONLY'||env?.AMENDMENT_V062_ENABLED!=='OFFLINE_FIXTURE_ONLY'||env?.AMENDMENT_V061_ENABLED!=='OFFLINE_FIXTURE_ONLY')return false;
  if(typeof env.STAGING_ORIGIN!=='string')return false;
  const base=new URL(env.STAGING_ORIGIN),url=new URL(req.url);
  if(base.protocol!=='https:'||base.origin!==env.STAGING_ORIGIN||base.username||base.password||url.origin!==base.origin||req.url!==base.origin+url.pathname||req.method!=='POST'||!ROUTES.has(url.pathname))return false;
  const h=req.headers;
  return h.get('Origin')===base.origin&&h.get('Sec-Fetch-Site')==='same-origin'&&h.get('X-Remura-CSRF')==='1'&&/^application\/json(?:;\s*charset=utf-8)?$/i.test(h.get('Content-Type')??'')&&(!h.has('Content-Encoding')||h.get('Content-Encoding')==='identity');
 }catch{return false;}
}
async function parse(req){
 let reader,done=false;
 try{
  const h=req.headers.get('Content-Length');if(h!==null&&(!/^[0-9]{1,4}$/.test(h)||Number(h)<2||Number(h)>CAP))throw Error('invalid');
  if(!req.body)throw Error('invalid');
  reader=req.body.getReader();const buffer=new Uint8Array(CAP);let length=0;
  for(;;){const r=await reader.read();if(r.done){done=true;break;}if(!(r.value instanceof Uint8Array)||length+r.value.length>CAP)throw Error('invalid');buffer.set(r.value,length);length+=r.value.length;}
  if(h!==null&&Number(h)!==length)throw Error('invalid');
  const o=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(buffer.subarray(0,length)));
  if(!o||Object.getPrototypeOf(o)!==Object.prototype)throw Error('invalid');return o;
 }finally{if(reader){if(!done)try{await reader.cancel()}catch{}reader.releaseLock();}}
}
export function createReconciliationHttpV065({fallback,burn,access,submit,mine,ownerQueue,now=()=>new Date().toISOString().slice(0,19)+'Z'}){
 if([fallback,burn,access,submit,mine,ownerQueue,now].some(x=>typeof x!=='function'))throw Error('missing_trusted_dependencies');
 return async(req,env,ctx)=>{
  let path;try{path=new URL(req.url).pathname;}catch{return deny();}
  if(env?.AMENDMENT_V065_ENABLED!=='OFFLINE_FIXTURE_ONLY'||env?.AMENDMENT_V064_ENABLED!=='OFFLINE_FIXTURE_ONLY')return deny();
  if(!ROUTES.has(path))return fallback(req,env,ctx); // v0.62 retains guarded owner review + intent and reads.
  if(!matchRequest(req,env))return deny();
  let body;try{body=await parse(req);}catch{return respond(400,{error:'invalid_body'});}
  if(path===LOOKUP||path===QUEUE){
   if(path===LOOKUP?!exact(body,[]):!exact(body,['after'])||!Number.isSafeInteger(body.after)||body.after<0)return respond(400,{error:'invalid_body'});
   try{return respond(200,{data:path===LOOKUP?await mine(ctx,env):await ownerQueue(ctx,env,body.after)});}catch{return deny();}
  }
  // A rejected preflight does not create a reservation or burn a token.
  let normalized;try{normalized=normalize(body,canonStamp(now()));}catch{return respond(400,{error:'invalid_body'});}
  try{
   // Burn one-use intent FIRST; subsequent attempts never auto-retry even if write outcome is unclear.
   const permitted=await burn(ctx,env,MUTATION,body,req.headers.get('X-Remura-Intent'));
   if(!permitted?.actor?.subject||!permitted.actor.email_tag)throw Error('identity');
   const actor=await access(ctx,env,permitted.actor); // fresh trusted identity after intent consumption
   if(actor.subject!==permitted.actor.subject||actor.email_tag!==permitted.actor.email_tag)throw Error('identity_changed');
   const db=env.CONTRIBUTORS_DB;
   const stmt=db.withSession('first-primary').prepare(RESERVATION_SQL_V065).bind(actor.subject,normalized.request_id,normalized.source_entry_id,normalized.price,normalized.observed_utc,normalized.note,canonStamp(now()),actor.subject,actor.email_tag);
   const inserted=await stmt.run();
   if(inserted?.success!==true||inserted.meta?.served_by_primary!==true||inserted.meta?.changes!==1)throw Error('reserve_unknown');
   const fresh=await access(ctx,env,actor);
   if(fresh.subject!==actor.subject||fresh.email_tag!==actor.email_tag)throw Error('changed');
   const receipt=await submit(ctx,env,body,actor); // existing v0.61 adapter rechecks D1 primary and role
   if(!receipt||!Number.isSafeInteger(receipt.id)||receipt.id<1||receipt.status!=='UNREVIEWED')throw Error('unconfirmed');
   return respond(200,{data:receipt});
  }catch{return uncertain();}
 };
}
// Intentionally no exported deployed fetch() or mutable globals.
