/* REMURA v1.47 — validation for private weekly evidence, not trade logs. */
(function(root){
 'use strict';
 const positiveInt=x=>Number.isSafeInteger(x)&&x>=0;
 const number=x=>typeof x==='number'&&Number.isFinite(x);
 const rounded=(a,b)=>Math.abs(a-b)<0.031;
 const validWeek=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&
   !Number.isNaN(Date.parse(x+'T00:00:00Z'));
 function metric(m,side){
   if(!m||
      !['directionalBps','benchmarkLongBps','favorableBps','adverseBps'].every(k=>number(m[k]))||
      typeof m.directionHit!=='boolean'||m.directionHit!==(m.directionalBps>0)||
      m.favorableBps<0||m.adverseBps>0||
      !rounded(m.directionalBps,(side==='long'?1:-1)*m.benchmarkLongBps))return null;
   return {directional:m.directionalBps,benchmark:m.benchmarkLongBps,
     favorable:m.favorableBps,adverse:m.adverseBps,hit:m.directionHit};
 }
 function group(g,rows){
   if(!g||!positiveInt(g.samples)||!positiveInt(g.weeks)||
      !positiveInt(g.positiveCalendar)||!positiveInt(g.negativeOrFlatCalendar)||
      !positiveInt(g.positiveTraded)||g.samples!==rows.length||
      g.positiveCalendar+g.negativeOrFlatCalendar!==rows.length||
      g.positiveCalendar!==rows.filter(r=>r.calendar24.hit).length||
      g.positiveTraded!==rows.filter(r=>r.trading96.hit).length||
      g.weeks!==new Set(rows.map(r=>r.week)).size)return null;
   if(rows.length){
     if(!number(g.meanCalendarBps)||!number(g.meanTradedBps)||
        !rounded(g.meanCalendarBps,rows.reduce((s,r)=>s+r.calendar24.directional,0)/rows.length)||
        !rounded(g.meanTradedBps,rows.reduce((s,r)=>s+r.trading96.directional,0)/rows.length))return null;
   }else if(g.meanCalendarBps!==null||g.meanTradedBps!==null)return null;
   return {samples:g.samples,weeks:g.weeks,hits:g.positiveCalendar,
      misses:g.negativeOrFlatCalendar,mean:g.meanCalendarBps,
      tradedMean:g.meanTradedBps};
 }
 function read(input){
   if(!input||input.schema!=='remura-case-audit-v1'||
     input.mode!=='research_only'||input.noSyntheticCandles!==true||
     input.executionCostsIncluded!==false||
     input.scope!=='last_12_COT_reference_weeks'||
     !Array.isArray(input.cases)||!Array.isArray(input.weekly)||
     !positiveInt(input.totalEligibleWeeks)||!positiveInt(input.weeksShown)||
     !positiveInt(input.pairedCasesShown)||
     input.weekly.length>12||input.weekly.length!==input.weeksShown||
     input.weeksShown>input.totalEligibleWeeks||
     input.pairedCasesShown!==input.cases.length||input.cases.length>456||
     !input.caseCountByRelationship)return null;
   const cases=[],keys=new Set();
   for(const r of input.cases){
     if(!r||typeof r.symbol!=='string'||!/^[A-Z0-9]{3,12}$/.test(r.symbol)||
       !validWeek(r.cotWeek)||!['long','short'].includes(r.cotSide)||
       !['aligned','divergent'].includes(r.initialRelationship))return null;
     const key=r.symbol+'|'+r.cotWeek;
     if(keys.has(key))return null;
     keys.add(key);
     const calendar24=metric(r.calendar24,r.cotSide);
     const trading96=metric(r.trading96,r.cotSide);
     if(!calendar24||!trading96||!number(r.deltaTradingMinusCalendarBps)||
       !rounded(r.deltaTradingMinusCalendarBps,
         trading96.directional-calendar24.directional))return null;
     cases.push({symbol:r.symbol,week:r.cotWeek,side:r.cotSide,
       relation:r.initialRelationship,calendar24,trading96,delta:r.deltaTradingMinusCalendarBps});
   }
   if(!['aligned','divergent'].every(r=>positiveInt(input.caseCountByRelationship[r])&&
        input.caseCountByRelationship[r]===cases.filter(x=>x.relation===r).length))return null;
   const weekly=[],seen=new Set();
   for(const r of input.weekly){
     if(!r||!validWeek(r.cotWeek)||seen.has(r.cotWeek)||
       !positiveInt(r.maturedCohorts)||!positiveInt(r.pairedSamples))return null;
     seen.add(r.cotWeek);
     const casesWeek=cases.filter(x=>x.week===r.cotWeek);
     if(casesWeek.length!==r.pairedSamples||r.maturedCohorts<r.pairedSamples)return null;
     const aligned=group(r.aligned,casesWeek.filter(x=>x.relation==='aligned'));
     const divergent=group(r.divergent,casesWeek.filter(x=>x.relation==='divergent'));
     if(!aligned||!divergent)return null;
     weekly.push({week:r.cotWeek,matured:r.maturedCohorts,paired:r.pairedSamples,
       aligned,divergent});
   }
   if(weekly.reduce((s,r)=>s+r.paired,0)!==cases.length||
      new Set(cases.map(r=>r.week)).size>weekly.length||
      cases.some(r=>!seen.has(r.week)))return null;
   return {cases,weekly,totalWeeks:input.totalEligibleWeeks};
 }
 const api={read};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
 root.REMURA_CASE_AUDIT=api;
})(typeof window!=='undefined'?window:globalThis);
