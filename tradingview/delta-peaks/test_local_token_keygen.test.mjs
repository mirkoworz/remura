// REMURA v0.8.35 — 13/11/2026 CET — strictly offline browser-logic tests.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createHash, webcrypto } from "node:crypto";
import { test } from "node:test";
import vm from "node:vm";

const html = readFileSync(new URL("./crea-token-test.html", import.meta.url), "utf8");
const script = html.match(/<script>([\s\S]*?)<\/script>/)?.[1];

function mount(secure=true) {
  assert.ok(script);
  const elements = new Map();
  const get = (id) => {
    if (!elements.has(id)) {
      elements.set(id, {
        hidden: id === "values", value: "", textContent: "",
        addEventListener(_event, fn) { this.handler = fn; },
        focus() { this.focused = true; },
        select() { this.selected = true; },
      });
    }
    return elements.get(id);
  };
  const buttons = ["hash", "url"].map(key => ({
    dataset: { copy: key },
    addEventListener(_event, fn) { this.handler = fn; }
  }));
  const copied = [];
  const context = {
    document: {
      getElementById: get,
      querySelectorAll(selector) {
        assert.equal(selector, "[data-copy]");
        return buttons;
      }
    },
    navigator: { clipboard: { async writeText(x) { copied.push(x); } } },
    crypto: secure ? webcrypto : undefined,
    isSecureContext: secure,
    TextEncoder,
    btoa: str => Buffer.from(str, "binary").toString("base64")
  };
  vm.runInNewContext(script, context);
  return {get, buttons, copied};
}

test("self-contained key generator neither contacts network nor persists raw secrets", () => {
  assert.match(html, /connect-src 'none'/);
  assert.match(html, /default-src 'none'/);
  assert.doesNotMatch(html, /<script\s+src/i);
  assert.doesNotMatch(script, /\bfetch\s*\(|\bXMLHttpRequest\b|\bWebSocket\b|sendBeacon|localStorage|sessionStorage/);
  assert.doesNotMatch(script, /Math\.random|document\.cookie|\beval\s*\(/);
  assert.match(script, /getRandomValues\(new Uint8Array\(32\)\)/);
  assert.match(script, /crypto\.subtle\.digest\(/);
  assert.match(html, /REMURA.*v0\.8\.35/);
});

test("crypto-generated 256-bit token gives correct URL and SHA-256 digest", async () => {
  const ui = mount();
  await ui.get("generate").handler();
  assert.equal(ui.get("values").hidden, false);
  const url = ui.get("url").value;
  assert.match(url, /^https:\/\/remura-tv-webhook-test\.mirkoworz\.workers\.dev\/ingest\/[A-Za-z0-9_-]{43}$/);
  assert.doesNotMatch(url, /remura-tv-ingest-lab|remura-tv-lab-test/);
  const token = url.split("/").at(-1);
  const hash = createHash("sha256").update(token).digest("hex");
  assert.equal(ui.get("hash").value, hash);
  assert.equal(hash.length, 64);
  assert.notEqual(hash, token);
  await ui.buttons[0].handler();
  await ui.buttons[1].handler();
  assert.deepEqual(ui.copied, [hash, url]);
  ui.get("clear").handler();
  assert.equal(ui.get("values").hidden, true);
  assert.equal(ui.get("url").value, "");
  assert.equal(ui.get("hash").value, "");
});

test("generator refuses insecure browser and never falls back to weak randomness", async () => {
  const ui = mount(false);
  await ui.get("generate").handler();
  assert.equal(ui.get("values").hidden, true);
  assert.equal(ui.get("hash").value, "");
  assert.equal(ui.get("url").value, "");
  assert.match(ui.get("status").textContent, /non disponibile/i);
});
