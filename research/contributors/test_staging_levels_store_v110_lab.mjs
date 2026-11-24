import assert from 'node:assert/strict';
import { createHash, randomUUID } from 'node:crypto';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import test from 'node:test';
import { createLevelsStoreV110, normalizeLevelV110 } from './staging_levels_store_v110_lab.mjs';

const legacy = readFileSync(new URL('./staging-readonly-v105-REVIEW-ONLY.sql', import.meta.url), 'utf8');
const slots = readFileSync(new URL('./staging-slots-v110.sql', import.meta.url), 'utf8');
const levels = readFileSync(new URL('./staging-levels-v110.sql', import.meta.url), 'utf8');
const stamp = '2026-11-24T22:15:00Z';
const tag = label => createHash('sha256').update('local test ' + label).digest('hex');
const person = label => ({ subject: tag(label + ' subject'), email_tag: tag(label + ' email') });
const owner = person('owner');
const permanent = person('permanent');
const friendB = person('second');
const friendC = person('third');

function atomic(sqlite, sql) {
  sqlite.exec('BEGIN');
  try {
    sqlite.exec(sql);
    sqlite.exec('COMMIT');
  } catch (error) {
    sqlite.exec('ROLLBACK');
    throw error;
  }
}

function original(sqlite, reserved = true) {
  sqlite.exec('PRAGMA foreign_keys=ON');
  if (reserved) sqlite.exec('CREATE TABLE _cf_KV (key TEXT PRIMARY KEY, value BLOB) WITHOUT ROWID');
  sqlite.exec(legacy);
  sqlite.prepare('INSERT INTO lab_owner VALUES (1,?,?,0)').run(owner.subject, owner.email_tag);
  sqlite.prepare("INSERT INTO lab_identities VALUES ('friend-a',?,?,0)").run(permanent.subject, permanent.email_tag);
  sqlite.exec('UPDATE lab_state SET read_enabled=1');
}

function adapter(sqlite, observe = () => {}) {
  return {
    withSession(mode) {
      assert.equal(mode, 'first-primary');
      return {
        prepare(sql) {
          return {
            bind(...args) {
              return {
                async all() {
                  const stmt = sqlite.prepare(sql);
                  const results = stmt.all(...args).map(row => ({ ...row }));
                  const result = { success: true, meta: { served_by_primary: true }, results };
                  return observe(sql, result) ?? result;
                }
              };
            }
          };
        }
      };
    }
  };
}

function fixture(t, { writable = true, observe, path = ':memory:' } = {}) {
  const sqlite = new DatabaseSync(path);
  t.after(() => sqlite.close());
  original(sqlite);
  atomic(sqlite, slots);
  atomic(sqlite, levels);
  if (writable) {
    sqlite.exec('UPDATE lab_state SET write_enabled=1');
    sqlite.exec("INSERT INTO lab_level_catalog_v110 VALUES ('EURUSD','OANDA','EURUSD','SPOT','','local-test',1)");
  }
  return { sqlite, store: createLevelsStoreV110(adapter(sqlite, observe)) };
}

function input(extra = {}) {
  return normalizeLevelV110({
    request_id: randomUUID(), market: 'EURUSD', provider: 'OANDA', ticker: 'EURUSD', product: 'SPOT',
    contract: '', period: 'DAY', kind: 'DELTA_PEAK', price: '1,20000', anchor_utc: '2026-11-24T07:15:00Z',
    observed_utc: '2026-11-24T08:15:00Z', note: 'Local proposal', ...extra
  }, stamp);
}

async function enroll(store, actor, slot) {
  const revision = await store.slotRevision(owner, slot);
  assert.equal((await store.invite(owner, slot, actor.email_tag, stamp, revision)).status, 'INVITED');
  const invite = await store.getInvite(actor);
  assert.equal(invite.slot, slot);
  assert.equal((await store.enroll(actor, stamp, invite.revision)).status, 'ACTIVE');
}

