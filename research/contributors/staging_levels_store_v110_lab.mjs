// REMURA Contributors v1.10 LAB. Every statement starts on D1 primary.
// The Worker supplies freshly verified Access HMAC tags, never client identity fields.
import { normalizeNewLevelV076, newLevelFingerprintV076 } from './level_attempt_journal_v076_lab.mjs';

export const normalizeLevelV110 = normalizeNewLevelV076;
const pageSize = 20;
const hash = /^[a-f0-9]{64}$/;
const requestKey = /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/;
const contributorSlots = ['friend-a', 'friend-b', 'friend-c'];

export class LevelsStoreError extends Error {
  constructor(code) {
    super(code);
    this.code = code;
  }
}

const contributorRead = `SELECT 1 FROM lab_identities i CROSS JOIN lab_state s
  WHERE i.subject=?1 AND i.email_tag=?2 AND i.revoked=0 AND s.id=1 AND s.read_enabled=1`;
const contributorWrite = `${contributorRead} AND s.write_enabled=1`;
const ownerRead = `SELECT 1 FROM lab_owner i CROSS JOIN lab_state s
  WHERE i.id=1 AND i.subject=?1 AND i.email_tag=?2 AND i.revoked=0 AND s.id=1 AND s.read_enabled=1`;
const ownerWrite = `${ownerRead} AND s.write_enabled=1`;
const unenrolled = `NOT EXISTS(SELECT 1 FROM lab_owner WHERE subject=?1 OR email_tag=?2)
  AND NOT EXISTS(SELECT 1 FROM lab_identities WHERE subject=?1 OR email_tag=?2)`;
const joinEnabled = `EXISTS(SELECT 1 FROM lab_state WHERE id=1 AND read_enabled=1 AND write_enabled=1)`;
const receiptFields = `e.id,e.market,e.provider,e.ticker,e.product,e.contract,e.period,e.kind,e.price,
  e.anchor_utc,e.observed_utc,e.received_utc,e.note,e.publication_mode,COALESCE(d.action,'UNREVIEWED') AS status,d.at_utc AS reviewed_utc`;
const intakeCandidate = `SELECT ?3 AS request_id,?4 AS fingerprint,?5 AS market,?6 AS provider,
  ?7 AS ticker,?8 AS product,?9 AS contract,?10 AS period,?11 AS kind,?12 AS price,
  ?13 AS anchor_utc,?14 AS observed_utc,?15 AS received_utc,?16 AS note,?17 AS publication_mode`;

