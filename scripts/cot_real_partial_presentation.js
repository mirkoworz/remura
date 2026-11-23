#!/usr/bin/env node
/* REMURA B v21.4 LAB — read-only presentation contract for authenticated-by-log,
 * PARTIAL CFTC real values recovered from previous run. It does not invoke API,
 * perform parity, create trading ideas, imply 28 actual cross numbers or deploy.
 */
"use strict";
const fs=require("node:fs");
const path=require("node:path");
const SCHEMA="remura-b-cftc-partial-presentation-v1";
const VERSION="B_V21_4_LAB";
const PROOF=path.resolve(__dirname,"../research/real-proofs/REMURA-B-CFTC-20261123-STDOUT-PARTIAL-EXCERPT.json");

function dateUtc(s){
 if(typeof s!=="string"||!/^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(?:\\.\\d+)?Z$/.test(s)||!Number.isFinite(Date.parse(s)))
  throw Error("explicit_utc_required");
 return Date.parse(s);
}
function build(p,{nowUtc}={}){
 const now=dateUtc(nowUtc);
 if(!p||p.schema!=="remura-b-cftc-stdout-excerpt-v1"||p.version!=="B_V21_3_LAB")
  throw Error("not_the_existing_partial_stdout_proof");
 const e=p.evidence||{},g=p.groupSummary||{},d=p.period||{};
 if(e.githubRunId!==45206837974||e.githubJobId!==137804869184||
    e.sourceStdoutProofMarker!=="REMURA_B_PUBLIC_CFTC_PROOF"||
    e.sourceSnapshotRowsReported!==980||
    e.fullSourceSnapshotRecoverableFromThisExcerpt!==false||
    e.excerptEquivalentToOriginalFullSnapshot!==false||
    e.localFirstSeenTimeAttested!==false||
    e.fullRawRowValuesAvailable!==false||
    e.dataIsPublicWeeklyFuturesNotLiveOrders!==true||
    typeof e.fullSnapshotRowsSha256ReportedByRun!=="string"||
    !/^[a-f0-9]{64}$/.test(e.fullSnapshotRowsSha256ReportedByRun)||
    dateUtc(e.sourceSnapshotReadAtUtc)>now||
    d.latestReportDate!=="2026-11-17"||d.previousReportDate!=="2026-11-10"||
    g.crossesPrintedInRun!==5||g.totalCrossesComputedInPastRun!==28||
    g.tffDirectPrintedInRun!==4||g.disaggDirectPrintedInRun!==3||
    g.crossesStatisticallyIndependent!==false)
  throw Error("partial_provenance_unverified_or_incomplete");
 const rows=p.observations;
 if(!Array.isArray(rows)||rows.length!==12)throw Error("not_exactly_twelve_logged_rows");
 const symbols=new Set();
 const groups={tff_fx:[],tff_direct:[],disagg_direct:[]};
 for(const x of rows){
  if(!x||typeof x.symbol!=="string"||!/^[A-Z0-9]{3,8}$/.test(x.symbol)||
     symbols.has(x.symbol)||x.reportDate!==d.latestReportDate||
     !Number.isFinite(x.weeklyCategoryANetChangePp)||
     !Number.isFinite(x.categoryGapPp)||
     Math.abs(x.weeklyCategoryANetChangePp)>200||
     Math.abs(x.categoryGapPp)>400)
     throw Error("invalid_cftc_stdout_entry");
  symbols.add(x.symbol);
  let key;
  if(x.dataset==="tff"&&x.calculationType==="synthetic_fx_relative"&&x.underlyingPositioningNotDirectForex===true)
   key="tff_fx";
  else if(x.dataset==="tff"&&x.calculationType==="futures_reference"&&x.underlyingPositioningNotDirectForex===false)
   key="tff_direct";
  else if(x.dataset==="disagg"&&x.calculationType==="futures_reference"&&x.underlyingPositioningNotDirectForex===false)
   key="disagg_direct";
  else throw Error("unexpected_cftc_group");
  groups[key].push({symbol:x.symbol,weeklyNetDeltaPp:x.weeklyCategoryANetChangePp,
                   categoryGapPp:x.categoryGapPp,reportDate:x.reportDate,
                   sourceType:key==="tff_fx"?"SYNTHETIC_FUTURES_CROSS":"DIRECT_FUTURES_REFERENCE"});
 }
 if(groups.tff_fx.length!==5||groups.tff_direct.length!==4||groups.disagg_direct.length!==3)
   throw Error("logged_group_count_mismatch");
 const ageDays=Math.floor((now-Date.parse(d.latestReportDate+"T00:00:00Z"))/86400000);
 if(ageDays<0)throw Error("future_report");
 return {
  schema:SCHEMA,version:VERSION,mode:"HISTORICAL_DESCRIPTIVE_PARTIAL_ONLY",
  state:ageDays>14?"STALE_HISTORIC_PARTIAL":"HISTORIC_PARTIAL",
  dataReportDate:d.latestReportDate,priorReportDate:d.previousReportDate,
  sourceReadAtUtc:e.sourceSnapshotReadAtUtc,runId:e.githubRunId,
  publicEvidenceUrl:"https://github.com/mirkoworz/remura/actions/runs/45206837974",
  ageDaysFromCftcReportDate:ageDays,reportDateNotReleaseDate:true,
  provenance:"EXISTING_SUCCESSFUL_GITHUB_AUDIT_STDOUT_NOT_RAW_RECOMPUTATION",
  raw980SourceRowsRecovered:false,numberOfDisplayedObservations:12,
  numberOfDisplayedFxCrosses:5,numberOfTotalFxCrossesRecomputed:0,
  firstSeenAuthenticated:false,privatePublicParityVerified:false,
  institutionalLiveOrders:false,forecastOrTradeSignals:false,alphaProven:false,
  labels:{tffA:"Asset Manager/Institutional",tffB:"Leveraged Funds",
          disaggA:"Managed Money",disaggB:"Producer/Merchant",
          weeklyNetDeltaPp:"Net category-A weekly change / futures OI, percentage points",
          categoryGapPp:"Net category-A vs category-B, percentage points"},
  groups
 };
}
function main(argv=process.argv.slice(2)){
 if(argv.length!==0 && !(argv.length===2&&argv[0]==="--now-utc"))
  throw Error("only_optional_clock_allowed");
 const asOf=argv.length===2?argv[1]:new Date().toISOString();
 const x=JSON.parse(fs.readFileSync(PROOF,"utf8"));
 const out=build(x,{nowUtc:asOf});
 process.stdout.write(JSON.stringify(out,null,2)+"\n");
}
if(require.main===module){try{main();}catch(e){console.error("REMURA_B_PARTIAL_READONLY_REJECTED");process.exitCode=2;}}
module.exports={build,SCHEMA,VERSION};