test('migrations preserve gates, existing rows and provider-reserved table', async t => {
  const { sqlite, store } = fixture(t, { writable: false });
  assert.deepEqual(await store.profile(owner), {
    role: 'OWNER', slot: 'owner', can_read: true, can_write: false, can_recover: false
  });
  assert.deepEqual(await store.profile(permanent), {
    role: 'CONTRIBUTOR', slot: 'friend-a', can_read: true, can_write: false, can_recover: false
  });
  assert.equal(sqlite.prepare('SELECT subject=? AS same FROM lab_owner').get(owner.subject).same, 1);
  assert.equal(sqlite.prepare('SELECT email_tag=? AS same FROM lab_identities').get(permanent.email_tag).same, 1);
  assert.equal(sqlite.prepare("SELECT COUNT(*) AS total FROM sqlite_schema WHERE name='_cf_KV'").get().total, 1);
  assert.equal(sqlite.prepare('SELECT COUNT(*) AS total FROM lab_level_catalog_v110').get().total, 0);
  assert.deepEqual(await store.slots(owner), [
    { slot: 'friend-a', status: 'ACTIVE' }, { slot: 'friend-b', status: 'VACANT' }, { slot: 'friend-c', status: 'VACANT' }
  ]);
  assert.throws(() => atomic(sqlite, levels), /CHECK constraint failed/);
  assert.equal(sqlite.prepare('PRAGMA integrity_check').get().integrity_check, 'ok');
  assert.deepEqual(sqlite.prepare('PRAGMA foreign_key_check').all(), []);
});

test('unexpected schema and mistimed migration roll back without touching the starting tables', t => {
  const sqlite = new DatabaseSync(':memory:');
  t.after(() => sqlite.close());
  original(sqlite, false);
  assert.throws(() => atomic(sqlite, levels), /CHECK constraint failed/);
  atomic(sqlite, slots);
  sqlite.exec('CREATE TABLE unexpected(x)');
  assert.throws(() => atomic(sqlite, levels), /CHECK constraint failed/);
  assert.throws(() => sqlite.exec('UPDATE lab_state SET write_enabled=1'), /CHECK constraint failed/);
  assert.equal(sqlite.prepare("SELECT COUNT(*) AS total FROM sqlite_schema WHERE name LIKE '%migration_guard%'").get().total, 0);
});

test('one transaction applies both release phases and rolls back both on a later fault', t => {
  const sqlite = new DatabaseSync(':memory:');
  t.after(() => sqlite.close());
  original(sqlite);
  assert.throws(() => atomic(sqlite, slots + levels + 'SELECT * FROM missing_local_test_table;'), /no such table/);
  assert.equal(sqlite.prepare("SELECT instr(sql, 'friend-c') AS present FROM sqlite_schema WHERE name='lab_identities'").get().present, 0);
  atomic(sqlite, slots + levels);
  assert.deepEqual(Object.values(sqlite.prepare('SELECT write_enabled,read_enabled,recovery_enabled FROM lab_state').get()), [0, 1, 0]);
});

test('owner invites both vacant slots and verified principals enroll with isolated profiles', async t => {
  const { store } = fixture(t);
  await enroll(store, friendB, 'friend-b');
  await enroll(store, friendC, 'friend-c');
  for (const [actor, slot] of [[permanent, 'friend-a'], [friendB, 'friend-b'], [friendC, 'friend-c']]) {
    assert.deepEqual(await store.profile(actor), {
      role: 'CONTRIBUTOR', slot, can_read: true, can_write: true, can_recover: false
    });
    assert.equal(await store.getInvite(actor), null);
  }
  assert.equal(await store.profile({ ...owner, email_tag: permanent.email_tag }), null);
  assert.equal(await store.profile({ ...friendB, email_tag: friendC.email_tag }), null);
  assert.equal((await store.audit(owner)).length, 4);
  const fields = Object.keys((await store.audit(owner))[0]).sort();
  assert.deepEqual(fields, ['action', 'at_utc', 'entry_id', 'id', 'reason', 'slot']);
});

test('invitation eligibility, replay and withdrawal bind to one specific revision', async t => {
  const { store } = fixture(t);
  assert.equal(await store.invite(permanent, 'friend-b', friendB.email_tag, stamp, 0), null);
  assert.equal(await store.invite(owner, 'friend-b', owner.email_tag, stamp, 0), null);
  assert.equal(await store.invite(owner, 'friend-b', permanent.email_tag, stamp, 0), null);
  await assert.rejects(() => store.slotRevision(friendC, 'friend-b'), { code: 'denied' });
  await store.invite(owner, 'friend-b', friendB.email_tag, stamp, 0);
  assert.equal(await store.invite(owner, 'friend-c', friendB.email_tag, stamp, 0), null);
  assert.equal(await store.getInvite(friendC), null);
  const first = await store.getInvite(friendB);
  assert.equal(await store.enroll(friendC, stamp, first.revision), null);
  const mismatched = { subject: owner.subject, email_tag: friendB.email_tag };
  assert.equal(await store.getInvite(mismatched), null);
  assert.equal(await store.enroll(mismatched, stamp, first.revision), null);
  assert.equal((await store.withdraw(owner, 'friend-b', stamp, first.revision)).status, 'VACANT');
  assert.equal(await store.invite(owner, 'friend-b', friendB.email_tag, stamp, 0), null);
  await store.invite(owner, 'friend-b', friendB.email_tag, stamp, await store.slotRevision(owner, 'friend-b'));
  assert.equal(await store.enroll(friendB, stamp, first.revision), null);
  assert.equal(await store.withdraw(owner, 'friend-b', stamp, first.revision), null);
  const current = await store.getInvite(friendB);
  assert.equal((await store.enroll(friendB, stamp, current.revision)).status, 'ACTIVE');
  assert.equal(await store.enroll(friendB, stamp, current.revision), null);
});

