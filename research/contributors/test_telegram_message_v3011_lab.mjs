import test from "node:test";
import assert from "node:assert/strict";
import {prepareTelegramMessage as build} from "./telegram_message_v3011_lab.mjs";
const receipt={id:2,market:"EURUSD",provider:"FIXTURE",ticker:"EURUSD",product:"SPOT",contract:"",period:"DAY",kind:"DELTA_PEAK",price:"1.09694",received_utc:"2026-11-26T11:23:41Z",note:"private fixture note"};
const event={state:"COMMITTED",newCanonical:true,test:false,slot:"friend-c",receipt};
const policy={enabled:true,startAfterReceipt:1,allowedMappings:[["EURUSD","FIXTURE","EURUSD","SPOT",""]]};
test("synthetic allowlisted event renders anonymous pending-review message",()=>{
 const m=build(event,policy);assert.equal(m.receiptId,2);
 assert.match(m.text,/🇪🇺 🇺🇸 EUR\/USD/);
 assert.match(m.text,/REMURA Contributor/);
 assert.match(m.text,/Non ancora esaminato/);
 assert.match(m.text,/12:23:41/);
 assert.doesNotMatch(m.text,/friend-c|private fixture note/);
});
test("default off and source gates",()=>{
 assert.equal(build(event),null);
 assert.equal(build(event,{...policy,allowedMappings:[]}),null);
 assert.equal(build({...event,receipt:{...receipt,provider:"ECB"}},{...policy,allowedMappings:[["EURUSD","ECB","EURUSD","SPOT",""]]}),null);
});
test("exclude historic, duplicates, test account and unclassified records",()=>{
 for(const x of [{...event,state:"DUPLICATE"},{...event,newCanonical:false},{...event,test:true},{...event,test:undefined},{...event,slot:"friend-a"},{...event,receipt:{...receipt,id:1}},{...event,receipt:{...receipt,note:"TEST V30.9 - NON OPERATIVO"}}]) assert.equal(build(x,policy),null);
});
test("invalid price, timestamp, or classification is rejected",()=>{
 for(const r of [{...receipt,price:"0"},{...receipt,kind:"toString"},{...receipt,received_utc:"2026-02-30T00:00:00Z"}]) assert.equal(build({...event,receipt:r},policy),null);
});
