// REMURA v0.8.115 LAB — 17/11/2026 CET
// Candidate D1 admission, separate binding, no provisioning or active Worker.
export const RESERVE_SQL = `UPDATE level_admission_v1 SET
 enabled=CASE WHEN last_ms IS NOT NULL AND ?2<last_ms THEN 0 ELSE enabled END,
 allowed=CASE WHEN last_ms IS NOT NULL AND ?2<last_ms THEN 0
   WHEN attempts>=48 THEN 0
   WHEN last_ms IS NULL OR CAST(last_ms/60000 AS INTEGER)<>CAST(?2/60000 AS INTEGER) THEN 1
   WHEN window_count<20 THEN 1 ELSE 0 END,
 window_count=CASE WHEN (last_ms IS NOT NULL AND ?2<last_ms) OR attempts>=48 THEN window_count
   WHEN last_ms IS NULL OR CAST(last_ms/60000 AS INTEGER)<>CAST(?2/60000 AS INTEGER) THEN 1
   WHEN window_count<20 THEN window_count+1 ELSE window_count END,
 attempts=CASE WHEN (last_ms IS NOT NULL AND ?2<last_ms) OR attempts>=48 THEN attempts ELSE attempts+1 END,
 last_ms=CASE WHEN (last_ms IS NOT NULL AND ?2<last_ms) OR attempts>=48 THEN last_ms ELSE ?2 END
 WHERE id=1 AND pin=?1 AND enabled=1
 AND (attempts<48 OR ?2<last_ms)
 RETURNING enabled,allowed`;
export const STOP_SQL = `UPDATE level_admission_v1 SET enabled=0,allowed=0
 WHERE id=1 AND pin=?1 RETURNING enabled`;
const hex=/^[a-f0-9]{64}$/;
export async function reserve(db,pin,now){
 if(!db || typeof pin!=="string" || !hex.test(pin) || !Number.isSafeInteger(now) || now<=0 || now>=4102444800000) return "UNAVAILABLE";
 try{
  const row=await db.prepare(RESERVE_SQL).bind(pin,now).first();
  if(row===null)return "CLOSED_OR_CAP";
  if(row?.enabled===0 && row.allowed===0)return "CLOSED_OR_CAP";
  if(row?.enabled===1 && row.allowed===1)return "RESERVED";
  if(row?.enabled===1 && row.allowed===0)return "RATE_LIMIT";
  return "UNAVAILABLE";
 }catch{return "UNAVAILABLE";}
}
