// REMURA Contributors v0.67 LAB — NEW targeted tests; does not invoke historical suites.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {mountRecoveryPortalV067,OwnerRecoveryClientV067,validateOwnReceiptsV067} from './recovery_portal_v067_lab.mjs';
const base=new URL('.',import.meta.url);
const source=n=>readFileSync(new URL(n,base),'utf8');
const html=source('contributors_recovery_v067_lab.html'),owner=source('contributors_owner_recovery_v067_lab.html');
const css=source('contributors_recovery_v067_lab.css'),moduleText=source('recovery_portal_v067_lab.mjs');
const reqid='00000000-0000-4000-8000-000000000003',subject='a'.repeat(64);
const one={status:'UNRESOLVED',attempt_id:1,request_id:reqid,mayResubmit:false,manualApprovalRequired:true};
const my=[{id:7,source_entry_id:1,price:'1.2345',observed_utc:'2026-11-21T08:00:00Z',received_utc:'2026-11-21T08:01:00Z',note:'PRIVATE NOTE',status:'UNREVIEWED'}];
const oRow=(id=1,status='UNRESOLVED')=>({attempt_id:id,subject,request_id:reqid,status,manualApprovalRequired:true});
const response=(data,options={})=>new Response(JSON.stringify({data}),{status:options.status??200,headers:{'Content-Type':options.type??'application/json','Cache-Control':options.cache??'no-store'}});
function fakeDOM(){
 const nodes=new Map();
 function node(){return {children:[],textContent:'',disabled:false,listeners:{},addEventListener(event,cb){this.listeners[event]=cb;},appendChild(n){this.children.push(n);return n;},replaceChildren(...x){this.children=x;}};}
 for(const id of ['recoveryHeadline','recoverySummary','recoveryCode','recoveryList','refreshRecovery','refreshReceipts','leaveRecovery','moreRecovery','sendGate','recoveryExtra'])nodes.set('#'+id,node());
 return {doc:{querySelector:id=>nodes.get(id),createElement:()=>node()},get:id=>nodes.get('#'+id)};
}
function makeFetch(data=one){const calls=[];let fail=false;
 const fetcher=async(path,opts)=>{calls.push({path,opts});if(fail)throw Error('network_error');
  if(path==='/api/amendment/reconcile')return response(data);
  if(path==='/api/amendment/mine')return response(my);
  if(path==='/owner/amendment/reconcile-queue')return response([oRow()]);
  throw Error('unexpected_route');
 };
 return {fetcher,calls,setFail:v=>{fail=v;}};
}
const mount=(role='CONTRIBUTOR',fetcher=null)=>{const ui=fakeDOM();return {...ui,portal:mountRecoveryPortalV067({doc:ui.doc,role,fetcher})};};

