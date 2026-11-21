// REMURA Contributors v0.63 LAB — genuine UI state + injected client integration tests.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {mountAmendmentUIV063} from './contributors_amendment_v063_lab.mjs';
import {AmendmentClientV063} from './amendment_client_v063_lab.mjs';
import {amendmentHttpCandidateV062} from './amendment_http_v062_lab.mjs';
import {fixture} from './amendment_http_fixture_v062_lab.mjs';
const html=readFileSync(new URL('./contributors_amendment_v063_lab.html',import.meta.url),'utf8');
const js=readFileSync(new URL('./contributors_amendment_v063_lab.mjs',import.meta.url),'utf8');
function makeDoc(){
 const nodes=new Map();let pending=false;
 const element=()=>({textContent:'',disabled:false,listeners:{},classList:{add(n){if(n==='pending')pending=true;},remove(n){if(n==='pending')pending=false;}},addEventListener(n,fn){this.listeners[n]=fn;}});
 for(const id of ['#state','#feedback','#proposed','#when','#receiptStatus','#submitToLab','#checkReceipts','.status'])nodes.set(id,element());
 const form=element();form.elements={price:{value:''},observed:{value:''},note:{value:''},sourceId:{value:'1'}};
 nodes.set('#amendmentForm',form);
 return {nodes,doc:{querySelector:s=>nodes.get(s)},form,pending:()=>pending,node:s=>nodes.get(s),preview:()=>form.listeners.submit({preventDefault(){}}),send:()=>nodes.get('#submitToLab').listeners.click(),receipts:()=>nodes.get('#checkReceipts').listeners.click(),reset:()=>form.listeners.reset()};
}
const GOOD='2026-11-21T08:30:00Z';
function ready(ui){ui.form.elements.price.value='1,2345';ui.form.elements.observed.value=GOOD;ui.form.elements.note.value='fixture';ui.preview();}
function clientStub(){let submitted=0;let reads=0;let uncertain=false;return {get uncertain(){return uncertain;},set uncertain(v){uncertain=v;},async mutate(_,p){submitted++;return {id:11,status:'UNREVIEWED',duplicate:false};},async read(){reads++;return [{id:11}]},get submitted(){return submitted;},get reads(){return reads;}};}
const mount=(ui,client)=>mountAmendmentUIV063({doc:ui.doc,client,newId:()=> '11111111-1111-4111-8111-111111111111',now:()=>Date.parse('2026-11-21T09:42:00Z')});

