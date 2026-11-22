# REMURA Contributors v0.92 LAB — gated 1–2-friend pilot
**22 Nov 2026 (Europe/Rome) — DRAFT PLAN ONLY / NO-GO.** No production, no signup, no Cloudflare API calls.

## What the pilot must do
A friend can authenticate into a private portal, read permitted REMURA material
without changing it, and create/edit **only that friend's own levels** through
a bounded contributor route. A distinct OWNER role alone reviews/approves.
Permissions must be enforced by the server on *every* route and ownership
predicate, not hidden buttons. No friend can approve, change Oracle/COT,
modify another person's levels, access Secrets or alter REMURA production.

## Evidence already completed (do not rerun by habit)
- Private Access + D1 composition fixture 15/15.
- Revocation lifecycle 12/12; ownership / real-schema HTTP router 18/18.
- Free manual preflight 18/18; Access Free **50-seat hard-cap logic** 22/22.
These are fixture outcomes, not a real Access/D1 allowance or iPhone Safari proof.

## Sequential release gates; all must be TRUE
**G0: Written authorization.** Any Cloudflare query, Access user, remote
database, staging Worker, real account or deployment requires separate explicit
approval, including scope and budget. Existing 2/2 GraphQL allowance used on
21 Nov cannot be reused.

**G1: Real free headroom.** Verify actual billing plan and current remaining
Workers requests, D1 reads/writes/storage, Access seats (OWNER + users +
any other active seats), and GitHub Actions quota. Unknown is UNKNOWN, never
zero, never an assumed 50 seats available. No action if free margin is not
confirmed or a spend might occur. Retain proof of the provider observation
without disclosing secrets.

**G2: Server authorization.** Cloudflare Access identity independently
validated; default-deny methods/routes; only own-record create/update;
read-only route constraints for REMURA; OWNER-only review/approval; reject
owner impersonation, forged headers, cross-user access and mutation-by-GET.
Prefer separate private staging resources, no production writes.

**G3: Revocation and privacy.** Session expiry/logout/Access removal/revoke
cannot leave reusable credentials or lingering write rights. Audit without
sensitive content, limit retention, configure no-store private pages, include
minimal rate controls and anti-replay policy. No data sent to Telegram by
default.

**G4: Physical Safari evidence.** On an actual iPhone Safari, document first
login, navigation, correct own-level write, denial of other-user edits and
OWNER operations, logout, re-login and successful revoked-user denial. Desktop
Safari or synthetic tests are not a substitute.

**G5: Small controlled pilot.** Only after G0–G4 and a distinct go-ahead:
onboard 1–2 consenting friends, monitor usage/costs and be ready to revoke.
A successful pilot is not permission to open registrations to everyone.

## Acceptance / abort
All G0–G5 pass => possible separately authorized pilot. Any missing quota,
unverified login, cross-user write, owner leakage, unauthorized deploy or
unexpected charge => **NO-GO and stop**. No production permission is implied
by this document. Do not repeat prior green synthetic suites without changed
code or concrete regression evidence.