test('01 contributor banner first node displays version and actual CET update',()=>assert.match(html,/<body data-role="CONTRIBUTOR">\s*<div class="version">REMURA Contributors v0\.67 LAB · 21\/11\/2026 11:57 CET/));
test('02 owner banner first node displays version and actual CET update',()=>assert.match(owner,/<body data-role="OWNER">\s*<div class="version">REMURA Contributors v0\.67 LAB · 21\/11\/2026 11:57 CET/));
test('03 both offline documents prohibit outbound connections',()=>{for(const h of [html,owner]){assert.match(h,/connect-src 'none'/);assert.match(h,/form-action 'none'/);assert.doesNotMatch(h,/on(?:click|load|submit)=|<form\b/i);}});
test('04 browser bundle has no direct fetch, storage, web socket or mutation handler',()=>{assert.doesNotMatch(moduleText,/(?:(?<![\.#])\bfetch\s*\(|XMLHttpRequest|localStorage|sessionStorage|indexedDB|WebSocket|navigator\.sendBeacon)/);assert.doesNotMatch(moduleText,/\/api\/amendment\/submit|\/owner\/amendment\/review/);});
test('05 all standalone controls are offline and disabled by default',()=>{const u=mount();assert.equal(u.get('refreshRecovery').disabled,true);assert.equal(u.get('refreshReceipts').disabled,true);assert.equal(u.get('moreRecovery').disabled,true);assert.equal(u.get('recoveryCode').textContent,'OFFLINE · LAB');});
test('06 owner standalone cannot query data by default',()=>{const u=mount('OWNER');assert.equal(u.get('refreshRecovery').disabled,true);assert.equal(u.get('refreshReceipts').disabled,true);});
test('07 five status descriptions exist; none provide permission to resubmit',async()=>{for(const state of ['NO_ATTEMPT','UNRESOLVED','COMMITTED_UNREVIEWED','COMMITTED_REVIEWED','CLOSED']){const {fetcher}=makeFetch(state==='NO_ATTEMPT'?{status:state,mayResubmit:false,manualApprovalRequired:true}:{...one,status:state});const u=mount('CONTRIBUTOR',fetcher);await u.portal.refresh();assert.equal(u.get('recoveryCode').textContent,state);assert.match(u.get('sendGate').textContent,/BLOCCATI/);assert.equal('send' in u.portal,false);}});
test('08 no attempt displays zero receipts and does not unlock any operation',async()=>{const u=mount('CONTRIBUTOR',makeFetch({status:'NO_ATTEMPT',mayResubmit:false,manualApprovalRequired:true}).fetcher);await u.portal.refresh();assert.equal(u.get('recoveryList').children.length,0);assert.match(u.get('recoverySummary').textContent,/non è un permesso/i);});
test('09 unresolved explains owner manual verification',async()=>{const u=mount('CONTRIBUTOR',makeFetch().fetcher);await u.portal.refresh();assert.match(u.get('recoverySummary').textContent,/verifica manuale/);assert.equal(u.get('recoveryList').children.length,1);});
test('10 closed never enables a retry',async()=>{const u=mount('CONTRIBUTOR',makeFetch({...one,status:'CLOSED'}).fetcher);await u.portal.refresh();assert.match(u.get('recoverySummary').textContent,/non è un’autorizzazione/);assert.match(u.get('sendGate').textContent,/BLOCCATI/);});
test('11 actual v0.65 client consumes exact guarded POST and no retry',async()=>{const f=makeFetch();const u=mount('CONTRIBUTOR',f.fetcher);await u.portal.refresh();assert.deepEqual(f.calls.map(x=>x.path),['/api/amendment/reconcile']);assert.equal(f.calls[0].opts.method,'POST');assert.equal(f.calls[0].opts.credentials,'same-origin');assert.equal(f.calls[0].opts.cache,'no-store');});
test('12 contributor fetch never calls owner route',async()=>{const f=makeFetch();const u=mount('CONTRIBUTOR',f.fetcher);await u.portal.refresh();await u.portal.receipts();assert.equal(f.calls.some(c=>c.path.startsWith('/owner/')),false);});
test('13 receipts use only server scoped mine route with no actor query',async()=>{const f=makeFetch();const u=mount('CONTRIBUTOR',f.fetcher);await u.portal.receipts();assert.deepEqual(f.calls.map(c=>c.path),['/api/amendment/mine']);assert.equal(f.calls[0].opts.body,'{"after":0}');assert.equal(u.get('recoveryList').children.length,1);});
test('14 receipts only expose minimum personal projection, no notes/prices',async()=>{const f=makeFetch();const u=mount('CONTRIBUTOR',f.fetcher);await u.portal.receipts();const displayed=JSON.stringify(u.get('recoveryList').children);assert.doesNotMatch(displayed,/PRIVATE NOTE|1\.2345|subject/);assert.match(displayed,/Ricevuta #7/);});
test('15 no subject injection or extra wire fields into personal receipts',()=>{assert.throws(()=>validateOwnReceiptsV067([{...my[0],subject}]),/NOT_ATTESTED/);});
test('16 receipt rejects invalid time, price, status, order and excessive payload',()=>{for(const row of [{...my[0],received_utc:'bad'},{...my[0],price:'1e10'},{...my[0],status:'PENDING'},my[0]]){if(row!==my[0])assert.throws(()=>validateOwnReceiptsV067([row]),/NOT_ATTESTED/);}assert.throws(()=>validateOwnReceiptsV067([my[0],my[0]]),/NOT_ATTESTED/);});
test('17 request can fail without optimistic confirmation',async()=>{const f=makeFetch();f.setFail(true);const u=mount('CONTRIBUTOR',f.fetcher);await u.portal.refresh();assert.equal(u.get('recoveryCode').textContent,'NON VERIFICATO');assert.equal(u.get('recoveryList').children.length,0);});
test('18 bad server mayResubmit permission produces no verified state',async()=>{const u=mount('CONTRIBUTOR',makeFetch({...one,mayResubmit:true}).fetcher);await u.portal.refresh();assert.equal(u.get('recoveryCode').textContent,'NON VERIFICATO');});
test('19 unexpected identity data in personal status is rejected by v0.65',async()=>{const u=mount('CONTRIBUTOR',makeFetch({...one,subject}).fetcher);await u.portal.refresh();assert.equal(u.get('recoveryCode').textContent,'NON VERIFICATO');});
test('20 owner client accepts only exact owner queue HTTP read',async()=>{const f=makeFetch();const c=new OwnerRecoveryClientV067(f.fetcher);const data=await c.inspect();assert.equal(data.length,1);assert.equal(f.calls[0].path,'/owner/amendment/reconcile-queue');assert.equal(f.calls[0].opts.body,'{"after":0}');assert.equal(f.calls[0].opts.headers['X-Remura-CSRF'],'1');});
test('21 owner page displays queue, not personal receipts',async()=>{const f=makeFetch();const u=mount('OWNER',f.fetcher);await u.portal.refresh();assert.equal(f.calls.length,1);assert.equal(f.calls[0].path,'/owner/amendment/reconcile-queue');assert.match(JSON.stringify(u.get('recoveryList').children),/Tentativo #1/);assert.equal(u.get('refreshReceipts').disabled,true);});
test('22 malformed owner record with extra private fields is denied',async()=>{const c=new OwnerRecoveryClientV067(async()=>response([{...oRow(),private_note:'DO NOT LEAK'}]));await assert.rejects(()=>c.inspect(),/NOT_ATTESTED/);});
test('23 owner queue disallows CLOSED/released state',async()=>{const c=new OwnerRecoveryClientV067(async()=>response([oRow(1,'CLOSED')]));await assert.rejects(()=>c.inspect(),/NOT_ATTESTED/);});
test('24 owner queue denies subject absent or malformed',async()=>{const c=new OwnerRecoveryClientV067(async()=>response([{...oRow(),subject:'bob'}]));await assert.rejects(()=>c.inspect(),/NOT_ATTESTED/);});
test('25 owner queue denies non 200 or cacheable replies',async()=>{for(const o of [{status:403},{cache:'public,max-age=50'}]){const c=new OwnerRecoveryClientV067(async()=>response([oRow()],o));await assert.rejects(()=>c.inspect(),/NOT_ATTESTED/);}});
test('26 owner queue denies unsorted rows and duplicate IDs',async()=>{for(const data of [[oRow(2),oRow(1)],[oRow(1),oRow(1)]]){const c=new OwnerRecoveryClientV067(async()=>response(data));await assert.rejects(()=>c.inspect(),/NOT_ATTESTED/);}});
test('27 owner queue limits replies to 20 and exact cursor',async()=>{const c=new OwnerRecoveryClientV067(async()=>response(Array.from({length:21},(_,i)=>oRow(i+1))));await assert.rejects(()=>c.inspect(),/NOT_ATTESTED/);await assert.rejects(()=>c.inspect(-1),/NOT_ATTESTED/);});
test('28 owner pagination follows server cursor without skipping',async()=>{const calls=[];const fetcher=async(path,o)=>{const after=JSON.parse(o.body).after;calls.push(after);return response(after===0?Array.from({length:20},(_,i)=>oRow(i+1)):[oRow(21)]);};const u=mount('OWNER',fetcher);await u.portal.refresh();assert.equal(u.get('moreRecovery').disabled,false);await u.portal.more();assert.equal(u.get('recoveryList').children.length,21);assert.deepEqual(calls,[0,20]);});
test('29 manual clear invalidates in-flight result after leave',async()=>{let finish;const fetcher=()=>new Promise(r=>{finish=r;});const u=mount('CONTRIBUTOR',fetcher);const pending=u.portal.refresh();u.portal.leave();finish(response(one));await pending;assert.equal(u.get('recoveryList').children.length,0);assert.equal(u.get('refreshRecovery').disabled,true);assert.match(u.get('recoveryCode').textContent,/CHIUSA/);});
test('30 refresh resets old verified snapshot before a failed read',async()=>{const f=makeFetch();const u=mount('CONTRIBUTOR',f.fetcher);await u.portal.refresh();assert.equal(u.get('recoveryList').children.length,1);f.setFail(true);await u.portal.refresh();assert.equal(u.get('recoveryList').children.length,0);assert.equal(u.get('recoveryCode').textContent,'NON VERIFICATO');});
test('31 repeated button while pending does not dispatch twice',async()=>{let finish;let hits=0;const f=()=>{hits++;return new Promise(r=>finish=r);};const u=mount('CONTRIBUTOR',f);const one=u.portal.refresh();await u.portal.refresh();finish(response({status:'NO_ATTEMPT',mayResubmit:false,manualApprovalRequired:true}));await one;assert.equal(hits,1);});
test('32 iPhone responsive layout and safe-area styling present',()=>{assert.match(html,/viewport-fit=cover/);assert.match(css,/@media\(max-width:780px\)/);assert.match(css,/@media\(max-width:400px\)/);assert.match(css,/safe-area-inset-left/);});
test('33 no real provider logout or deployed function claimed',()=>{assert.match(html,/non equivale a logout Cloudflare Access/);assert.match(owner,/non realizza un logout del provider/);assert.doesNotMatch(moduleText,/export\s+default\s*\{|addEventListener\(['"]fetch/);});