const SQL = Object.freeze({
  profile: `
    SELECT 'OWNER' AS role,'owner' AS slot,s.read_enabled,s.write_enabled,s.recovery_enabled
    FROM lab_owner i CROSS JOIN lab_state s
    WHERE i.id=1 AND i.subject=?1 AND i.email_tag=?2 AND i.revoked=0 AND s.id=1
    UNION ALL
    SELECT 'CONTRIBUTOR',i.slot,s.read_enabled,s.write_enabled,0
    FROM lab_identities i CROSS JOIN lab_state s
    WHERE i.subject=?1 AND i.email_tag=?2 AND i.revoked=0 AND s.id=1`,
  catalog: `
    SELECT market,provider,ticker,product,contract FROM lab_level_catalog_v110
    WHERE active=1 AND EXISTS(${contributorRead})
    ORDER BY market,provider,ticker,product,contract LIMIT 257`,
  receipts: `
    SELECT ${receiptFields}
    FROM lab_level_attempts_v110 e
    LEFT JOIN lab_activity_v110 d ON d.entry_id=e.id
    WHERE e.subject=?1 AND e.email_tag=?2 AND e.duplicate_of IS NULL AND e.id>?3
     AND EXISTS(${contributorRead}) ORDER BY e.id LIMIT 20`,
  lookup: `
    WITH permit AS (${contributorRead})
    SELECT ${receiptFields},a.fingerprint,(a.duplicate_of IS NOT NULL) AS is_duplicate
    FROM permit
    LEFT JOIN lab_level_attempts_v110 a ON a.subject=?1 AND a.email_tag=?2 AND a.request_id=?3
    LEFT JOIN lab_level_attempts_v110 e ON e.id=COALESCE(a.duplicate_of,a.id)
     AND e.subject=?1 AND e.email_tag=?2 AND e.duplicate_of IS NULL
    LEFT JOIN lab_activity_v110 d ON d.entry_id=e.id`,
  submit: `
    WITH candidate AS (${intakeCandidate})
    INSERT INTO lab_level_attempts_v110(
     subject,email_tag,request_id,fingerprint,market,provider,ticker,product,contract,
     period,kind,price,anchor_utc,observed_utc,received_utc,note,source_group,duplicate_of,publication_mode)
    SELECT ?1,?2,n.request_id,n.fingerprint,n.market,n.provider,n.ticker,n.product,n.contract,
     n.period,n.kind,n.price,n.anchor_utc,n.observed_utc,n.received_utc,n.note,c.source_group,p.id,n.publication_mode
    FROM candidate n JOIN lab_level_catalog_v110 c USING(market,provider,ticker,product,contract)
    LEFT JOIN lab_level_attempts_v110 p
     ON p.subject=?1 AND p.email_tag=?2 AND p.duplicate_of IS NULL
     AND (p.market,p.provider,p.ticker,p.product,p.contract,p.period,p.kind,p.price,p.anchor_utc)=
         (n.market,n.provider,n.ticker,n.product,n.contract,n.period,n.kind,n.price,n.anchor_utc)
    WHERE c.active=1 AND EXISTS(${contributorWrite})
     AND NOT EXISTS(SELECT 1 FROM lab_level_attempts_v110 WHERE subject=?1 AND request_id=n.request_id)
     AND (p.id IS NOT NULL OR NOT EXISTS(
      SELECT 1 FROM lab_level_attempts_v110 e WHERE e.subject=?1 AND e.duplicate_of IS NULL
      AND e.received_utc BETWEEN substr(n.received_utc,1,10)||'T00:00:00Z'
                             AND substr(n.received_utc,1,10)||'T23:59:59Z'
      LIMIT 1 OFFSET 19
     ))
     AND NOT EXISTS(
      SELECT 1 FROM lab_level_attempts_v110 e WHERE e.subject=?1
      AND e.received_utc BETWEEN substr(n.received_utc,1,10)||'T00:00:00Z'
                             AND substr(n.received_utc,1,10)||'T23:59:59Z'
      LIMIT 1 OFFSET 59
     )
    RETURNING id`,
  submitUnavailable: `
    SELECT CASE WHEN NOT EXISTS(${contributorWrite}) THEN 'denied'
     WHEN NOT EXISTS(SELECT 1 FROM lab_level_catalog_v110
      WHERE market=?3 AND provider=?4 AND ticker=?5 AND product=?6 AND contract=?7 AND active=1)
     THEN 'invalid_mapping' ELSE 'capacity' END AS code`,
  pending: `
    SELECT ${receiptFields},i.slot FROM lab_level_pending_v110 p
    JOIN lab_level_attempts_v110 e ON e.id=p.entry_id
    JOIN lab_identities i ON i.subject=e.subject AND i.email_tag=e.email_tag
    LEFT JOIN lab_activity_v110 d ON d.entry_id=e.id
    WHERE p.entry_id>?3 AND e.duplicate_of IS NULL AND d.id IS NULL AND EXISTS(${ownerRead})
    ORDER BY p.entry_id LIMIT 20`,
  history: `
    SELECT ${receiptFields},i.slot FROM lab_activity_v110 d
    JOIN lab_level_attempts_v110 e ON e.id=d.entry_id
    JOIN lab_identities i ON i.subject=e.subject AND i.email_tag=e.email_tag
    WHERE d.entry_id>?3 AND e.duplicate_of IS NULL AND EXISTS(${ownerRead})
    ORDER BY d.entry_id LIMIT 20`,
  audit: `
    SELECT id,entry_id,slot,action,at_utc,reason FROM lab_activity_v110
    WHERE id>?3 AND EXISTS(${ownerRead}) ORDER BY id LIMIT 20`,
  review: `
    INSERT INTO lab_activity_v110(entry_id,action,at_utc,reason)
    SELECT e.id,?4,?5,?6 FROM lab_level_attempts_v110 e
    WHERE e.id=?3 AND e.duplicate_of IS NULL AND e.received_utc<=?5 AND EXISTS(${ownerWrite})
     AND NOT EXISTS(SELECT 1 FROM lab_activity_v110 d WHERE d.entry_id=e.id)
     AND (?4='REJECTED' OR EXISTS(
      SELECT 1 FROM lab_identities i JOIN lab_level_catalog_v110 c
      ON (c.market,c.provider,c.ticker,c.product,c.contract)=(e.market,e.provider,e.ticker,e.product,e.contract)
      WHERE i.subject=e.subject AND i.email_tag=e.email_tag AND i.revoked=0
       AND c.active=1 AND c.source_group=e.source_group
     ))
    RETURNING entry_id AS id,action,at_utc`,
  slots: `
    SELECT slot,status FROM lab_slot_status_v110 WHERE EXISTS(${ownerRead}) ORDER BY slot`,
  slotRevision: `
    SELECT revision FROM lab_slot_status_v110 WHERE slot=?3 AND EXISTS(${ownerRead})`,
  getInvite: `
    SELECT slot,revision FROM lab_slot_status_v110
    WHERE status='INVITED' AND invite_email_tag=?2 AND ${unenrolled} AND ${joinEnabled}`,
  invite: `
    INSERT INTO lab_activity_v110(slot,action,at_utc,invite_email_tag)
    SELECT slot,'INVITED',?5,?4 FROM lab_slot_status_v110
    WHERE slot=?3 AND status='VACANT' AND revision=?6 AND EXISTS(${ownerWrite})
     AND NOT EXISTS(SELECT 1 FROM lab_slot_status_v110 WHERE invite_email_tag=?4)
     AND NOT EXISTS(SELECT 1 FROM lab_owner WHERE email_tag=?4)
     AND NOT EXISTS(SELECT 1 FROM lab_identities WHERE email_tag=?4)
    RETURNING slot,'INVITED' AS status,at_utc`,
  withdraw: `
    INSERT INTO lab_activity_v110(slot,action,at_utc)
    SELECT slot,'WITHDRAWN',?4 FROM lab_slot_status_v110
    WHERE slot=?3 AND status='INVITED' AND revision=?5 AND EXISTS(${ownerWrite})
    RETURNING slot,'VACANT' AS status,at_utc`,
  enroll: `
    INSERT INTO lab_activity_v110(slot,action,at_utc,invite_email_tag,enrollment_subject)
    SELECT slot,'ENROLLED',?3,?2,?1 FROM lab_slot_status_v110
    WHERE status='INVITED' AND invite_email_tag=?2 AND revision=?4
     AND ${unenrolled} AND ${joinEnabled}
    RETURNING slot,'ACTIVE' AS status,at_utc`,
  revoke: `
    INSERT INTO lab_activity_v110(slot,action,at_utc)
    SELECT slot,'REVOKED',?4 FROM lab_slot_status_v110
    WHERE slot=?3 AND status='ACTIVE' AND revision=?5 AND EXISTS(${ownerWrite})
    RETURNING slot,'REVOKED' AS status,at_utc`
});

