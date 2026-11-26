// Direct Cloudflare Access Worker for the dedicated REMURA Contributors staging origin.
import {normalizeNewLevelV076} from './level_attempt_journal_v076_lab.mjs';
import {scheduleTelegramAfterSubmit} from './telegram_transport_v3012_lab.mjs';
import {createLevelsStoreV110, LevelsStoreError} from './staging_levels_store_v110_lab.mjs';
import {
  CONTRIBUTORS_BROWSER_V110, CONTRIBUTORS_CSS_V110, renderContributorsPageV110,
} from './contributors_ui_v110_lab.mjs';

const HEX = /^[a-f0-9]{64}$/;
const UUID = /^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/;
const EMAIL = /^[^\s@\u0000-\u001f\u007f-\u009f]{1,64}@[^\s@\u0000-\u001f\u007f-\u009f]{1,189}$/u;
const SLOTS = new Set(['friend-a', 'friend-b', 'friend-c']);
const INVITE_SLOTS = new Set(['friend-b', 'friend-c']);
const ROLE_DIRECTORY = {OWNER: '/owner/', CONTRIBUTOR: '/contributors/', INVITED: '/join/'};
const READS = new Map([
  ['/api/catalog', 'CONTRIBUTOR'],
  ['/api/receipts', 'CONTRIBUTOR'],
  ['/api/level-attempt/status', 'CONTRIBUTOR'],
  ['/owner/queue', 'OWNER'],
  ['/owner/history', 'OWNER'],
  ['/owner/audit', 'OWNER'],
  ['/owner/collaborators', 'OWNER'],
]);
const PAGED = new Set(['/api/receipts', '/owner/queue', '/owner/history', '/owner/audit']);
const ACTIONS = new Map([
  ['/api/submit', 'CONTRIBUTOR'],
  ['/owner/review', 'OWNER'],
  ['/owner/invite', 'OWNER'],
  ['/owner/withdraw', 'OWNER'],
  ['/owner/revoke', 'OWNER'],
  ['/api/enroll', 'INVITED'],
]);
const SLOT_ACTIONS = new Set(['/owner/invite', '/owner/withdraw', '/owner/revoke']);
const SENSITIVE_HEADERS = ['x-remura-role', 'x-remura-subject', 'x-remura-actor', 'x-remura-admin'];
const LIMIT_BYTES = 4096;
const PAGE_SIZE = 20;
const INTENT_TTL = 90;
const ENCODER = new TextEncoder();
const HEADERS = {
  'Cache-Control': 'private, no-store, max-age=0',
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'X-Robots-Tag': 'noindex, nofollow, noarchive',
  'Referrer-Policy': 'no-referrer',
  'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
  'Cross-Origin-Resource-Policy': 'same-origin',
  'Content-Security-Policy': "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; object-src 'none'; form-action 'none'; frame-ancestors 'none'",
};
const REQUEST_ERRORS = {
  denied: 403, invalid: 400, conflict: 409, invalid_mapping: 409,
  capacity: 429,
};

function response(body, type, status = 200) {
  return new Response(body, {status, headers: {...HEADERS, 'Content-Type': type}});
}

function json(body, status = 200) {
  return response(JSON.stringify(body), 'application/json; charset=utf-8', status);
}

function reject(code = 'denied') {
  return json({error: code}, REQUEST_ERRORS[code]);
}

function unavailable(write) {
  return json({error: write ? 'outcome_unknown' : 'temporarily_unavailable'}, 503);
}

function hasKey(value) {
  return typeof value === 'string' && HEX.test(value) && !/^0+$/.test(value);
}

function bytes(value) {
  return Uint8Array.from(value.match(/../g), part => parseInt(part, 16));
}

function hex(value) {
  return Array.from(new Uint8Array(value), part => part.toString(16).padStart(2, '0')).join('');
}

function hmac(secret, usages) {
  return crypto.subtle.importKey('raw', bytes(secret), {name: 'HMAC', hash: 'SHA-256'}, false, usages);
}

function ready(env, url) {
  return url.protocol === 'https:' && url.origin === env?.STAGING_ORIGIN &&
    !url.username && !url.password &&
    env.PRIVATE_WORKER_V078 === 'STAGING_AUTHENTICATED_READONLY' &&
    env.CONTRIBUTORS_STAGE_READONLY === 'EXPLICIT_STAGING_ONLY' &&
    env.STAGING_ENABLED === 'D1_CANDIDATE' &&
    typeof env.ACCESS_AUD === 'string' && HEX.test(env.ACCESS_AUD) &&
    typeof env.ACCESS_ACCOUNT === 'string' && /^[a-f0-9]{32}$/.test(env.ACCESS_ACCOUNT) &&
    hasKey(env.IDENTITY_HMAC_KEY) && typeof env.CONTRIBUTORS_DB?.withSession === 'function';
}

