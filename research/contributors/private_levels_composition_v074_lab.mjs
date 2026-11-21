// REMURA Contributors v0.74 LAB — 21/11/2026 15:36 CET.
// Composition of reviewed original v0.31 Access, D1 profile, intent+submission HTTP
// with new v0.74 private role gates. Inert candidate: NO Worker default fetch/deploy.
import {accessBinding} from './access_binding_candidate.mjs';
import {profile} from './d1_access_candidate.mjs';
import {candidateRequest} from './http_access_candidate.mjs';
import {createLevelApiGateV074} from './level_api_gate_v074_lab.mjs';
import {createPrivateWorkerRouterV074} from './private_worker_router_v074_lab.mjs';
import {protectedReadCandidateV069} from './protected_read_composition_v069_lab.mjs';
import {readFileSync} from 'node:fs';
// Node-only LAB manifest. A future Worker build MUST replace Node file access with
// compile-time embedded static text; do not point Wrangler at this module.
const filenames=['contributors_recovery_v072_private_lab.html','contributors_owner_recovery_v072_private_lab.html','contributors_levels_v074_lab.html','owner_levels_v074_lab.html',
 'contributors_recovery_v067_lab.css','recovery_portal_v072_lab.mjs','secure_exit_v072_lab.mjs','recovery_transport_v070_lab.mjs','reconciliation_client_v065_lab.mjs','amendment_client_v063_lab.mjs','contributors_levels_v074_lab.css','contributors_levels_ui_v074_lab.mjs','contributors_candidate_client.mjs'];
export const fixtureAssetFilesV074=Object.freeze(Object.fromEntries(filenames.map(name=>[name,readFileSync(new URL('./'+name,import.meta.url),'utf8')])));
export const protectedLevelApiV074=createLevelApiGateV074({authenticate:accessBinding,profileRead:profile,handler:candidateRequest});
export const privateWorkerCandidateV074=createPrivateWorkerRouterV074({authenticate:accessBinding,profileRead:profile,protectedRead:protectedReadCandidateV069,levelApi:protectedLevelApiV074,assetFiles:fixtureAssetFilesV074});