test('semantic duplicates and request-key conflicts remain scoped to their contributor', async t => {
  const { store, sqlite } = fixture(t);
  await enroll(store, friendB, 'friend-b');
  const first = input();
  const accepted = await store.submit(permanent, first, stamp);
  assert.equal(accepted.state, 'COMMITTED');
  assert.equal(accepted.receipt.price, '1.2');
  assert.deepEqual(await store.submit(permanent, first, stamp), accepted);
  await assert.rejects(store.submit(permanent, { ...first, note: 'other' }, stamp), { code: 'conflict' });
  const duplicate = input({ price: '1.20', observed_utc: '2026-11-24T09:15:00Z', note: 'other' });
  assert.deepEqual(await store.submit(permanent, duplicate, stamp), {
    state: 'DUPLICATE', receipt: accepted.receipt
  });
  assert.deepEqual(await store.lookup(permanent, duplicate.request_id), {
    state: 'DUPLICATE', receipt: accepted.receipt
  });
  assert.deepEqual(await store.lookup(friendB, first.request_id), { state: 'NOT_FOUND' });
  const separate = await store.submit(friendB, first, stamp);
  assert.equal(separate.state, 'COMMITTED');
  assert.notEqual(separate.receipt.id, accepted.receipt.id);
  assert.deepEqual((await store.receipts(permanent)).map(row => row.id), [accepted.receipt.id]);
  assert.deepEqual((await store.receipts(friendB)).map(row => row.id), [separate.receipt.id]);
  assert.equal(sqlite.prepare('SELECT COUNT(*) AS total FROM lab_level_attempts_v110').get().total, 3);
  assert.equal((await store.queue(owner)).length, 2);
  assert.deepEqual(await store.queue(permanent), []);
});

test('database rejects mappings and reports bounded canonical capacity', async t => {
  const { store, sqlite } = fixture(t);
  assert.deepEqual(await store.catalog(permanent), [
    { market: 'EURUSD', provider: 'OANDA', ticker: 'EURUSD', product: 'SPOT', contract: '' }
  ]);
  assert.deepEqual(await store.catalog(owner), []);
  await assert.rejects(store.submit(permanent, input({ ticker: 'MISSING' }), stamp), { code: 'invalid_mapping' });
  const receipts = [];
  for (let i = 1; i <= 20; i++) {
    receipts.push((await store.submit(permanent, input({ price: String(i) }), stamp)).receipt);
  }
  await assert.rejects(store.submit(permanent, input({ price: '21' }), stamp), { code: 'capacity' });
  assert.equal((await store.submit(permanent, input({ price: '1' }), stamp)).state, 'DUPLICATE');
  assert.equal((await store.receipts(permanent)).length, 20);
  assert.deepEqual(await store.receipts(permanent, receipts.at(-1).id), []);
  sqlite.exec('UPDATE lab_level_catalog_v110 SET active=0');
  assert.deepEqual(await store.catalog(permanent), []);
  await assert.rejects(store.submit(permanent, input({ price: '22' }), stamp), { code: 'invalid_mapping' });
});

test('new request IDs have a separate daily ceiling and known keys remain recoverable', async t => {
  const { store, sqlite } = fixture(t);
  const first = input();
  const accepted = await store.submit(permanent, first, stamp);
  for (let index = 1; index < 60; index++) {
    assert.equal((await store.submit(permanent, input(), stamp)).state, 'DUPLICATE');
  }
  await assert.rejects(store.submit(permanent, input(), stamp), { code: 'capacity' });
  await assert.rejects(store.submit(permanent, input({ price: '1.45' }), stamp), { code: 'capacity' });
  assert.deepEqual(await store.submit(permanent, first, stamp), accepted);
  assert.equal(sqlite.prepare('SELECT COUNT(*) AS total FROM lab_level_attempts_v110').get().total, 60);
  assert.equal(sqlite.prepare('SELECT COUNT(*) AS total FROM lab_level_pending_v110').get().total, 1);
  assert.equal((await store.submit(permanent, input(), '2026-11-25T00:00:01Z')).state, 'DUPLICATE');
});

