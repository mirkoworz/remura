// REMURA Contributors v0.96 LAB — 22/11/2026 22:28 CET
// Pre-submit browser review ONLY. Reuses candidate D1 normalize constraints.
// This code is NOT authentication, authorization, a receipt or a D1 mutation.
const PERIODS=new Set(["DAY","WEEK","CURRENT_MONTH","PREVIOUS_MONTH"]);
const KINDS=new Set(["DELTA_PEAK","EFFORT_RESULT","OTHER_VOLUME_LEVEL"]);
const PRODUCTS=new Set(["SPOT","CFD","INDEX","FUTURE"]);
const stamp=v=>{
 if(typeof v!=="string"||!/^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$/.test(v))return null;
 const n=Date.parse(v);
 return Number.isFinite(n)&&new Date(n).toISOString().replace(".000Z","Z")===v?n:null;
};
function inspectLevelV096(mapping,fields,now=Date.now()){
 const denied=(reason)=>({ok:false,reason,data:null,authorizes:false,requestIdGenerated:false});
 if(!mapping||Object.getPrototypeOf(mapping)!==Object.prototype||
    !fields||Object.getPrototypeOf(fields)!==Object.prototype||!Number.isFinite(now))
   return denied("invalid_input");
 const keys=["market","provider","ticker","product","contract"];
 if(keys.some(k=>typeof mapping[k]!=="string"||typeof fields[k]!=="string"||fields[k]!==mapping[k]))
   return denied("mapping_mismatch");
 const {market,provider,ticker,product,contract}=mapping;
 if(!/^[A-Z0-9_]{1,24}$/.test(market)||
    !/^[A-Z0-9_]{1,16}$/.test(provider)||
    !/^[A-Z0-9_.!-]{1,24}$/.test(ticker)||!PRODUCTS.has(product)||
    (product==="FUTURE"?(!/^[A-Z0-9_.-]{1,24}$/.test(contract)||ticker.includes("!")):contract!==""))
   return denied("catalog_mapping_invalid");
 if(!PERIODS.has(fields.period)||!KINDS.has(fields.kind))return denied("classification_invalid");
 if(typeof fields.price!=="string")return denied("price_invalid");
 let price=fields.price.replace(",",".");
 if(!/^(?:0|[1-9][0-9]{0,7})(?:\.[0-9]{1,8})?$/.test(price)||!/[1-9]/.test(price))
   return denied("price_invalid");
 if(price.includes("."))price=price.replace(/0+$/,"").replace(/\.$/,"");
 const anchor=stamp(fields.anchor_utc),observed=stamp(fields.observed_utc);
 if(anchor===null||observed===null||anchor>observed||observed>now)
   return denied("chronology_invalid");
 if(typeof fields.note!=="string"||[...fields.note].length>280||
    /[\u0000-\u001f\u007f-\u009f\uD800-\uDFFF]/u.test(fields.note))return denied("note_invalid");
 const data={market,provider,ticker,product,contract,period:fields.period,
   kind:fields.kind,price,anchor_utc:fields.anchor_utc,
   observed_utc:fields.observed_utc,note:fields.note};
 return {ok:true,reason:"CLIENT_REVIEW_ONLY",data,authorizes:false,
   requestIdGenerated:false,serverAccessVerified:false,serverReceipt:false};
}
function summaryLevelV096(data){
 if(!data||Object.getPrototypeOf(data)!==Object.prototype)return "";
 const keys=[["Mercato",data.market],["Broker",data.provider],["Ticker",data.ticker],
 ["Prodotto",data.product],["Contratto",data.contract||"—"],["Periodo",data.period],
 ["Metodo",data.kind],["Prezzo",data.price],["Anchor UTC",data.anchor_utc],
 ["Osservato UTC",data.observed_utc],["Note",data.note||"—"]];
 return "RICONTROLLA LA PROPOSTA (nessun dato ancora inviato)\n\n"+
   keys.map(([k,v])=>k+": "+String(v)).join("\n")+
   "\n\nQuesta verifica locale NON autorizza né prova l'acquisizione nel database.";
}
export {inspectLevelV096,summaryLevelV096};
