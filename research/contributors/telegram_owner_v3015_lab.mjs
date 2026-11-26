// REMURA V30.15 LAB. OWNER-only Telegram policy, no credentials in responses.
const ownerRead=`EXISTS(SELECT 1 FROM lab_owner i CROSS JOIN lab_state s
 WHERE i.id=1 AND i.subject=?1 AND i.email_tag=?2 AND i.revoked=0
 AND s.id=1 AND s.read_enabled=1)`;
const ownerWrite=`EXISTS(SELECT 1 FROM lab_owner i CROSS JOIN lab_state s
 WHERE i.id=1 AND i.subject=?1 AND i.email_tag=?2 AND i.revoked=0
 AND s.id=1 AND s.read_enabled=1 AND s.write_enabled=1 AND s.recovery_enabled=0)`;
export const TELEGRAM_OWNER_SQL=Object.freeze({
 read:`SELECT enabled,epoch,start_after_receipt FROM lab_telegram_policy_v3012 WHERE id=1 AND ${ownerRead}`,
 change:`UPDATE lab_telegram_policy_v3012
 SET enabled=?3,epoch=epoch+CASE WHEN ?3=1 THEN 1 ELSE 0 END,
 start_after_receipt=CASE WHEN ?3=1 THEN (SELECT COALESCE(MAX(id),0) FROM lab_level_attempts_v110) ELSE start_after_receipt END
 WHERE id=1 AND enabled=1-?3 AND epoch=?4 AND ${ownerWrite}
 AND (?3=0 OR EXISTS(SELECT 1 FROM lab_telegram_sources_v3012 m JOIN lab_level_catalog_v110 c
 USING(market,provider,ticker,product,contract) WHERE c.active=1))
 RETURNING enabled,epoch,start_after_receipt`
});
async function query(db,sql,actor,extra=[]){
 if(!/^[a-f0-9]{64}$/.test(actor?.subject??'')||!/^[a-f0-9]{64}$/.test(actor?.email_tag??''))throw Error('telegram_denied');
 const r=await db.withSession('first-primary').prepare(sql).bind(actor.subject,actor.email_tag,...extra).all();
 if(r?.success!==true||r.meta?.served_by_primary!==true||!Array.isArray(r.results)||r.results.length>1)throw Error('telegram_unavailable');
 const row=r.results[0];
 if(!row)return null;
 if(![0,1].includes(row.enabled)||!Number.isSafeInteger(row.epoch)||row.epoch<1||
 !Number.isSafeInteger(row.start_after_receipt)||row.start_after_receipt<0)throw Error('telegram_unavailable');
 return row;
}
export function readTelegramPolicy(db,actor){return query(db,TELEGRAM_OWNER_SQL.read,actor);}
export function changeTelegramPolicy(db,actor,body){
 if(typeof body?.enabled!=='boolean'||!Number.isSafeInteger(body.epoch)||body.epoch<1)throw Error('telegram_invalid');
 return query(db,TELEGRAM_OWNER_SQL.change,actor,[Number(body.enabled),body.epoch]);
}
