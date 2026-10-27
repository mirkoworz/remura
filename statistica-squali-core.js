/* REMURA v1.40 — Verified, no-mock statistics UI model.
   All values come from private aggregate API and are treated as untrusted. */
(function(root){
  'use strict';
  const HORIZONS=[1,4,24];
  const SEGMENTS=['all','aligned','divergent','observation',
                  'technical_confirmation','qualified_event'];
  const VERDICTS=['Campione insufficiente','Descrittivo, non prova predittiva'];
  function nint(v){return Number.isSafeInteger(v)&&v>=0?v:null;}
  function finite(v){return typeof v==='number'&&Number.isFinite(v)?v:null;}
  function pct(v){return v===null?null:finite(v)!==null&&v>=0&&v<=100?v:null;}
  function read(input){
    if(!input||input.schema!=='remura-forward-validation-v1'||!Array.isArray(input.segments)||
       input.mode!=='research_only')return null;
    const cohorts=nint(input.cohorts),outcomes=nint(input.outcomes);
    if(cohorts===null||outcomes===null||input.segments.length!==18)return null;
    const items={};
    for(const raw of input.segments){
      if(!raw||!HORIZONS.includes(raw.horizonHours)||!SEGMENTS.includes(raw.segment))return null;
      const id=String(raw.horizonHours)+':'+raw.segment;
      if(items[id])return null;
      const samples=nint(raw.samples),weeks=nint(raw.reportWeeks);
      const matured=nint(raw.maturedCohorts),unevaluated=nint(raw.unevaluatedMatured);
      const coverage=raw.coveragePct===null?pct(null):pct(raw.coveragePct);
      if(samples===null||weeks===null||matured===null||unevaluated===null||
         samples>matured||unevaluated!==matured-samples||
         weeks>samples|| (matured===0?coverage!==null:coverage===null)||
         !VERDICTS.includes(raw.verdict)||
         (raw.verdict===VERDICTS[1]&&(samples<30||weeks<8)))return null;
      const hit=samples?pct(raw.directionHitPct):null;
      const ci=raw.wilson95Pct;
      const low=samples&&Array.isArray(ci)&&ci.length===2?pct(ci[0]):null;
      const high=samples&&Array.isArray(ci)&&ci.length===2?pct(ci[1]):null;
      const mean=samples?finite(raw.meanDirectionalBps):null;
      const benchmark=samples?finite(raw.meanLongBenchmarkBps):null;
      const favorable=samples?finite(raw.meanFavorableBps):null;
      const adverse=samples?finite(raw.meanAdverseBps):null;
      if(samples&&(hit===null||low===null||high===null||low>high||
          mean===null||benchmark===null||favorable===null||adverse===null||
          favorable<0||adverse>0))return null;
      items[id]={samples,weeks,matured,unevaluated,coverage,verdict:raw.verdict,
        hit,low,high,mean,benchmark,favorable,adverse};
    }
    if(Object.keys(items).length!==18)return null;
    return {cohorts,outcomes,items};
  }
  function formatPercent(value){
    return value===null?'—':value.toLocaleString('it-IT',{minimumFractionDigits:1,maximumFractionDigits:1})+'%';
  }
  function formatBps(value){
    return value===null?'—':(value>0?'+':'')+
      value.toLocaleString('it-IT',{minimumFractionDigits:1,maximumFractionDigits:2})+' bp';
  }
  const api={read,formatPercent,formatBps,HORIZONS,SEGMENTS};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  root.REMURA_STAT_VALIDATION=api;
})(typeof window!=='undefined'?window:globalThis);
