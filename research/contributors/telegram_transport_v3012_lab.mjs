// REMURA V30.12 LAB. Outbound-only Telegram API; no polling or inbound webhook.
import {createTelegramOutbox,dispatchOne} from "./telegram_dispatch_v3012_lab.mjs";
export function createTelegramTransport(env, fetchImpl=globalThis.fetch){
 const token=env?.TELEGRAM_BOT_TOKEN, chat=env?.TELEGRAM_CHAT_ID;
 if(env?.TELEGRAM_BRIDGE_V3012!=="EXPLICIT_STAGING_ONLY" ||
    typeof token!=="string" || !/^[0-9]{5,20}:[A-Za-z0-9_-]{20,100}$/.test(token) ||
    typeof chat!=="string" || !/^-[1-9][0-9]{0,15}$/.test(chat) ||
    !Number.isSafeInteger(Number(chat)) || typeof fetchImpl!=="function")return null;
 return async text=>{
  if(typeof text!=="string"||!text||text.length>3500)return {ok:false};
  const controller=new AbortController();
  const timeout=setTimeout(()=>controller.abort(),8000);
  try{
   const res=await fetchImpl("https://api.telegram.org/bot"+token+"/sendMessage",{
    method:"POST",redirect:"error",signal:controller.signal,
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({chat_id:chat,text,link_preview_options:{is_disabled:true}})
   });
   if(!res.ok)return {ok:false};
   const reply=await res.json();
   if(reply?.ok!==true||String(reply.result?.chat?.id)!==chat||
      !Number.isSafeInteger(reply.result?.message_id)||reply.result.message_id<1)return {ok:false};
   return {ok:true,messageId:reply.result.message_id};
  }catch{return {ok:false};}
  finally{clearTimeout(timeout);}
 };
}
export function scheduleTelegramAfterSubmit(ctx,env,result,profile){
 // COMMITTED can also be a replay: durable outbox claim, not this hook, prevents duplicate sends.
 if(!["friend-b","friend-c"].includes(profile?.slot)||result?.state!=="COMMITTED"||
    !Number.isSafeInteger(result.receipt?.id)||result.receipt.id<1||
    typeof ctx?.waitUntil!=="function")return;
 const send=createTelegramTransport(env);
 if(!send)return;
 // Never alter the contributor's response because Telegram failed.
 try{ctx.waitUntil(dispatchOne({store:createTelegramOutbox(env.CONTRIBUTORS_DB),send,enabled:true,
    receiptId:result.receipt.id}).catch(()=>{}));}catch{}
}
