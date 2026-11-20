# REMURA Contributors v0.18 LAB — 15/11/2026 08:34 CET

DRAFT / NO MERGE. Identity-only staging actually deployed and positive owner test observed on 16/11/2026; no contributor service. No further deployment or ingress activation without the corresponding authorization. Historical candidate configuration below is not current runtime evidence.

- `wrangler.staging.json`: dedicated name, no routes, workers.dev and previews false, observability off, no DB, bindings, scheduled triggers or credentials. Do not run deploy or upload. No account resources created by this commit.
- `staging_identity_worker.mjs`: only GET / at exact configured HTTPS origin; explicit disabled default and exact audience/account/UUID/email test binding. No caller headers or role trusted, no service tokens, no fallback. Generic denial and no-store; no identity output, no network, logging or persistence. One test account only. Test binding must be set privately after identity is independently verified; no real identifiers in repository. No role or contributor authorization issued.
- Before any exposure: confirm actual account Free / Zero Trust and latest aggregate report; require explicit staging deploy authorization; choose new unique name, check no collision; create isolated Worker with no ingress and disabled gate; configure Worker-level Access all traffic with Google-only and exact email test account; verify no overlapping path policy. If Access cannot be configured without activating ingress, leave handler disabled during creation. Never modify global policies or other Workers.
- Bootstrap UUID: obtain only from trusted Access admin identity record (not user claim or email fallback), verify account and Google sign-in, bind exact test UUID/email privately. If unavailable, stop and design a controlled bootstrap before enabling. Runtime identity fields may differ; fail closed, never weaken check just to pass. No PII in logs/checkpoints.
- On explicit authorization only: enable test ingress protected by Access, private env binding + IDENTITY_ONLY; verify anonymous denial, alternative IdP denial, wrong user, service token, spoofed header, removal/reinvite and revocation, Safari iPhone. Test response alone does not prove policy or revocation. If uncertain disable gate and ingress. No D1, data, POST or owner endpoint in this phase. App budget still not a hard cap.
- Next: separately authorized D1 test DB / schema and form after identity probe, CSRF, mapping, access isolation, privacy, retention and restore gates. No automatic import or scientific admission.

Sources: https://developers.cloudflare.com/workers/configuration/cloudflare-access/ and https://developers.cloudflare.com/workers/wrangler/configuration/ (15/11/2026).
Local offline test: node research/contributors/test_staging_identity.mjs. CI node test is not evidence of real Access, Wrangler validation, or deployed auth.

## Collaudo negativo reale — runbook

REMURA v0.18 LAB — checkpoint 16/11/2026 00:47 CET. Documentation only; no runtime change.

Precondition: obtain confirmation of Production OFF, Preview OFF, DISABLED after the prior test. Confirm dedicated Google-only exact-owner policy still attached after config change; no policy broadening. Keep no external bindings. A new limited exposure needs express authorization (not implied by prior test). Use at most 20 intentional requests in a single operator session; no polling, no token logging, stop immediately on unexpected success or missing Access. Close ingress first, then restore DISABLED, verify both switches and record sanitized results; no screenshots of cookies, JWT, UUID, email or session URLs in repository.

| Case | Expected | Evidence / constraint |
|---|---|---|
| Anonymous clean browser or curl without cookies | Access login redirect or denial, never success body | prior bootstrap evidenced; repeat only if useful after new config |
| Anonymous request with bogus Cf-Access-Jwt-Assertion and synthetic email or bogus service-token headers | not admitted | use fake strings only, no real service tokens; edge denial does not exercise Worker branch |
| Owner clean GET / from Safari iPhone | exact success body | positive already observed on Mac; record status separately if available |
| Owner GET /?probe=1 and GET /not-a-route | generic closed body, expected 403 | already authenticated browser, no sensitive query values |
| Other Google account owned/controlled by operator, if already available | Access denies | do not invite or modify policy; if unavailable mark NOT_TESTED |
| Alternative login method | absent or denied | Google-only UI shown earlier; no enabling alternate providers merely for a test |
| Application-scoped revoke existing tokens | previous authenticated session no longer admitted without new authentication | separate authorization, verify only dedicated staging app; no global logout or per-user revocation; existing browser may reauthenticate via SSO, distinguish new token from old; if cannot distinguish mark inconclusive |
| Identity mismatch/reinsert and true service token | deferred | synthetic tests already cover context mismatch; do not create service tokens, delete owner or rebind identities; separately approved isolated test identity needed |

Do not treat redirects as Worker 403 or success body as independently captured status. Do not export HAR or cookies. Browser navigation may auto-SSO; avoid treating that as failure of revocation without token-specific evidence. No real session-token copying to chat or GitHub. Application-level revoke does not permanently ban a still-authorized user. Future contributor app requires its own durable identity/role/revocation checks at each operation independent of Access token lifetime. Serve protected dynamic routes directly in the Worker: Cloudflare documents that ctx.access is not passed through Static Assets router or service bindings. Do not replace with unverified headers. Sources checked 16/11/2026: https://developers.cloudflare.com/cloudflare-one/access-controls/access-settings/session-management/ and https://developers.cloudflare.com/workers/configuration/cloudflare-access/ .

D1 next gate: only dedicated new empty DB after express permission. No existing D1 edits; keep writes disabled by default. Verify actual D1 budget/metadata, migration constraints, rollback and adapter compatibility; real contributor invitations and level admission remain separate.

## Esiti sessione sicurezza — 16/11/2026 01:12 CET
Operator-reported curl statuses 302/302/401 for anonymous, fabricated identity and fabricated service token. No genuine token exercised and redirect Location not captured. Safari iPhone success with clean URL reported; initial generic denial not reproduced, cause unproven. Application-specific revocation UI confirmed in Additional settings → Application Audience (AUD) Tag → Revoke existing tokens; operator reports Google login prompt on same iPhone session after revocation. Behavioral evidence only, no persistent role revocation, no identity removal/rebind. First closure after Mac confirmed earlier; second closure pending explicit confirmation. Remaining route/query and foreign account tests not performed. Do not create alternate identities or service tokens solely for testing. No D1 or new exposure authorized by this record.
