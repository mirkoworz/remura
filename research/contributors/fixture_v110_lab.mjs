// Local fixture for the v1.10 Worker. It does not provide a deployable configuration.
import {createHmac, randomBytes, randomUUID, timingSafeEqual} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {createServer} from 'node:http';
import {DatabaseSync} from 'node:sqlite';
import {pathToFileURL} from 'node:url';
import sourceWorker from './staging_contributors_v110_lab.mjs';

const packagedWorker = process.env.REMURA_V110_WORKER_FILE;
const worker = packagedWorker ? (await import(pathToFileURL(packagedWorker))).default : sourceWorker;

const FIXTURE_ORIGIN = 'https://contributors-v110.invalid';
const COOKIE = 'remura_lab_access';
const json64 = value => Buffer.from(JSON.stringify(value)).toString('base64url');
const hexKey = () => randomBytes(32).toString('hex');
const nowSeconds = () => Math.floor(Date.now() / 1000);

async function applySql(db, name, atomic = false) {
  const source = await readFile(new URL(name, import.meta.url), 'utf8');
  if (atomic) db.exec('BEGIN IMMEDIATE');
  try {
    db.exec(source);
    if (atomic) db.exec('COMMIT');
  } catch (error) {
    if (atomic && db.isTransaction) db.exec('ROLLBACK');
    throw error;
  }
}

function localD1(db) {
  const adapter = {
    prepare(sql) {
      return {
        bind(...values) {
          return {
            async all() {
              return {
                success: true,
                meta: {served_by_primary: true},
                results: db.prepare(sql).all(...values),
              };
            },
          };
        },
      };
    },
    withSession(mode) {
      if (mode !== 'first-primary') throw Error('expected primary-first D1 session');
      return adapter;
    },
  };
  return adapter;
}

async function identityTags(identity, env) {
  const tag = (domain, value) => createHmac('sha256', Buffer.from(env.IDENTITY_HMAC_KEY, 'hex'))
    .update(JSON.stringify(['remura-contributors-v1', env.ACCESS_ACCOUNT, env.ACCESS_AUD, domain, value])).digest('hex');
  return [tag('uuid', identity.user_uuid), tag('email', identity.email)];
}

