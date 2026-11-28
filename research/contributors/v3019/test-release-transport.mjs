// Node 22+, offline only; deliberately fake credentials and mock fetch.
import assert from "node:assert/strict";
import {createGroupedTelegramTransport,releaseMode} from "./proposal-telegram-transport.mjs";
import {isReleaseRealm,isSyntheticRealm} from "./proposal-realm.mjs";
export async function run(check){
 let n=0;const ok=v=>{check(v);n++;};
 const env={REMURA_V3019_MODE:"STAGING_CANDIDATE_ONLY",REMURA_V3019_REAL_TELEGRAM:"EXPLICITLY_AUTHORIZED",TELEGRAM_BRIDGE_V3012:"EXPLICIT_STAGING_ONLY",TELEGRAM_BOT_TOKEN:"123456:FAKE_TOKEN_FOR_TEST_ONLY_123456789",TELEGRAM_CHAT_ID:"-12345"};
 let calls=0,mode="good",last;
 const fake=async(url,opts)=>{
  calls++;last={url,opts};
  if(mode==="throw")throw Error("fake timeout");
  if(mode==="http")return {ok:false};
  return {ok:true,json:async()=>mode==="json"?Promise.reject(Error("bad json")):mode==="api"?{ok:false}:{ok:true,result:{chat:{id:mode==="chat"?-999:-12345},message_id:mode==="id"?0:77}}};
 };
 ok(releaseMode(env));
 for(const patch of [{REMURA_V3019_MODE:undefined},{REMURA_V3019_REAL_TELEGRAM:undefined},{TELEGRAM_BRIDGE_V3012:undefined},{REMURA_V3019_LAB_MODE:"SYNTHETIC_ONLY"},{REMURA_V3019_TRANSPORT:"SYNTHETIC_TRANSPORT_ONLY"},{TELEGRAM_BOT_TOKEN:"bad"},{TELEGRAM_CHAT_ID:"12345"}]){
  ok(createGroupedTelegramTransport({...env,...patch},fake)===null);
 }
 ok(calls===0);
 const send=createGroupedTelegramTransport(env,fake);
 const message="🦈 REMURA INTELLIGENCE\n\n• 12.5\n• 13\nRif. P7 · Approvazione automatica REMURA";
 ok(!(await send("invalid")).ok&&calls===0);
 ok(!(await send(message+" ".repeat(4000))).ok&&calls===0);
 const reply=await send(message);
 ok(reply.ok&&reply.messageId===77&&calls===1);
 ok(last.url==="https://api.telegram.org/bot"+env.TELEGRAM_BOT_TOKEN+"/sendMessage");
 const body=JSON.parse(last.opts.body);
 ok(last.opts.method==="POST"&&last.opts.redirect==="error"&&body.chat_id==="-12345"&&body.text===message);
 ok(!Object.hasOwn(body,"parse_mode")&&body.link_preview_options.is_disabled===true);
 for(const m of ["throw","http","json","api","chat","id"]){mode=m;const before=calls;ok(!(await send(message)).ok&&calls===before+1);}
 const db=(results,primary=true,fail=false)=>({withSession:(s)=>{ok(s==="first-primary");return {prepare:()=>({bind:()=>({all:async()=>{if(fail)throw Error("db");return {success:true,meta:{served_by_primary:primary},results};}})})};}});
 ok(await isReleaseRealm(db([{realm:"STAGING_CANDIDATE"}])));
 ok(!await isReleaseRealm(db([],true,true)));
 ok(!await isReleaseRealm(db([{realm:"STAGING_CANDIDATE"}],false)));
 ok(!await isReleaseRealm(db([])));
 ok(await isSyntheticRealm(db([])));
 ok(!await isSyntheticRealm(db([{name:"lab_delivery_realm_v3019"}])));
 ok(!await isSyntheticRealm(db([],false)));
 ok(!await isSyntheticRealm(db([],true,true)));
 return n;
}
if(typeof process!=="undefined"&&process.argv[1]?.endsWith("test-release-transport.mjs"))console.log((await run(assert.ok))+" checks PASS");
