// REMURA V30.19 RELEASE CANDIDATE — no external action at module import.
// Existing credentials and bridge gate preserved; a new separate authorization gate is required.
export function releaseMode(env){
 return env?.REMURA_V3019_MODE==="STAGING_CANDIDATE_ONLY"&&env?.REMURA_V3019_LAB_MODE==null&&env?.REMURA_V3019_TRANSPORT==null;
}
export function createGroupedTelegramTransport(env,fetchImpl=globalThis.fetch){
 const token=env?.TELEGRAM_BOT_TOKEN,chat=env?.TELEGRAM_CHAT_ID;
 if(!releaseMode(env)||env.REMURA_V3019_REAL_TELEGRAM!=="EXPLICITLY_AUTHORIZED"||
 env.TELEGRAM_BRIDGE_V3012!=="EXPLICIT_STAGING_ONLY"||
 typeof token!=="string"||!/^[0-9]{5,20}:[A-Za-z0-9_-]{20,100}$/.test(token)||
 typeof chat!=="string"||!/^-[1-9][0-9]{0,15}$/.test(chat)||
 !Number.isSafeInteger(Number(chat))||typeof fetchImpl!=="function")return null;
 return async text=>{
  if(typeof text!=="string"||!text.startsWith("🦈 REMURA INTELLIGENCE\n")||text.length>3500||
   !/Rif\. P[1-9][0-9]* · (Approvazione automatica REMURA|Approvato dall’OWNER)$/.test(text))return {ok:false};
  const controller=new AbortController();
  const timeout=setTimeout(()=>controller.abort(),8000);
  try{
   const res=await fetchImpl("https://api.telegram.org/bot"+token+"/sendMessage",{
    method:"POST",redirect:"error",signal:controller.signal,headers:{"Content-Type":"application/json"},
    body:JSON.stringify({chat_id:chat,text,link_preview_options:{is_disabled:true}})
   });
   if(!res.ok)return {ok:false};
   const reply=await res.json();
   if(reply?.ok!==true||String(reply.result?.chat?.id)!==chat||
    !Number.isSafeInteger(reply.result?.message_id)||reply.result.message_id<1)return {ok:false};
   return {ok:true,messageId:reply.result.message_id};
  }catch{return {ok:false};}finally{clearTimeout(timeout);}
 };
}
