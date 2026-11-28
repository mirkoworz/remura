# REMURA V30.19 release gate — 28 November 2026 09:28 CET
## Verified documentation (not actual account metrics)
Cloudflare D1 Free: 5,000,000 rows read/day, 100,000 rows written/day, 5 GB total, 500 MB/database, 50 queries/Worker invocation. Daily quotas account-wide, reset UTC. On Free D1 exceeds daily limits by failing queries, not automatically charging overage. Index updates and scans count, so an invocation count is not a row count. Sources:
- https://developers.cloudflare.com/d1/platform/pricing/
- https://developers.cloudflare.com/d1/platform/limits/
- https://developers.cloudflare.com/changelog/post/2026-09-01-d1-free-tier-limit-enforcement/
Pilot maximum: 3 contributors, 20 submitted prices per contributor/UTC day across ledgers, 60 proposals/attempts per contributor/day, max 60 prices/180 proposals aggregate. Not a bound on read scans or other account traffic. No scheduled polling added. Actual row/worker budgets must be verified from current dashboard before installation; 27 Nov verification is historical. Proposed conservative preflight stop above 80% of ANY account free quota; not automatically activated.
## Migration
proposal-release-migration.sql is exact concatenation of four pinned SQL sources (header comments identify their blobs). One Wrangler migration file, not four separate remote operations; no BEGIN/COMMIT inside. Cloudflare documents rollback of a failed individual migration:
https://developers.cloudflare.com/d1/wrangler-commands/#d1-migrations-apply
https://developers.cloudflare.com/d1/worker-api/d1-database/#batch
No remote execution, no config or production change. A real installation must first verify current plan, D1 schema, migration history, approved backup/Time Travel bookmark, old Telegram pending/sending=0, write STOP, Telegram OFF and zero new proposal tables. Local D1 parity still unverified. Keep all old tables and records. Restore old worker read-only with Telegram OFF and preserve new ledger after rollback; V30.18 cannot display new proposals and old write guard remains closed. Real transport is separately gated and OFF by default.
## Executed evidence
13/13 SQLite 3.46.1 actual checks of realm installation/rollback/immutability using minimal synthetic base, SQL git blob 39f3aed18e11371e68624c1ecdd9f13697022e19 exactly matches local file. Test source recorded in test_release_realm.py (equivalent test, not full D1). Prior 37/37 mock transport checks not repeated. New LAB Worker rejects any request on release realm, not only simulated delivery.
## Not yet executed
Full Node integration test now covers synthetic and release modes, guarded mocked Telegram (no network), role and mode changes, concurrent replay, legacy rollback read-only. JS source parse only; full runtime requires authenticated local checkout, not available in this runtime. Offline runner run-v3019-offline.sh only executes new integration, no installs. Browser/Safari, actual Cloudflare metrics, D1 compatibility, real Telegram delivery and release authorization remain open. Never deploy a candidate on this evidence alone.
