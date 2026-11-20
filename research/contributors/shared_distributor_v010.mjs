// REMURA Experience v0.10 LAB — 20/11/2026 17:09 CET
// Inert fixture-only service. No Worker entrypoint, actual Access adapter, storage or network.
// Injected adapters are trusted synthetic dependencies, not a production security boundary.
export function buildDistributor({authorize,readSnapshot,projectPrices,projectForex,origin,clock}){
 const PATH="/api/approved-snapshot";
 const utf8Bytes=s=>{let n=0;for(const c of s){const cp=c.codePointAt(0);n+=cp<=0x7f?1:cp<=0x7ff?2:cp<=0xffff?3:4;}return n;};
 if(origin!=="https://contributors.fixture.invalid"||![authorize,readSnapshot,projectPrices,projectForex,clock].every(f=>typeof f==="function"))throw Error("FIXTURE_ONLY");
 const keys=(o,ks)=>o!==null&&typeof o==="object"&&Object.getPrototypeOf(o)===Object.prototype&&Object.keys(o).length===ks.length&&ks.every(k=>Object.hasOwn(o,k));
 const stamp=s=>typeof s==="string"&&/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$/.test(s)&&Number.isFinite(Date.parse(s))&&new Date(Date.parse(s)).toISOString().replace(".000Z","Z")===s;
 const token=s=>typeof s==="string"&&/^[A-Za-z0-9_-]{1,64}$/.test(s);
 const allowed=p=>keys(p,["role","can_read","generation","subject"])&&p.role==="CONTRIBUTOR"&&p.can_read===true&&token(p.generation)&&token(p.subject);
 const headers=Object.freeze({"Cache-Control":"no-store, max-age=0","Content-Type":"application/json; charset=utf-8","X-Content-Type-Options":"nosniff","Cross-Origin-Resource-Policy":"same-origin","Referrer-Policy":"no-referrer"});
 const reply=(status,body)=>({status,headers,body:JSON.stringify(body)});
 const deny=()=>reply(403,{error:"UNAVAILABLE"});
 const unavailable=()=>reply(503,{error:"UNAVAILABLE"});
 const codes={EUR:"099741",GBP:"096742",JPY:"097741",AUD:"232741",CAD:"090741",CHF:"092741",NZD:"112741"};
 const pairs=["EURUSD","GBPUSD","AUDUSD","NZDUSD","USDJPY","USDCAD","USDCHF","EURGBP","EURJPY","EURCHF","EURCAD","EURAUD","EURNZD","GBPJPY","GBPCHF","GBPCAD","GBPAUD","GBPNZD","AUDJPY","AUDCHF","AUDCAD","AUDNZD","NZDJPY","NZDCAD","NZDCHF","CADJPY","CADCHF","CHFJPY"];
 return async function handle(req,ctx){
  if(!keys(req,["method","url","origin","body"])||req.method!=="POST"||req.url!==origin+PATH||req.origin!==origin||req.body!==null)return deny();
  try{
   const raw=await authorize(ctx);
   if(!allowed(raw))return deny();
   const p={...raw};
   const now=clock();if(!Number.isSafeInteger(now)||now<0)return unavailable();
   const rawSnapshot=await readSnapshot();
   if(typeof rawSnapshot!=="string"||rawSnapshot.length>8192||utf8Bytes(rawSnapshot)>8192)return unavailable();
   const s=JSON.parse(rawSnapshot);
   if(!keys(s,["schema","revision","as_of","prices","forex_rows"])||s.schema!=="REMURA_SHARED_FIXTURE_V1"||!Number.isSafeInteger(s.revision)||s.revision<1||!stamp(s.as_of)||Date.parse(s.as_of)>now||now-Date.parse(s.as_of)>15*60000||!Array.isArray(s.forex_rows)||s.forex_rows.length>7)return unavailable();
   const seen=new Set();
   for(const row of s.forex_rows){
    if(!row||!Object.values(codes).includes(row.code)||seen.has(row.code))return unavailable();
    seen.add(row.code);
    const currency=Object.keys(codes).find(k=>codes[k]===row.code);
    const checkPair=({JPY:"USDJPY",CAD:"USDCAD",CHF:"USDCHF"})[currency]||currency+"USD";
    projectForex(checkPair,[row],s.as_of);
   }
   const priceInput={schema:"REMURA_APPROVED_FIXTURE_V1",as_of:s.as_of,prices:s.prices,cot:[]};
   projectPrices(priceInput,now);
   const cot=pairs.map(pair=>{
    const selected=[pair.slice(0,3),pair.slice(3)].filter(c=>c!=="USD").map(c=>codes[c]);
    return projectForex(pair,s.forex_rows.filter(r=>selected.includes(r.code)),s.as_of);
   });
   const final=await authorize(ctx);
   if(!allowed(final)||final.subject!==p.subject||final.generation!==p.generation||final.role!==p.role)return deny();
   const delivery=clock();
   if(!Number.isSafeInteger(delivery)||delivery<now||delivery-Date.parse(s.as_of)>15*60000)return unavailable();
   const pview=projectPrices(priceInput,delivery);
   const body={schema:"REMURA_SHARED_VIEW_FIXTURE_V1",revision:s.revision,as_of:s.as_of,synthetic:true,scientific_admission:false,prices:pview.prices,cot,sentiment:{myfxbook:"UNAVAILABLE",capital:"UNAVAILABLE"},delta:"UNAVAILABLE"};
   const response=reply(200,body);
   return utf8Bytes(response.body)<=16384?response:unavailable();
  }catch{return unavailable();}
 };
}