test('review approval and rejection are final, audited, and reflected in personal receipts', async t => {
  const { store, sqlite } = fixture(t);
  const first = input();
  const accepted = (await store.submit(permanent, first, stamp)).receipt;
  const declined = (await store.submit(permanent, input({ price: '1.25' }), stamp)).receipt;
  assert.deepEqual((await store.queue(owner)).map(row => row.slot), ['friend-a', 'friend-a']);
  assert.deepEqual(await store.history(owner), []);
  const approve = { id: accepted.id, action: 'APPROVED', reason: '  Verificato  ' };
  assert.equal(await store.review(permanent, approve, stamp), null);
  assert.deepEqual(await store.review(owner, approve, stamp), {
    id: accepted.id, action: 'APPROVED', at_utc: stamp
  });
  assert.equal(await store.review(owner, { ...approve, action: 'REJECTED' }, stamp), null);
  await store.review(owner, { id: declined.id, action: 'REJECTED', reason: 'Incompleto' }, stamp);
  assert.deepEqual(await store.queue(owner), []);
  assert.deepEqual((await store.history(owner)).map(row => row.status), ['APPROVED', 'REJECTED']);
  assert.deepEqual((await store.receipts(permanent)).map(row => row.status), ['APPROVED', 'REJECTED']);
  assert.equal((await store.lookup(permanent, first.request_id)).receipt.reviewed_utc, stamp);
  assert.deepEqual((await store.audit(owner)).map(row => row.reason), ['Verificato', 'Incompleto']);
  assert.throws(() => sqlite.exec("UPDATE lab_activity_v110 SET reason='altered'"), /activity_immutable/);
  assert.throws(() => sqlite.exec('DELETE FROM lab_level_attempts_v110'), /attempt_immutable/);
  assert.throws(() => sqlite.exec('INSERT OR REPLACE INTO lab_activity_v110 SELECT * FROM lab_activity_v110'), /activity_immutable/);
  assert.throws(() => sqlite.exec('INSERT OR REPLACE INTO lab_level_attempts_v110 SELECT * FROM lab_level_attempts_v110'), /attempt_immutable/);
});

test('approval requires an active catalog source and active contributor, rejection still possible', async t => {
  const { store, sqlite } = fixture(t);
  const first = (await store.submit(permanent, input(), stamp)).receipt;
  sqlite.exec('UPDATE lab_level_catalog_v110 SET active=0');
  assert.equal(await store.review(owner, { id: first.id, action: 'APPROVED', reason: 'Valid' }, stamp), null);
  sqlite.exec('UPDATE lab_level_catalog_v110 SET active=1');
  await store.revoke(owner, { slot: 'friend-a' }, stamp, 0);
  assert.equal(await store.review(owner, { id: first.id, action: 'APPROVED', reason: 'Valid' }, stamp), null);
  assert.equal((await store.review(owner, { id: first.id, action: 'REJECTED', reason: 'Revoked' }, stamp)).action, 'REJECTED');
});

test('revocation atomically seals the slot and removes read/write access', async t => {
  const { store, sqlite } = fixture(t);
  await enroll(store, friendB, 'friend-b');
  const saved = input();
  await store.submit(friendB, saved, stamp);
  const revision = await store.slotRevision(owner, 'friend-b');
  assert.equal(await store.revoke(owner, { slot: 'friend-b' }, stamp, 0), null);
  assert.equal(await store.revoke(friendC, { slot: 'friend-b' }, stamp, revision), null);
  assert.equal((await store.revoke(owner, { slot: 'friend-b' }, stamp, revision)).status, 'REVOKED');
  assert.equal(await store.profile(friendB), null);
  await assert.rejects(store.lookup(friendB, saved.request_id), { code: 'denied' });
  assert.deepEqual(await store.receipts(friendB), []);
  await assert.rejects(store.submit(friendB, saved, stamp), { code: 'denied' });
  assert.equal(await store.invite(owner, 'friend-b', friendC.email_tag, stamp, await store.slotRevision(owner, 'friend-b')), null);
  assert.throws(() => sqlite.exec("UPDATE lab_identities SET revoked=0 WHERE slot='friend-b'"), /identity_immutable/);
  assert.throws(() => sqlite.exec("DELETE FROM lab_identities WHERE slot='friend-b'"), /identity_immutable/);
  assert.throws(() => sqlite.exec("INSERT OR REPLACE INTO lab_identities SELECT * FROM lab_identities WHERE slot='friend-b'"), /identity_already_bound/);
  assert.equal((await store.audit(owner)).at(-1).action, 'REVOKED');
});

