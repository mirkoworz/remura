// REMURA v0.8.116 LAB — 17/11/2026 CET
// Structural port only. No configuration digest equivalence or source attestation.
const MAX=15000;
const fields=s=>s.split(" ");
const F=fields("schema version mode symbol feed ticker chart_type timezone session timeframe calendar product_status contract snapshot_open_ms snapshot_close_ms sender_clock_ms receive_clock_ms history_complete method_er configuration levels");
const C=fields("lower_tf lookback multiplier max_efficiency min_peak_gap daily_min_effort daily_anchor fp_ticks fp_imbalance_pct fp_value_area_pct atr_length delta_library price_decimal_places_max");
const L=fields("period rank price peak_origin_close_ms period_start_ms period_end_ms boundary_observed method");
const ORDER=[["DAY",1],["DAY",2],["DAY",3],["WEEK",1],["CURRENT_MONTH",1],["PREVIOUS_OBSERVED_MONTH",1]];
function need(b){if(!b)throw Error("INVALID");}
class Num {constructor(token){this.token=token;this.val=Number(token);need(Number.isFinite(this.val));}}
function n(x){need(x instanceof Num);return x.val;}
function int(x){need(x instanceof Num&&/^-?(?:0|[1-9][0-9]*)$/.test(x.token)&&Number.isSafeInteger(x.val));return x.val;}
function clock(x,whole=true){const v=int(x);need(v>0&&v<4102444800000&&(!whole||v%1000===0));return v;}
function exact(x,keys){need(x!==null&&typeof x==="object"&&Object.getPrototypeOf(x)===null&&Object.keys(x).length===keys.length&&keys.every(k=>Object.hasOwn(x,k)));}
export function strictJSON(raw){
 need(typeof raw==="string"&&new TextEncoder().encode(raw).length<=MAX);
 let i=0,nodes=0;
 const ws=()=>{while(i<raw.length&&/[ \t\r\n]/.test(raw[i]))i++;};
 function string(){
  need(raw[i]==='"');const start=i++;
  while(i<raw.length){const c=raw[i++];if(c==='"')return JSON.parse(raw.slice(start,i));if(c==="\\"){need(i<raw.length);i++;}}
  throw Error("INVALID");
 }
 function val(depth){
  ws();need(depth<=16&&++nodes<=1024);
  const c=raw[i];
  if(c==='"')return string();
  if(c==="{"){
   i++;ws();const o=Object.create(null);
   if(raw[i]==="}"){i++;return o;}
   for(;;){ws();const k=string();need(!Object.hasOwn(o,k));ws();need(raw[i++]===":");o[k]=val(depth+1);ws();
    const sep=raw[i++];if(sep==="}")return o;need(sep===",");}
  }
  if(c==="["){
   i++;ws();const a=[];if(raw[i]==="]"){i++;return a;}
   for(;;){a.push(val(depth+1));ws();const sep=raw[i++];if(sep==="]")return a;need(sep===",");}
  }
  for(const [token,v] of [["true",true],["false",false],["null",null]])if(raw.startsWith(token,i)){i+=token.length;return v;}
  const m=/^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?/.exec(raw.slice(i));
  need(m);i+=m[0].length;return new Num(m[0]);
 }
 const out=val(0);ws();need(i===raw.length);return out;
}
function sameClock(a,b){return a===null&&b===null||(a instanceof Num&&b instanceof Num&&a.val===b.val);}
function shortString(v){return typeof v==="string"&&[...v].length>0&&[...v].length<=100&&!/[\uD800-\uDFFF]/u.test(v);}
export function validateLevelStructure(raw){
 const e=strictJSON(raw);exact(e,["schema","snapshot"]);
 need(e.schema==="remura.tv.level.transport.preview.v1");
 const p=e.snapshot;exact(p,F);
 need(p.schema==="remura.tv.level.local.probe.v1"&&p.version==="0.9.3-level-preview"&&p.mode==="REALTIME_WEBHOOK_PREVIEW");
 need(p.symbol==="FX:EURUSD"&&p.feed==="FX"&&p.ticker==="EURUSD"&&p.timeframe==="5");
 need(p.calendar==="TRADINGVIEW_CHART_PERIOD_V1"&&p.product_status==="UNATTESTED"&&p.contract===null&&p.receive_clock_ms===null&&p.history_complete===false&&p.method_er==="SIGNED_BODY_ATR_OVER_RELATIVE_ABS_DELTA_V1");
 need(["chart_type","timezone","session"].every(k=>shortString(p[k])));
 const op=clock(p.snapshot_open_ms),cl=clock(p.snapshot_close_ms),sent=clock(p.sender_clock_ms,false);
 need(cl-op===300000&&cl%300000===0&&cl<=sent);
 const c=p.configuration;exact(c,C);
 need(c.lower_tf==="1"&&["HL2","POC FOOTPRINT"].includes(c.daily_anchor)&&c.delta_library==="TradingView/ta/14");
 need(int(c.price_decimal_places_max)===10&&int(c.atr_length)===14&&int(c.fp_value_area_pct)===70);
 need(int(c.lookback)>=5&&int(c.min_peak_gap)>=0&&int(c.min_peak_gap)<=100&&int(c.fp_ticks)>=1);
 need(n(c.multiplier)>=1&&n(c.max_efficiency)>=-1&&n(c.max_efficiency)<=1&&n(c.daily_min_effort)>=0&&n(c.fp_imbalance_pct)>=100);
 need(Array.isArray(p.levels)&&p.levels.length===6);
 let present=0;
 for(let i=0;i<6;i++){
  const row=p.levels[i],[period,rank]=ORDER[i];exact(row,L);
  need(row.period===period&&int(row.rank)===rank&&typeof row.boundary_observed==="boolean");
  const method=period==="DAY"?(c.daily_anchor==="HL2"?"DAY_TOP3_ABS_DELTA_HL2":"DAY_TOP3_ABS_DELTA_FP_POC"):"PERIOD_MAX_ABS_DELTA_HL2";
  need(row.method===method);
  const s=row.period_start_ms,t=row.period_end_ms,o=row.peak_origin_close_ms,price=row.price;
  if(s===null||t===null){need(period==="PREVIOUS_OBSERVED_MONTH"&&s===null&&t===null&&o===null&&price===null&&!row.boundary_observed);continue;}
  const start=clock(s),end=clock(t);need(start<end);
  if(period==="PREVIOUS_OBSERVED_MONTH")need(end<=cl&&start<clock(p.levels[4].period_start_ms));else need(start<=op&&op<cl&&cl<=end);
  if(period==="DAY"&&i>0){const first=p.levels[0];need(sameClock(s,first.period_start_ms)&&sameClock(t,first.period_end_ms)&&row.boundary_observed===first.boundary_observed);}
  need((o===null)===(price===null));
  if(o!==null){
   const origin=clock(o);need(start<origin&&origin<=Math.min(end,cl));
   need(typeof price==="string"&&/^[0-9]{1,8}(?:\.[0-9]{1,10})?$/.test(price)&&/[1-9]/.test(price));
   if(period==="DAY"&&i>0)need(p.levels[i-1].price!==null);
   present++;
  }
 }
 return {present_levels:present,missing_levels:6-present,configuration_equivalence:false,receipt_authenticated:false,scientific_admission:false,operational_signal:false};
}
