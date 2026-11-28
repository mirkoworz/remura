// Offline test candidate; Node >=22, no network.
import assert from 'node:assert/strict';
import test from 'node:test';
import {randomUUID} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {createFixtureV110} from '../fixture_v110_lab.mjs';
import worker from './worker-v3019-lab.mjs';
import legacy from '../release/remura-contributors-v3018-worker.mjs';
async function fixture(t){
 const f=await createFixtureV110({write:false});
 t.after(()=>f.db.close());
 const adapter={
  withSession(mode){assert.equal(mode,'first-primary');return adapter;},
  prepare(sql){
   return {bind(...v){
    return {async all(){
     const stmt=f.db.prepare(sql);
     const nums=[...sql.matchAll(/\?(\d+)/g)].map(x=>Number(x[1]));
     const args=Object.fromEntries([...new Set(nums)].map(i=>['?'+i,v[i-1]]));
     return {success:true,meta:{served_by_primary:true},results:nums.length?stmt.all(args):stmt.all(...v)};
    }};
   }};
  }
 };
 f.env.CONTRIBUTORS_DB=adapter;
 const apply=async p=>f.db.exec(await readFile(new URL(p,import.meta.url),'utf8'));
 await apply('../telegram-outbox-v3012.sql');await apply('../telegram-publication-v3014.sql');
 await apply('../continuous-catalog-v3018-inactive.sql');
 f.db.exec("UPDATE lab_level_catalog_v110 SET active=1 WHERE contract='CONTINUOUS'");
 f.db.exec("INSERT INTO lab_telegram_sources_v3012 SELECT market,provider,ticker,product,contract FROM lab_level_catalog_v110 WHERE ticker='NQ_CONT' AND provider='RITHMIC'");
 const migration=async()=>{f.db.exec('BEGIN IMMEDIATE');try{for(const p of ['./proposal-preflight.sql','./proposal-schema.sql','./proposal-approval.sql'])await apply(p);f.db.exec('COMMIT');}catch(e){if(f.db.isTransaction)f.db.exec('ROLLBACK');throw e;}};
 f.flags({write:true});await assert.rejects(migration);f.flags({write:false});await migration();f.flags({write:true});
 f.env.REMURA_V3019_LAB_MODE='SYNTHETIC_ONLY';f.env.REMURA_V3019_TRANSPORT='SYNTHETIC_TRANSPORT_ONLY';
 const request=async(role,path,{method='GET',body,headers={},token=role?f.issueToken(role):''}={})=>{
  const jobs=[],ctx={...f.accessContext(token),waitUntil:p=>jobs.push(p)};
  const r=await worker.fetch(new Request(f.env.STAGING_ORIGIN+path,{method,headers,body:body===undefined?undefined:JSON.stringify(body)}),f.env,ctx);
  await Promise.all(jobs);return r;
 };
 const issue=(role,path,body)=>request(role,'/api/intent',{method:'POST',headers:f.postHeaders,body:{path,body}});
 const action=async(role,path,body)=>{const proof=await issue(role,path,body);if(!proof.ok)return proof;const {intent}=await proof.json();return request(role,path,{method:'POST',headers:{...f.postHeaders,'X-Remura-Intent':intent},body});};
 for(const slot of ['friend-b','friend-c']){
  assert.equal((await action('owner','/owner/invite',{slot,email:f.identity(slot).email})).status,200);
  assert.equal((await action(slot,'/api/enroll',{})).status,200);
 }
 const payload=(extra={})=>({request_id:randomUUID(),mapping_id:'FUTURES_NQ_RITHMIC',kind:'CVD_DIVERGENCE',period:'DAY',prices:'12,5\n13\n12.50',note:'',...extra});
 const get=async(role,path,opts)=>{const r=await request(role,path,opts);assert.equal(r.status,200,path);return r.json();};
 const mutate=async(role,path,body)=>{const r=await action(role,path,body);assert.equal(r.status,200,path);return r.json();};
 return {...f,request,issue,action,payload,get,mutate};
}
test('full historical migration and new authenticated proposal flow',async t=>{
 const f=await fixture(t),submit='/api/proposals/submit',mode='/owner/approval/mode',review='/owner/proposals/review';
 const toggle=async enabled=>{const p=await f.get('owner','/owner/telegram/status');return f.mutate('owner','/owner/telegram/toggle',{enabled,epoch:p.epoch});};
 const setMode=async m=>{const p=await f.get('owner','/owner/approval/status');return f.mutate('owner',mode,{mode:m,revision:p.revision});};
 const status=(role,p)=>f.get(role,'/api/proposals/status',{headers:{'X-Remura-Request-ID':p.request_id}});
 assert.equal((await f.request(null,'/api/proposals')).status,403);
 assert.equal((await f.request('friend-a','/owner/proposals')).status,403);
 assert.equal((await f.issue('friend-b',mode,{mode:'MANUAL',revision:1})).status,403);
 assert.equal((await f.issue('friend-b','/api/submit',f.payload())).status,403);
 assert.equal((await f.get('friend-b','/api/proposals/catalog')).items.length,24);
 assert.equal((await f.get('owner','/owner/approval/status')).mode,'AUTOMATIC');
 const a=f.payload();let r=await f.mutate('friend-b',submit,a);assert.deepEqual(r.prices,['12.5','13']);assert.equal(r.decision,'APPROVED');assert.equal(r.telegram_state,'NOT_QUEUED');
 assert.equal((await status('friend-c',a)).state,'NOT_FOUND');
 await toggle(true);assert.equal((await status('friend-b',a)).telegram_state,'NOT_QUEUED');
 const b=f.payload();const pair=await Promise.all([f.mutate('friend-b',submit,b),f.mutate('friend-b',submit,b)]);assert.equal(pair[0].id,pair[1].id);assert.equal((await status('friend-b',b)).telegram_state,'SENT');
 assert.equal((await f.mutate('friend-a',submit,f.payload())).publication_mode,'TEST');
 await setMode('MANUAL');const c=f.payload();r=await f.mutate('friend-b',submit,c);assert.equal(r.decision,'PENDING');assert.equal(r.telegram_state,'NOT_QUEUED');
 await setMode('AUTOMATIC');assert.equal((await status('friend-b',c)).decision,'PENDING');
 const decision={id:r.id,action:'APPROVED',reason:'review'};
 const reviewed=await Promise.all([f.action('owner',review,decision),f.action('owner',review,decision)]);assert.deepEqual(reviewed.map(x=>x.status).sort(),[200,409]);
 assert.equal((await status('friend-b',c)).telegram_state,'SENT');
 await setMode('MANUAL');const d=f.payload();r=await f.mutate('friend-b',submit,d);await toggle(false);await toggle(true);
 await f.mutate('owner',review,{id:r.id,action:'APPROVED',reason:'review'});assert.equal((await status('friend-b',d)).telegram_state,'NOT_QUEUED');
 const e=f.payload();r=await f.mutate('friend-b',submit,e);await f.mutate('owner',review,{id:r.id,action:'REJECTED',reason:'review'});assert.equal((await status('friend-b',e)).telegram_state,'NOT_QUEUED');
 assert.ok((await f.get('owner','/owner/approval/audit')).items.length>=5);
 for(const path of ['/contributors/levels/','/contributors/levels/proposal-form.mjs','/contributors/legacy/'])assert.equal((await f.request('friend-b',path)).status,200);
 assert.equal((await f.request('owner','/owner/levels/')).status,200);
 f.flags({write:false});assert.equal((await f.issue('friend-b',submit,f.payload())).status,403);
 const old=await legacy.fetch(new Request(f.env.STAGING_ORIGIN+'/contributors/levels/'),f.env,f.accessContext(f.issueToken('friend-b')));assert.equal(old.status,200);
});
