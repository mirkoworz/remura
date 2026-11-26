// REMURA V30.11 Telegram Bridge LAB. Pure message builder, no network.
const periods = Object.freeze({DAY:"Giornaliero",WEEK:"Settimanale",CURRENT_MONTH:"Mese corrente",PREVIOUS_MONTH:"Mese precedente"});
const kinds = Object.freeze({DELTA_PEAK:"Picco Delta",EFFORT_RESULT:"Effort / Result",OTHER_VOLUME_LEVEL:"Altro livello volumetrico"});
const flags = Object.freeze({EUR:"🇪🇺",USD:"🇺🇸",GBP:"🇬🇧",JPY:"🇯🇵",CHF:"🇨🇭",CAD:"🇨🇦",AUD:"🇦🇺",NZD:"🇳🇿"});
const stamp = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/;
export function prepareTelegramMessage(event, policy = {}) {
  // Server-internal input only; never derive identity or test status from client.
  // A persistent, unique receipt outbox must enforce deduplication before any send.
  if (policy.enabled !== true || event?.state !== "COMMITTED" ||
      event.newCanonical !== true || event.test !== false ||
      !["friend-b","friend-c"].includes(event.slot)) return null;
  const r=event.receipt;
  if (!r || !Number.isSafeInteger(r.id) || r.id < 1 ||
      !Number.isSafeInteger(policy.startAfterReceipt) || policy.startAfterReceipt < 0 ||
      r.id <= policy.startAfterReceipt || typeof r.note !== "string" ||
      /\b(?:TEST|COLLAUDO|NON[ -]OPERATIVO)\b/i.test(r.note)) return null;
  if (typeof r.market !== "string" || !/^[A-Z0-9_]{1,24}$/.test(r.market) ||
      typeof r.provider !== "string" || !/^[A-Z0-9_]{1,16}$/.test(r.provider) ||
      typeof r.ticker !== "string" || !/^[A-Z0-9_.!-]{1,24}$/.test(r.ticker) ||
      typeof r.contract !== "string" || !/^[A-Z0-9_.-]{0,24}$/.test(r.contract) ||
      !["SPOT","CFD","FUTURE","INDEX"].includes(r.product) ||
      (r.product === "FUTURE" ? !r.contract || r.ticker.includes("!") : r.contract !== "") ||
      r.provider === "ECB") return null;
  // Explicit OWNER-reviewed authentic volumetric mappings; empty by default.
  const mapping=[r.market,r.provider,r.ticker,r.product,r.contract];
  if (!Array.isArray(policy.allowedMappings) || !policy.allowedMappings.some(x =>
      Array.isArray(x) && x.length===5 && x.every((v,i)=>v===mapping[i]))) return null;
  if (!Object.hasOwn(periods,r.period) || !Object.hasOwn(kinds,r.kind) ||
      typeof r.price !== "string" || !/^(?:0|[1-9][0-9]{0,7})(?:\.[0-9]{1,8})?$/.test(r.price) ||
      !/[1-9]/.test(r.price) || typeof r.received_utc !== "string" ||
      !stamp.test(r.received_utc) || !Number.isFinite(Date.parse(r.received_utc)) ||
      new Date(r.received_utc).toISOString().replace(".000Z","Z") !== r.received_utc) return null;
  const a=r.market.slice(0,3),b=r.market.slice(3);
  const market=flags[a] && flags[b] ? flags[a]+" "+flags[b]+" "+a+"/"+b : "📊 "+r.market;
  const time=new Intl.DateTimeFormat("it-IT",{timeZone:"Europe/Rome",dateStyle:"short",timeStyle:"medium"}).format(new Date(r.received_utc));
  return Object.freeze({receiptId:r.id,text:[
    "🦈 REMURA | NUOVO LIVELLO", "",market,"🎯 Livello: "+r.price,
    "📊 Metodologia: "+kinds[r.kind],"⏳ Periodo: "+periods[r.period],
    "📡 Fonte dati: "+r.provider+" · "+r.ticker+(r.contract?" · "+r.contract:""),
    "🕒 Ricevuto: "+time+" (Roma)","👤 REMURA Contributor",
    "📌 Rif. #"+r.id+" · Non ancora esaminato dall’OWNER"
  ].join("\n")});
}
