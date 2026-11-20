// REMURA Experience v0.21 LAB — 20/11/2026 CET
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {makeConsumerV2,validateV2} from './consumer_v021.mjs';
const f=JSON.parse(execFileSync('python3',[fileURLToPath(new URL('./fixture_reply_v021.py',import.meta.url))],{encoding:'utf8'}));
const parsed=r=>JSON.parse(r.body);
function change(r,fn){const x=parsed(r);fn(x);return {...r,body:JSON.stringify(x)};}
function setup(){let t=f.now,reply=f.fresh;const c=makeConsumerV2({request:async()=>reply,clock:()=>t});return {c,time:v=>t=v,reply:v=>reply=v};}
const seed=async s=>assert.equal(await s.c.refresh(),'READY');
test('real v020 response and 28 pairs',async()=>{const s=setup();await seed(s);assert.equal(s.c.read().cot.length,28);assert.equal(s.c.read().prices[0].price,1.25);});
test('cached price expires and value removed',async()=>{const s=setup();await seed(s);s.time(f.now+1);assert.equal(s.c.read().prices[0].price,null);assert.equal(s.c.read().prices[0].freshness,'STALE');});
test('same revision fresh to stale accepted',async()=>{const s=setup();await seed(s);s.time(f.now+1);s.reply(f.stale);await seed(s);assert.equal(s.c.read().prices[0].price,null);});
test('stale latch prevents same revision resurrection',async()=>{const s=setup();s.reply(f.stale);await seed(s);s.reply(f.fresh);assert.equal(await s.c.refresh(),'UNAVAILABLE');assert.equal(s.c.read(),null);});
test('stale number rejected',()=>assert.throws(()=>validateV2({...parsed(f.stale),prices:[{...parsed(f.stale).prices[0],price:1.25}]},f.now+1)));
test('fresh null rejected',()=>assert.throws(()=>validateV2({...parsed(f.fresh),prices:[{...parsed(f.fresh).prices[0],price:null}]},f.now)));
test('V1 rejected',()=>assert.throws(()=>validateV2({...parsed(f.fresh),schema:'REMURA_SHARED_VIEW_FIXTURE_V1'},f.now)));
test('same revision altered fresh price denied',async()=>{const s=setup();await seed(s);s.reply(change(f.fresh,x=>x.prices[0].price=2));assert.equal(await s.c.refresh(),'UNAVAILABLE');});
test('same revision changed COT denied',async()=>{const s=setup();await seed(s);s.reply(change(f.fresh,x=>x.cot[0].asset_gap=30));assert.equal(await s.c.refresh(),'UNAVAILABLE');});
test('older revision denied',async()=>{const s=setup();s.reply(change(f.fresh,x=>x.revision=2));await seed(s);s.reply(f.fresh);assert.equal(await s.c.refresh(),'UNAVAILABLE');});
test('new revision accepted',async()=>{const s=setup();await seed(s);s.reply(change(f.fresh,x=>{x.revision=2;x.prices[0].price=2;}));await seed(s);assert.equal(s.c.read().prices[0].price,2);});
test('snapshot expiry clears view',async()=>{const s=setup();await seed(s);s.time(f.now+900001);assert.equal(s.c.read(),null);});
test('clock regression permanently closes consumer',async()=>{const s=setup();await seed(s);s.time(f.now-1);assert.equal(s.c.read(),null);s.time(f.now);assert.equal(await s.c.refresh(),'CANCELLED');});
test('logout permanent, new instance required',async()=>{const s=setup();await seed(s);s.c.close();assert.equal(s.c.read(),null);assert.equal(await s.c.refresh(),'CANCELLED');});
test('logout cancels late response',async()=>{let resolve;const c=makeConsumerV2({request:()=>new Promise(r=>resolve=r),clock:()=>f.now});const pending=c.refresh();c.close();resolve(f.fresh);assert.equal(await pending,'CANCELLED');assert.equal(c.read(),null);});
test('out of order requests cannot overwrite newer result',async()=>{const resolvers=[];const c=makeConsumerV2({request:()=>new Promise(r=>resolvers.push(r)),clock:()=>f.now});const p=c.refresh(),q=c.refresh();resolvers[1](change(f.fresh,x=>x.revision=2));assert.equal(await q,'READY');resolvers[0](f.fresh);assert.equal(await p,'CANCELLED');assert.equal(c.read().revision,2);});
test('403 revokes local session',async()=>{const s=setup();await seed(s);s.reply({status:403});assert.equal(await s.c.refresh(),'DENIED');assert.equal(s.c.read(),null);s.reply(f.fresh);assert.equal(await s.c.refresh(),'CANCELLED');});
test('failed refresh hides old view',async()=>{const s=setup();await seed(s);s.reply({status:503});assert.equal(await s.c.refresh(),'UNAVAILABLE');assert.equal(s.c.read(),null);});
test('no-store mandatory',async()=>{const s=setup();s.reply({...f.fresh,headers:{}});assert.equal(await s.c.refresh(),'UNAVAILABLE');});
test('response size cap',async()=>{const s=setup();s.reply({...f.fresh,body:' '.repeat(16385)});assert.equal(await s.c.refresh(),'UNAVAILABLE');});
test('returned clone cannot mutate session',async()=>{const s=setup();await seed(s);s.c.read().prices[0].price=999;assert.equal(s.c.read().prices[0].price,1.25);});
test('invalid COT or private extra field rejected',()=>{assert.throws(()=>validateV2({...parsed(f.fresh),secret:'x'},f.now));const x=parsed(f.fresh);x.cot.pop();assert.throws(()=>validateV2(x,f.now));});
