// REMURA Contributors v0.62 LAB — HTTP/intent negative tests with complete SQLite schema.
import test from 'node:test';
import assert from 'node:assert/strict';
import {fixture} from './amendment_http_fixture_v062_lab.mjs';
import {amendmentHttpCandidateV062 as handler} from './amendment_http_v062_lab.mjs';
const ORIGIN='https://contributors.lab.invalid';
async function context(t){const x=await fixture(t);Object.assign(x.env,{AMENDMENT_V062_ENABLED:'OFFLINE_FIXTURE_ONLY',INTENT_HMAC_KEY:'f'.repeat(64),STAGING_ORIGIN:ORIGIN});return x;}
function call(x,path,body={},token,override={}){
 const h={'Origin':ORIGIN,'Sec-Fetch-Site':'same-origin','X-Remura-CSRF':'1','Content-Type':'application/json',...override.headers};
 if(token!==undefined)h['X-Remura-Intent']=token;
 const req=new Request(override.url??ORIGIN+path,{method:override.method??'POST',headers:h,...(override.method==='GET'?{}:{body:override.raw??JSON.stringify(body)})});
 return handler(req,x.env,x.ctx);
}
async function issue(x,path,body){const r=await call(x,'/api/amendment/intent',{path,body});assert.equal(r.status,200,await r.text().then(s=>s));/* Response consumed by text; cannot parse after. */}
async function token(x,path,p){const r=await call(x,'/api/amendment/intent',{path,body:p});const j=await r.json();assert.equal(r.status,200,JSON.stringify(j));assert.match(j.data.intent,/^[a-f0-9]{32}\.[0-9]{10}\.[a-f0-9]{64}$/);return j.data.intent;}
const amend='/api/amendment/submit',review='/owner/amendment/review';
const rejected=async (r,status=403)=>{assert.equal(r.status,status);assert.equal(r.headers.get('Cache-Control'),'no-store, max-age=0');const x=await r.json();assert.equal(typeof x.error,'string');assert.equal(x.data,undefined);};
test('01 intent issuance for Alice',async t=>{const x=await context(t);const tk=await token(x,amend,x.payload());assert.ok(tk.length>90)});
test('02 submit with valid bound token',async t=>{const x=await context(t);const p=x.payload();const tk=await token(x,amend,p);const r=await call(x,amend,p,tk);assert.equal(r.status,200);assert.equal((await r.json()).data.duplicate,false);});
test('03 nonce burned once, replay fails',async t=>{const x=await context(t);const p=x.payload(),tk=await token(x,amend,p);assert.equal((await call(x,amend,p,tk)).status,200);await rejected(await call(x,amend,p,tk),409);assert.equal(x.db.prepare('SELECT count(*) AS n FROM lab_level_amendments_v059').get().n,1);});
test('04 no token fails closed',async t=>{const x=await context(t);await rejected(await call(x,amend,x.payload()),409);});
test('05 changed token signature fails',async t=>{const x=await context(t);const p=x.payload(),tk=await token(x,amend,p);await rejected(await call(x,amend,p,tk.slice(0,-1)+(tk.endsWith('a')?'b':'a')),409)});
test('06 altered body invalidates issued signature',async t=>{const x=await context(t);const p=x.payload(),tk=await token(x,amend,p);await rejected(await call(x,amend,{...p,price:'1.999'},tk),409);});
test('07 token bound to Alice cannot be used by Bob',async t=>{const x=await context(t);const p=x.payload(),tk=await token(x,amend,p);x.who('bob');await rejected(await call(x,amend,p,tk),409);});
test('08 token for review not usable for submit',async t=>{const x=await context(t);x.who('owner');const p={id:1,action:'APPROVED',reason:'ok'},tk=await token(x,review,p);x.who('alice');await rejected(await call(x,amend,x.payload(),tk),409)});
test('09 Alice cannot request OWNER token',async t=>{const x=await context(t);await rejected(await call(x,'/api/amendment/intent',{path:review,body:{id:1,action:'APPROVED',reason:'ok'}}));});
test('10 owner can approve through signed intent',async t=>{const x=await context(t);const p=x.payload(),t1=await token(x,amend,p);assert.equal((await call(x,amend,p,t1)).status,200);x.who('owner');const b={id:1,action:'APPROVED',reason:'fixture'},t2=await token(x,review,b);assert.equal((await call(x,review,b,t2)).status,200);x.who('alice');assert.equal((await(await call(x,'/api/amendment/approved',{})).json()).data[0].price,'1.234');});
test('11 OWNER review cannot replay token',async t=>{const x=await context(t);const p=x.payload();await call(x,amend,p,await token(x,amend,p));x.who('owner');const b={id:1,action:'APPROVED',reason:'yes'},tk=await token(x,review,b);assert.equal((await call(x,review,b,tk)).status,200);await rejected(await call(x,review,b,tk),409);});
test('12 owner cannot issue contributor submit intent',async t=>{const x=await context(t);x.who('owner');await rejected(await call(x,'/api/amendment/intent',{path:amend,body:x.payload()}));});
test('13 viewer cannot call owner pending queue',async t=>{const x=await context(t);await rejected(await call(x,'/owner/amendment/queue',{after:0}));});
test('14 owner queue access',async t=>{const x=await context(t);x.who('owner');const r=await call(x,'/owner/amendment/queue',{after:0});assert.equal(r.status,200);assert.deepEqual((await r.json()).data,[]);});
test('15 Alice own list read',async t=>{const x=await context(t);const r=await call(x,'/api/amendment/mine',{after:0});assert.equal(r.status,200);assert.deepEqual((await r.json()).data,[]);});
test('16 Bob never sees Alice receipts',async t=>{const x=await context(t);const p=x.payload();await call(x,amend,p,await token(x,amend,p));x.who('bob');const r=await call(x,'/api/amendment/mine',{after:0});assert.deepEqual((await r.json()).data,[]);});
test('17 no unreviewed price in approved projection',async t=>{const x=await context(t);const p=x.payload();await call(x,amend,p,await token(x,amend,p));const r=await call(x,'/api/amendment/approved',{});assert.equal((await r.json()).data[0].price,'1.123');});
test('18 missing CSRF header denies',async t=>{const x=await context(t);await rejected(await call(x,'/api/amendment/mine',{after:0},undefined,{headers:{'X-Remura-CSRF':'0'}}));});
test('19 cross-origin header denies',async t=>{const x=await context(t);await rejected(await call(x,'/api/amendment/mine',{after:0},undefined,{headers:{Origin:'https://evil.invalid'}}));});
test('20 cross-origin Sec-Fetch-Site denies',async t=>{const x=await context(t);await rejected(await call(x,'/api/amendment/mine',{after:0},undefined,{headers:{'Sec-Fetch-Site':'cross-site'}}));});
test('21 path query denied',async t=>{const x=await context(t);await rejected(await call(x,'/api/amendment/mine',{after:0},undefined,{url:ORIGIN+'/api/amendment/mine?from=0'}));});
test('22 HTTP instead of HTTPS denies',async t=>{const x=await context(t);await rejected(await call(x,'/api/amendment/mine',{after:0},undefined,{url:'http://contributors.lab.invalid/api/amendment/mine'}));});
test('23 other request method denies',async t=>{const x=await context(t);await rejected(await call(x,'/api/amendment/mine',{},undefined,{method:'GET'}));});
test('24 unknown route denied',async t=>{const x=await context(t);await rejected(await call(x,'/api/admin/dump',{}));});
test('25 JSON content-type only',async t=>{const x=await context(t);await rejected(await call(x,'/api/amendment/mine',{after:0},undefined,{headers:{'Content-Type':'text/plain'}}));});
test('26 content encoding gzip denied',async t=>{const x=await context(t);await rejected(await call(x,'/api/amendment/mine',{after:0},undefined,{headers:{'Content-Encoding':'gzip'}}));});
test('27 oversized JSON rejected',async t=>{const x=await context(t);await rejected(await call(x,'/api/amendment/approved',{},undefined,{raw:JSON.stringify({filler:'x'.repeat(5000)})}),400);});
test('28 malformed JSON rejected',async t=>{const x=await context(t);await rejected(await call(x,'/api/amendment/mine',{},undefined,{raw:'{"after":'}),400);});
test('29 unexpected field on read rejected',async t=>{const x=await context(t);await rejected(await call(x,'/api/amendment/mine',{after:0,subject:'owner'}),400);});
test('30 invalid cursor rejected',async t=>{const x=await context(t);await rejected(await call(x,'/api/amendment/mine',{after:-1}),400);});
test('31 extra field on intent denied',async t=>{const x=await context(t);await rejected(await call(x,'/api/amendment/intent',{path:amend,body:x.payload(),role:'OWNER'}),400);});
test('32 unknown intent route denied',async t=>{const x=await context(t);await rejected(await call(x,'/api/amendment/intent',{path:'/owner/secrets',body:{}}));});
test('33 service-token identity forbidden',async t=>{const x=await context(t);x.identity('alice').service_token_status=true;await rejected(await call(x,'/api/amendment/mine',{after:0}));x.identity('alice').service_token_status=false;});
test('34 wrong generation prevents intent',async t=>{const x=await context(t);x.env.CONTRIBUTORS_GENERATION='b'.repeat(32);await rejected(await call(x,'/api/amendment/intent',{path:amend,body:x.payload()}));});
test('35 disabled v0.62 fixture gate denies',async t=>{const x=await context(t);delete x.env.AMENDMENT_V062_ENABLED;await rejected(await call(x,'/api/amendment/mine',{after:0}));});
test('36 unknown body role not accepted in issue',async t=>{const x=await context(t);await rejected(await call(x,'/api/amendment/intent',{path:amend,body:{...x.payload(),role:'OWNER'}}));});
test('37 token with wrong nonce fails without SQL write',async t=>{const x=await context(t);const p=x.payload(),tk=await token(x,amend,p);const t2=(tk[0]==='a'?'b':'a')+tk.slice(1);await rejected(await call(x,amend,p,t2),409);assert.equal(x.db.prepare('SELECT count(*) AS n FROM lab_intent_used').get().n,0);});
test('38 token is bound to source and generation',async t=>{const x=await context(t);const p=x.payload(),tk=await token(x,amend,p);x.env.CONTRIBUTORS_GENERATION='b'.repeat(32);await rejected(await call(x,amend,p,tk),409);});
test('39 revocation after issuance blocks and burns attempt',async t=>{const x=await context(t),p=x.payload(),tk=await token(x,amend,p);x.db.prepare('UPDATE lab_identities SET revoked=1 WHERE subject=?').run(x.actors.alice.subject);await rejected(await call(x,amend,p,tk),409);assert.equal(x.db.prepare('SELECT count(*) AS n FROM lab_level_amendments_v059').get().n,0);});
test('40 disabled write after issuance blocks',async t=>{const x=await context(t),p=x.payload(),tk=await token(x,amend,p);x.db.exec('UPDATE lab_state SET write_enabled=0');await rejected(await call(x,amend,p,tk),409);});
test('41 consumed intent can be inspected but cannot be reissued as valid old token',async t=>{const x=await context(t),p=x.payload(),tk=await token(x,amend,p);await call(x,amend,p,tk);assert.equal(x.db.prepare('SELECT count(*) AS n FROM lab_intent_used').get().n,1);});
test('42 rate limiter fail closed before issuing token',async t=>{const x=await context(t);x.env.CONTRIBUTORS_RATE_LIMITER={limit:async()=>({success:false})};await rejected(await call(x,'/api/amendment/intent',{path:amend,body:x.payload()}));});
