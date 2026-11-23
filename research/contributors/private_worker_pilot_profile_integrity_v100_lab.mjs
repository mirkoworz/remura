// REMURA Contributors v1.00 LAB — 23/11/2026 Europe/Rome.
// Fail-closed profile integrity before every private GET or POST.
// Direct Worker composition only; NO default fetch, Access activation, D1 writes or deploy.
import {createPilotOwnerGuardV098} from './private_worker_pilot_owner_guard_v098_lab.mjs';
import {accessBinding} from './access_binding_candidate.mjs';
import {profile} from './d1_access_candidate.mjs';
import {protectedReadCandidateV069} from './protected_read_composition_v069_lab.mjs';
import {protectedLevelApiV096,ownerLevelAuditHandlerV078} from './private_levels_composition_v096_lab.mjs';
import {privateAssetFilesV096} from './private_assets_v096_lab.mjs';

// v0.98 protected OWNER loss of recovery on GET, but a malformed CONTRIBUTOR
// profile with can_recover=true could still receive the contributor HTML/JS.
// This guard uses the existing SAME profile read, no extra D1 read per request.
function validProfile(p){
  if(!p||typeof p!=='object'||Array.isArray(p))return false;
  if(p.can_read!==true||typeof p.can_write!=='boolean')return false;
  if(p.role==='OWNER')return p.can_recover===true;
  if(p.role==='CONTRIBUTOR')return p.can_recover===false;
  return false;
}
export function createPilotProfileIntegrityV100({
  authenticate,profileRead,protectedRead,levelApi,ownerAudit,assetFiles
}){
  if(typeof profileRead!=='function')throw Error('V100_PROFILE_READER_REQUIRED');
  return createPilotOwnerGuardV098({
    authenticate,
    profileRead:async(ctx,env,actor)=>{
      const p=await profileRead(ctx,env,actor);
      if(!validProfile(p))throw Error('V100_PROFILE_INTEGRITY_DENIED');
      return p;
    },
    protectedRead,levelApi,ownerAudit,assetFiles
  });
}

// Ready for an independently authorized staging build, not deployed or exported
// as a live fetch handler. Access and D1 identities remain unverified.
export const privateWorkerPilotV100=createPilotProfileIntegrityV100({
  authenticate:accessBinding,profileRead:profile,
  protectedRead:protectedReadCandidateV069,levelApi:protectedLevelApiV096,
  ownerAudit:ownerLevelAuditHandlerV078,assetFiles:privateAssetFilesV096
});
export const V100_PILOT=Object.freeze({
  version:'1.00',mode:'INERT_LAB',profileRoleCapabilityIntegrity:true,
  additionalD1ProfileReads:0,realProviderVerified:false,
  safariVerified:false,billingVerified:false,deployAuthorized:false,
  realPilotAllowed:false
});
