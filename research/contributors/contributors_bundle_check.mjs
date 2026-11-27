// REMURA Contributors v0.31 LAB — 16/11/2026 09:08 CET
// Reproducible offline check only. No network, npm, Wrangler, writes or deployment.
import {readFileSync} from "node:fs";
import {createHash} from "node:crypto";
const header="// REMURA Contributors v0.31 LAB — 16/11/2026 09:08 CET";
const map=Object.freeze({
 "/":["text/html; charset=utf-8","contributors_candidate.html"],
 "/contributors_candidate.css":["text/css; charset=utf-8","contributors_candidate.css"],
 "/contributors_candidate_ui.mjs":["text/javascript; charset=utf-8","contributors_candidate_ui.mjs"],
 "/contributors_candidate_client.mjs":["text/javascript; charset=utf-8","contributors_candidate_client.mjs"]
});
const files=Object.freeze([
 "contributors_candidate.html","contributors_candidate.css","contributors_candidate_ui.mjs","contributors_candidate_client.mjs",
 "contributors_candidate_assets.mjs","contributors_worker_candidate.mjs","http_access_candidate.mjs","access_binding_candidate.mjs",
 "operation_intent_candidate.mjs","d1_access_candidate.mjs","d1_lab_adapter.mjs","d1_lab_review.mjs","d1_access_candidate.sql"]);
const hash=b=>createHash("sha256").update(b).digest("hex");
function local(n){return readFileSync(new URL("./"+n,import.meta.url));}
function build(read=local){
 const data=Object.fromEntries(files.map(n=>{
  const b=read(n);if(!Buffer.isBuffer(b)||b.length<1||b.length>131072)throw Error("bad_file");
  return [n,b];
 }));
 const assets=Object.fromEntries(Object.entries(map).map(([p,[mime,n]])=>[p,{mime,body:data[n].toString("utf8")}]));
 const expected=header+"\n// Generated exact local assets; no user data or dynamic injection.\nexport const assets=Object.freeze("+JSON.stringify(assets)+");\n";
 if(!data["contributors_candidate_assets.mjs"].equals(Buffer.from(expected)))throw Error("asset_drift");
 for(const [n,b] of Object.entries(data)){
  if(!n.endsWith(".mjs")||n==="contributors_candidate_assets.mjs")continue;
  // Static source audit is intentionally not a general JS parser or an SBOM.
  for(const m of b.toString("utf8").matchAll(/(?:\bfrom\s*|\bimport\s*)["']([^"']+)["']/g)){
   if(!m[1].startsWith("./")||!files.includes(m[1].slice(2)))throw Error("unexpected_import");
  }
 }
 const entries=files.map(n=>({file:n,bytes:data[n].length,sha256:hash(data[n])}));
 return {kind:"REMURA_CONTRIBUTORS_OFFLINE_MANIFEST",version:"0.31 LAB",files:entries,manifest_sha256:hash(JSON.stringify(entries))};
}
export {build,files};
if(process.argv[1]?.endsWith("/contributors_bundle_check.mjs")){
 console.log(JSON.stringify(build(),null,2));
}
