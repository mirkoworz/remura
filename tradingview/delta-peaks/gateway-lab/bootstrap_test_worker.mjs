// REMURA TEST BOOTSTRAP v0.8.25 — 13/11/2026, ore 16:30 CET
// SOLO GITHUB. Da usare per creare, DOPO consenso, il Worker TEST iniziale.
// Nessun DB, limiter, Secret, token, fetch esterno, log, webhook o trading.
const COMMON_HEADERS = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
  "x-content-type-options": "nosniff",
};

function reply(code, body) {
  return new Response(JSON.stringify(body), {
    status: code, headers: COMMON_HEADERS,
  });
}

export default {
  async fetch(request, _env, _ctx) {
    // Ignora ambiente, credenziali, IP, body e query string:
    // un attaccante NON può attivare ingest con variabili non attese.
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/health" && !url.search)
      return reply(200, { status: "bootstrap_only", accepting: false });
    // Qualsiasi POST, incluso /ingest/<token>, resta inerte.
    return reply(503, { status: "disabled", accepting: false });
  },
};
