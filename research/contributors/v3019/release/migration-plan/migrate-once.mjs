// V30.19.1 — DRAFT only; run only in the reviewed, separately authorized environment.
import {createHash} from 'node:crypto';
import {readFileSync,writeFileSync,mkdtempSync,mkdirSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {spawnSync} from 'node:child_process';
const stop=(why)=>{throw Error(why)};
const req=(v,ok,why)=>{if(!ok(v))stop(why);return v};
const account=req(process.env.CLOUDFLARE_ACCOUNT_ID,x=>/^[a-f0-9]{32}$/.test(x??''),'account_id');
const db=req(process.env.REMURA_D1_DATABASE_ID,x=>/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/.test(x??''),'database_id');
const token=req(process.env.CLOUDFLARE_API_TOKEN,x=>typeof x==='string'&&x.length>=20,'token_missing');
const bookmark=req(process.env.REMURA_FINAL_BOOKMARK,x=>typeof x==='string'&&x.length>=16&&x.length<=300&&!/\s/.test(x),'final_bookmark_missing');
req(process.env.REMURA_MIGRATION_CONFIRM,x=>x==='APPLY_V30191_D1_ONLY','approval_missing');
req(process.env.GITHUB_RUN_ATTEMPT,x=>x==='1','no_retry');
req(process.env.REMURA_FREE_GATE,x=>x==='FREE_VERIFIED_BELOW_80_PERCENT','quota_confirmation_missing');
const sql=readFileSync('research/contributors/v3019/proposal-release-migration.sql');
const hash=createHash('sha1').update('blob '+sql.length+'\0').update(sql).digest('hex');
if(hash!=='9d60a56fbb2bb111048c80bd4a8438f79ac9c0e8')stop('migration_digest');
const url='https://api.cloudflare.com/client/v4/accounts/'+account+'/d1/database/'+db;
async function api(suffix='',body){
 let r;
 try{r=await fetch(url+suffix,{method:body?'POST':'GET',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined,redirect:'error',signal:AbortSignal.timeout(20000)});}catch{stop('api_transport_uncertain');}
 let data;try{data=await r.json()}catch{stop('api_response_invalid')}
 if(!r.ok||data.success!==true)stop('api_rejected');
 return data.result;
}
async function row(sql){
 const r=await api('/query',{sql});
 if(!Array.isArray(r)||r.length!==1||r[0].success!==true||r[0].results?.length!==1)stop('query_shape');
 return r[0].results[0];
}
const pre="SELECT (SELECT COUNT(*) FROM lab_state) AS flags,(SELECT read_enabled FROM lab_state WHERE id=1) AS rd,(SELECT write_enabled FROM lab_state WHERE id=1) AS wr,(SELECT recovery_enabled FROM lab_state WHERE id=1) AS rec,(SELECT COUNT(*) FROM lab_telegram_policy_v3012) AS policy_rows,(SELECT enabled FROM lab_telegram_policy_v3012 WHERE id=1) AS tg,(SELECT COUNT(*) FROM lab_telegram_outbox_v3012 WHERE state IN('PENDING','SENDING','UNKNOWN')) AS queued,(SELECT COUNT(*) FROM sqlite_schema WHERE name LIKE '%v3019') AS new_objects,(SELECT COUNT(*) FROM pragma_table_info('lab_level_attempts_v110') WHERE name='publication_mode') AS publication,(SELECT COUNT(*) FROM lab_telegram_sources_v3012) AS allowlist";
const expected={flags:1,rd:1,wr:0,rec:0,policy_rows:1,tg:0,queued:0,new_objects:0,publication:1,allowlist:0};
function expect(r,e){for(const [k,v] of Object.entries(e))if(r[k]!==v)stop('pre_or_post_condition_'+k)}
const dir=mkdtempSync(join(tmpdir(),'remura-v30191-'));
try{
 const meta=await api();
 if(meta?.uuid!==db||meta?.name!=='remura-contributors-staging')stop('target_database_mismatch');
 expect(await row(pre),expected);
 // No other migration file is copied, no project config or deploy command.
 mkdirSync(join(dir,'migrations'));
 writeFileSync(join(dir,'migrations','30191_remura_contributors.sql'),sql,{mode:0o600});
 writeFileSync(join(dir,'wrangler.json'),JSON.stringify({name:'remura-contributors-migration-only',account_id:account,compatibility_date:'2026-11-28',d1_databases:[{binding:'CONTRIBUTORS_DB',database_name:'remura-contributors-staging',database_id:db,migrations_dir:'migrations'}]}),{mode:0o600});
 const cli=resolve('research/contributors/v3019/release/migration-plan/node_modules/.bin/wrangler');
 const env={PATH:process.env.PATH,HOME:process.env.HOME,CI:'true',CLOUDFLARE_ACCOUNT_ID:account,CLOUDFLARE_API_TOKEN:token,WRANGLER_SEND_METRICS:'false',WRANGLER_LOG:'error'};
 // Explicit single attempt. Suppress raw responses (may contain private metadata).
 const result=spawnSync(cli,['d1','migrations','apply','CONTRIBUTORS_DB','--remote','--config',join(dir,'wrangler.json')],{cwd:dir,env,encoding:'utf8',timeout:120000,maxBuffer:1024*1024});
 if(result.error||result.status!==0)stop('migration_outcome_uncertain_stop_no_retry');
 const after=await row(pre);
 const {new_objects,...unchanged}=expected;expect(after,unchanged);
 const verify=await row("SELECT (SELECT COUNT(*) FROM sqlite_schema WHERE type='table' AND name IN('lab_proposals_v3019','lab_proposal_outbox_v3019','lab_approval_policy_v3019','lab_proposal_admission_v3019','lab_proposal_decision_v3019','lab_policy_audit_v3019','lab_delivery_realm_v3019')) AS tables,(SELECT realm FROM lab_delivery_realm_v3019 WHERE id=1) AS realm,(SELECT mode FROM lab_approval_policy_v3019 WHERE id=1) AS mode,(SELECT COUNT(*) FROM lab_proposals_v3019) AS proposals,(SELECT COUNT(*) FROM lab_proposal_outbox_v3019) AS outbox");
 expect(verify,{tables:7,realm:'STAGING_CANDIDATE',mode:'AUTOMATIC',proposals:0,outbox:0});
 console.log('REMURA_V30191_D1_MIGRATION=PASS; WRITE=OFF; TELEGRAM=OFF');
}catch(e){console.error('REMURA_STOP: '+(e instanceof Error&&/^[a-z0-9_]+$/.test(e.message)?e.message:'unexpected_error_no_retry'));process.exitCode=1;}
finally{rmSync(dir,{recursive:true,force:true});}
