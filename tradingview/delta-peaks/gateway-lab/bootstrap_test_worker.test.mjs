// REMURA BOOTSTRAP TEST v0.8.25 — 13/11/2026 ore 16:30 CET
// Tutti input sintetici in Node, nessun HTTP esterno né D1.
import test from "node:test";
import assert from "node:assert/strict";
import bootstrap from "./bootstrap_test_worker.mjs";

const ORIGIN = "https://remura-tv-webhook-test.invalid";
const SENSITIVE = "test-synthetic-should-never-be-reflected-abcdef012345";
function req(path, method = "GET", extra = {}) {
  return new Request(ORIGIN + path, {method, ...extra});
}

async function unpack(res) {
  return {status: res.status, body: await res.json(),
    contentType: res.headers.get("content-type"),
    noStore: res.headers.get("cache-control")};
}

test("health confirms unavailable even with risky bindings supplied", async () => {
  let calls = 0;
  const env = {
    INGEST_ENABLED: "true",
    WEBHOOK_TOKEN_SHA256: "a".repeat(64),
    TELEMETRY_DB: {prepare() {calls++; throw Error("D1 must never be used");}},
    INGEST_RATE_LIMITER: {limit() {calls++; throw Error("Limiter not used");}},
  };
  const res = await unpack(await bootstrap.fetch(req("/health"), env));
  assert.equal(res.status, 200);
  assert.deepEqual(res.body, {status: "bootstrap_only", accepting: false});
  assert.equal(res.noStore, "no-store");
  assert.equal(calls, 0);
});

test("all POST webhook variants remain disabled", async () => {
  const samples = [
    "/ingest/" + SENSITIVE,
    "/",
    "/health",
    "/ingest/" + SENSITIVE + "?retry=1",
    "/events",
  ];
  for (const p of samples) {
    const out = await unpack(await bootstrap.fetch(req(p, "POST", {
      headers: {"content-type": "application/json"},
      body: JSON.stringify({token: SENSITIVE, type: "BAR_EVENT"}),
    }), {INGEST_ENABLED: "true"}));
    assert.equal(out.status, 503, p);
    assert.equal(out.body.accepting, false);
    assert.equal(out.body.status, "disabled");
    assert.doesNotMatch(JSON.stringify(out.body), /test-synthetic-should-never/);
  }
});

test("no database or other environment calls even with hostile environment", async () => {
  const never = new Proxy({}, {get() {throw new Error("env accessed");}});
  const res = await unpack(await bootstrap.fetch(req("/ingest/" + SENSITIVE, "POST"), never));
  assert.equal(res.status, 503);
  assert.equal(res.body.accepting, false);
});

test("unauthorized paths and query on health reveal no state", async () => {
  const paths = ["/health?token=" + SENSITIVE, "/Health", "/health/", "/",
                 "/ingest/" + SENSITIVE];
  for (const path of paths) {
    const out = await unpack(await bootstrap.fetch(req(path)));
    assert.equal(out.status, 503);
    assert.equal(out.body.accepting, false);
  }
});

test("other HTTP methods are disabled and no content is echoed", async () => {
  for (const method of ["PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]) {
    const res = await bootstrap.fetch(req("/ingest/" + SENSITIVE, method));
    assert.equal(res.status, 503);
    assert.equal(res.headers.get("cache-control"), "no-store");
  }
});

test("response always has JSON no-store and nosniff headers", async () => {
  for (const request of [req("/health"), req("/"), req("/ingest/" + SENSITIVE, "POST")]) {
    const res = await bootstrap.fetch(request);
    assert.match(res.headers.get("content-type"), /^application\/json/);
    assert.equal(res.headers.get("cache-control"), "no-store");
    assert.equal(res.headers.get("x-content-type-options"), "nosniff");
  }
});