test('01 version and Italian timestamp at very top',()=>assert.match(html,/<body>\s*<div class="version">REMURA Contributors v0\.63 LAB · 21\/11\/2026 09:42 CET/));
test('02 offline default page prohibits any network',()=>assert.match(html,/connect-src 'none'/));
test('03 all write controls disabled without injected client',()=>{const ui=makeDoc();mount(ui,null);ready(ui);assert.equal(ui.node('#submitToLab').disabled,true);assert.equal(ui.node('#checkReceipts').disabled,true);});
test('04 no direct network or storage access in UI module',()=>{assert.doesNotMatch(js,/(?:\bfetch\s*\(|XMLHttpRequest|localStorage|indexedDB|WebSocket|navigator\.sendBeacon)/);});
test('05 input has no automatic live credentials or tokens',()=>{assert.doesNotMatch(html,/(?:SECRET_KEY|PRIVATE_KEY|Bearer\s+|data-access-token)/i);});
test('06 pending preview with synthetic values',()=>{const ui=makeDoc();const cl=clientStub();mount(ui,cl);ready(ui);assert.equal(ui.pending(),true);assert.match(ui.node('#state').textContent,/NON INVIATA/);assert.equal(ui.node('#proposed').textContent,'1,2345');assert.equal(cl.submitted,0);});
test('07 invalid price stops before transport',async()=>{const ui=makeDoc(),cl=clientStub();mount(ui,cl);ui.form.elements.price.value='1e10';ui.form.elements.observed.value=GOOD;ui.preview();assert.equal(ui.node('#submitToLab').disabled,true);await ui.send();assert.equal(cl.submitted,0);});
test('08 future UTC not previewable',()=>{const ui=makeDoc();mount(ui,clientStub());ui.form.elements.price.value='1.2';ui.form.elements.observed.value='2030-01-01T00:00:00Z';ui.preview();assert.match(ui.node('#state').textContent,/NON VALIDI/);});
test('09 valid submit shows receipt, never claims publication',async()=>{const ui=makeDoc(),cl=clientStub();mount(ui,cl);ready(ui);await ui.send();assert.equal(cl.submitted,1);assert.match(ui.node('#state').textContent,/RICEVUTA CONFERMATA/);assert.match(ui.node('#feedback').textContent,/NON cambia/);assert.equal(ui.node('#published')?.textContent,undefined);});
test('10 successful submit disables further writes',async()=>{const ui=makeDoc(),cl=clientStub();const view=mount(ui,cl);ready(ui);await ui.send();assert.equal(view.isLocked(),true);await ui.send();assert.equal(cl.submitted,1);});
test('11 unknown outcome shows explicit uncertainty and locks',async()=>{const ui=makeDoc(),cl=clientStub();cl.mutate=async()=>{cl.uncertain=true;throw Error('lost confirmation')};const view=mount(ui,cl);ready(ui);await ui.send();assert.equal(view.isLocked(),true);assert.match(ui.node('#state').textContent,/ESITO INCERTO/);assert.equal(ui.node('#submitToLab').disabled,true);});
test('12 read receipts allowed even after an uncertain write',async()=>{const ui=makeDoc(),cl=clientStub();cl.mutate=async()=>{cl.uncertain=true;throw Error('timeout')};mount(ui,cl);ready(ui);await ui.send();await ui.receipts();assert.equal(cl.reads,1);assert.match(ui.node('#receiptStatus').textContent,/resta incerto/);});
test('13 refusal before dispatch does not produce confirmed receipt',async()=>{const ui=makeDoc(),cl=clientStub();cl.mutate=async()=>{throw Error('no token')};mount(ui,cl);ready(ui);await ui.send();assert.match(ui.node('#state').textContent,/NON CONFERMATO/);assert.doesNotMatch(ui.node('#state').textContent,/RICEVUTA CONFERMATA/);});
test('14 request ID generated only at user-confirmed dispatch',async()=>{const ui=makeDoc(),cl=clientStub();let ids=0;const view=mountAmendmentUIV063({doc:ui.doc,client:cl,newId:()=>{ids++;return '11111111-1111-4111-8111-111111111111'},now:()=>Date.parse('2026-11-21T09:42:00Z')});ready(ui);assert.equal(ids,0);await ui.send();assert.equal(ids,1);assert.equal(view.isLocked(),true);});
test('15 missing uuid blocks with no network',async()=>{const ui=makeDoc(),cl=clientStub();mountAmendmentUIV063({doc:ui.doc,client:cl,newId:()=>null,now:()=>Date.parse('2026-11-21T09:42:00Z')});ready(ui);await ui.send();assert.equal(cl.submitted,0);assert.match(ui.node('#state').textContent,/BLOCCATO/);});
test('16 closing view disables sending',async()=>{const ui=makeDoc(),cl=clientStub();const view=mount(ui,cl);ready(ui);view.disconnect();assert.equal(ui.node('#submitToLab').disabled,true);await ui.send();assert.equal(cl.submitted,0);});
test('17 offline iPhone staging call-to-action remains disabled',()=>{assert.match(html,/id="submitToLab" disabled/);assert.match(html,/id="checkReceipts"[^>]*disabled/);});
test('18 page declares LAB browser view not a real submission',()=>{assert.match(html,/OFFLINE/);assert.match(html,/Nessuna connessione LAB attiva/);});

async function integrated(t,{lose=false}={}){
 const x=await fixture(t);
 const origin='https://contributors.lab.invalid';
 Object.assign(x.env,{AMENDMENT_V062_ENABLED:'OFFLINE_FIXTURE_ONLY',INTENT_HMAC_KEY:'f'.repeat(64),STAGING_ORIGIN:origin});
 const calls=[];
 const fetcher=async(path,options)=>{
  calls.push(path);
  const request=new Request(origin+path,{...options,headers:{...options.headers,Origin:origin,'Sec-Fetch-Site':'same-origin'}});
  const response=await amendmentHttpCandidateV062(request,x.env,x.ctx);
  if(lose&&path==='/api/amendment/submit')throw Error('lost response');
  return response;
 };
 const client=new AmendmentClientV063(fetcher);
 const ui=makeDoc();
 const view=mountAmendmentUIV063({doc:ui.doc,client,newId:()=> '11111111-1111-4111-8111-111111111111',now:Date.now});
 ui.form.elements.price.value='1,2345';ui.form.elements.observed.value=new Date(Date.now()-30000).toISOString().slice(0,19)+'Z';
 ui.preview();
 return {x,ui,client,view,calls};
}
test('19 UI -> client -> HTTP -> SQLite full synthetic chain confirms only verified receipt',async t=>{
 const {x,ui,client,calls}=await integrated(t);
 await ui.send();
 assert.match(ui.node('#state').textContent,/RICEVUTA CONFERMATA/);
 assert.equal(x.db.prepare('SELECT count(*) AS n FROM lab_level_amendments_v059').get().n,1);
 assert.deepEqual(calls,['/api/amendment/intent','/api/amendment/submit']);
 assert.equal(client.uncertain,false);
});
test('20 UI -> client -> HTTP lost-after-commit locks without auto retry and permits receipt check',async t=>{
 const {x,ui,client,calls}=await integrated(t,{lose:true});
 await ui.send();
 assert.match(ui.node('#state').textContent,/ESITO INCERTO/);
 assert.equal(client.uncertain,true);
 await ui.send();
 assert.equal(calls.filter(p=>p==='/api/amendment/submit').length,1);
 assert.equal(x.db.prepare('SELECT count(*) AS n FROM lab_level_amendments_v059').get().n,1);
 await ui.receipts();assert.match(ui.node('#receiptStatus').textContent,/resta incerto/);
});
test('21 UI confirmed amendment stays unapproved until separate owner decision',async t=>{
 const {x,ui,client}=await integrated(t);
 await ui.send();
 const orig=await client.read('/api/amendment/approved',{});assert.equal(orig[0].price,'1.123');
 x.who('owner');
 const result=await client.mutate('/owner/amendment/review',{id:1,action:'APPROVED',reason:'synthetic'});
 assert.equal(result.action,'APPROVED');
 x.who('alice');
 const after=await client.read('/api/amendment/approved',{});assert.equal(after[0].price,'1.2345');
});
