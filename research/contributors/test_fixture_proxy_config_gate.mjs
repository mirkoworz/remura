// REMURA Contributors v0.52 LAB — offline only
import {fixtureConfigGate} from './fixture_proxy_config_gate.mjs';
const evidence={"account_id":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","fixture_uuid":"00000000-0000-0000-0000-000000000002","lab_uuid":"00000000-0000-0000-0000-000000000001"};
const cfg={"name":"remura-contributors-fixture-proxy","account_id":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","compatibility_date":"2026-11-15","workers_dev":false,"preview_urls":false,"routes":[],"d1_databases":[{"binding":"CONTRIBUTORS_FIXTURE_DB","database_name":"remura-contributors-fixture","database_id":"00000000-0000-0000-0000-000000000002","remote":true}]};
function testCases(gate,cfg,evidence){
 const assert=ok=>{if(!ok)throw Error("assertion_failed");};
 const out=gate(cfg,evidence);assert(out.status==="STATIC_FIXTURE_CONFIG_MATCH"&&out.binding_count===1&&out.cloudflare_identity_attested===false&&out.provider_called===false&&out.authorization_granted===false);
 let count=1;
 const rejected=(c,e=evidence)=>{let denied=false;try{gate(c,e);}catch(err){denied=err.message==="fixture_config_denied";}assert(denied);count++;};
 const b=cfg.d1_databases[0];
 for(const patch of [{workers_dev:true},{preview_urls:true},{routes:["example.invalid/*"]},{account_id:"b".repeat(32)},{name:"remura-contributors-staging"},{env:{}},{kv_namespaces:[]},{vars:{}},{main:"worker.js"},{d1_databases:[]},{d1_databases:[b,b]}])rejected({...cfg,...patch});
 for(const patch of [{database_name:"remura-contributors-lab"},{database_id:evidence.lab_uuid},{database_id:"00000000-0000-0000-0000-000000000003"},{binding:"CONTRIBUTORS_DB"},{remote:false},{remote:"true"},{preview_database_id:evidence.lab_uuid}])rejected({...cfg,d1_databases:[{...b,...patch}]});
 for(const e of [{...evidence,lab_uuid:evidence.fixture_uuid},{...evidence,fixture_uuid:"invalid"},{...evidence,account_id:"invalid"},{...evidence,unverified:true},null])rejected(cfg,e);
 return count;
}
console.log('REMURA fixture config offline cases: '+testCases(fixtureConfigGate,cfg,evidence)+' PASS');
