/* REMURA v1.46: strict parser for private, paired market research. */
(function(root){
  'use strict';
  const pct=v=>typeof v==='number'&&Number.isFinite(v)&&v>=0&&v<=100;
  const finite=v=>typeof v==='number'&&Number.isFinite(v);
  const integer=v=>Number.isSafeInteger(v)&&v>=0;
  const verdicts=['Campione insufficiente','Descrittivo, non prova predittiva'];
  function group(x){
    if(!x||!integer(x.cohortsMatured)||!integer(x.pairedSamples)||
       !integer(x.unpairedMatured)||!integer(x.reportWeeksPaired)||
       x.pairedSamples+x.unpairedMatured!==x.cohortsMatured||
       x.reportWeeksPaired>x.pairedSamples)return null;
    const values=[];
    for(const key of ['calendar24','trading96']){
      const item=x[key],n=x.pairedSamples;
      if(!item||item.samples!==n||item.reportWeeks!==x.reportWeeksPaired||
         !verdicts.includes(item.verdict)||
         (item.verdict===verdicts[1]&&(n<30||item.reportWeeks<8)))return null;
      if(!n){
        if(['directionHitPct','wilson95Pct','meanDirectionalBps',
             'meanLongBenchmarkBps'].some(k=>item[k]!=null))return null;
      }else{
        if(!pct(item.directionHitPct)||
           !Array.isArray(item.wilson95Pct)||item.wilson95Pct.length!==2||
           !pct(item.wilson95Pct[0])||!pct(item.wilson95Pct[1])||
           item.wilson95Pct[0]>item.wilson95Pct[1]||
           !finite(item.meanDirectionalBps)||!finite(item.meanLongBenchmarkBps)||
           !finite(item.meanFavorableBps)||!finite(item.meanAdverseBps)||
           item.meanFavorableBps<0||item.meanAdverseBps>0)return null;
      }
      values.push({metric:key,samples:n,weeks:item.reportWeeks,
        verdict:item.verdict,hit:n?item.directionHitPct:null,
        low:n?item.wilson95Pct[0]:null,high:n?item.wilson95Pct[1]:null,
        mean:n?item.meanDirectionalBps:null,baseline:n?item.meanLongBenchmarkBps:null});
    }
    const delta=x.deltaTradingMinusCalendarBps;
    if(n?(!finite(delta)||Math.abs(delta-(values[1].mean-values[0].mean))>0.03):delta!==null)return null;
    return {matured:x.cohortsMatured,matched:n,unmatched:x.unpairedMatured,
      weeks:x.reportWeeksPaired,delta:delta,values};
  }
  function read(input){
    if(!input||input.schema!=='remura-market-audit-v1'||
       input.mode!=='research_only'||input.noSyntheticCandles!==true||
       !Array.isArray(input.markets)||!Array.isArray(input.relationships)||
       input.relationships.length!==2||input.markets.length>38)return null;
    const total=group(input.total);
    if(!total)return null;
    const relations={};
    for(const item of input.relationships){
      if(!item||!['aligned','divergent'].includes(item.relationship)||
         Object.hasOwn(relations,item.relationship))return null;
      const parsed=group(item);
      if(!parsed)return null;
      relations[item.relationship]=parsed;
    }
    if(!relations.aligned||!relations.divergent||
       relations.aligned.matured+relations.divergent.matured!==total.matured||
       relations.aligned.matched+relations.divergent.matched!==total.matched)return null;
    const markets=[],seen=new Set();
    for(const item of input.markets){
      if(!item||typeof item.symbol!=='string'||!/^[A-Z0-9]{3,12}$/.test(item.symbol)||
         seen.has(item.symbol))return null;
      seen.add(item.symbol);
      const parsed=group(item);
      if(!parsed)return null;
      markets.push({symbol:item.symbol,...parsed});
    }
    if(markets.reduce((s,m)=>s+m.matured,0)!==total.matured||
       markets.reduce((s,m)=>s+m.matched,0)!==total.matched)return null;
    return {total,relations,markets:markets.sort((a,b)=>a.symbol.localeCompare(b.symbol))};
  }
  const api={read};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  root.REMURA_MARKET_AUDIT=api;
})(typeof window!=='undefined'?window:globalThis);
