// REMURA Contributors v0.52 LAB — 20/11/2026 CET
// Pure config comparison only. No Wrangler import, credentials, network, deployment or proof of provider identity.
// Evidence must be independently verified privately by owner before any authorized remote session.
function fixtureConfigGate(cfg,evidence){
 const need=ok=>{if(!ok)throw Error("fixture_config_denied");};
 const exact=(obj,keys)=>obj!==null&&typeof obj==="object"&&!Array.isArray(obj)&&Object.getPrototypeOf(obj)===Object.prototype&&Object.keys(obj).sort().join("|")===keys.slice().sort().join("|");
 const uuid=x=>typeof x==="string"&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(x);
 need(exact(evidence,["account_id","fixture_uuid","lab_uuid"]));
 need(typeof evidence.account_id==="string"&&/^[0-9a-f]{32}$/.test(evidence.account_id)&&uuid(evidence.fixture_uuid)&&uuid(evidence.lab_uuid)&&evidence.fixture_uuid!==evidence.lab_uuid);
 need(exact(cfg,["name","account_id","compatibility_date","workers_dev","preview_urls","routes","d1_databases"]));
 need(cfg.name==="remura-contributors-fixture-proxy"&&cfg.account_id===evidence.account_id&&cfg.compatibility_date==="2026-11-15"&&cfg.workers_dev===false&&cfg.preview_urls===false&&Array.isArray(cfg.routes)&&cfg.routes.length===0);
 need(Array.isArray(cfg.d1_databases)&&cfg.d1_databases.length===1);
 const b=cfg.d1_databases[0];
 need(exact(b,["binding","database_name","database_id","remote"]));
 need(b.binding==="CONTRIBUTORS_FIXTURE_DB"&&b.database_name==="remura-contributors-fixture"&&b.database_id===evidence.fixture_uuid&&b.database_id!==evidence.lab_uuid&&b.remote===true);
 return Object.freeze({status:"STATIC_FIXTURE_CONFIG_MATCH",binding_count:1,cloudflare_identity_attested:false,provider_called:false,authorization_granted:false});
}
export {fixtureConfigGate};
