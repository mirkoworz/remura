// REMURA Contributors v0.63 LAB — 21/11/2026 CET
// Real client -> simulated HTTP controller -> original D1 candidate schema (Node sqlite).
import test from 'node:test';
import assert from 'node:assert/strict';
import {fixture} from './amendment_http_fixture_v062_lab.mjs';
import {amendmentHttpCandidateV062 as serve} from './amendment_http_v062_lab.mjs';
import {AmendmentClientV063} from './amendment_client_v063_lab.mjs';
const ORIGIN='https://contributors.lab.invalid';
const SUBMIT='/api/amendment/submit', REVIEW='/owner/amendment/review';
const DENY=async p=>assert.rejects(p,/REMURA_REQUEST_NOT_CONFIRMED|.*/);
async function session(t){
 const x=await fixture(t);
 Object.assign(x.env,{AMENDMENT_V062_ENABLED:'OFFLINE_FIXTURE_ONLY',INTENT_HMAC_KEY:'f'.repeat(64),STAGING_ORIGIN:ORIGIN});
 const wire=[];const ctrl={};
 const transport=async(path,opts)=>{
  wire.push({path,opts});
  if(ctrl.failBefore?.(path))throw Error('synthetic network failure');
  const headers={...opts.headers,Origin:ORIGIN,'Sec-Fetch-Site':'same-origin'};
  const req=new Request(ORIGIN+path,{...opts,headers});
  const response=await serve(req,x.env,x.ctx);
  if(ctrl.failAfter?.(path))throw Error('lost response after server');
  if(ctrl.replaceResponse?.(path))return ctrl.replaceResponse(path,response);
  return response;
 };
 const client=new AmendmentClientV063(transport);
 return {...x,wire,ctrl,transport,client};
}
const reviewPayload=(id=1)=>({id,action:'APPROVED',reason:'approved in fixture'});
const getCount=(x,t)=>x.db.prepare('SELECT count(*) AS n FROM '+t).get().n;
const last=(x)=>x.wire.at(-1);