test('closing writes keeps personal read and stops every mutation even if a former permission is cached', async t => {
  const { store, sqlite } = fixture(t);
  const first = input();
  const saved = (await store.submit(permanent, first, stamp)).receipt;
  await store.invite(owner, 'friend-b', friendB.email_tag, stamp, 0);
  const invitation = await store.getInvite(friendB);
  sqlite.exec('UPDATE lab_state SET write_enabled=0');
  assert.equal((await store.lookup(permanent, first.request_id)).state, 'COMMITTED');
  assert.deepEqual(await store.receipts(permanent), [saved]);
  await assert.rejects(store.submit(permanent, input({ price: '1.25' }), stamp), { code: 'denied' });
  assert.equal(await store.getInvite(friendB), null);
  assert.equal(await store.enroll(friendB, stamp, invitation.revision), null);
  assert.equal(await store.withdraw(owner, 'friend-b', stamp, invitation.revision), null);
  assert.equal(await store.invite(owner, 'friend-c', friendC.email_tag, stamp, 0), null);
  assert.equal(await store.review(owner, { id: saved.id, action: 'APPROVED', reason: 'Valid' }, stamp), null);
  assert.equal(await store.revoke(owner, { slot: 'friend-a' }, stamp, 0), null);
});

test('a committed write with a lost D1 reply is resolved through read-only lookup', async t => {
  let loseReply = true;
  const { store, sqlite } = fixture(t, {
    observe(sql) {
      if (loseReply && sql.includes('INSERT INTO lab_level_attempts_v110')) {
        loseReply = false;
        throw new Error('simulated lost reply');
      }
    }
  });
  const first = input();
  await assert.rejects(store.submit(permanent, first, stamp), /simulated lost reply/);
  assert.equal((await store.lookup(permanent, first.request_id)).state, 'COMMITTED');
  assert.equal(sqlite.prepare('SELECT COUNT(*) AS total FROM lab_level_attempts_v110').get().total, 1);
  assert.deepEqual(await store.lookup(permanent, randomUUID()), { state: 'NOT_FOUND' });
});

test('independent SQLite connections converge on one receipt for concurrent equivalent submissions', async () => {
  const directory = mkdtempSync(join(tmpdir(), 'remura-v110-sqlite-'));
  try {
    const path = join(directory, 'levels.sqlite');
    const writer = new DatabaseSync(path);
    const reader = new DatabaseSync(path);
    try {
      original(writer);
      atomic(writer, slots);
      atomic(writer, levels);
      writer.exec('UPDATE lab_state SET write_enabled=1');
      writer.exec("INSERT INTO lab_level_catalog_v110 VALUES ('EURUSD','OANDA','EURUSD','SPOT','','local-test',1)");
      reader.exec('PRAGMA foreign_keys=ON');
      const first = input();
      const second = input();
      const stores = [createLevelsStoreV110(adapter(writer)), createLevelsStoreV110(adapter(reader))];
      const results = await Promise.all([stores[0].submit(permanent, first, stamp), stores[1].submit(permanent, second, stamp)]);
      assert.deepEqual(results.map(({ state }) => state).sort(), ['COMMITTED', 'DUPLICATE']);
      assert.equal(results[0].receipt.id, results[1].receipt.id);
      const sameRequest = input({ price: '1.27' });
      const reruns = await Promise.all(stores.map(store => store.submit(permanent, sameRequest, stamp)));
      assert.deepEqual(reruns[0], reruns[1]);
      assert.equal(await stores[0].lookup(permanent, first.request_id).then(result => result.receipt.id), results[0].receipt.id);
    } finally {
      reader.close();
      writer.close();
    }
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test('a non-primary database response can never authorize access', async t => {
  const { store } = fixture(t, {
    observe(_sql, result) {
      return { ...result, meta: { served_by_primary: false } };
    }
  });
  await assert.rejects(store.profile(permanent), /levels_store_unavailable/);
  await assert.rejects(store.getInvite(friendB), /levels_store_unavailable/);
});