// Keep the exact v1.08 HMAC namespace and values so existing D1 bindings survive.
async function identityTag(key, env, domain, value) {
  const data = JSON.stringify(['remura-contributors-v1', env.ACCESS_ACCOUNT, env.ACCESS_AUD, domain, value]);
  return hex(await crypto.subtle.sign('HMAC', key, ENCODER.encode(data)));
}

async function authenticate(ctx, env) {
  const access = ctx?.access;
  if (access?.aud !== env.ACCESS_AUD || typeof access.getIdentity !== 'function') return null;
  const identity = await access.getIdentity();
  if (identity?.account_id !== env.ACCESS_ACCOUNT || typeof identity.user_uuid !== 'string' ||
      !UUID.test(identity.user_uuid) || typeof identity.email !== 'string' || !EMAIL.test(identity.email) ||
      identity.service_token_status !== false ||
      (identity.service_token_id != null && identity.service_token_id !== '')) return null;
  const key = await hmac(env.IDENTITY_HMAC_KEY, ['sign']);
  const [subject, email_tag] = await Promise.all([
    identityTag(key, env, 'uuid', identity.user_uuid),
    identityTag(key, env, 'email', identity.email),
  ]);
  return {actor: Object.freeze({subject, email_tag}), key};
}

function writesEnabled(env) {
  return env.CONTRIBUTORS_V110_WRITE === 'EXPLICIT_STAGING_ONLY' &&
    hasKey(env.INTENT_HMAC_KEY) && env.INTENT_HMAC_KEY !== env.IDENTITY_HMAC_KEY;
}

async function resolvedProfile(store, actor, allowWrite, mayBeInvited) {
  const profile = await store.profile(actor);
  if (profile?.can_read === true) {
    return {data: {...profile, can_write: allowWrite && profile.can_write === true}};
  }
  if (profile === null && allowWrite && mayBeInvited) {
    const invited = await store.getInvite(actor);
    if (INVITE_SLOTS.has(invited?.slot) && Number.isSafeInteger(invited.revision) && invited.revision > 0) {
      return {
        data: {role: 'INVITED', slot: invited.slot, can_read: true, can_write: true, can_recover: false},
        revision: invited.revision,
      };
    }
  }
  return null;
}

function originAllowed(req, origin) {
  const site = req.headers.get('Sec-Fetch-Site');
  const contentType = req.headers.get('Content-Type')?.toLowerCase().trim();
  return req.headers.get('Origin') === origin &&
    (site === null || site === 'same-origin') &&
    req.headers.get('X-Remura-CSRF') === '1' &&
    (contentType === 'application/json' || contentType === 'application/json; charset=utf-8') &&
    !req.headers.has('Content-Encoding');
}

function shape(value, fields) {
  return !!value && Object.getPrototypeOf(value) === Object.prototype &&
    Object.keys(value).length === fields.length && fields.every(field => Object.hasOwn(value, field));
}

async function requestBody(req) {
  const declaration = req.headers.get('Content-Length');
  if (declaration !== null && (!/^[1-9]\d{0,3}$/.test(declaration) || Number(declaration) > LIMIT_BYTES)) {
    throw Error('length');
  }
  const reader = req.body?.getReader();
  if (!reader) throw Error('body');
  const data = new Uint8Array(LIMIT_BYTES);
  let length = 0;
  try {
    for (;;) {
      const {value, done} = await reader.read();
      if (done) break;
      if (length + value.byteLength > LIMIT_BYTES) {
        void reader.cancel().catch(() => {});
        throw Error('length');
      }
      data.set(value, length);
      length += value.byteLength;
    }
  } finally {
    reader.releaseLock();
  }
  if (declaration !== null && Number(declaration) !== length) throw Error('length');
  return JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(data.subarray(0, length)));
}

