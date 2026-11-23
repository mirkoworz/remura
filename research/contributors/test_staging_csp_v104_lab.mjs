// REMURA Contributors v1.04 LAB — only newly added no-script/no-connect safeguards.
// Synthetic authorized responses; no Access sessions, D1 queries, Secrets or network.
import test from 'node:test';
import assert from 'node:assert/strict';
import {createStagingCspV104,V104_READONLY} from './private_worker_staging_csp_v104_lab.mjs';
import {V102_ENTRY} from './staging_readonly_entry_v102_lab.mjs';
const ORIGIN='https://v104-fixture.invalid';
const pages=['/contributors/','/contributors/levels/','/owner/','/owner/levels/'];
const oldHtml='<!doctype html><html lang="it"><head>'+
  '<title>REMURA Contributors v1.03 LAB · Consultazione</title></head>'+
  '<body><div>REMURA Contributors v1.03 LAB · 23/11/2026 23:05 CET (Europe/Rome)</div>'+
  '<main><p>SOLA LETTURA</p></main><footer>REMURA v1.03 LAB</footer></body></html>';
function harness(){
 const calls={delegated:0};
 let html=oldHtml, allowed=true;
 const guardedRead=async req=>{
   calls.delegated++;
   if(!allowed)return new Response('denied',{status:403});
   const p=new URL(req.url).pathname;
   return new Response(p.endsWith('.css')?'CSS_OK':html,{
     status:200,headers:{'Content-Type':p.endsWith('.css')?'text/css':'text/html',
       'Cache-Control':'no-store', 'Content-Security-Policy':"script-src 'self'; connect-src 'self'"}});
 };
 const app=createStagingCspV104({guardedRead});
 return {calls,setHtml:x=>{html=x;},deny:()=>{allowed=false;},
   send:(p,options={})=>app(new Request(ORIGIN+p,options),{},{} )};
}
test('01 all four private pages visibly stamped v1.04 and browser scripts/fetch disabled',async()=>{
 const h=harness();
 for(const p of pages){
   const response=await h.send(p);
   const html=await response.text(),csp=response.headers.get('content-security-policy');
   assert.equal(response.status,200);
   assert.match(html,/REMURA Contributors v1\.04 LAB · 24\/11\/2026 00:12 CET/);
   assert.ok(!html.includes('v1.03'),p);
   assert.match(csp,/script-src 'none'/);
   assert.match(csp,/connect-src 'none'/);
   assert.match(csp,/form-action 'none'/);
   assert.match(csp,/frame-ancestors 'none'/);
   assert.match(csp,/style-src 'self'/);
   assert.match(response.headers.get('cache-control'),/no-store/);
   assert.equal(response.headers.get('x-frame-options'),'DENY');
   assert.match(response.headers.get('x-robots-tag'),/noindex/);
 }
 assert.equal(h.calls.delegated,4);
});
test('02 upstream denied Access/D1 status is not replaced or hidden',async()=>{
 const h=harness();h.deny();
 const r=await h.send('/owner/');
 assert.equal(r.status,403);assert.equal(await r.text(),'denied');
 assert.equal(h.calls.delegated,1);
});
test('03 unexpected executable markup or missing stamp fails closed',async()=>{
 const h=harness();
 for(const html of [
   oldHtml+'<script src="/malicious.js"></script>',
   oldHtml.replace('SOLA LETTURA','<form><input></form>'),
   oldHtml.replace('23/11/2026 23:05 CET','sconosciuto'),
   oldHtml.replaceAll('REMURA Contributors v1.03 LAB','INTERFACE_NON_ATTESTATA')
 ]){
   h.setHtml(html);const r=await h.send('/owner/levels/');
   assert.equal(r.status,403);
 }
});
test('04 protected CSS passes through without pretending a writable API',async()=>{
 const h=harness();
 const res=await h.send('/contributors/levels/contributors_private_levels_v076_lab.css');
 assert.equal(res.status,200);
 assert.equal(await res.text(),'CSS_OK');
 assert.equal(h.calls.delegated,1);
});
test('05 non-GET methods fail before consulting any delegate',async()=>{
 const h=harness();
 for(const method of ['POST','PUT','PATCH','DELETE','OPTIONS']){
   const o={method,...(['POST','PUT','PATCH'].includes(method)?{body:'{}'}:{})};
   assert.equal((await h.send('/api/submit',o)).status,403);
 }
 assert.equal(h.calls.delegated,0);
 assert.equal(V104_READONLY.realPilotAllowed,false);
 assert.equal(V102_ENTRY.deployed,false);
 assert.equal(V104_READONLY.additionalD1Reads,0);
});
