/* REMURA Contributors Draft v0.95 LAB — 22/11/2026 22:20 CET
 * Reuses candidate intake field contract: LOCAL DRAFT ONLY.
 * No authentication, server trust, network, write, or role attestation.
 */
(function(root,factory){
  "use strict";
  const api=factory();
  if(typeof module==="object"&&module.exports)module.exports=api;
  root.REMURA_CONTRIBUTORS_DRAFT=api;
})(typeof window!=="undefined"?window:globalThis,function(){
  "use strict";
  const PERIODS=Object.freeze(["DAY","WEEK","CURRENT_MONTH","PREVIOUS_MONTH"]);
  const KINDS=Object.freeze(["DELTA_PEAK","EFFORT_RESULT","OTHER_VOLUME_LEVEL"]);
  const PRODUCTS=Object.freeze(["SPOT_CFD","FUTURE","OTHER"]);
  const TICKER=/^[A-Z0-9][A-Z0-9._\/-]{1,23}$/;
  const SOURCE=/^[\p{L}\p{N}][\p{L}\p{N} ._\/-]{1,59}$/u;
  function utc(v){
    if(typeof v!=="string"||! /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(v))return null;
    const n=Date.parse(v);
    return Number.isFinite(n)&&new Date(n).toISOString().replace(".000Z","Z")===v?n:null;
  }
  function clean(v){
    return typeof v==="string"?v.trim():"";
  }
  function price(v){
    if(typeof v!=="string")return null;
    const raw=v.trim().replace(",",".");
    if(!/^\d{1,9}(?:\.\d{1,8})?$/.test(raw))return null;
    const n=Number(raw);
    if(!Number.isFinite(n)||n<=0)return null;
    return raw;
  }
  function validate(input,now=Date.now()){
    const errors=[];
    if(!input||typeof input!=="object"||Array.isArray(input)||!Number.isFinite(now))
      return {ok:false,errors:["Dati non validi"],draft:null};
    const market=clean(input.market).toUpperCase(),provider=clean(input.provider),
      ticker=clean(input.ticker).toUpperCase(),product=clean(input.product),
      contract=clean(input.contract).toUpperCase(),period=clean(input.period),
      kind=clean(input.kind),value=price(input.price),
      anchor=clean(input.anchor_utc),observed=clean(input.observed_utc),
      note=clean(input.note);
    if(!TICKER.test(market))errors.push("Strumento non valido");
    if(!SOURCE.test(provider))errors.push("Fonte/broker non valido");
    if(!TICKER.test(ticker))errors.push("Ticker non valido");
    if(!PRODUCTS.includes(product))errors.push("Tipo prodotto non valido");
    if(contract&&!TICKER.test(contract))errors.push("Contratto non valido");
    if(product==="FUTURE"&&!contract)errors.push("Indica il contratto del future");
    if(!PERIODS.includes(period))errors.push("Periodo non valido");
    if(!KINDS.includes(kind))errors.push("Metodologia non valida");
    if(value===null)errors.push("Prezzo non valido (positivo, massimo 8 decimali)");
    const a=utc(anchor),b=utc(observed);
    if(a===null)errors.push("Anchor UTC non valido");
    if(b===null)errors.push("Osservazione UTC non valida");
    if(a!==null&&b!==null){
      if(a>b)errors.push("Anchor successivo all'osservazione");
      if(b>now+120000)errors.push("Osservazione futura");
      if(b<now-180*86400000)errors.push("Osservazione più vecchia di 180 giorni");
    }
    if(note.length>280||/[\x00-\x08\x0b\x0c\x0e-\x1f]/.test(note))
      errors.push("Note troppo lunghe o con caratteri non validi");
    if(errors.length)return {ok:false,errors,draft:null};
    return {ok:true,errors:[],draft:{
      schema:"remura.contributors.local_draft.v095",
      status:"LOCAL_ONLY_UNVERIFIED",
      market,provider,ticker,product,contract,
      period,kind,price:value,anchor_utc:anchor,observed_utc:observed,note,
      identity_verified:false,mapping_verified:false,
      sent_to_server:false,received_by_owner:false,approved:false
    }};
  }
  function exportJSON(input,now=Date.now()){
    const result=validate(input,now);
    return result.ok?{...result,json:JSON.stringify(result.draft,null,2)}:{...result,json:null};
  }
  return Object.freeze({PERIODS,KINDS,PRODUCTS,validate,exportJSON});
});