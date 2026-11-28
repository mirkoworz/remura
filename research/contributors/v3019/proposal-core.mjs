// REMURA V30.19 LAB — 28/11/2026 07:25 CET.
// Pure catalogue and proposal normalization. No data downloads.
export const VERSION="V30.19 LAB";
export const UPDATED="28/11/2026 07:25 CET";
const fx=["EURUSD","GBPUSD","USDJPY","USDCHF","USDCAD","AUDUSD","NZDUSD","EURGBP","EURJPY","EURCHF","EURAUD","EURCAD","EURNZD","GBPJPY","GBPCHF","GBPAUD","GBPCAD","GBPNZD","AUDJPY","AUDCAD","AUDCHF","AUDNZD","NZDJPY","NZDCAD","NZDCHF","CADJPY","CADCHF","CHFJPY"];
const cfd={Forex:fx,Metalli:["XAUUSD","XAGUSD"],Indici:["NAS100","US500","US30","GER40","UK100","JP225"],Energia:["WTI","BRENT"]};
const futures={Valute:["6E","6B","6J","6A","6C","6S","6N"],Metalli:["GC","SI"],Indici:["NQ","ES","YM","RTY"],Energia:["CL"]};
const markets={"6E":"EURUSD","6B":"GBPUSD","6J":"JPYUSD","6A":"AUDUSD","6C":"CADUSD","6S":"CHFUSD","6N":"NZDUSD"};
export const LABELS=Object.freeze({XAUUSD:"Oro",XAGUSD:"Argento",NAS100:"Nasdaq",US500:"S&P 500",US30:"Dow Jones",GER40:"DAX",UK100:"FTSE",JP225:"Nikkei",WTI:"Petrolio WTI",BRENT:"Petrolio Brent",NQ:"Nasdaq",ES:"S&P 500",YM:"Dow Jones",RTY:"Russell 2000",GC:"Oro",SI:"Argento",CL:"Petrolio","6E":"Euro","6B":"Sterlina","6J":"Yen","6A":"Dollaro australiano","6C":"Dollaro canadese","6S":"Franco svizzero","6N":"Dollaro neozelandese"});
export const KINDS=Object.freeze({DELTA_PEAK:"Picco Delta",EFFORT_RESULT:"Sforzo / Risultato",CVD_DIVERGENCE:"Divergenza CVD"});
export const PERIODS=Object.freeze({DAY:"Giornaliero",WEEK:"Settimanale",CURRENT_MONTH:"Mensile",PREVIOUS_MONTH:"Mese precedente"});
export const CATALOG=Object.freeze(Object.entries({CFD:cfd,FUTURES:futures}).flatMap(([mode,cats])=>Object.entries(cats).flatMap(([category,assets])=>assets.flatMap(asset=>(mode==="CFD"?["OANDA","FXCM"]:["RITHMIC","DXFEED"]).map(provider=>Object.freeze({
 id:[mode,asset,provider].join("_"),mode,category,asset,provider,
 market:markets[asset]??asset,product:mode==="CFD"?"CFD":"FUTURE",contract:mode==="CFD"?"":"CONTINUOUS",
 ticker:mode==="FUTURES"?asset+"_CONT":asset+"_MANUAL",
 // Internal aliases only; actual CFD mapping needs source evidence.
 availability:mode==="FUTURES"&&!["YM","RTY"].includes(asset)?"V3018_EXISTING":"UNVERIFIED_CANDIDATE"
}))))));
const uuid=/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/;
export function pricesFromText(raw){
 if(typeof raw!=="string"||raw.length>600)throw Error("invalid_prices");
 const lines=raw.split(/\r?\n/).map(x=>x.trim()).filter(Boolean);
 if(lines.length<1||lines.length>20)throw Error("invalid_prices");
 const result=[];
 for(const line of lines){
  if(!/^\d{1,8}(?:[.,]\d{1,8})?$/.test(line))throw Error("invalid_price");
  const [a,b=""]=line.replace(",",".").split(".");
  const i=a.replace(/^0+(?=\d)/,""),d=b.replace(/0+$/,"");
  const canonical=d?i+"."+d:i;
  if(canonical==="0")throw Error("invalid_price");
  if(!result.includes(canonical))result.push(canonical);
 }
 return result;
}
export function normalizeProposal(body){
 const fields=["request_id","mapping_id","kind","period","prices","note"];
 if(!body||Object.getPrototypeOf(body)!==Object.prototype||Object.keys(body).length!==fields.length||fields.some(k=>!Object.hasOwn(body,k)||typeof body[k]!=="string")||!uuid.test(body.request_id))throw Error("invalid_fields");
 const mapping=CATALOG.find(x=>x.id===body.mapping_id);
 if(!mapping||!Object.hasOwn(KINDS,body.kind)||!Object.hasOwn(PERIODS,body.period))throw Error("invalid_mapping");
 const note=body.note.trim();
 if([...note].length>280||/[\u0000-\u001f\u007f-\u009f\uD800-\uDFFF]/u.test(note))throw Error("invalid_note");
 const prices=pricesFromText(body.prices);
 // Canonical payload is stable between intent issuance, submit and retry; no changing time in HMAC.
 return Object.freeze({request_id:body.request_id,mapping_id:mapping.id,kind:body.kind,period:body.period,prices:prices.join("\n"),note});
}
export function payloadForStorage(body){
 const p=normalizeProposal(body),m=CATALOG.find(x=>x.id===p.mapping_id);
 return {proposal:p,mapping:m,prices:p.prices.split("\n"),payload:JSON.stringify([p.mapping_id,p.kind,p.period,p.prices,p.note])};
}
export function classify(slot,note){
 if(!["friend-a","friend-b","friend-c"].includes(slot))throw Error("denied");
 return slot==="friend-a"||/TEST|COLLAUDO|NON[ -]OPERATIVO/i.test(note)?"TEST":"TELEGRAM";
}
export function formatGrouped(row,{preview=false}={}){
 const p=normalizeProposal(row.proposal),m=CATALOG.find(x=>x.id===p.mapping_id);
 if(!preview&&(row.state!=="COMMITTED"||row.publication_mode!=="TELEGRAM"||!["friend-b","friend-c"].includes(row.slot)||classify(row.slot,p.note)!=="TELEGRAM"||!Number.isSafeInteger(row.id)||row.id<1))return null;
 if(typeof row.received_utc!=="string"||!Number.isFinite(Date.parse(row.received_utc))||new Date(row.received_utc).toISOString().replace(".000Z","Z")!==row.received_utc)throw Error("invalid_time");
 const date=new Intl.DateTimeFormat("it-IT",{timeZone:"Europe/Rome",dateStyle:"short",timeStyle:"medium"}).format(new Date(row.received_utc));
 const lines=["🦈 REMURA INTELLIGENCE","",m.asset+(LABELS[m.asset]?" — "+LABELS[m.asset]:"")+" · "+(m.mode==="FUTURES"?"FUTURES":"CFD"),"📡 "+m.provider+(m.mode==="FUTURES"?" · Continuativo":""),"📊 "+KINDS[p.kind],"📅 "+PERIODS[p.period],"","🎯 LIVELLI VOLUMETRICI",...p.prices.split("\n").map(x=>"• "+x)];
 if(m.mode==="FUTURES")lines.push("","Grafico continuativo: scadenza/adeguamento non verificati.");
 // Notes stay private by design until user separately approves publication.
 lines.push("","🕒 Inserito: "+date+" (Roma)",preview?"ANTEPRIMA · NON OPERATIVO":"Rif. P"+row.id+" · Non ancora esaminato dall’OWNER");
 return lines.join("\n");
}
