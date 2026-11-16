// REMURA Contributors v0.27 LAB — 16/11/2026 07:24 CET
// Offline candidate direct Worker handler. No Wrangler config, deployment, bindings or public route.
// No Static Assets router; pass the original trusted ctx through to each handler.
import {assets} from "./contributors_candidate_assets.mjs";
import {accessBinding} from "./access_binding_candidate.mjs";
import {verifyGeneration} from "./operation_intent_candidate.mjs";
import {profile} from "./d1_access_candidate.mjs";
import {candidateRequest} from "./http_access_candidate.mjs";
const APIs=new Set(["/api/profile","/api/catalog","/api/intent","/api/submit","/api/receipts","/owner/queue","/owner/history","/owner/review"]);
const common=Object.freeze({
 "Cache-Control":"no-store, max-age=0","X-Content-Type-Options":"nosniff",
 "Referrer-Policy":"no-referrer","X-Frame-Options":"DENY",
 "Cross-Origin-Resource-Policy":"same-origin",
 "Permissions-Policy":"camera=(), microphone=(), geolocation=(), payment=()",
 "Content-Security-Policy":"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; form-action 'none'; frame-ancestors 'none'; base-uri 'none'; object-src 'none'"
});
const plain=(status)=>new Response("REMURA Contributors staging closed",{status,headers:{...common,"Content-Type":"text/plain; charset=utf-8"}});
async function workerCandidate(req,env,ctx){
 try{
  if(env?.WORKER_CANDIDATE_ENABLED!=="LAB_ONLY"||env.HTTP_CANDIDATE_ENABLED!=="LAB_ONLY"||env.STAGING_ENABLED!=="D1_CANDIDATE"||typeof env.STAGING_ORIGIN!=="string")return plain(403);
  const origin=new URL(env.STAGING_ORIGIN),url=new URL(req.url);
  if(origin.protocol!=="https:"||origin.origin!==env.STAGING_ORIGIN||origin.username||origin.password||req.url!==origin.origin+url.pathname||url.origin!==origin.origin)return plain(403);
  if(req.method==="POST"&&APIs.has(url.pathname))return await candidateRequest(req,env,ctx);
  if(req.method!=="GET"||!Object.hasOwn(assets,url.pathname))return plain(403);
  const a=await accessBinding(ctx,env);
  const limited=await env.CONTRIBUTORS_RATE_LIMITER.limit({key:a.subject});
  if(limited?.success===false)return plain(429);
  if(limited?.success!==true)return plain(403);
  // All four assets require trusted Access and current generation. Only HTML also
  // checks live durable role; other assets contain static code, no user records.
  await verifyGeneration(env);
  if(url.pathname==="/")await profile(ctx,env);
  const asset=assets[url.pathname];
  return new Response(asset.body,{status:200,headers:{...common,"Content-Type":asset.mime}});
 }catch{return plain(403);}
}
export {workerCandidate};
// Candidate only. No deployment config selects this module.
export default {fetch:workerCandidate};
