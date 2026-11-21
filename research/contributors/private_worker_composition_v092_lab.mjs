// REMURA Contributors v0.92 LAB — 21/11/2026, Europe/Rome.
// Inert, no default fetch, no Cloudflare activation, secrets, D1 writes, or deploy.
import {accessBinding} from './access_binding_candidate.mjs';
import {profile} from './d1_access_candidate.mjs';
import {protectedReadCandidateV069} from './protected_read_composition_v069_lab.mjs';
import {protectedLevelApiV078,ownerLevelAuditHandlerV078} from './private_levels_composition_v078_lab.mjs';
import {privateAssetFilesV078} from './private_assets_v078_lab.mjs';
import {createPostGuardedPrivateWorkerV090} from './private_post_guard_v090_lab.mjs';

// Deny ALL OWNER operations when recovery authority has been revoked.
// This intentionally also closes the OWNER's generic profile endpoint;
// it does not revoke a user at the provider or alter D1. A single D1 primary
// profile lookup suffices for each GET, rather than the earlier double-read.
// v0.78 still authenticates Access and checks read/role on protected GET.
async function strictProfile(ctx,env,actor){
 const p=await profile(ctx,env,actor);
 if(p?.role==='OWNER'&&p.can_recover!==true)return null;
 return p;
}

// Existing real LAB delegates; central POST guard v0.90 is unchanged.
export const privateWorkerCandidateV092=createPostGuardedPrivateWorkerV090({
 authenticate:accessBinding,profileRead:strictProfile,
 protectedRead:protectedReadCandidateV069,
 levelApi:protectedLevelApiV078,
 ownerAudit:ownerLevelAuditHandlerV078,
 assetFiles:privateAssetFilesV078
});
export const V092_COMPOSITION=Object.freeze({
 version:'0.92',type:'INERT_LAB_CANDIDATE',ownerGetRecoveryGate:true,
 ownerNoRecoveryDeniedAcrossRoutes:true,ownerGetPrimaryProfileReads:1,
 postV090RealDelegatesWired:true,workflowsMayDeploy:false,
 liveAccessJwtVerified:false,realD1Tested:false,realSafariTested:false,
 freeQuotaAttested:false,pilotAllowed:false
});
