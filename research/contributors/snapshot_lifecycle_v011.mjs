// REMURA Experience v0.11 LAB — 20/11/2026 17:13 CET
// In-memory fixture lifecycle only. Not durable rollback protection or real authorization.
export function makePublisher({approve,priceProjection,forexProjection,clock}){
 if(![approve,priceProjection,forexProjection,clock].every(f=>typeof f==="function"))throw Error("FIXTURE_ONLY");
 let current=null;
 const keys=(o,k)=>o!==null&&typeof o==="object"&&Object.getPrototypeOf(o)===Object.prototype&&Object.keys(o).length===k.length&&k.every(x=>Object.hasOwn(o,x));
 const stamp=s=>typeof s==="string"&&/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$/.test(s)&&Number.isFinite(Date.parse(s))&&new Date(Date.parse(s)).toISOString().replace(".000Z","Z")===s;
 const pairs={"099741":"EURUSD","096742":"GBPUSD","097741":"USDJPY","232741":"AUDUSD","090741":"USDCAD","092741":"USDCHF","112741":"NZDUSD"};
 const utf8=s=>{let n=0;for(const c of s){const p=c.codePointAt(0);n+=p<=127?1:p<=2047?2:p<=65535?3:4}return n};
 async function publish(raw,expectedRevision,ctx){
  try{
   const old=current?.revision??0;
   if(!Number.isSafeInteger(expectedRevision)||expectedRevision!==old||old===Number.MAX_SAFE_INTEGER)return "CONFLICT";
   if(typeof raw!=="string"||raw.length>8192||utf8(raw)>8192)return "REJECTED";
   const x=JSON.parse(raw),now=clock();
   if(!Number.isSafeInteger(now)||!keys(x,["schema","as_of","prices","forex_rows"])||x.schema!=="REMURA_PUBLISH_FIXTURE_V1"||!stamp(x.as_of)||Date.parse(x.as_of)>now||now-Date.parse(x.as_of)>15*60000||!Array.isArray(x.forex_rows)||x.forex_rows.length>7||current&&x.as_of<current.as_of)return "REJECTED";
   priceProjection({schema:"REMURA_APPROVED_FIXTURE_V1",as_of:x.as_of,prices:x.prices,cot:[]},now);
   const seen=new Set();
   for(const row of x.forex_rows){if(!row||!Object.hasOwn(pairs,row.code)||seen.has(row.code))return "REJECTED";seen.add(row.code);forexProjection(pairs[row.code],[row],x.as_of)}
   const body=JSON.stringify({schema:"REMURA_SHARED_FIXTURE_V1",revision:old+1,as_of:x.as_of,prices:x.prices,forex_rows:x.forex_rows});
   if(utf8(body)>8192)return "REJECTED";
   if(await approve(ctx,body,old)!==true)return "DENIED";
   if((current?.revision??0)!==old)return "CONFLICT";
   const end=clock();
   if(!Number.isSafeInteger(end)||end<now||end-Date.parse(x.as_of)>15*60000)return "REJECTED";
   current=Object.freeze({revision:old+1,as_of:x.as_of,body});
   return "PUBLISHED";
  }catch{return "REJECTED"}
 }
 return Object.freeze({publish,readSnapshot:()=>current?.body??null});
}
export function makeConsumer({request,validate,clock}){
 if(![request,validate,clock].every(f=>typeof f==="function"))throw Error("FIXTURE_ONLY");
 let epoch=0,view=null,revision=0,asOf="",stable=null;
 const utf8=s=>{let n=0;for(const c of s){const p=c.codePointAt(0);n+=p<=127?1:p<=2047?2:p<=65535?3:4}return n};
 function close(){epoch++;view=null;revision=0;asOf="";stable=null}
 async function refresh(){
  const id=++epoch;view=null;
  try{
   const r=await request();
   if(id!==epoch)return "CANCELLED";
   if(r?.status!==200||r.headers?.["Cache-Control"]!=="no-store, max-age=0"||typeof r.body!=="string"||r.body.length>16384||utf8(r.body)>16384)return "UNAVAILABLE";
   const candidate=validate(JSON.parse(r.body),clock());
   if(!candidate||candidate.revision<revision||candidate.as_of<asOf)return "UNAVAILABLE";
   const fingerprint=JSON.stringify({...candidate,prices:candidate.prices.map(({freshness,...p})=>p)});
   if(candidate.revision===revision&&stable!==fingerprint)return "UNAVAILABLE";
   revision=candidate.revision;asOf=candidate.as_of;stable=fingerprint;view=JSON.stringify(candidate);return "READY";
  }catch{return id===epoch?"UNAVAILABLE":"CANCELLED"}
 }
 function read(){if(view===null)return null;try{return validate(JSON.parse(view),clock())}catch{view=null;return null}}
 return Object.freeze({refresh,close,read});
}
