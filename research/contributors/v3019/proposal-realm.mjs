// V30.19 realm verification. No external service.
export async function isReleaseRealm(db){
 if(typeof db?.withSession!=="function")return false;
 try{
  const r=await db.withSession("first-primary").prepare("SELECT realm FROM lab_delivery_realm_v3019 WHERE id=1").bind().all();
  return r?.success===true&&r.meta?.served_by_primary===true&&Array.isArray(r.results)&&r.results.length===1&&r.results[0].realm==="STAGING_CANDIDATE";
 }catch{return false;}
}
export async function isSyntheticRealm(db){
 if(typeof db?.withSession!=="function")return false;
 try{
  const r=await db.withSession("first-primary").prepare("SELECT name FROM sqlite_schema WHERE name='lab_delivery_realm_v3019'").bind().all();
  return r?.success===true&&r.meta?.served_by_primary===true&&Array.isArray(r.results)&&r.results.length===0;
 }catch{return false;}
}
