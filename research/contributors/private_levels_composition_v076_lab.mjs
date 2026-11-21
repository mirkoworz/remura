// REMURA Contributors v0.76 LAB — 21/11/2026 15:57 CET.
// Worker-friendly ES module, with embedded assets and NO automatic default fetch.
// Runtime assumes empty new_level_attempts_v076_lab.sql overlay on synthetic fixture.
import {accessBinding} from './access_binding_candidate.mjs';
import {profile} from './d1_access_candidate.mjs';
import {candidateRequest} from './http_access_candidate.mjs';
import {createLevelApiGateV074} from './level_api_gate_v074_lab.mjs';
import {createDurableLevelApiV076} from './durable_level_api_v076_lab.mjs';
import {createPrivateWorkerRouterV076} from './private_worker_router_v076_lab.mjs';
import {protectedReadCandidateV069} from './protected_read_composition_v069_lab.mjs';
import {privateAssetFilesV076} from './private_assets_v076_lab.mjs';
export const durableLevelHandlerV076=createDurableLevelApiV076({
 authenticate:accessBinding,profileRead:profile,originalHandler:candidateRequest
});
const originalLevelGate=createLevelApiGateV074({
 authenticate:accessBinding,profileRead:profile,handler:durableLevelHandlerV076
});
export const protectedLevelApiV076=(req,env,ctx)=>{
 let url;try{url=new URL(req.url)}catch{return new Response('{"error":"denied"}',{status:403,headers:{'Content-Type':'application/json','Cache-Control':'no-store'}});}
 return url.pathname==='/api/level-attempt/status'
  ? durableLevelHandlerV076(req,env,ctx)
  : originalLevelGate(req,env,ctx);
};
export const privateWorkerCandidateV076=createPrivateWorkerRouterV076({
 authenticate:accessBinding,profileRead:profile,
 protectedRead:protectedReadCandidateV069,
 levelApi:protectedLevelApiV076,
 assetFiles:privateAssetFilesV076
});
