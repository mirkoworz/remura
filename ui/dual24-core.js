/* REMURA v1.45: strict, private dual-24h experiment schema. */
(function(root){
  'use strict';
  const METRICS=['calendar24','trading96'];
  const SEGMENTS=['all','aligned','divergent','observation',
                  'technical_confirmation','qualified_event'];
  const VERDICTS=['Campione insufficiente','Descrittivo, non prova predittiva'];
  const count=v=>Number.isSafeInteger(v)&&v>=0?v:null;
  const real=v=>typeof v==='number'&&Number.isFinite(v)?v:null;
  const percent=v=>v===null?null:real(v)!==null&&v>=0&&v<=100?v:null;
  function read(input){
    if(!input||input.schema!=='remura-dual24-validation-v1'||
       input.mode!=='research_only'||input.noSyntheticCandles!==true||
       !Array.isArray(input.segments)||input.segments.length!==12)return null;
    const cohorts=count(input.cohorts),outcomes=count(input.outcomes);
    if(cohorts===null||outcomes===null)return null;
    const items={};
    for(const raw of input.segments){
      if(!raw||!METRICS.includes(raw.metric)||!SEGMENTS.includes(raw.segment))return null;
      const key=raw.metric+':'+raw.segment;
      if(items[key])return null;
      const n=count(raw.samples),weeks=count(raw.reportWeeks);
      const candidates=count(raw.potentiallyMatureCohorts);
      const excluded=count(raw.unmeasuredCandidates);
      const coverage=percent(raw.coveragePct);
      const delayed=count(raw.delayedExits);
      const elapsed=raw.meanElapsedHours===null?null:real(raw.meanElapsedHours);
      const pauses=raw.meanVerifiedPauseCount===null?null:real(raw.meanVerifiedPauseCount);
      if(n===null||weeks===null||candidates===null||excluded===null||delayed===null||
         n>candidates||weeks>n||excluded!==candidates-n||delayed>n||
         (candidates===0?coverage!==null:coverage===null)||
         (coverage!==null&&Math.abs(coverage-100*n/candidates)>0.06)||
         !VERDICTS.includes(raw.verdict)||
         (raw.verdict===VERDICTS[1]&&(n<30||weeks<8)))return null;
      const metrics=['directionHitPct','wilson95Pct','meanDirectionalBps',
                     'meanLongBenchmarkBps','meanFavorableBps','meanAdverseBps'];
      if(!n&&metrics.some(k=>raw[k]!==null&&raw[k]!==undefined))return null;
      const hit=n?percent(raw.directionHitPct):null;
      const ci=raw.wilson95Pct;
      const low=n&&Array.isArray(ci)&&ci.length===2?percent(ci[0]):null;
      const high=n&&Array.isArray(ci)&&ci.length===2?percent(ci[1]):null;
      const mean=n?real(raw.meanDirectionalBps):null;
      const baseline=n?real(raw.meanLongBenchmarkBps):null;
      const favorable=n?real(raw.meanFavorableBps):null;
      const adverse=n?real(raw.meanAdverseBps):null;
      if(n&&(hit===null||low===null||high===null||low>high||
        mean===null||baseline===null||favorable===null||adverse===null||
        favorable<0||adverse>0||elapsed===null||elapsed<24||
        pauses===null||pauses<0))return null;
      if(!n&&(elapsed!==null||pauses!==null))return null;
      items[key]={samples:n,weeks,candidates,excluded,coverage,delayed,elapsed,pauses,
        verdict:raw.verdict,hit,low,high,mean,baseline,favorable,adverse};
    }
    if(Object.keys(items).length!==12)return null;
    return {cohorts,outcomes,items};
  }
  const api={read,METRICS,SEGMENTS};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  root.REMURA_DUAL24=api;
})(typeof window!=='undefined'?window:globalThis);
