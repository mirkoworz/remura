// REMURA Filone D v1.74 evidence, 24/11/2026 00:11 CET.
// Six public Pages GETs exactly, no retries, Cloudflare API, credentials, CFTC
// queries, deploys or private data. Compares deployed bytes to reviewed Git blobs
// plus the explicit disabled-Firebase preview substitution.
import {readFileSync,writeFileSync} from "node:fs";
import {createHash} from "node:crypto";
const BASE="https://remura-lab-v1731-iphone.pages.dev";
const CHECKS=Object.freeze([
  {remote:"/",local:"index.html",kind:"home"},
  {remote:"/shark-cockpit",local:"shark-cockpit.html",kind:"canonical_cockpit"},
  {remote:"/shark-cockpit.js",local:"shark-cockpit.js",kind:"cockpit_logic"},
  {remote:"/shark-cockpit-core.js",local:"shark-cockpit-core.js",kind:"cftc_core"},
  {remote:"/data/myfxbook/latest.json",local:"data/myfxbook/latest.json",kind:"retail_snapshot"},
  {remote:"/capital-cloud-config.js",kind:"firebase_disabled_preview"}
]);
const NULL_FIREBASE=Buffer.from("/* REMURA isolated preview only. No production Firebase/Google auth. */\nwindow.REMURA_FIREBASE_CONFIG = null;\n");
const digest=b=>createHash("sha256").update(b).digest("hex");
const report={type:"REMURA_PAGES_DEPLOYED_BYTES_ATTESTATION",sourceVersion:"1.73.1",
  host:new URL(BASE).hostname,readOnly:true,noRetries:true,requests:0,
  timeUtc:new Date().toISOString(),results:[]};
for(const spec of CHECKS){
  const x={path:spec.remote,kind:spec.kind,ok:false};
  try{
    const uri=new URL(spec.remote,BASE);
    if(uri.origin!==BASE)throw Error("CROSS_ORIGIN");
    const res=await fetch(uri,{method:"GET",redirect:"manual",credentials:"omit",
      headers:{Accept:"*/*"},signal:AbortSignal.timeout(12000)});
    report.requests++;
    x.status=res.status;
    if(res.status!==200)throw Error("UNEXPECTED_HTTP_STATUS");
    const declared=Number(res.headers.get("content-length")||0);
    if(declared>2000000)throw Error("OVERSIZE_DECLARED");
    const remote=Buffer.from(await res.arrayBuffer());
    if(remote.length>2000000)throw Error("OVERSIZE_BODY");
    const local=spec.kind==="firebase_disabled_preview"?NULL_FIREBASE:readFileSync(spec.local);
    x.deployedSha256=digest(remote);x.expectedSha256=digest(local);
    x.bytes=remote.length;
    x.ok=x.deployedSha256===x.expectedSha256;
    if(!x.ok)x.error="BYTES_DIFFER_FROM_REVIEWED_SOURCE";
  }catch(e){x.error=(e?.message||"FETCH_FAILED").slice(0,100)}
  report.results.push(x);
  console.log(x.kind+": "+(x.ok?"EXACT_MATCH":"NOT_ATTESTED")+
    " HTTP "+(x.status??"NETWORK_ERROR")+" "+(x.error??""));
}
report.passed=report.results.filter(x=>x.ok).length;
report.failed=CHECKS.length-report.passed;
report.verdict=report.failed===0?"SIX_PUBLIC_ASSETS_MATCH_REVIEWED_BLOBS":"DEPLOYED_ASSETS_NOT_ATTESTED";
writeFileSync("remura-v174-pages-asset-digests.json",JSON.stringify(report,null,2)+"\n");
console.log("REMURA_DEPLOY_INTEGRITY="+report.verdict+" "+report.passed+"/"+CHECKS.length);
if(report.failed)process.exitCode=1;