export async function createFixtureV110({write = true, recovery = false, dbPath = ':memory:'} = {}) {
  const db = new DatabaseSync(dbPath, {enableForeignKeyConstraints: true});
  const jwtKey = randomBytes(32);
  const identities = {};
  const env = {
    STAGING_ENABLED: 'D1_CANDIDATE',
    STAGING_ORIGIN: FIXTURE_ORIGIN,
    PRIVATE_WORKER_V078: 'STAGING_AUTHENTICATED_READONLY',
    CONTRIBUTORS_STAGE_READONLY: 'EXPLICIT_STAGING_ONLY',
    CONTRIBUTORS_V110_WRITE: 'EXPLICIT_STAGING_ONLY',
    ACCESS_ACCOUNT: randomBytes(16).toString('hex'),
    ACCESS_AUD: hexKey(),
    IDENTITY_HMAC_KEY: hexKey(),
    INTENT_HMAC_KEY: hexKey(),
    CONTRIBUTORS_DB: localD1(db),
  };

  function identity(name) {
    identities[name] ??= {
      account_id: env.ACCESS_ACCOUNT,
      user_uuid: randomUUID(),
      email: `lab-${randomBytes(12).toString('hex')}@fixture.invalid`,
      service_token_status: false,
      service_token_id: null,
    };
    return identities[name];
  }

  function issueToken(name, claims = {}, attributes = {}) {
    const payload = {
      ...identity(name), iss: FIXTURE_ORIGIN, aud: env.ACCESS_AUD,
      nbf: nowSeconds() - 1, exp: nowSeconds() + 3600, ...claims,
    };
    const body = `${json64({alg: 'HS256', typ: 'JWT', ...attributes})}.${json64(payload)}`;
    return `${body}.${createHmac('sha256', jwtKey).update(body).digest('base64url')}`;
  }

  function accessContext(token) {
    if (!token) return {};
    try {
      const parts = token.split('.');
      if (parts.length !== 3 || parts.some(part => !/^[A-Za-z0-9_-]+$/.test(part))) return {};
      const [head, body, signature] = parts;
      const supplied = Buffer.from(signature, 'base64url');
      const expected = createHmac('sha256', jwtKey).update(`${head}.${body}`).digest();
      if (supplied.length !== expected.length || !timingSafeEqual(supplied, expected)) return {};
      const header = JSON.parse(Buffer.from(head, 'base64url'));
      const claims = JSON.parse(Buffer.from(body, 'base64url'));
      if (header.alg !== 'HS256' || header.typ !== 'JWT' || claims.iss !== FIXTURE_ORIGIN ||
          claims.aud !== env.ACCESS_AUD || !Number.isInteger(claims.nbf) || !Number.isInteger(claims.exp) ||
          claims.nbf > nowSeconds() || claims.exp <= nowSeconds()) return {};
      const {account_id, user_uuid, email, service_token_status, service_token_id} = claims;
      return {access: {aud: claims.aud, getIdentity: async () => ({
        account_id, user_uuid, email, service_token_status, service_token_id,
      })}};
    } catch {
      return {};
    }
  }

  function flags({read = true, write = true, recovery = false} = {}) {
    db.prepare('UPDATE lab_state SET read_enabled=?,write_enabled=?,recovery_enabled=? WHERE id=1')
      .run(Number(read), Number(write), Number(recovery));
  }

  try {
    await applySql(db, './staging-readonly-v105-REVIEW-ONLY.sql');
    db.prepare('UPDATE lab_state SET read_enabled=1 WHERE id=1').run();
    db.prepare('INSERT INTO lab_owner(id,subject,email_tag) VALUES (1,?,?)')
      .run(...await identityTags(identity('owner'), env));
    db.prepare("INSERT INTO lab_identities(slot,subject,email_tag) VALUES ('friend-a',?,?)")
      .run(...await identityTags(identity('friend-a'), env));
    await applySql(db, './staging-slots-v110.sql', true);
    await applySql(db, './staging-levels-v110.sql', true);
    db.prepare("INSERT INTO lab_level_catalog_v110(market,provider,ticker,product,contract,source_group,active) VALUES ('EURUSD','OANDA','EURUSD','SPOT','','LAB',1)").run();
    flags({write, recovery});
  } catch (error) {
    db.close();
    throw error;
  }

  function request(name, path, {method = 'GET', body, headers = {}, token = name ? issueToken(name) : '', ctx} = {}) {
    return worker.fetch(new Request(FIXTURE_ORIGIN + path, {
      method, body: body === undefined ? undefined : JSON.stringify(body), headers,
    }), env, ctx ?? accessContext(token));
  }

  const postHeaders = {'Content-Type': 'application/json', Origin: FIXTURE_ORIGIN,
    'Sec-Fetch-Site': 'same-origin', 'X-Remura-CSRF': '1'};
  async function action(name, path, body, options = {}) {
    const proof = await request(name, '/api/intent', {
      method: 'POST', body: {path, body}, headers: postHeaders,
    });
    if (!proof.ok) return proof;
    const {intent} = await proof.json();
    return request(name, path, {
      method: 'POST', body, headers: {...postHeaders, 'X-Remura-Intent': intent}, ...options,
    });
  }

  function payload(overrides = {}) {
    return {request_id: randomUUID(), market: 'EURUSD', provider: 'OANDA',
      ticker: 'EURUSD', product: 'SPOT', contract: '', period: 'WEEK', kind: 'DELTA_PEAK',
      price: '1.0849', anchor_utc: '2026-11-16T00:00:00Z',
      observed_utc: '2026-11-17T12:30:00Z', note: 'Collaudo locale', ...overrides};
  }

  return {db, env, flags, identity, issueToken, accessContext, request, action, payload, postHeaders};
}

export async function serveFixtureV110(fixture) {
  const traffic = [];
  const server = createServer(async (incoming, outgoing) => {
    try {
      const headers = new Headers(incoming.headers);
      const token = (headers.get('Cookie') ?? '').split('; ')
        .find(cookie => cookie.startsWith(`${COOKIE}=`))?.slice(COOKIE.length + 1);
      headers.delete('Cookie');
      headers.delete('Cf-Access-Jwt-Assertion');
      if (headers.get('Origin') === origin) headers.set('Origin', FIXTURE_ORIGIN);
      const chunks = [];
      for await (const chunk of incoming) chunks.push(chunk);
      const path = incoming.url;
      const body = chunks.length ? Buffer.concat(chunks) : undefined;
      traffic.push({method: incoming.method, path});
      const result = await worker.fetch(new Request(FIXTURE_ORIGIN + path, {
        method: incoming.method, headers, body,
      }), fixture.env, fixture.accessContext(token));
      outgoing.writeHead(result.status, Object.fromEntries(result.headers));
      outgoing.end(Buffer.from(await result.arrayBuffer()));
    } catch {
      outgoing.writeHead(502).end();
    }
  });
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  const origin = `http://127.0.0.1:${server.address().port}`;
  return {
    origin, traffic, cookie: COOKIE,
    async close() {
      server.closeAllConnections();
      await new Promise((resolve, reject) => server.close(error => error ? reject(error) : resolve()));
    },
  };
}
