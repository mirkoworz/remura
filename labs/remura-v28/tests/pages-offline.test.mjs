import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { runInNewContext } from 'node:vm';

const worker = await readFile(new URL('../sw.js', import.meta.url), 'utf8');

for (const path of ['/', '/isolated/remura/']) {
  test(`Cloudflare Pages shell and offline aliases at ${path}`, async () => {
    const scope = new URL(path, 'https://remura.example').href;
    const index = new URL('index.html', scope).href;
    const listeners = new Map();
    const cached = new Set();
    const savedShell = new Response('<!doctype html><title>REMURA</title>');

    runInNewContext(worker, {
      URL,
      Request,
      self: {
        registration: { scope },
        addEventListener: (type, listener) => listeners.set(type, listener),
      },
      caches: {
        open: async () => ({
          async addAll(requests) {
            for (const request of requests) {
              assert.equal(request.redirect, 'error');
              if (request.url === index) throw new TypeError('Pages redirects index.html to the directory');
            }
            for (const request of requests) cached.add(request.url);
          },
        }),
        match: async key => cached.has(key) ? savedShell : undefined,
      },
      fetch: async () => { throw new TypeError('Offline'); },
    });

    let install;
    listeners.get('install')({ waitUntil: promise => { install = promise; } });
    await install;
    assert(cached.has(scope));
    assert(!cached.has(index));

    for (const url of [scope, index + '?preview=1']) {
      let response;
      listeners.get('fetch')({
        request: { url, mode: 'navigate', method: 'GET' },
        respondWith: promise => { response = promise; },
      });
      assert.equal(await response, savedShell);
    }
  });
}
