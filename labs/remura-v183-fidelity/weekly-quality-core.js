/* REMURA v1.48 — strict read-only weekly quality contract. */
(function(root){
 'use strict';
 const count=x=>Number.isSafeInteger(x)&&x>=0;
 const states=['recorded_before_observation','unknown_legacy','captured_after_observation','missing_cot_reference'];
 const validWeek=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&
   !Number.isNaN(Date.parse(x+'T00:00:00Z'));
 const sum=(x,keys)=>keys.reduce((s,k)=>s+x[k],0);
 function read(x){
  if(!x||x.schema!=='remura-weekly-quality-v1'||x.mode!=='research_only'||
    x.noSyntheticCandles!==true||
    x.firstSeenMeaning!=='REMURA first CFTC row capture (NOT official publication)'||
    x.legacyProvenance!=='unknown_not_backfilled'||
    !Array.isArray(x.weekly)||x.weekly.length>12||
    !count(x.independentCotWeeksObserved)||
    !count(x.weeksWithBothRelationships)||
    !count(x.weeksDivergenceBetter)||!count(x.weeksConcordanceBetter)||
    !count(x.weeksEqual)||!count(x.casesAudited)||
    !count(x.minCotWeeksForDescriptiveReview)||
    x.minCotWeeksForDescriptiveReview!==8||
    !x.captureCounts||!states.every(k=>count(x.captureCounts[k]))||
    sum(x.captureCounts,states)!==x.casesAudited||
    x.weeksDivergenceBetter+x.weeksConcordanceBetter+x.weeksEqual!==x.weeksWithBothRelationships||
    !['Campione insufficiente',
      'Descrittivo: correlazioni e verifica fuori campione non risolte'].includes(x.quality)||
    (x.independentCotWeeksObserved<8)!==(x.quality==='Campione insufficiente'))return null;
  let checked=0,both=0,better=0,worse=0,tie=0,weekCount=0;
  const aggregated=Object.fromEntries(states.map(k=>[k,0]));
  const keys=new Set(),weekly=[];
  for(const w of x.weekly){
   if(!w||!validWeek(w.cotWeek)||keys.has(w.cotWeek)||
      !count(w.pairedSamples)||!count(w.alignedSamples)||
      !count(w.divergentSamples)||!count(w.alignedHits)||
      !count(w.divergentHits)||
      w.alignedSamples+w.divergentSamples!==w.pairedSamples||
      w.alignedHits>w.alignedSamples||w.divergentHits>w.divergentSamples||
      !w.captureCounts||!states.every(k=>count(w.captureCounts[k]))||
      sum(w.captureCounts,states)!==w.pairedSamples||
      !Array.isArray(w.sharedFactorWarnings)||w.sharedFactorWarnings.length>8)return null;
   const expected=w.alignedSamples&&w.divergentSamples
    ?Math.round(1000*(w.divergentHits/w.divergentSamples-
                      w.alignedHits/w.alignedSamples))/10:null;
   if(expected===null?w.divergentMinusAlignedHitPp!==null:
      typeof w.divergentMinusAlignedHitPp!=='number'||
      Math.abs(expected-w.divergentMinusAlignedHitPp)>0.051)return null;
   const overlaps=[];
   for(const f of w.sharedFactorWarnings){
    if(!f||!['USD','precious_metals','us_equity_indices','energy',
        'EUR','GBP','JPY','CAD','AUD','CHF','NZD'].includes(f.factor)||
       !count(f.markets)||f.markets<2||f.markets>w.pairedSamples||
       overlaps.some(v=>v.factor===f.factor))return null;
    overlaps.push({factor:f.factor,markets:f.markets});
   }
   for(const k of states)aggregated[k]+=w.captureCounts[k];
   checked+=w.pairedSamples;weekCount+=w.pairedSamples>0?1:0;
   if(expected!==null){
     both++;
     if(expected>0)better++;
     else if(expected<0)worse++;
     else tie++;
   }
   keys.add(w.cotWeek);
   weekly.push({week:w.cotWeek,samples:w.pairedSamples,
     aligned:w.alignedSamples,alignedHits:w.alignedHits,
     divergent:w.divergentSamples,divergentHits:w.divergentHits,
     delta:expected,counts:w.captureCounts,overlaps});
  }
  if(checked!==x.casesAudited||weekCount!==x.independentCotWeeksObserved||
     both!==x.weeksWithBothRelationships||better!==x.weeksDivergenceBetter||
     worse!==x.weeksConcordanceBetter||tie!==x.weeksEqual||
     states.some(k=>aggregated[k]!==x.captureCounts[k]))return null;
  return {weeks:x.independentCotWeeksObserved,
    both,better,worse,tie,quality:x.quality,cases:x.casesAudited,
    counts:x.captureCounts,weekly};
 }
 const api={read};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
 root.REMURA_WEEKLY_QUALITY=api;
})(typeof window!=='undefined'?window:globalThis);
