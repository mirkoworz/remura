import {dispatchOne} from "./telegram_dispatch_v3012_lab.mjs";
import {createTelegramTransport} from "./telegram_transport_v3012_lab.mjs";
// All sends simulated. No real secrets, endpoint calls, or D1 connections.
const receipt={id:2,market:"EURUSD",provider:"FIXTURE",ticker:"EURUSD",product:"SPOT",contract:"",period:"DAY",kind:"DELTA_PEAK",price:"1.09694",received_utc:"2026-11-26T11:23:41Z",note:"",slot:"friend-c",start_after_receipt:1};
function assert(x,label){if(!x)throw Error(label);}
export async function runTests(){
 const tests=[];
 for(const mode of ["off","send","timeout","blocked","finishFail"]){
  let calls=0,claimed=false,finished;
  const store={claim:async(now,id)=>{assert(id===2,"wrong receipt");if(claimed)return null;claimed=true;return {receipt_id:2,epoch:2}},
   load:async()=>mode==="blocked"?null:receipt,
   finish:async(...v)=>{if(mode==="finishFail")throw Error("simulated");finished=v}};
  const send=async t=>{calls++;if(mode==="timeout")throw Error("simulated");assert(!t.includes("friend-c"),"identity leak");return {ok:true,messageId:42}};
  const opts={store,send,enabled:mode!=="off",receiptId:2};
  const first=await dispatchOne(opts),second=await dispatchOne(opts);
  const expected={off:"OFF",send:"SENT",timeout:"UNKNOWN",blocked:"BLOCKED",finishFail:"FINALIZATION_UNKNOWN"}[mode];
  assert(first.state===expected&&calls===(["off","blocked"].includes(mode)?0:1)&&second.state===(mode==="off"?"OFF":"EMPTY"),mode);
  if(mode==="send")assert(finished[3]===42,"message id");
  tests.push(mode);
 }
 const env={TELEGRAM_BRIDGE_V3012:"EXPLICIT_STAGING_ONLY",TELEGRAM_BOT_TOKEN:"123456789:"+"x".repeat(32),TELEGRAM_CHAT_ID:"-1001234567890"};
 let requests=0;
 const fetchMock=async(url,options)=>{requests++;assert(url==="https://api.telegram.org/bot"+env.TELEGRAM_BOT_TOKEN+"/sendMessage","endpoint");
  const body=JSON.parse(options.body);
  assert(body.chat_id===env.TELEGRAM_CHAT_ID&&body.text==="fixture"&&options.redirect==="error","body");
  return {ok:true,json:async()=>({ok:true,result:{chat:{id:Number(env.TELEGRAM_CHAT_ID)},message_id:42}})};};
 assert(createTelegramTransport({},fetchMock)===null,"default off");
 assert(createTelegramTransport({...env,TELEGRAM_CHAT_ID:"123"},fetchMock)===null,"private chat blocked");
 assert(requests===0,"unexpected call");tests.push("transport config");
 const send=createTelegramTransport(env,fetchMock);
 assert((await send("fixture")).messageId===42&&requests===1,"mock transport");tests.push("transport send");
 const wrong=createTelegramTransport(env,async()=>({ok:true,json:async()=>({ok:true,result:{chat:{id:-99},message_id:42}})}));
 assert((await wrong("fixture")).ok===false,"wrong chat");tests.push("transport response");
 return tests;
}
console.log(JSON.stringify(await runTests()));