function tags(actor) {
  if (!hash.test(actor?.subject ?? '') || !hash.test(actor?.email_tag ?? '')) {
    throw new LevelsStoreError('denied');
  }
  return [actor.subject, actor.email_tag];
}

function cursor(value, min = 0) {
  if (!Number.isSafeInteger(value) || value < min) throw new LevelsStoreError('invalid_input');
  return value;
}

function slot(value, allowPermanent = true) {
  if (!contributorSlots.includes(value) || (!allowPermanent && value === 'friend-a')) {
    throw new LevelsStoreError('invalid_input');
  }
  return value;
}

function reasonText(value) {
  if (typeof value !== 'string' || !value.trim() || [...value].length > 280 ||
    /[\u0000-\u001f\u007f-\u009f\uD800-\uDFFF]/u.test(value)) {
    throw new LevelsStoreError('invalid_input');
  }
  return value.trim();
}

function outcome(row) {
  const { fingerprint, is_duplicate, ...receipt } = row;
  if (receipt.id === null) return { state: 'NOT_FOUND' };
  if (!Number.isSafeInteger(receipt.id) || receipt.id < 1 ||
    !hash.test(fingerprint ?? '') || ![0, 1].includes(is_duplicate)) {
    throw new Error('levels_store_unavailable');
  }
  return { state: is_duplicate === 1 ? 'DUPLICATE' : 'COMMITTED', receipt };
}

