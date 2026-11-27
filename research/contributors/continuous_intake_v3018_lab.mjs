// V30.18 LAB: explicit chart-observation sentinel within existing additive schema.
// Alias is internal; neither a vendor ticker nor an expiring contract.
import {CONTINUOUS_CHOICES} from "./continuous_catalog_v3017_lab.mjs";
export const CONTINUOUS_MARKER="CONTINUOUS";
export const CONTINUOUS_ROWS=Object.freeze(CONTINUOUS_CHOICES.map(x=>Object.freeze({
 market:x.market,provider:x.feed,ticker:x.root+"_CONT",product:"FUTURE",contract:CONTINUOUS_MARKER,
 source_group:"CHART_ONLY_"+x.exchange+"_"+x.root,active:0
})));
export function continuousMapping(row){
 return CONTINUOUS_ROWS.find(x=>["market","provider","ticker","product","contract"].every(k=>x[k]===row?.[k]))??null;
}
export function checkContinuousMapping(row){
 const reserved=row?.contract===CONTINUOUS_MARKER||String(row?.ticker??"").endsWith("_CONT");
 if(reserved&&!continuousMapping(row))throw Error("invalid_continuous_mapping");
 return row;
}
export function describeChartSeries(row){
 const c=continuousMapping(row);
 if(!c)return null;
 return Object.freeze({root:c.ticker.slice(0,-5),feed:c.provider,
 sourceTicker:null,activeContract:null,adjustment:"UNKNOWN",rollMethod:"UNKNOWN",
 quote:"MANUAL_CHART_OBSERVATION",scienceEligible:false});
}
