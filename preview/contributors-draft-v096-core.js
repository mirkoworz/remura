/* REMURA Contributors v0.96 LAB — 22/11/2026 22:28 CET.
 * Exact public-field constraints mirrored from research/contributors/d1_lab_adapter.mjs
 * (no request_id, identity, Access JWT or D1 writer in this local draft).
 * Server-side normalize, mapping and identity remain authoritative.
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
  const PRODUCTS=Object.freeze(["SPOT","CFD","INDEX","FUTURE"]);
  const MARKET=/^[A-Z0-9_]{1,24}$/;
  const PROVIDER=/^[A-Z0-9_]{1,16}$/;
  const TICKER=/^[A-Z0-9_.!-]{1,24}$/;
  const CONTRACT=/^[A-Z0-9_.-]{1,24}$/;
  const UNSAFE_NOTE=/[\u0000-\u001f\u007f-\u009f\uD800-\uDFFF]/u;
  const clean=x=>typeof x==="string"?x.trim():"";
  const upper=x=>clean(x).toUpperCase();
  function utc(v){
    if(typeof v!=="string"||!/^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$/.test(v))return null;
    const n=Date.parse(v);
    return Number.isFinite(n)&&new Date(n).toISOString().replace(".000Z","Z")===v?n:null;
  }
  function canonicalPrice(v){
    if(typeof v!=="string")return null;
    const p=v.replace(",",".");
    if(!/^(?:0|[1-9][0-9]{0,7})(?:\.[0-9]{1,8})?$/.test(p)||!/[1-9]/.test(p))return null;
    return p.includes(".")?p.replace(/0+$/,"").replace(/\.$/,""):p;
  }
  function validate(input,now=Date.now()){
    const errors=[];
    if(!input||Object.getPrototypeOf(input)!==Object.prototype||!Number.isFinite(now))
      return {ok:false,errors:["Dati non validi"],draft:null};
    const market=upper(input.market),provider=upper(input.provider),ticker=upper(input.ticker),
      product=clean(input.product),contract=upper(input.contract),
      period=clean(input.period),kind=clean(input.kind),
      price=canonicalPrice(clean(input.price)),anchor=clean(input.anchor_utc),
      observed=clean(input.observed_utc),note=typeof input.note==="string"?input.note:"";
    if(!MARKET.test(market))errors.push("Strumento non valido per il server (1–24 lettere/numeri/_)");
    if(!PROVIDER.test(provider))errors.push("Fonte non valida: codice catalogo (1–16 lettere/numeri/_)");
    if(!TICKER.test(ticker))errors.push("Ticker non valido per il server");
    if(!PRODUCTS.includes(product))errors.push("Prodotto non previsto nel catalogo server");
    if(product==="FUTURE"){
      if(!CONTRACT.test(contract)||ticker.includes("!"))errors.push("Future: contratto esatto necessario, ticker continuo non consentito");
    }else if(contract!=="")errors.push("Contratto vuoto per SPOT, CFD e INDEX");
    if(!PERIODS.includes(period))errors.push("Periodo non valido");
    if(!KINDS.includes(kind))errors.push("Metodologia non valida");
    if(price===null)errors.push("Prezzo: 1–8 cifre intere, massimo 8 decimali, maggiore di zero");
    const a=utc(anchor),b=utc(observed);
    if(a===null)errors.push("Anchor non UTC canonico");
    if(b===null)errors.push("Osservazione non UTC canonica");
    if(a!==null&&b!==null){
      if(a>b)errors.push("L'anchor è successivo all'osservazione");
      if(b>now)errors.push("L'osservazione è nel futuro");
    }
    if([...note].length>280||UNSAFE_NOTE.test(note))
      errors.push("Note troppo lunghe o contenenti caratteri di controllo");
    if(errors.length)return {ok:false,errors,draft:null};
    return {ok:true,errors:[],draft:{
      schema:"remura.contributors.local_draft.v096",
      status:"LOCAL_ONLY_UNVERIFIED",market,provider,ticker,product,contract,
      period,kind,price,anchor_utc:anchor,observed_utc:observed,note,
      identity_verified:false,mapping_verified:false,
      sent_to_server:false,received_by_owner:false,approved:false
    }};
  }
  function exportJSON(input,now=Date.now()){
    const result=validate(input,now);
    return result.ok?{...result,json:JSON.stringify(result.draft,null,2)}:{...result,json:null};
  }
  return Object.freeze({PERIODS,KINDS,PRODUCTS,validate,exportJSON,canonicalPrice});
});