test('01 client confirms valid amendment only after two HTTP 200',async t=>{
 const x=await session(t);const out=await x.client.mutate(SUBMIT,x.payload());
 assert.equal(out.status,'UNREVIEWED');assert.equal(out.duplicate,false);assert.equal(x.wire.length,2);assert.equal(x.client.uncertain,false);
});
test('02 all requests are relative POST, same-origin, no-store and no redirects',async t=>{
 const x=await session(t);await x.client.mutate(SUBMIT,x.payload());
 assert.ok(x.wire.every(w=>w.path.startsWith('/')&&!w.path.startsWith('//')&&w.opts.method==='POST'&&w.opts.credentials==='same-origin'&&w.opts.mode==='same-origin'&&w.opts.redirect==='error'&&w.opts.cache==='no-store'));
});
test('03 token is sent only to mutation, not issue',async t=>{
 const x=await session(t);await x.client.mutate(SUBMIT,x.payload());
 assert.equal(x.wire[0].opts.headers['X-Remura-Intent'],undefined);
 assert.match(x.wire[1].opts.headers['X-Remura-Intent'],/^[a-f0-9]{32}\.[0-9]{10}\.[a-f0-9]{64}$/);
});
test('04 response success updates client state',async t=>{
 const x=await session(t);await x.client.mutate(SUBMIT,x.payload());assert.equal(x.client.uncertain,false);assert.equal(x.client.busy,false);
});
test('05 server cannot serve Alice with Bob entry',async t=>{
 const x=await session(t);await DENY(x.client.mutate(SUBMIT,x.payload(2)));assert.equal(x.client.uncertain,true);assert.equal(getCount(x,'lab_level_amendments_v059'),0);
});
test('06 owner cannot submit an amendment',async t=>{
 const x=await session(t);x.who('owner');await DENY(x.client.mutate(SUBMIT,x.payload()));assert.equal(x.client.uncertain,false);
});
test('07 Alice cannot review for owner',async t=>{
 const x=await session(t);await DENY(x.client.mutate(REVIEW,reviewPayload()));assert.equal(x.client.uncertain,false);
});
test('08 confirmed owner review changes approved projection only then',async t=>{
 const x=await session(t);await x.client.mutate(SUBMIT,x.payload());
 assert.equal((await x.client.read('/api/amendment/approved',{}))[0].price,'1.123');
 x.who('owner');const r=await x.client.mutate(REVIEW,reviewPayload());assert.equal(r.action,'APPROVED');
 x.who('alice');assert.equal((await x.client.read('/api/amendment/approved',{}))[0].price,'1.234');
});
test('09 Alice cannot read private OWNER review queue',async t=>{
 const x=await session(t);await DENY(x.client.read('/owner/amendment/queue',{after:0}));
});
test('10 Alice own receipts exclude Bob',async t=>{
 const x=await session(t);await x.client.mutate(SUBMIT,x.payload());
 assert.equal((await x.client.read('/api/amendment/mine',{after:0})).length,1);
 x.who('bob');assert.equal((await x.client.read('/api/amendment/mine',{after:0})).length,0);
});
test('11 lost response after commit leaves uncertainty and only one write',async t=>{
 const x=await session(t);x.ctrl.failAfter=p=>p===SUBMIT;
 await DENY(x.client.mutate(SUBMIT,x.payload()));
 assert.equal(x.client.uncertain,true);assert.equal(getCount(x,'lab_level_amendments_v059'),1);
 await DENY(x.client.mutate(SUBMIT,x.payload()));assert.equal(getCount(x,'lab_level_amendments_v059'),1);
});
test('12 server 409 after intent burn locks without retry',async t=>{
 const x=await session(t);const p=x.payload(2);await DENY(x.client.mutate(SUBMIT,p));
 assert.equal(x.client.uncertain,true);assert.equal(x.wire.filter(w=>w.path===SUBMIT).length,1);
});
test('13 client can READ while uncertain but cannot resume mutations',async t=>{
 const x=await session(t);x.ctrl.failAfter=p=>p===SUBMIT;
 await DENY(x.client.mutate(SUBMIT,x.payload()));
 const rows=await x.client.read('/api/amendment/mine',{after:0});assert.equal(rows.length,1);
 assert.equal(x.client.uncertain,true);
});
test('14 error before intent never enters unknown-commit state',async t=>{
 const x=await session(t);x.ctrl.failBefore=p=>p==='/api/amendment/intent';
 await DENY(x.client.mutate(SUBMIT,x.payload()));assert.equal(x.client.uncertain,false);
 assert.equal(x.wire.filter(w=>w.path===SUBMIT).length,0);
});
test('15 untrusted response missing no-store blocks confirmation',async t=>{
 const x=await session(t);x.ctrl.replaceResponse=p=>p===SUBMIT?new Response('{"data":{"id":1,"status":"UNREVIEWED","duplicate":false}}',{status:200,headers:{'Content-Type':'application/json'}}):null;
 await DENY(x.client.mutate(SUBMIT,x.payload()));assert.equal(x.client.uncertain,true);
});
test('16 forged confirmation id rejected',async t=>{
 const x=await session(t);x.ctrl.replaceResponse=p=>p===SUBMIT?new Response('{"data":{"id":-1,"status":"UNREVIEWED","duplicate":false}}',{status:200,headers:{'Content-Type':'application/json','Cache-Control':'no-store'}}):null;
 await DENY(x.client.mutate(SUBMIT,x.payload()));assert.equal(x.client.uncertain,true);
});
test('17 any malformed 200 after write remains uncertain',async t=>{
 const x=await session(t);x.ctrl.replaceResponse=p=>p===SUBMIT?new Response('not-json',{status:200,headers:{'Content-Type':'application/json','Cache-Control':'no-store'}}):null;
 await DENY(x.client.mutate(SUBMIT,x.payload()));assert.equal(x.client.uncertain,true);
});
test('18 redirected mutation response denied',async t=>{
 const x=await session(t);x.ctrl.replaceResponse=p=>p===SUBMIT?{status:200,redirected:true,headers:{get:()=> 'application/json'}}:null;
 await DENY(x.client.mutate(SUBMIT,x.payload()));assert.equal(x.client.uncertain,true);
});
test('19 issue missing token never dispatches mutation',async t=>{
 const x=await session(t);x.ctrl.replaceResponse=p=>p==='/api/amendment/intent'?new Response('{"data":{"intent":"bad","expires_unix":1}}',{status:200,headers:{'Content-Type':'application/json','Cache-Control':'no-store'}}):null;
 await DENY(x.client.mutate(SUBMIT,x.payload()));assert.equal(x.client.uncertain,false);assert.equal(x.wire.filter(w=>w.path===SUBMIT).length,0);
});
test('20 issue expired token never dispatches mutation',async t=>{
 const x=await session(t);x.ctrl.replaceResponse=p=>p==='/api/amendment/intent'?new Response(JSON.stringify({data:{intent:'a'.repeat(32)+'.1234567890.'+'b'.repeat(64),expires_unix:1}}),{status:200,headers:{'Content-Type':'application/json','Cache-Control':'no-store'}}):null;
 await DENY(x.client.mutate(SUBMIT,x.payload()));assert.equal(x.client.uncertain,false);
});
test('21 no automatic retry when HTTP fetch rejects before response',async t=>{
 const x=await session(t);x.ctrl.failBefore=p=>p===SUBMIT;await DENY(x.client.mutate(SUBMIT,x.payload()));
 assert.equal(x.wire.filter(w=>w.path===SUBMIT).length,1);assert.equal(x.client.uncertain,true);
});
test('22 current view invalidates between issuance and dispatch',async t=>{
 const x=await session(t);let alive=true;const original=x.transport;
 const client=new AmendmentClientV063(async(p,o)=>{const r=await original(p,o);if(p==='/api/amendment/intent')alive=false;return r;});
 await DENY(client.mutate(SUBMIT,x.payload(),{stillCurrent:()=>alive}));
 assert.equal(client.uncertain,false);assert.equal(x.wire.filter(w=>w.path===SUBMIT).length,0);
});
test('23 changing view after commit never confirms',async t=>{
 const x=await session(t);let alive=true;const client=new AmendmentClientV063(async(p,o)=>{const r=await x.transport(p,o);if(p===SUBMIT)alive=false;return r;});
 await DENY(client.mutate(SUBMIT,x.payload(),{stillCurrent:()=>alive}));assert.equal(client.uncertain,true);
});
test('24 busy flag blocks concurrent operations',async t=>{
 const x=await session(t);let unblock;const hold=new Promise(ok=>unblock=ok);
 const client=new AmendmentClientV063(async(p,o)=>{if(p==='/api/amendment/intent')await hold;return x.transport(p,o)});
 const p=client.mutate(SUBMIT,x.payload());assert.equal(client.busy,true);
 await DENY(client.mutate(SUBMIT,x.payload(1,8)));unblock();await p;assert.equal(client.busy,false);
});
test('25 unrelated arbitrary API routes cannot be accessed',async t=>{
 const x=await session(t);await DENY(x.client.read('/owner/secrets',{}));assert.equal(x.wire.length,0);
});
test('26 reads require strict empty or cursor payloads',async t=>{
 const x=await session(t);await DENY(x.client.read('/api/amendment/approved',{role:'OWNER'}));
 await DENY(x.client.read('/api/amendment/mine',{after:-1}));assert.equal(x.wire.length,0);
});
test('27 extra user-supplied subject rejected prior to intent',async t=>{
 const x=await session(t);await DENY(x.client.mutate(SUBMIT,{...x.payload(),subject:'owner'}));assert.equal(x.wire.length,0);
});
test('28 malformed request_id rejected prior to network',async t=>{
 const x=await session(t);await DENY(x.client.mutate(SUBMIT,{...x.payload(),request_id:'bad'}));assert.equal(x.wire.length,0);
});
test('29 scientific price rejected prior to network',async t=>{
 const x=await session(t);await DENY(x.client.mutate(SUBMIT,{...x.payload(),price:'1e5'}));assert.equal(x.wire.length,0);
});
test('30 future observation refused before token request',async t=>{
 const x=await session(t);await DENY(x.client.mutate(SUBMIT,{...x.payload(),observed_utc:'2099-01-01T00:00:00Z'}));assert.equal(x.wire.length,0);
});
test('31 malicious overlong note fails before network',async t=>{
 const x=await session(t);await DENY(x.client.mutate(SUBMIT,{...x.payload(),note:'z'.repeat(281)}));assert.equal(x.wire.length,0);
});
test('32 review body can only contain ID action and reason',async t=>{
 const x=await session(t);await DENY(x.client.mutate(REVIEW,{...reviewPayload(),role:'OWNER'}));assert.equal(x.wire.length,0);
});
test('33 empty review reason rejected before issuance',async t=>{
 const x=await session(t);await DENY(x.client.mutate(REVIEW,{...reviewPayload(),reason:'  '}));assert.equal(x.wire.length,0);
});
test('34 a second mutation after a confirmed first uses new token',async t=>{
 const x=await session(t);await x.client.mutate(SUBMIT,x.payload());await x.client.mutate(SUBMIT,x.payload(1,8));
 const tokens=x.wire.filter(w=>w.path===SUBMIT).map(w=>w.opts.headers['X-Remura-Intent']);assert.equal(new Set(tokens).size,2);
});
test('35 no implicit live fetcher allowed',()=>assert.throws(()=>new AmendmentClientV063()));
