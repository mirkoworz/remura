// REMURA v1.73.1 — 24/11/2026, Europe/Rome.
// Follow-up ONLY for the HTTP 308 on /shark-cockpit.html from the 10/11
// public smoke. TWO HTTPS GETs exactly, no retries and no other endpoints.
// No secrets, no cloud control-plane actions, no deploy.
import {writeFileSync} from "node:fs";
const BASE=new URL("https://remura-lab-v1731-iphone.pages.dev/");
const first=new URL("/shark-cockpit.html",BASE);
const info={host:BASE.hostname,check:"CLOUDFLARE_PAGES_CANONICAL_REDIRECT",
  requests:0,passed:false};
try{
  const a=await fetch(first,{method:"GET",redirect:"manual",credentials:"omit",
    signal:AbortSignal.timeout(12000)});
  info.requests++;
  info.initialStatus=a.status;
  if(a.status!==308&&a.status!==301&&a.status!==302)throw Error("EXPECTED_PAGES_REDIRECT");
  const loc=a.headers.get("location");
  if(!loc)throw Error("MISSING_LOCATION");
  const target=new URL(loc,first);
  if(target.origin!==BASE.origin||target.search||target.hash||
     !/^\/shark-cockpit\/?$/.test(target.pathname))
     throw Error("NONCANONICAL_REDIRECT_TARGET");
  info.redirectPath=target.pathname;
  const b=await fetch(target,{method:"GET",redirect:"manual",credentials:"omit",
    signal:AbortSignal.timeout(12000)});
  info.requests++;
  info.finalStatus=b.status;
  info.finalContentType=(b.headers.get("content-type")||"").split(";")[0];
  info.robotsHeader=b.headers.get("x-robots-tag")||null;
  if(b.status!==200||!info.finalContentType.includes("html"))throw Error("NON_HTML_CANONICAL_RESPONSE");
  const html=await b.text();
  if(html.length>250000)throw Error("OVERSIZE_HTML");
  if(!html.includes("SHARK COCKPIT v1.73.1")||
     !html.includes('src="./shark-cockpit.js?v=')||
     !html.includes("Myfxbook"))
     throw Error("WRONG_COCKPIT_HTML_ON_CANONICAL");
  info.passed=true;
}catch(e){info.failure=String(e?.message||e).slice(0,120)}
writeFileSync("remura-canonical-v173.json",JSON.stringify(info,null,2)+"\n");
console.log("REMURA_PAGES_CANONICAL="+(info.passed?"PASS":"FAIL")+" "+
  JSON.stringify(info));
if(!info.passed)process.exitCode=1;