function normalizeAction(path, body, now) {
  if (path === '/api/submit') {
    if (!body || Object.getPrototypeOf(body)!==Object.prototype) throw Error('fields');
    const {publication_mode,...original}=body;
    const normalized=normalizeNewLevelV076(original,now);
    if (publication_mode===undefined) return normalized; // legacy client remains PRIVATE
    if (!['PRIVATE','TEST','TELEGRAM'].includes(publication_mode)) throw Error('publication');
    return Object.freeze({...normalized,publication_mode});
  }
  if (path === '/owner/review' && shape(body, ['id', 'action', 'reason']) &&
      Number.isSafeInteger(body.id) && body.id > 0 &&
      ['APPROVED', 'REJECTED'].includes(body.action) && typeof body.reason === 'string') {
    const reason = body.reason.trim();
    if (reason && [...reason].length <= 280 && !/[\u0000-\u001f\u007f-\u009f\uD800-\uDFFF]/u.test(reason)) {
      return {id: body.id, action: body.action, reason};
    }
  }
  if (path === '/owner/invite' && shape(body, ['slot', 'email']) && INVITE_SLOTS.has(body.slot) &&
      typeof body.email === 'string' && EMAIL.test(body.email)) return body;
  if (path === '/owner/withdraw' && shape(body, ['slot']) && INVITE_SLOTS.has(body.slot)) return body;
  if (path === '/owner/revoke' && shape(body, ['slot']) && SLOTS.has(body.slot)) return body;
  if (path === '/api/enroll' && shape(body, [])) return body;
  throw Error('fields');
}

function intentMessage(env, actor, profile, path, body, expiry, revision, nonce) {
  const fields = Object.keys(body).sort().map(name => [name, body[name]]);
  return ENCODER.encode(JSON.stringify([
    'remura-contributors-v110-mutation', env.STAGING_ORIGIN, env.ACCESS_ACCOUNT, env.ACCESS_AUD,
    actor.subject, actor.email_tag, profile.role, profile.slot, path, fields, expiry, revision, nonce,
  ]));
}

async function issueIntent(env, actor, profile, path, body, revision, time) {
  const nonce = hex(crypto.getRandomValues(new Uint8Array(16)));
  const expiry = time + INTENT_TTL;
  const key = await hmac(env.INTENT_HMAC_KEY, ['sign']);
  const mac = await crypto.subtle.sign('HMAC', key, intentMessage(env, actor, profile, path, body, expiry, revision, nonce));
  return [nonce, expiry, revision, hex(mac)].join('.');
}

async function verifyIntent(env, actor, profile, path, body, token, time) {
  if (!token || !/^[a-f0-9]{32}\.\d{10}\.(0|[1-9]\d{0,15})\.[a-f0-9]{64}$/.test(token)) return null;
  const [nonce, expires, version, mac] = token.split('.');
  const expiry = Number(expires);
  const revision = Number(version);
  if (expiry <= time || expiry > time + INTENT_TTL || !Number.isSafeInteger(revision)) return null;
  const key = await hmac(env.INTENT_HMAC_KEY, ['verify']);
  const valid = await crypto.subtle.verify(
    'HMAC', key, bytes(mac), intentMessage(env, actor, profile, path, body, expiry, revision, nonce),
  );
  return valid ? revision : null;
}

function cursor(url) {
  if (!url.search) return 0;
  if (!/^\?after=(0|[1-9]\d{0,15})$/.test(url.search)) return null;
  const after = Number(url.search.slice('?after='.length));
  return Number.isSafeInteger(after) ? after : null;
}

function page(items) {
  return json({items, next: items.length === PAGE_SIZE ? items.at(-1).id : null});
}

async function get(req, url, store, actor, profile) {
  const path = url.pathname;
  if (path === '/api/profile' || READS.has(path)) {
    const origin = req.headers.get('Origin');
    const site = req.headers.get('Sec-Fetch-Site');
    if ((origin !== null && origin !== url.origin) ||
        (site !== null && site !== 'same-origin' && site !== 'none')) return reject();
  }
  if (url.search && !PAGED.has(path)) return reject('invalid');
  if (path === '/api/profile') return json(profile);
  if (READS.has(path)) {
    if (READS.get(path) !== profile.role) return reject();
    const after = cursor(url);
    if (after === null) return reject('invalid');
    switch (path) {
      case '/api/catalog':
        return json({items: await store.catalog(actor)});
      case '/api/receipts':
        return page(await store.receipts(actor, after));
      case '/api/level-attempt/status': {
        const requestId = req.headers.get('X-Remura-Request-ID');
        if (!requestId || !UUID.test(requestId)) return reject('invalid');
        return json(await store.lookup(actor, requestId));
      }
      case '/owner/queue':
        return page(await store.queue(actor, after));
      case '/owner/history':
        return page(await store.history(actor, after));
      case '/owner/audit':
        return page(await store.audit(actor, after));
      case '/owner/collaborators': {
        const items = await store.slots(actor);
        return json({items: items.map(({slot, status}) => ({slot, status: status === 'VACANT' ? 'AVAILABLE' : status}))});
      }
    }
  }
  const directory = ROLE_DIRECTORY[profile.role];
  if (path === '/') return new Response(null, {status: 303, headers: {...HEADERS, Location: directory}});
  if (path === directory + 'contributors-v110.css') {
    return response(CONTRIBUTORS_CSS_V110, 'text/css; charset=utf-8');
  }
  if (path === directory + 'contributors-v110.js') {
    return response(CONTRIBUTORS_BROWSER_V110[profile.role], 'text/javascript; charset=utf-8');
  }
  if (path !== directory && (profile.role === 'INVITED' || path !== directory + 'levels/')) return reject();
  const html = renderContributorsPageV110(path, profile);
  return typeof html === 'string' ? response(html, 'text/html; charset=utf-8') : reject();
}

