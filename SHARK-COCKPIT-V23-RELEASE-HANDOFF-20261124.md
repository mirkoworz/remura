# REMURA D — V23 release handoff (24/11/2026 08:35 CET)
Review-only, no merge/deploy. Current public isolated preview remains v1.73.1. Main observed 774e2d4882cae6426f9292820491a64ed23cf3aa; D source 74b3f4c51ec131da4c03a9a796ea3dfbd9c232b2; PR #114 Draft. Compare main...D: 22 ahead / 1 behind before this document.
 
## Concrete integration boundary
Future release branch from then-current main, after approval: selectively port only the 13 runtime paths below, preserving the current main Myfxbook data, other concurrent work and legacy nav/SW/splash. Inspect the index diff rather than wholesale replacing the latest home. Never automatically carry preview helpers, network smoke/attestation workflows or disabled-Firebase preview settings into production.
- index.html (three changed lines, review against current main)
- shark-cockpit.html
- shark-cockpit.css
- shark-cockpit.js
- shark-cockpit-core.js
- shark-evidence-core.js
- shark-evidence-ui.js
- shark-focus-core.js
- shark-focus-ui.js
- shark-movers-core.js
- shark-movers-ui.js
- shark-trends-core.js
- shark-trends-ui.js

Review tests/shark-v173-mainline-compat.test.js separately; no weakening legacy gates. PR #114 stays Draft; do not merge #113. No changes to nav.js, sw.js, Splash, C/B/A collectors, Oracle or private data. Preview package is not the production release.

## Retail data update: reuse, do not duplicate
Main latest.json observed updatedAt 2026-11-24T00:06:19Z, later than deployed preview 23/11 13:12 CET. This is repository evidence, not proof of a current schedule or of production URL freshness. At 08:35 CET both timestamps exceed 3 hours.
Existing readRetail() fetches same-origin ./data/myfxbook/latest.json with cache:no-store and no credentials; core.summarizeRetail already checks per-symbol t, source, sample size, age <=3h and labels ARCHIVED_RETAIL or UNKNOWN. No new vendor subscription, endpoint, poller, or duplicate collector needed. For official release keep the existing same-origin publisher; coordinate with B to attest its schedule, public host freshness and failure behavior. For immutable isolated Pages preview label data archived; a new bundle would require separate authorization and would invalidate the current asset attestation. A refresh cannot advance a static snapshot. No remote GitHub raw fallback or token in browser. Known future UI improvement: re-evaluate freshness on foreground return using cached rows and current time, without networking; do not alter attested preview until release decision.

## Only outstanding browser evidence for unchanged preview
Owner opens https://remura-lab-v1731-iphone.pages.dev/shark-cockpit once and captures the message after loading plus available-contract count and one actual CFTC reference date/value. UI states: both datasets loaded / partial / unreachable. The code uses two public CFTC datasets, with host fallback on failure; the browser can make up to four GET for a load, no automatic polling. Do not repeat HTTP smoke, hashes, redirect or local HTML test. If failure capture exact message, diagnose actual cause, coordinate B's verified snapshot as a future same-origin fallback only with provenance and no invented values. HTTP 200 or UI label alone cannot certify report timeliness or first-seen time. No trade signals/profit claims.
 
## Release / rollback gates
Confirm Safari runtime, current main and data publisher health, Free account, review A+B and Mac, exact candidate diff and explicit authorization. Record pre-release production commit and existing hosting deployment ID, preserve working artifact and rollback route before merge/deploy. Any access failure, private data exposure, core navigation break or missing/incorrect report labels blocks release; restore previous verified deployment using provider rollback only with authorization, no reset/force push. PWA/offline remains a separate Mac-coordinated release. No actual rollback performed.
