// Runnable with Node: node test-dispatch-v3019.mjs
import assert from "node:assert/strict";
import {dispatchGroupedFixture,SQL} from "./proposal-store.mjs";
import {formatGrouped} from "./proposal-core.mjs";
import {createLabDispatcher,normalizeRecovery,scheduleProposalLab} from "./proposal-dispatch-lab.mjs";
export async function run(check){
 let n=0;const ok=x=>{check(x);n++;};
 const row={id:7,state:"COMMITTED",decision:"APPROVED",decision_origin:"AUTOMATIC",slot:"friend-b",publication_mode:"TELEGRAM",received_utc:"2026-11-28T07:57:00Z",proposal:{request_id:"aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",mapping_id:"FUTURES_NQ_RITHMIC",kind:"CVD_DIVERGENCE",period:"DAY",prices:"12.5\n13",note:"private note"}};
 let state="PENDING",sends=0,allow=true,fail=false,finishFail=false,claimFail=false,current=row,last;
 const store={claim:async id=>{if(claimFail)throw Error("claim");if(state!=="PENDING")return null;state="SENDING";return {proposal_id:id,epoch:1};},load:async()=>allow?current:null,finish:async(id,s,msg)=>{if(finishFail)throw Error("finish");state=s;last=msg;}};
 const send=async msg=>{sends++;ok(msg.includes("• 12.5")&&msg.includes("• 13")&&!msg.includes("private note"));if(fail)throw Error("timeout");return {ok:true,messageId:7};};
 const go=()=>dispatchGroupedFixture({store,proposalId:7,send,permit:"OFFLINE_FIXTURE_ONLY"});
 ok(formatGrouped(row).includes("Approvazione automatica REMURA"));
 ok(formatGrouped({...row,decision_origin:"OWNER"}).includes("Approvato dall’OWNER"));
 ok(formatGrouped({...row,decision:"PENDING"})===null);
 ok(formatGrouped({...row,decision:"REJECTED"})===null);
 ok(formatGrouped({...row,slot:"friend-a"})===null);
 ok(formatGrouped({...row,publication_mode:"TEST"})===null);
 const both=await Promise.all([go(),go()]);ok(both.some(x=>x.state==="SENT")&&both.some(x=>x.state==="EMPTY"));ok(sends===1&&state==="SENT"&&last===7);
 state="PENDING";allow=false;ok((await go()).state==="BLOCKED"&&sends===1);
 state="PENDING";allow=true;fail=true;ok((await go()).state==="UNKNOWN");ok((await go()).state==="EMPTY"&&sends===2);
 state="PENDING";fail=false;finishFail=true;ok((await go()).state==="FINALIZATION_UNKNOWN");ok(state==="SENDING"&&(await go()).state==="EMPTY"&&sends===3);
 finishFail=false;claimFail=true;state="PENDING";ok((await go()).state==="CLAIM_UNKNOWN"&&sends===3);
 ok((await dispatchGroupedFixture({store,proposalId:7,send,permit:"LIVE"})).state==="OFF");
 ok(createLabDispatcher({REMURA_V3019_LAB_MODE:"SYNTHETIC_ONLY"})===null);
 ok(scheduleProposalLab({}, {},7)===false);
 ok(normalizeRecovery({id:7,epoch:2,action:"MARK_UNKNOWN"}).epoch===2);
 let denied=false;try{normalizeRecovery({id:7,epoch:2,action:"RETRY"})}catch{denied=true;}ok(denied);
 ok(SQL.claim.includes("d.action='APPROVED'")&&SQL.load.includes("p.epoch=o.epoch"));
 return n;
}
if(typeof process!=="undefined"&&process.argv[1]?.endsWith("test-dispatch-v3019.mjs"))console.log((await run(assert.ok))+" checks PASS");