export function createLevelsStoreV110(db) {
  async function rows(key, args, max = 1) {
    const result = await db.withSession('first-primary').prepare(SQL[key]).bind(...args).all();
    if (result?.success !== true || result.meta?.served_by_primary !== true ||
      !Array.isArray(result.results) || result.results.length > max) {
      throw new Error('levels_store_unavailable');
    }
    return result.results;
  }

  async function single(key, args) {
    return (await rows(key, args))[0] ?? null;
  }

  async function lookupRecord(actor, requestId) {
    if (!requestKey.test(requestId ?? '')) throw new LevelsStoreError('invalid_input');
    const row = await single('lookup', [...tags(actor), requestId]);
    if (!row) throw new LevelsStoreError('denied');
    return row;
  }

  function listPage(key, actor, after) {
    return rows(key, [...tags(actor), cursor(after)], pageSize);
  }

  return Object.freeze({
    async profile(actor) {
      const row = await single('profile', tags(actor));
      if (!row) return null;
      const validRole = row.role === 'OWNER' && row.slot === 'owner' ||
        row.role === 'CONTRIBUTOR' && contributorSlots.includes(row.slot) && row.recovery_enabled === 0;
      if (!validRole || ![row.read_enabled, row.write_enabled, row.recovery_enabled].every(bit => bit === 0 || bit === 1)) {
        throw new Error('levels_store_unavailable');
      }
      return {
        role: row.role,
        slot: row.slot,
        can_read: row.read_enabled === 1,
        can_write: row.write_enabled === 1,
        can_recover: row.recovery_enabled === 1
      };
    },
    catalog: actor => rows('catalog', tags(actor), 256),
    receipts: (actor, after = 0) => listPage('receipts', actor, after),
    queue: (actor, after = 0) => listPage('pending', actor, after),
    history: (actor, after = 0) => listPage('history', actor, after),
    audit: (actor, after = 0) => listPage('audit', actor, after),
    slots: actor => rows('slots', tags(actor), 3),
    async slotRevision(actor, targetSlot) {
      const row = await single('slotRevision', [...tags(actor), slot(targetSlot)]);
      if (!row) throw new LevelsStoreError('denied');
      return cursor(row.revision);
    },
    getInvite: actor => single('getInvite', tags(actor)),
    invite(actor, targetSlot, emailTag, now, revision) {
      if (!hash.test(emailTag ?? '')) throw new LevelsStoreError('invalid_input');
      return single('invite', [...tags(actor), slot(targetSlot, false), emailTag, now, cursor(revision)]);
    },
    withdraw: (actor, targetSlot, now, revision) =>
      single('withdraw', [...tags(actor), slot(targetSlot, false), now, cursor(revision)]),
    enroll: (actor, now, revision) => single('enroll', [...tags(actor), now, cursor(revision)]),
    revoke: (actor, { slot: targetSlot }, now, revision) =>
      single('revoke', [...tags(actor), slot(targetSlot), now, cursor(revision)]),
    review(actor, { id, action, reason }, now) {
      if (!['APPROVED', 'REJECTED'].includes(action)) throw new LevelsStoreError('invalid_input');
      return single('review', [...tags(actor), cursor(id, 1), action, now, reasonText(reason)]);
    },
    async lookup(actor, requestId) {
      return outcome(await lookupRecord(actor, requestId));
    },
    async submit(actor, level, now, publication_mode='PRIVATE') {
      if(!['PRIVATE','TEST','TELEGRAM'].includes(publication_mode))throw new LevelsStoreError('invalid_input');
      const identity = tags(actor);
      const { request_id, market, provider, ticker, product, contract, period, kind, price, anchor_utc, observed_utc, note } = level;
      const fingerprint = await newLevelFingerprintV076(level);
      const inserted = await single('submit', [
        ...identity, request_id, fingerprint, market, provider, ticker, product, contract,
        period, kind, price, anchor_utc, observed_utc, now, note, publication_mode
      ]);
      let record;
      try {
        record = await lookupRecord(actor, request_id);
      } catch (error) {
        // The write succeeded before a later access/storage failure.
        if (inserted) throw new Error('levels_store_unavailable');
        throw error;
      }
      const result = outcome(record);
      if (result.state !== 'NOT_FOUND') {
        if (record.fingerprint !== fingerprint) throw new LevelsStoreError('conflict');
        return result;
      }
      if (inserted) throw new Error('levels_store_unavailable');
      const status = await single('submitUnavailable', [...identity, market, provider, ticker, product, contract]);
      if (!status) throw new Error('levels_store_unavailable');
      throw new LevelsStoreError(status.code);
    }
  });
}
