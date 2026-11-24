import assert from 'node:assert/strict';
import test from 'node:test';
import {createFixtureV110} from './fixture_v110_lab.mjs';
import legacy from './staging_readonly_bundle_v108_lab.mjs';

async function setup(t, options) {
  const fixture = await createFixtureV110(options);
  t.after(() => fixture.db.close());
  return fixture;
}

async function issue(fixture, role, path, body, headers = fixture.postHeaders) {
  return fixture.request(role, '/api/intent', {method: 'POST', body: {path, body}, headers});
}

async function enroll(fixture, slot) {
  const invitation = await fixture.action('owner', '/owner/invite', {slot, email: fixture.identity(slot).email});
  assert.equal(invitation.status, 200);
  assert.equal((await fixture.request(slot, '/join/')).status, 200);
  assert.equal((await fixture.action(slot, '/api/enroll', {})).status, 200);
}

test('Access context and current D1 role protect pages, role assets and APIs', async t => {
  const f = await setup(t);
  for (const route of ['/owner/', '/contributors/levels/', '/owner/contributors-v110.js', '/api/catalog']) {
    assert.equal((await f.request(null, route)).status, 403);
  }
  for (const route of ['/owner/', '/owner/contributors-v110.js', '/owner/queue']) {
    assert.equal((await f.request('friend-a', route)).status, 403);
  }
  for (const claims of [{service_token_status: true}, {email: f.identity('friend-b').email}, {exp: 1}]) {
    assert.equal((await f.request('friend-a', '/api/profile', {token: f.issueToken('friend-a', claims)})).status, 403);
  }
  assert.equal((await f.request('friend-a', '/api/profile', {
    headers: {Origin: 'https://other.invalid'},
  })).status, 403);
  const dashboard = await f.request('friend-a', '/contributors/');
  assert.equal(dashboard.status, 200);
  assert.match(dashboard.headers.get('Cache-Control'), /no-store/);
  assert.match(dashboard.headers.get('Content-Security-Policy'), /frame-ancestors 'none'/);
  const html = await dashboard.text();
  assert.equal((html.match(/<th scope="row">/g) ?? []).length, 42);
  assert.doesNotMatch(html, /href="\/owner\//);
});

test('an intent gates same-origin creation and fails on payload changes or another identity', async t => {
  const f = await setup(t);
  const body = f.payload();
  assert.equal((await f.request('friend-a', '/api/submit', {
    method: 'POST', headers: f.postHeaders, body,
  })).status, 403);
  assert.equal((await issue(f, 'friend-a', '/api/submit', body, {
    ...f.postHeaders, Origin: 'https://other.invalid',
  })).status, 403);
  assert.equal((await issue(f, 'friend-a', '/api/submit', {...body, note: 'x'.repeat(4096)})).status, 400);
  const proof = await issue(f, 'friend-a', '/api/submit', body);
  assert.equal(proof.status, 200);
  const {intent} = await proof.json();
  const headers = {...f.postHeaders, 'X-Remura-Intent': intent};
  assert.equal((await f.request('friend-a', '/api/submit', {
    method: 'POST', headers, body: {...body, price: '1.1'},
  })).status, 403);
  await enroll(f, 'friend-b');
  assert.equal((await f.request('friend-b', '/api/submit', {method: 'POST', headers, body})).status, 403);
  assert.equal((await f.request('friend-a', '/api/submit', {method: 'POST', headers, body})).status, 200);
  assert.equal((await f.request('friend-a', '/api/submit', {method: 'POST', headers, body})).status, 200);
  assert.equal((await (await f.request('friend-a', '/api/receipts')).json()).items.length, 1);
});

test('three slots stay isolated and a revoked Access session loses app authorization', async t => {
  const f = await setup(t);
  await enroll(f, 'friend-b');
  await enroll(f, 'friend-c');
  const draft = f.payload();
  const original = await (await f.action('friend-a', '/api/submit', draft)).json();
  const duplicate = await (await f.action('friend-a', '/api/submit', f.payload({note: 'Secondo tentativo'}))).json();
  assert.equal(original.state, 'COMMITTED');
  assert.equal(duplicate.state, 'DUPLICATE');
  assert.equal(original.receipt.id, duplicate.receipt.id);
  for (const role of ['friend-b', 'friend-c']) {
    assert.equal((await (await f.request(role, '/api/receipts')).json()).items.length, 0);
    const headers = {'X-Remura-Request-ID': draft.request_id};
    assert.deepEqual(await (await f.request(role, '/api/level-attempt/status', {headers})).json(), {state: 'NOT_FOUND'});
  }
  const rejected = await f.action('owner', '/owner/review', {
    id: original.receipt.id, action: 'REJECTED', reason: 'Controllo locale',
  });
  assert.equal(rejected.status, 200);
  assert.equal((await (await f.request('friend-a', '/api/receipts')).json()).items[0].status, 'REJECTED');
  assert.equal((await f.action('owner', '/owner/revoke', {slot: 'friend-b'})).status, 200);
  assert.equal((await f.request('friend-b', '/api/profile')).status, 403);
  assert.equal((await f.request('friend-c', '/api/profile')).status, 200);
});

test('each write gate can independently close mutations and v1.08 can roll back on migrated SQLite', async t => {
  const f = await setup(t, {write: false});
  assert.equal((await issue(f, 'friend-a', '/api/submit', f.payload())).status, 403);
  for (const [role, route, status] of [['owner', '/owner/', 200], ['friend-a', '/contributors/', 200],
    ['friend-a', '/owner/', 403]]) {
    const result = await legacy.fetch(new Request(f.env.STAGING_ORIGIN + route), f.env, f.accessContext(f.issueToken(role)));
    assert.equal(result.status, status);
    if (status === 200) assert.match(await result.text(), /v1\.08 LAB/);
  }
  f.flags({write: true});
  delete f.env.CONTRIBUTORS_V110_WRITE;
  assert.equal((await issue(f, 'friend-a', '/api/submit', f.payload())).status, 403);
  assert.equal((await f.request('friend-a', '/api/receipts')).status, 200);
  assert.equal((await (await f.request('friend-a', '/api/profile')).json()).can_write, false);
});
