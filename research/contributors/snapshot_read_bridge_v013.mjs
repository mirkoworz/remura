// REMURA Experience v0.13 LAB — 20/11/2026 CET
// Synthetic adapter only. NOT a Worker, not real Request parsing, no runtime bindings.
// Dependencies imitate frozen v0.56 Access, generation, profile and rate-limit interfaces.
export function makeReadBridge({accessBinding,verifyGeneration,profile,rateLimit,distributor}){
 if(![accessBinding,verifyGeneration,profile,rateLimit,distributor].every(f=>typeof f==="function"))throw Error("FIXTURE_ONLY");
 const origin="https://contributors.fixture.invalid",path="/api/approved-snapshot",hex=(s,n)=>typeof s==="string"&&s.length===n&&/^[a-f0-9]+$/.test(s);
 const closed=status=>({status,headers:{"Cache-Control":"no-store, max-age=0","Content-Type":"application/json; charset=utf-8","X-Content-Type-Options":"nosniff"},body:'{"error":"UNAVAILABLE"}'});
 return async function handle(req,env,ctx){
  try{
   if(!req||req.method!=="POST"||req.url!==origin+path||req.origin!==origin||req.site!=="same-origin"||req.csrf!=="1"||req.contentType!=="application/json"||req.body!=="{}"||req.encoding!=="identity"||env?.mode!=="SYNTHETIC_ONLY")return closed(403);
   const generation=env.CONTRIBUTORS_GENERATION,pin=env.CONTRIBUTORS_JOURNAL_PIN;
   if(!hex(generation,32)||!hex(pin,64))return closed(403);
   const actor=await accessBinding(ctx,env);
   if(!actor||!hex(actor.subject,64)||!hex(actor.email_tag,64))return closed(403);
   const expected=Object.freeze({subject:actor.subject,email_tag:actor.email_tag});
   const limit=await rateLimit(expected.subject);
   if(limit?.success!==true)return closed(limit?.success===false?429:403);
   const authorize=async()=>{
    if(env.CONTRIBUTORS_GENERATION!==generation||env.CONTRIBUTORS_JOURNAL_PIN!==pin)return null;
    await verifyGeneration(env);
    const a=await accessBinding(ctx,env,expected);
    if(!a||a.subject!==expected.subject||a.email_tag!==expected.email_tag)return null;
    const p=await profile(ctx,env,expected);
    if(!p||p.role!=="CONTRIBUTOR"||p.can_read!==true)return null;
    await verifyGeneration(env);
    if(env.CONTRIBUTORS_GENERATION!==generation||env.CONTRIBUTORS_JOURNAL_PIN!==pin)return null;
    return {role:"CONTRIBUTOR",can_read:true,generation,subject:expected.subject};
   };
   // The factory is a trusted test dependency, never taken from the request.
   const handleFixture=distributor(authorize);
   return await handleFixture({method:"POST",url:origin+path,origin,body:null},{});
  }catch{return closed(403)}
 };
}