async function mutate(path, body, revision, {store, actor, key, env, now, ctx, profile}) {
  let result;
  switch (path) {
    case '/api/submit': {
      const receipt = await store.submit(actor, body, now);
      scheduleTelegramAfterSubmit(ctx, env, receipt, profile);
      return json(receipt);
    }
    case '/owner/review':
      result = await store.review(actor, body, now);
      break;
    case '/owner/invite': {
      const emailTag = await identityTag(key, env, 'email', body.email);
      if (emailTag === actor.email_tag) return reject('conflict');
      result = await store.invite(actor, body.slot, emailTag, now, revision);
      break;
    }
    case '/owner/withdraw':
      result = await store.withdraw(actor, body.slot, now, revision);
      break;
    case '/owner/revoke':
      result = await store.revoke(actor, body, now, revision);
      break;
    case '/api/enroll':
      result = await store.enroll(actor, now, revision);
      break;
  }
  return result ? json(result) : reject('conflict');
}

async function post(req, url, opts) {
  const {store, actor, profile, env} = opts;
  if (!profile.can_write || url.search || !originAllowed(req, url.origin)) return reject();
  const issuing = url.pathname === '/api/intent';
  if (!issuing && ACTIONS.get(url.pathname) !== profile.role) return reject();
  let path, body;
  const time = Math.floor(Date.now() / 1000);
  const now = new Date(time * 1000).toISOString().replace('.000Z', 'Z');
  try {
    const parsed = await requestBody(req);
    if (issuing && !shape(parsed, ['path', 'body'])) return reject('invalid');
    path = issuing ? parsed.path : url.pathname;
    if (ACTIONS.get(path) !== profile.role) return reject();
    body = normalizeAction(path, issuing ? parsed.body : parsed, now);
  } catch {
    return reject('invalid');
  }
  if (issuing) {
    let revision = 0;
    if (SLOT_ACTIONS.has(path)) revision = await store.slotRevision(actor, body.slot);
    if (path === '/api/enroll') revision = opts.inviteRevision;
    if (!Number.isSafeInteger(revision) || revision < 0) return reject();
    return json({intent: await issueIntent(env, actor, profile, path, body, revision, time)});
  }
  const revision = await verifyIntent(env, actor, profile, path, body, req.headers.get('X-Remura-Intent'), time);
  if (revision === null || (path === '/api/enroll' && revision !== opts.inviteRevision)) return reject();
  try {
    return await mutate(path, body, revision, {...opts, now});
  } catch (error) {
    if (error instanceof LevelsStoreError && Object.hasOwn(REQUEST_ERRORS, error.code)) return reject(error.code);
    return unavailable(true);
  }
}

function knownRoute(path, method) {
  if (method === 'POST') return path === '/api/intent' || ACTIONS.has(path);
  if (method !== 'GET') return false;
  if (path === '/' || path === '/api/profile' || READS.has(path)) return true;
  return /^\/(?:owner|contributors)\/(?:levels\/|contributors-v110\.(?:css|js))?$/.test(path) ||
    /^\/join\/(?:contributors-v110\.(?:css|js))?$/.test(path);
}

export default {
  async fetch(req, env, ctx) {
    let url, identity;
    try {
      url = new URL(req.url);
      if (!ready(env, url) || !knownRoute(url.pathname, req.method) ||
          SENSITIVE_HEADERS.some(name => req.headers.has(name))) return reject();
      identity = await authenticate(ctx, env);
      if (!identity) return reject();
    } catch {
      return reject();
    }
    try {
      const store = createLevelsStoreV110(env.CONTRIBUTORS_DB);
      const {actor, key} = identity;
      const mayBeInvited = ['/api/profile', '/api/intent', '/api/enroll', '/'].includes(url.pathname) ||
        url.pathname.startsWith('/join/');
      const access = await resolvedProfile(store, actor, writesEnabled(env), mayBeInvited);
      if (!access) return reject();
      if (req.method === 'GET') return await get(req, url, store, actor, access.data);
      return await post(req, url, {store, actor, key, env, ctx, profile: access.data, inviteRevision: access.revision});
    } catch (error) {
      if (error instanceof LevelsStoreError && Object.hasOwn(REQUEST_ERRORS, error.code)) return reject(error.code);
      return unavailable(false);
    }
  },
};
