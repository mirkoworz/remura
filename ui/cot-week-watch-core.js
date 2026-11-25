/* REMURA v1.50: verify private CFTC week-watch metadata before rendering. */
(function(root){
 'use strict';
 const kinds=['tff','disagg'];
 const states=['ok','disabled','no_data','incomplete','timestamp_review',
               'source_error','age_review','status_review'];
 const n=x=>Number.isSafeInteger(x)&&x>=0;
 const week=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&
  !Number.isNaN(Date.parse(x+'T00:00:00Z'));
 const stamp=x=>x===null||(typeof x==='string'&&
  /^\d{4}-\d{2}-\d{2}T/.test(x)&&Number.isFinite(Date.parse(x)));
 const codes={tff:["099741","096742","097741","232741","090741","092741",
   "112741","13874A","209742","124603","098662"],
  disagg:["088691","084691","067651"]};
 const metadata=g=>g&&n(g.present)&&n(g.expected)&&
  n(g.firstSeenKnown)&&n(g.firstSeenUnknown)&&n(g.invalidFirstSeen)&&
  n(g.recentlyCapturedRows48h)&&Array.isArray(g.missingCodes)&&
  g.expected>=g.present&&g.present===g.firstSeenKnown+g.firstSeenUnknown+g.invalidFirstSeen&&
  g.recentlyCapturedRows48h<=g.firstSeenKnown;
 function read(x){
  if(!x||x.schema!=='remura-cot-week-watch-v1'||x.mode!=='diagnostic_only'||
     x.collectorCadenceHours!==6||x.officialReleaseTimeVerified!==false||
     x.captureMeans!=='first_local_capture_not_publication'||
     typeof x.enabled!=='boolean'||!['ready','waiting','attention','disabled'].includes(x.status)||
     (x.status==='disabled')!==(!x.enabled)||
     x.expectedContracts!==14||typeof x.latestWeekLocallyCapturedIn48h!=='boolean'||
     typeof x.hasTwoCompleteReferenceWeeks!=='boolean'||
     x.latestCommonCompleteWeek!==null&&!week(x.latestCommonCompleteWeek)||
     x.previousCommonCompleteWeek!==null&&!week(x.previousCommonCompleteWeek)||
     x.hasTwoCompleteReferenceWeeks!==(x.previousCommonCompleteWeek!==null)||
     !Array.isArray(x.weeks)||x.weeks.length>6||!x.datasets)return null;
  const groups={};
  for(const kind of kinds){
   const g=x.datasets[kind],expected=codes[kind];
   if(!metadata(g)||g.expected!==expected.length||
      !states.includes(g.state)||!['ok','error','not_collected','unknown'].includes(g.collectorState)||
      g.latestCotWeek!==null&&!week(g.latestCotWeek)||
      (g.latestCotWeek===null)!==(g.reportAgeDays===null)||
      g.reportAgeDays!==null&&!n(g.reportAgeDays)||
      !stamp(g.lastCollectorAttemptUtc)||!stamp(g.lastSuccessUtc)||
      !g.missingCodes.every(v=>expected.includes(v))||
      new Set(g.missingCodes).size!==g.missingCodes.length||
      g.missingCodes.length!==g.expected-g.present)return null;
   groups[kind]=g;
  }
  if(x.status==='ready'&&(kinds.some(k=>groups[k].state!=='ok')||
      !groups.tff.latestCotWeek||
      groups.tff.latestCotWeek!==groups.disagg.latestCotWeek))return null;
  if(x.latestWeekLocallyCapturedIn48h&&(
     !x.latestCommonCompleteWeek||
     groups.tff.latestCotWeek!==x.latestCommonCompleteWeek||
     groups.disagg.latestCotWeek!==x.latestCommonCompleteWeek||
     kinds.some(k=>groups[k].recentlyCapturedRows48h<1)))return null;
  const weeks=[],seen=new Set();
  for(const item of x.weeks){
   if(!item||!week(item.cotWeek)||seen.has(item.cotWeek)||
      typeof item.complete!=='boolean'||!item.datasets)return null;
   seen.add(item.cotWeek);
   const report={week:item.cotWeek,complete:item.complete,datasets:{}};
   for(const kind of kinds){
    const g=item.datasets[kind],expected=codes[kind];
    if(!metadata(g)||g.expected!==expected.length||
      !g.missingCodes.every(v=>expected.includes(v))||
      new Set(g.missingCodes).size!==g.missingCodes.length||
      g.missingCodes.length!==g.expected-g.present)return null;
    report.datasets[kind]=g;
   }
   if(report.complete!==(kinds.every(k=>report.datasets[k].missingCodes.length===0)))return null;
   weeks.push(report);
  }
  if(x.latestCommonCompleteWeek!==null&&weeks.length&&
     weeks[0].week===x.latestCommonCompleteWeek&&!weeks[0].complete)return null;
  return {enabled:x.enabled,status:x.status,
   lastComplete:x.latestCommonCompleteWeek,
   previousComplete:x.previousCommonCompleteWeek,
   hasTwoWeeks:x.hasTwoCompleteReferenceWeeks,
   newCapture:x.latestWeekLocallyCapturedIn48h,
   datasets:groups,weeks};
 }
 // Local acquisition attestation, derived solely from the unmodified v1.49 API.
 // This proves that capture timestamps EXIST for every selected row;
 // it does NOT establish official release time, net profitability or predictive skill.
 function captureSummary(parsed){
  if(!parsed||!Array.isArray(parsed.weeks)||!parsed.datasets)return null;
  const newest=parsed.weeks[0];
  if(!newest)return {
   state:'waiting',cotWeek:null,traced:0,total:14,
   tff:0,disagg:0,missing:14,invalid:0,
   lastComplete:parsed.lastComplete||null,collectorReady:false
  };
  const t=newest.datasets.tff,d=newest.datasets.disagg;
  if(!t||!d)return null;
  const traced=t.firstSeenKnown+d.firstSeenKnown;
  const invalid=t.invalidFirstSeen+d.invalidFirstSeen;
  const present=t.present+d.present;
  const complete=newest.complete&&present===14&&
   newest.week===parsed.lastComplete&&
   ['tff','disagg'].every(k=>parsed.datasets[k].latestCotWeek===newest.week);
  let state;
  if(!complete)state='partial';
  else if(invalid)state='invalid';
  else if(traced===14)state='fully_tracked';
  else if(traced>0)state='partly_tracked';
  else state='legacy';
  return {state,cotWeek:newest.week,traced,total:14,
   tff:t.firstSeenKnown,disagg:d.firstSeenKnown,
   present,missing:14-present,invalid,
   lastComplete:parsed.lastComplete||null,
   collectorReady:parsed.enabled&&parsed.status==='ready'};
 }
 const api={read,captureSummary};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
 root.REMURA_COT_WEEK_WATCH=api;
})(typeof window!=='undefined'?window:globalThis);
