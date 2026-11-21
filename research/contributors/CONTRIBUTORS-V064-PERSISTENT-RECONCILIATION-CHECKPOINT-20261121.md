# REMURA Contributors v0.64 LAB — checkpoint del registro persistente
**21 novembre 2026 · Europe/Rome · solo laboratorio, nessun deploy**

## Provenienza e continuità
- Repository \`mirkoworz/remura\`, nuovo branch isolato \`research/contributors-server-reconcile-v064-20261121\`.
- Base esatta: v0.63 \`research/contributors-client-ux-v063-20261121\` @ \`34d0ae663b0c03cb3214a8c2f8dd1505047d1c66\`.
- Schema candidato D1 completo originale \`d1_access_candidate.sql\`, Git blob \`9ed38b6ed83755186af05f1bf28b4608cdc5f901\`, già acquisito nei test v0.60.
- Overlay additivo v0.59 \`d1_amendment_v059_lab.sql\`, blob \`289cb54f0b3e33976b255ce976ca5e00bc43ab3c\`, immutato.
- Four new files, exact Git blob matches with the local files actually tested:
  - \`research/contributors/d1_reconciliation_v064_lab.sql\` — \`2cc5f0ccdda660771bc56dc4ddb34bfc942f973a\`
  - \`research/contributors/test_d1_reconciliation_v064_lab.py\` — \`dce89e67feec19d5152f1550e7aafbc978105993\`
  - \`research/contributors/reconciliation_reader_v064_lab.mjs\` — \`d816b1b786e51b137e0584099060d85330f037d2\`
  - \`research/contributors/test_reconciliation_reader_v064_lab.mjs\` — \`2be02b8b8dad9f6b1c6d73ca8370c6ccfa6d607c\`
- No existing file changed in v0.64. Old v0.63 browser still OFFLINE with no real fetcher. No UI updated, so visible version/date header v0.63 on the last UI remains unchanged.

## Implementation
**Additional SQL** (never migrated to live D1): append-only immutable \`lab_amend_attempts_v064\` reservations and \`lab_amend_releases_v064\` owner clearance, plus new BEFORE INSERT guard on \`lab_level_amendments_v059\`.
- A request is bound to subject, request_id, original entry, proposed price, observation UTC and note, with reserved UTC. While there is an attempt without signed-off release for that subject, another attempt for the same subject is rejected at SQL commit.
- A mutation without a matching still-active reservation is rejected, even when calling the old v0.59 INSERT directly; replays with altered body/source/request_id and delayed writes after owner clearance are denied by the new guard. The original entry remains immutable.
- An owner release requires recovery_enabled and the registered non-revoked owner. \`REVIEWED\` release requires an existing mutation with owner decision (APPROVED/REJECTED/REVOKED). \`ABORTED_BY_OWNER\` requires no mutation in the database and a specific owner action; NEVER automatic clearance by browser.
- All reservation and release records are immutable. Physical durability, privileged DB administrators and real distributed D1 consistency are NOT verified by this SQL fixture. SQL checks alone do not authenticate actor, user, clock or real independent evidence; trusted service validation is still required.
- **Important operational caveat:** this overlay adds a mandatory guard to v0.59 mutation. The existing v0.62 HTTP controller is **NOT yet changed to create a reservation**, so combining this SQL with the old HTTP controller directly would block its writes. Do NOT deploy/migrate it without an integrated atomic reservation path and tests.

**Read-only reconciliation module** \`reconciliation_reader_v064_lab.mjs\`: imports historical Access-binding candidate, requires fixture-only flag, attested generation/journal pin and primary-session metadata, subject rate limit and fresh identity. Returns NO_ATTEMPT, UNRESOLVED, COMMITTED_UNREVIEWED, COMMITTED_REVIEWED or CLOSED, always \`mayResubmit=false\` and \`manualApprovalRequired=true\` for the contributor. No notes, prices, personal data of another contributor, secrets, new mutation or HTTP route. Separate OWNER-only read queue for unresolved attempts; no release operation exported.

## Test results (actually executed)
- Local Linux, Python 3.13 / SQLite WAL file in temporary directory, foreign keys and two concurrent connections; Node v22 / node:sqlite full original schema in memory, WebCrypto / mocked D1 primary and mock Access identity. No network calls, real users or Cloudflare secrets.
- Python: \`cd research/contributors && python -W error::ResourceWarning -m unittest -q test_d1_reconciliation_v064_lab.py\` — **48/48 PASS**.
- Node: \`cd research/contributors && node --test --disable-warning=ExperimentalWarning test_reconciliation_reader_v064_lab.mjs\` — **28/28 PASS**.
- New distinct tests **76/76 PASS**, followed by **three independent complete reruns**: 3×76 = **228/228 stability executions PASS** (not additional distinct tests).
- SQL cases include source ownership, revoked actor, missing parent, duplicate attempt, cross-contributor isolation, immutability, missing/mismatched reservation guard, old delayed write after owner clearance, an unavailable write gate, release policy, rollback, file persistence after connection close, two simultaneous reservations (only one wins), and competing abort vs delayed commit.
- Node cases include role-based recovery privacy, missing or mismatched Access, service token denial, generation mismatch, primary metadata, read and rate limit flags, owner-only queue, fresh identity recheck, no implicit permission to resubmit and zero writes by the recovery reader.
- Previous v0.63 tests 56, v0.62 tests 60, v0.61 tests 40, v0.60 tests 80, and historic Oracle/Experience/TradingView tests were NOT re-run because their source code was unchanged.
- GitHub blob hashes for all four files match the tested local bytes.

## NO-GO / still unresolved
1. No version of \`amendment_http_v062_lab.mjs\` or \`amendment_client_v063_lab.mjs\` uses the new reservation functions yet. A **server-side coordinated reserve-before-mutate implementation and HTTP route for read-only reconciliation** remain open for v0.65 LAB. Without this, v0.64 is a tested security extension, not an end-to-end feature.
2. Privileged owner clearance of a request with no matching mutation still needs out-of-band evidence/audit and actual trusted authentication; SQL owner check alone cannot prove an operator independent or verify current real time. A committed mutation cannot be aborted.
3. No actual D1 cloud semantics, regional consistency, Access JWT enforcement, multiple physical devices, Safari iPhone, Web deployment, real owner/contributor enrollment, cross-browser state or independent monotonic custody have been verified.
4. Reservation validity requires application-level validated price/timestamp/UUID, rate/size controls and a one-time intent; new SQL does not substitute for existing application validators. Owner manual abort in a hostile database environment is not a proof of no in-flight writes.
5. The provider's Free quotas (Cloudflare D1, Workers, GitHub Actions, Oracle) have **not** been retrieved; zero new cloud resources created and zero hosted tests intentionally triggered, but do not assert Free headroom without checking.

## Roadmap next
- **Contributors v0.65 LAB:** extend trusted HTTP fixture to atomically reserve, burn intent, perform only one amendment write, and offer a strictly read-only \`/api/amendment/reconcile\` status lookup; tests for two tabs, reload, logout, uncertain responses, late writes after owner release, revocation and prior request bound to different identity. No public deploy and no direct body->identity.
- **Contributors v0.66 iPhone LAB:** expose current status/OWNER queue as a deliberately isolated UI with version/date/time at top, never implicitly retry, test Safari Mac and physical iPhone when requested and available.
- **Contributors live:** after staging architecture, review Cloudflare Always Free limits, identity provider, audit trail, D1 migration safety, owner approvals, backup and opt-in. Explicit authorization required for any deploy/login/real database work.
- **Experience v0.30:** independent custody anti-rollback is DESIGN ONLY; do not assume Mac+iPhone with same account is independent, no key provisioning yet.
- **TradingView v0.8.181**: freeze first holdout 23–29 Nov 2026 UTC, second 30 Nov–6 Dec; do not infer institutional market edge without forward data and price-only baseline.
- **Oracle collector / Private Capture / Ampere Radar:** do not modify; v1.65 install still NO-GO, Private Capture hosted STOP; Telegram notifications for approved levels remain a future opt-in.

**Status: Contributors v0.64 LAB complete as a new SQL and read-only inspection fixture; real service/website still OFFLINE/NO-GO.**
