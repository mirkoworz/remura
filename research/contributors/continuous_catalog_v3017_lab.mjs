// REMURA V30.17 LAB — continuous chart selection, not a live data adapter.
// Symbols below are REMURA internal aliases, never feed API symbols.
import {ROOTS,PLATFORMS,FEEDS} from "./volumetric_catalog_v3013_lab.mjs";
export const CONTINUOUS_CHOICES=Object.freeze(Object.entries(ROOTS).flatMap(([root,ref])=>
 FEEDS.map(feed=>Object.freeze({id:feed+"_"+root+"_CONT",root,feed,
 market:ref.market,exchange:ref.exchange,forexReference:ref.forexReference,
 inverse:ref.inverse,platforms:PLATFORMS,series:"CONTINUOUS",
 sourceTicker:null,adjustment:null,rollMethod:null,activeContract:null,
 enabled:false,telegramEligible:false,scienceEligible:false}))));
export function describeContinuous(id){
 const row=CONTINUOUS_CHOICES.find(x=>x.id===id);
 if(!row)throw Error("unknown_continuous_choice");
 return row;
}
// Metadata is not inferred from current calendar, feed, or root.
// A continuous observation is a chart reference, not an executable contract quote.
// Preserve original reported price; no reciprocal conversion or rollover adjustment.
// Before live use, persist a versioned platform/feed profile (actual ticker,
// roll method and adjustment); permit an unknown underlying contract only with
// explicit CONTINUOUS label and keep it excluded from contract-specific science.
// Existing V30.16 intake schema/formatter do not encode this distinction;
// this module intentionally does not generate insert SQL or modify active mappings.
