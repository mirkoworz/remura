// REMURA Experience v0.27 LAB — 21/11/2026 CET
// Read-only, single-host rehearsal. NOT a real independent witness, deployment or authorization service.
import {createPublicKey, verify as edVerify} from 'node:crypto';
import {anchorDigest, verifyPinnedChain, GateDenied} from './anchor_proof_v026_lab.mjs';

export const RECEIPT_SCHEMA = 'REMURA_OFFLINE_CUSTODY_RECEIPT_V027_FIXTURE';
export const RECEIPT_MAX_AGE_MS = 24 * 60 * 60 * 1000; // illustrative LAB policy, not proof of freshness
const RECEIPT_FIELDS = ['schema','generation','custodian','sequence','digest','issued_at_ms'];
const HASH = /^[0-9a-f]{64}$/;
const SIGNATURE = /^[A-Za-z0-9+/]{86}==$/;
const LABEL = /^[A-Za-z0-9_.:-]{1,64}$/;
const fail = () => { throw new GateDenied(); };
const validTime = t => Number.isSafeInteger(t) && t >= 0;
const exact = (o, fields) => o !== null && typeof o === 'object' && !Array.isArray(o)
  && Object.getPrototypeOf(o) === Object.prototype
  && Object.keys(o).length === fields.length && fields.every(k => Object.hasOwn(o,k));

// Explicit order makes signatures deterministic. No private data included.
export function receiptBytes(receipt) {
  if (!exact(receipt, RECEIPT_FIELDS) || receipt.schema !== RECEIPT_SCHEMA
    || typeof receipt.generation !== 'string' || !LABEL.test(receipt.generation)
    || !['alpha','beta'].includes(receipt.custodian)
    || !Number.isSafeInteger(receipt.sequence) || receipt.sequence < 1 || receipt.sequence > 64
    || typeof receipt.digest !== 'string' || !HASH.test(receipt.digest)
    || !validTime(receipt.issued_at_ms)) fail();
  return Buffer.from(JSON.stringify(Object.fromEntries(RECEIPT_FIELDS.map(k => [k, receipt[k]]))), 'utf8');
}

function pinnedEd25519(pub) {
  try {
    if (typeof pub !== 'string' || pub.length > 2048) fail();
    const key = createPublicKey(pub);
    if (key.asymmetricKeyType !== 'ed25519') fail();
    return {key, der:key.export({format:'der', type:'spki'})};
  } catch { fail(); }
}

function verifyAttestation(attestation, role, expectedGeneration, key, now) {
  if (!exact(attestation, ['receipt','signature'])) fail();
  const r = attestation.receipt;
  const bytes = receiptBytes(r);
  if (r.custodian !== role || r.generation !== expectedGeneration
      || r.issued_at_ms > now || now - r.issued_at_ms > RECEIPT_MAX_AGE_MS) fail();
  if (typeof attestation.signature !== 'string' || !SIGNATURE.test(attestation.signature)) fail();
  const s = Buffer.from(attestation.signature, 'base64');
  if (s.length !== 64 || s.toString('base64') !== attestation.signature || !edVerify(null, bytes, key, s)) fail();
  return {sequence:r.sequence, digest:r.digest};
}

function externalFloorValid(floor) {
  return exact(floor,['sequence','digest']) && Number.isSafeInteger(floor.sequence)
    && floor.sequence >= 1 && floor.sequence <= 64
    && typeof floor.digest === 'string' && HASH.test(floor.digest);
}

/**
 * Conservative lab gate requiring three OUT-OF-BAND inputs:
 *   1) externally pre-pinned owner/custodian public keys for signed v0.26 history,
 *   2) two separately pinned storage-custodian public keys and their signed latest claims,
 *   3) an independently authenticated minimum known-good floor (seq + digest).
 * The caller MUST substantiate physical/admin/restore independence and actual latest status.
 * Here everything runs on ONE machine, with NO persistent monotonic storage.
 * It never promotes the floor, writes records or returns market values.
 */
export function reviewCustodyRecovery({records,generation,chainTrust,storageTrust,
                                       attestations,trustedFloor,nowMs}) {
  if (!validTime(nowMs) || typeof generation !== 'string' || !LABEL.test(generation)
      || !externalFloorValid(trustedFloor) || !exact(chainTrust,['owner','custodian'])
      || !exact(storageTrust,['alpha','beta']) || !exact(attestations,['alpha','beta'])) fail();
  const keys = [chainTrust.owner,chainTrust.custodian,storageTrust.alpha,storageTrust.beta]
    .map(pinnedEd25519);
  if (new Set(keys.map(x => x.der.toString('hex'))).size !== 4) fail();

  const a = verifyAttestation(attestations.alpha,'alpha',generation,keys[2].key,nowMs);
  const b = verifyAttestation(attestations.beta,'beta',generation,keys[3].key,nowMs);
  if (a.sequence !== b.sequence || a.digest !== b.digest) fail();
  if (!Array.isArray(records) || a.sequence !== records.length || trustedFloor.sequence > a.sequence) fail();
  // Verify complete signed history against the independently supplied proposed current head.
  const verified = verifyPinnedChain({records,trust:chainTrust,
    externalPin:{sequence:a.sequence,digest:a.digest},generation});
  // The old chain validator checks hashes/signatures; recovery also forbids duplicate
  // intents and backwards observation clocks across separately signed records.
  const intents = new Set();
  let lastObservation = -1;
  for (const r of records) {
    if (intents.has(r.entry.intent_id) || r.entry.observed_at_ms < lastObservation) fail();
    intents.add(r.entry.intent_id);
    lastObservation = r.entry.observed_at_ms;
  }
  if (attestations.alpha.receipt.issued_at_ms < lastObservation
      || attestations.beta.receipt.issued_at_ms < lastObservation) fail();
  const floorRecord = records[trustedFloor.sequence - 1];
  if (!floorRecord || anchorDigest(floorRecord.entry) !== trustedFloor.digest) fail();

  // Only an assessment of records: NO automatic approval, persistent pin or market response.
  return Object.freeze({status:'REVIEWABLE_LAB_ONLY',sequence:verified.sequence,
    digest:verified.digest,disposition:verified.disposition,
    manualApprovalRequired:true, marketDeliveryPermitted:false});
}

// Always denies when a proof is absent, expired, conflicting, or tampered with.
export function inspectRecoverySafely(input) {
  try { return reviewCustodyRecovery(input); }
  catch { return Object.freeze({status:'BLOCKED',manualApprovalRequired:true,marketDeliveryPermitted:false}); }
}
