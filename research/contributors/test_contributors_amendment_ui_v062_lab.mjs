// REMURA v0.62 LAB — static + offline interaction test, NOT real Safari / iPhone.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const html=readFileSync(new URL('./contributors_amendment_v062_lab.html',import.meta.url),'utf8');
const css=readFileSync(new URL('./contributors_amendment_v062_lab.css',import.meta.url),'utf8');
const js=readFileSync(new URL('./contributors_amendment_v062_lab.mjs',import.meta.url),'utf8');
const attr=(s)=>html.includes(s);
function mount(){
 const nodes=new Map();let pending=false;
 const el=(id)=>({textContent:'',classList:{add:x=>{if(x==='pending')pending=true},remove:x=>{if(x==='pending')pending=false}}});
 for(const id of ['#state','#feedback','#proposed','#when','.status'])nodes.set(id,el(id));
 const callbacks={};const form={elements:{price:{value:''},observed:{value:''},note:{value:''}},addEventListener:(name,fn)=>{callbacks[name]=fn}};
 nodes.set('#amendmentForm',form);
 vm.runInNewContext(js,{document:{querySelector:id=>nodes.get(id)},Date,queueMicrotask:fn=>fn()});
 const submit=()=>{let stopped=false;callbacks.submit({preventDefault:()=>{stopped=true}});return stopped};
 const reset=()=>callbacks.reset();
 const text=id=>nodes.get(id).textContent;
 return{form,submit,reset,text,pending:()=>pending};
}
test('01 version and date first body node',()=>assert.match(html,/<body>\s*<div class="version">REMURA Contributors v0\.62 LAB · 21\/11\/2026 09:29 CET/));
test('02 explicit non-deployed warning',()=>assert.ok(attr('DEMO NON DISTRIBUITA')));
test('03 viewport supports iPhone safe area',()=>{assert.match(html,/viewport-fit=cover/);assert.match(css,/safe-area-inset-left/)});
test('04 strict CSP denies connect and forms',()=>assert.match(html,/connect-src 'none'; object-src 'none'/));
test('05 no forbidden network or persistent storage in JS',()=>assert.doesNotMatch(js,/(?:\bfetch\s*\(|XMLHttpRequest|localStorage|indexedDB|WebSocket|navigator\.sendBeacon)/));
test('06 page includes price / UTC / note fields',()=>{for(const id of ['price','observed','note'])assert.ok(attr('id="'+id+'"'))});
test('07 readonly original ID',()=>assert.match(html,/id="sourceId"[^>]*readonly/));
test('08 status live region',()=>assert.match(html,/id="feedback" role="status" aria-live="polite"/));
test('09 responsive single column on mobile',()=>assert.match(css,/@media\(max-width:780px\)/));
test('10 respects reduced motion',()=>assert.match(css,/prefers-reduced-motion:reduce/));
test('11 valid preview does not send data',()=>{const x=mount();x.form.elements.price.value='1,23450';x.form.elements.observed.value='2026-11-21T07:00:00Z';assert.equal(x.submit(),true);assert.match(x.text('#state'),/PENDING/);assert.equal(x.text('#proposed'),'1,23450');assert.equal(x.pending(),true);});
test('12 invalid price rejects',()=>{const x=mount();x.form.elements.price.value='4e3';x.form.elements.observed.value='2026-11-21T07:00:00Z';x.submit();assert.match(x.text('#state'),/NON VALIDI/);});
test('13 negative prices reject',()=>{const x=mount();x.form.elements.price.value='-1';x.form.elements.observed.value='2026-11-21T07:00:00Z';x.submit();assert.equal(x.pending(),false);});
test('14 future UTC rejected',()=>{const x=mount();x.form.elements.price.value='1.20';x.form.elements.observed.value='2035-11-21T07:00:00Z';x.submit();assert.equal(x.pending(),false);});
test('15 invalid UTC rejected',()=>{const x=mount();x.form.elements.price.value='1.20';x.form.elements.observed.value='2026-11-21 07:00';x.submit();assert.equal(x.pending(),false);});
test('16 note control char rejected',()=>{const x=mount();x.form.elements.price.value='1.2';x.form.elements.observed.value='2026-11-21T07:00:00Z';x.form.elements.note.value='a\nb';x.submit();assert.equal(x.pending(),false);});
test('17 reset clears simulated approval state',()=>{const x=mount();x.form.elements.price.value='1.2';x.form.elements.observed.value='2026-11-21T07:00:00Z';x.submit();x.reset();assert.equal(x.pending(),false);assert.equal(x.text('#proposed'),'—');});
test('18 page explicitly warns that no live data is sent',()=>{assert.match(html,/nessun invio/i);assert.match(html,/non collegata a servizi/i)});
