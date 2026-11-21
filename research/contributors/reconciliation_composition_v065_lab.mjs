// REMURA Contributors v0.65 LAB — 21/11/2026 CET.
// Explicit composition of previously reviewed candidates. NO Worker fetch export or deploy.
import {createReconciliationHttpV065} from './reconciliation_http_v065_lab.mjs';
import {amendmentHttpCandidateV062} from './amendment_http_v062_lab.mjs';
import {burnAmendmentIntentLab} from './amendment_intent_v062_lab.mjs';
import {accessBinding} from './access_binding_candidate.mjs';
import {submitAmendmentLab} from './amendment_adapter_v061_lab.mjs';
import {inspectMyAmendmentRecoveryV064,inspectOwnerRecoveryQueueV064} from './reconciliation_reader_v064_lab.mjs';

// This callable candidate is not mounted or exported as fetch by the project.
// The offline feature switches and the historical Access/primary guards remain compulsory.
export const amendmentHttpCandidateV065=createReconciliationHttpV065({
 fallback:amendmentHttpCandidateV062,
 burn:burnAmendmentIntentLab,
 access:accessBinding,
 submit:submitAmendmentLab,
 mine:inspectMyAmendmentRecoveryV064,
 ownerQueue:inspectOwnerRecoveryQueueV064
});
