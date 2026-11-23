#!/usr/bin/env node
/* REMURA Filone B v21.1 LAB — 23/11/2026 Europe/Rome
 * Read ONLY an existing offline CFTC JSON snapshot. Print a presentation-ready
 * DESCRIPTIVE 7-currency/28-overlapping-cross contract to stdout. No HTTP,
 * SQLite, trading, writes, signal engine, future prices or authentication.
 */
"use strict";
const fs=require("node:fs");
const path=require("node:path");
const fx=require("../cot-intelligence-fx-factors.js");
const MAX_BYTES=8_000_000;
const VERSION="B_V21_1_LAB";
const SCHEMA="remura-cot-dashboard-fx-v1";
function utc(value){
 if(typeof value!=="string"||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/.test(value)
    ||!Number.isFinite(Date.parse(value)))throw Error("EXPLICIT_UTC_TIME_REQUIRED");
 return new Date(value).toISOString();
}
function render(snapshot,{nowUtc,observedAt}={}){
 const now=utc(nowUtc);
 const cutoff=observedAt===undefined?undefined:utc(observedAt);
 const source=snapshot&&snapshot.source;
 const parsed=fx.build(snapshot,{nowUtc:now,...(cutoff?{observedAt:cutoff}:{})});
 const state=parsed.state;
 const out={
  schema:SCHEMA,version:VERSION,mode:parsed.mode,
  generatedAtUtc:now,
  state,reason:state==="blocked"?parsed.reason:null,
  sourceDescription:parsed.source,
  publicApiReadAtUtc:parsed.publicReadAtUtc??null,
  capturedAsOfUtc:cutoff??null,
  latestCftcReportDate:parsed.reportDate??null,
  previousCftcReportDate:parsed.previousReportDate??null,
  underlyingCount:state==="descriptive_ready"?7:0,
  overlappingFxCrossCount:state==="descriptive_ready"?28:0,
  categoryLabels:{
   dataset:"CFTC TFF Futures Only",
   first:"Asset Manager/Institutional",
   second:"Leveraged Funds"
  },
  timeClaims:{
   reportDateIsNotPublicationDate:true,
   publicReadIsNotHistoricAvailability:true,
   privateFirstSeenIsSelfReported:true,
   sourceAuthenticatedByExporter:false
  },
  use:"DISPLAY_ONLY_WEEKLY_AGGREGATE_FUTURES_NOT_TRADING_SIGNALS",
  units:{netAndWeeklyDelta:"percentage_points_of_open_interest",
         openInterest:"futures_contracts",cotIndex:"0_to_100_not_probability"},
  factors:[],crosses:[],
  cautions:["7 CFTC currency futures, not 28 statistically independent bets",
            "Crosses derive from two currencies versus USD, NOT spot position",
            "Weekly report is not live institutional order flow",
            "No forward price, executed volume, forecast or profitability verified"]
 };
 if(state!=="descriptive_ready")return out;
 out.factors=parsed.factors.map(r=>({
  currency:r.currency,cftcContractCode:r.code,
  reportDate:r.reportDate,previousReportDate:r.previousReportDate,
  assetManagerNetPctOi:r.netAssetManagersPp,
  leveragedFundsNetPctOi:r.netLeveragedFundsPp,
  weeklyAssetManagerChangePp:r.weeklyAssetManagersPp,
  weeklyLeveragedFundsChangePp:r.weeklyLeveragedFundsPp,
  openInterestContracts:r.openInterestContracts,
  openInterestChangeContracts:r.openInterestDeltaContracts,
  cotIndex52AssetManagers:r.cotIndex52AssetManagers?.value??null,
  historyStatus:r.historicalStatus,
  localFirstSeenUtc:r.localFirstSeenAtUtc,
  previousLocalFirstSeenUtc:r.previousLocalFirstSeenAtUtc
 }));
 out.crosses=parsed.pairs.map(r=>({
  symbol:r.symbol,reportDate:r.reportDate,
  legs:r.componentSigns,
  assetManagerWeeklyRelativeChangePp:r.weeklyAssetManagersPp,
  leveragedFundsWeeklyRelativeChangePp:r.weeklyLeveragedFundsPp,
  derivedNotDirectSpot:true
 }));
 return out;
}
function argsOf(argv){
 const flags={};
 for(let i=0;i<argv.length;i+=2){
  const key=argv[i],value=argv[i+1];
  if(!["--snapshot","--now-utc","--observed-at"].includes(key)
     ||!value||value.startsWith("--")||Object.hasOwn(flags,key))
    throw Error("INVALID_OFFLINE_ARGUMENTS");
  flags[key]=value;
 }
 if(!flags["--snapshot"]||!flags["--now-utc"])throw Error("SNAPSHOT_AND_NOW_UTC_REQUIRED");
 return flags;
}
function readOffline(filename){
 const filenameReal=fs.realpathSync(path.resolve(filename));
 const st=fs.statSync(filenameReal);
 if(!st.isFile()||st.size<=0||st.size>MAX_BYTES)
   throw Error("INVALID_OR_OVERSIZE_OFFLINE_SNAPSHOT");
 return JSON.parse(fs.readFileSync(filenameReal,"utf8"));
}
function main(argv=process.argv.slice(2)){
 if(!argv.length){
  console.log(JSON.stringify({schema:SCHEMA,version:VERSION,
   status:"NO_OFFLINE_CFTC_SNAPSHOT_NO_REAL_FACTORS",
   factors:[],crosses:[],networkCalls:0,filesWritten:0}));
  return 0;
 }
 const flags=argsOf(argv);
 const report=render(readOffline(flags["--snapshot"]),{
  nowUtc:flags["--now-utc"],observedAt:flags["--observed-at"]
 });
 console.log(JSON.stringify(report,null,2));
 return 0;
}
if(require.main===module){
 try{process.exitCode=main();}
 catch(err){console.error("REMURA_COT_OFFLINE_EXPORT_REJECTED: "+err.message);process.exitCode=2;}
}
module.exports={render,argsOf,readOffline,main,SCHEMA,VERSION};
