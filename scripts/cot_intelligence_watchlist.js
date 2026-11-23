#!/usr/bin/env node
/* REMURA B v20.8 LAB — offline-only watchlist CLI.
 * Reads CFTC-only snapshot already exported from an OFFLINE SQLite COPY.
 * Does not fetch data, write files, access secrets or use market prices.
 */
"use strict";
const fs=require("node:fs");
const watch=require("../cot-intelligence-watchlist.js");

function parseArgs(args){
 const allowed=new Set(["--input","--now","--as-of","--window"]);
 const values={};
 for(let i=0;i<args.length;i+=2){
  const name=args[i],value=args[i+1];
  if(!allowed.has(name)||!value||values[name]!==undefined)
   throw new Error("INVALID_ARGUMENTS");
  values[name]=value;
 }
 if(!values["--input"]||!values["--now"])throw Error("INPUT_AND_NOW_REQUIRED");
 return values;
}
function run(args){
 const opts=parseArgs(args);
 const stat=fs.statSync(opts["--input"]);
 if(!stat.isFile()||stat.size>8_000_000||stat.size===0)throw Error("INVALID_INPUT_FILE");
 const snapshot=JSON.parse(fs.readFileSync(opts["--input"],"utf8"));
 const result=watch.build(snapshot,{
  nowUtc:opts["--now"],
  ...(opts["--as-of"]?{observedAt:opts["--as-of"]}:{}),
  ...(opts["--window"]?{window:Number(opts["--window"])}:{})
 });
 return result;
}
if(require.main===module){
 try{process.stdout.write(JSON.stringify(run(process.argv.slice(2)),null,2)+"\n");}
 catch(err){process.stderr.write("REMURA_B_OFFLINE_REFUSED: "+(err.code||err.message)+"\n");
  process.exitCode=2;}
}
module.exports={run,parseArgs};
