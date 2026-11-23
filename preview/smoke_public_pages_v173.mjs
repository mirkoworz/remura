// REMURA Shark Cockpit v1.73.1 LAB — 24/11/2026, Europe/Rome.
// A ONE-SHOT public-host verification: eleven bounded HTTPS GETs; NO retries,
// credentials, private endpoints, CFTC requests, Cloudflare API, deploy or merge.
// No response bodies are printed or kept in the output artifact.
import {writeFileSync} from "node:fs";
const BASE="https://remura-lab-v1731-iphone.pages.dev";
const TARGET=new URL(BASE);
const CHECKS=Object.freeze([
 {path:"/",type:"home"},
 {path:"/shark-cockpit.html",type:"cockpit"},
 {path:"/shark-cockpit.js",type:"cockpit_js"},
 {path:"/shark-cockpit-core.js",type:"core_js"},
 {path:"/shark-focus-ui.js",type:"focus_js"},
 {path:"/shark-cockpit.css",type:"cockpit_css"},
 {path:"/data/myfxbook/latest.json",type:"retail_snapshot"},
 {path:"/capital-cloud-config.js",type:"firebase_disabled"},
 {path:"/robots.txt",type:"noindex_robot"},
 {path:"/sw.js",type:"no_service_worker"},
 {path:"/private-api/health",type:"no_private_api"}
]);
const report={project:"REMURA",version:"1.73.1",host:TARGET.hostname,kind:"PUBLIC_PAGES_SMOKE_ONE_SHOT",
  readOnly:true,credentialsUsed:false,automaticRetries:0,
  deploymentAttempted:false,startedUtc:new Date().toISOString(),checks:[]};
let errors=0;
for (const spec of CHECKS){
  const url=new URL(spec.path,TARGET);
  if(url.origin!==TARGET.origin)throw Error("OUT_OF_SCOPE_ORIGIN");
  const item={path:spec.path,check:spec.type,status:null,ok:false};
  try{
    const res=await fetch(url,{
      method:"GET",redirect:"manual",credentials:"omit",
      headers:{Accept:spec.type==="retail_snapshot"?"application/json":"text/html, */*;q=0.8"},
      signal:AbortSignal.timeout(12000)
    });
    item.status=res.status;
    item.contentType=(res.headers.get("content-type")||"").split(";")[0];
    item.xRobots=res.headers.get("x-robots-tag")||null;
    if(res.status>=300&&res.status<400)throw Error("UNEXPECTED_REDIRECT");
    if(Number(res.headers.get("content-length")||0)>2000000)throw Error("OVERSIZE_RESPONSE");
    const raw=await res.text();
    if(raw.length>2000000)throw Error("OVERSIZE_BODY");
    switch(spec.type){
      case "home":
        if(res.status!==200||!raw.includes("Aggiornamento v1.73.1 LAB")||
          !raw.includes('href="./shark-cockpit.html"'))
          throw Error("WRONG_HOME_VERSION_OR_LINK");
        break;
      case "cockpit":
        if(res.status!==200||!raw.includes("SHARK COCKPIT v1.73.1")||
          !raw.includes('src="./shark-cockpit.js?v='))
          throw Error("WRONG_COCKPIT_VERSION_OR_SCRIPTS");
        break;
      case "cockpit_js":
        if(res.status!==200||!raw.includes("publicreporting.cftc.gov")||
          !raw.includes('fetch("./data/myfxbook/latest.json"'))
          throw Error("COCKPIT_DATA_ADAPTER_MISSING");
        break;
      case "core_js":
        if(res.status!==200||!raw.includes("REMURA_SHARK_CORE"))
          throw Error("MISSING_CFTC_CORE");
        break;
      case "focus_js":
        if(res.status!==200||!raw.includes("REMURA_SHARK_FOCUS_UI"))
          throw Error("MISSING_WATCHLIST_UI");
        break;
      case "cockpit_css":
        if(res.status!==200||!raw.includes(".retail-panel"))
          throw Error("MISSING_COCKPIT_STYLES");
        break;
      case "retail_snapshot": {
        if(res.status!==200)throw Error("MISSING_RETAIL_JSON");
        const doc=JSON.parse(raw);
        if(doc.source!=="Myfxbook Community Outlook"||!Number.isFinite(Date.parse(doc.updatedAt||""))||
          typeof doc.symbols!=="object"||!doc.symbols)
          throw Error("WRONG_RETAIL_PROVENANCE");
        item.retailSource=doc.source;item.retailTimestamp=doc.updatedAt;
        break;
      }
      case "firebase_disabled":
        if(res.status!==200||!/window\.REMURA_FIREBASE_CONFIG\s*=\s*null\s*;/.test(raw)||
          raw.includes("AIza")||raw.includes("apiKey:"))
          throw Error("UNSAFE_FIREBASE_PREVIEW_CONFIG");
        break;
      case "noindex_robot":
        if(res.status!==200||!raw.includes("Disallow: /"))
          throw Error("ROBOTS_POLICY_MISSING");
        break;
      case "no_service_worker":
        if(res.status===200&&(/self\.addEventListener\s*\(/.test(raw)||
          item.contentType?.includes("javascript")))
          throw Error("SERVICE_WORKER_EXPOSED");
        item.note=res.status===200?"HTML_FALLBACK_NOT_SERVICE_WORKER":"ABSENT_OR_NOT_FOUND";
        break;
      case "no_private_api":
        if(res.status===200&&item.contentType==="application/json")
          throw Error("UNEXPECTED_PRIVATE_API_JSON");
        item.note=res.status===200?"NON_JSON_FALLBACK":"NO_PRIVATE_API";
        break;
    }
    item.ok=true;
  }catch(e){
    errors++;
    item.error=(e?.message||"PUBLIC_READ_FAILED").slice(0,100);
  }
  report.checks.push(item);
  console.log(spec.path+" "+(item.ok?"PASS":"FAIL")+" "+(item.status??"network-error")+
              (item.error?" "+item.error:""));
}
report.endedUtc=new Date().toISOString();
report.pass=report.checks.filter(x=>x.ok).length;
report.fail=errors;
report.result=errors===0?"PUBLIC_SHELL_CHECKS_PASS":"PUBLIC_SHELL_NOT_ATTESTED";
writeFileSync("remura-public-pages-v173-smoke.json",JSON.stringify(report,null,2)+"\n");
console.log("REMURA_HOST_CHECK="+report.result+" "+report.pass+"/"+CHECKS.length);
if(errors)process.exitCode=1;
