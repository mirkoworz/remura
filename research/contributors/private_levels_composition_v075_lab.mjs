// REMURA Contributors v0.75 LAB — 21/11/2026 15:48 CET.
// Worker-compatible module imports only ES modules + immutable embedded static text.
// Explicitly NO default fetch export, no Wrangler config, no deployment or live access.
import {accessBinding} from './access_binding_candidate.mjs';
import {profile} from './d1_access_candidate.mjs';
import {candidateRequest} from './http_access_candidate.mjs';
import {createLevelApiGateV074} from './level_api_gate_v074_lab.mjs';
import {createPrivateWorkerRouterV075} from './private_worker_router_v075_lab.mjs';
import {protectedReadCandidateV069} from './protected_read_composition_v069_lab.mjs';
import {privateAssetFilesV075} from './private_assets_v075_lab.mjs';
export const protectedLevelApiV075=createLevelApiGateV074({
 authenticate:accessBinding,profileRead:profile,handler:candidateRequest
});
export const privateWorkerCandidateV075=createPrivateWorkerRouterV075({
 authenticate:accessBinding,profileRead:profile,
 protectedRead:protectedReadCandidateV069,levelApi:protectedLevelApiV075,
 assetFiles:privateAssetFilesV075
});
