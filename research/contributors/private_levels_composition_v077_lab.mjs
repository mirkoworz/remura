// REMURA Contributors v0.77 LAB — 21/11/2026 16:44 CET.
// Inert direct-Worker candidate: ES imports only, no default fetch or Wrangler/deploy.
// v0.77 OWNER reconciliation NEVER updates RESERVED slots or approves entries.
import {accessBinding} from './access_binding_candidate.mjs';
import {profile} from './d1_access_candidate.mjs';
import {candidateRequest} from './http_access_candidate.mjs';
import {createLevelApiGateV074} from './level_api_gate_v074_lab.mjs';
import {createDurableLevelApiV076} from './durable_level_api_v076_lab.mjs';
import {createPrivateWorkerRouterV077} from './private_worker_router_v077_lab.mjs';
import {createOwnerLevelAuditHttpV077} from './owner_level_audit_http_v077_lab.mjs';
import {protectedReadCandidateV069} from './protected_read_composition_v069_lab.mjs';
import {privateAssetFilesV077} from './private_assets_v077_lab.mjs';
export const durableLevelHandlerV077=createDurableLevelApiV076({
 authenticate:accessBinding,profileRead:profile,originalHandler:candidateRequest
});
const originalLevelGate=createLevelApiGateV074({
 authenticate:accessBinding,profileRead:profile,handler:durableLevelHandlerV077
});
export const protectedLevelApiV077=(req,env,ctx)=>{
 let url;try{url=new URL(req.url)}catch{
  return new Response('{"error":"denied"}',{status:403,headers:{'Content-Type':'application/json','Cache-Control':'no-store'}});
 }
 return url.pathname==='/api/level-attempt/status'
  ? durableLevelHandlerV077(req,env,ctx)
  : originalLevelGate(req,env,ctx);
};
export const ownerLevelAuditHandlerV077=createOwnerLevelAuditHttpV077({
 authenticate:accessBinding,profileRead:profile
});
export const privateWorkerCandidateV077=createPrivateWorkerRouterV077({
 authenticate:accessBinding,profileRead:profile,
 protectedRead:protectedReadCandidateV069,
 levelApi:protectedLevelApiV077,
 ownerAudit:ownerLevelAuditHandlerV077,
 assetFiles:privateAssetFilesV077
});
