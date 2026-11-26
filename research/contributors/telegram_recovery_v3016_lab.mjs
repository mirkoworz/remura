// REMURA V30.16 LAB: one OWNER-requested recovery, never retry an ambiguous send.
import {createTelegramTransport} from "./telegram_transport_v3012_lab.mjs";
import {createTelegramOutbox,dispatchOne} from "./telegram_dispatch_v3012_lab.mjs";
export async function recoverTelegramPending({env,actor,epoch,now=Date.now(),sendFactory=createTelegramTransport,storeFactory=createTelegramOutbox}){
 if(!Number.isSafeInteger(epoch)||epoch<1||!Number.isFinite(now)||
 !/^[a-f0-9]{64}$/.test(actor?.subject??"")||!/^[a-f0-9]{64}$/.test(actor?.email_tag??""))return {state:"BLOCKED"};
 const send=sendFactory(env);
 if(!send)return {state:"OFF"};
 const cutoff=new Date(now-15*60*1000).toISOString().slice(0,19)+"Z";
 return dispatchOne({store:storeFactory(env.CONTRIBUTORS_DB),send,enabled:true,recovery:{epoch,cutoff,actor}});
}
