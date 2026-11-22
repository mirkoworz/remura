# REMURA Shark Science — COT atomic capture v0.2 LAB handoff
**22 November 2026 (Europe/Rome) — OFFLINE ONLY / NO-GO for Oracle.**
This extends v0.1 revision lineage; it does **not** edit `scripts/cot_monitor.py`,
legacy tables, operational services, live SQLite or the Mac-owned v1.65 custody.

## Verified new branch evidence
Branch: `research/cot-revision-lineage-lab-20261121`.
- `research/cot/cot_atomic_ingest_v02_lab.py`: isolated synthetic-only in-memory
  store, with explicit source claim allowlist, timestamp and canonical payload.
- `research/cot/test_cot_atomic_ingest_v02_lab.py`: **16 new tests** only.
- Existing workflow `.github/workflows/remura-cot-revision-lineage-v01-only.yml`
  now targets these 16 new checks, leaving v0.1's 20/20 historical result intact.
- **GitHub Actions run 44998195582** (2026-11-22, UTC morning):
  https://github.com/mirkoworz/remura/actions/runs/44998195582 —
  completed SUCCESS; job logs checked; `Ran 16 tests`, `OK`,
  `REMURA_SHARK_COT_ATOMIC_V02=16_16_PASS`.

## What atomic means in this *candidate*, and what it does not
One SQLite transaction wraps:
(1) insert immutable capture_event envelope (source *claim*, local receipt
    *claim*, exact five fields per report and canonical digest);
(2) append new immutable per-(dataset, contract, report_date) version when
    content differs; and
(3) update a mutable current_head pointer to the newest committed version.
A failed mid-batch operation rolls back **all three** parts and preserves the
previous current pointer. Reading historical values uses `as_of(decision_utc)`
directly from versions, never current_head, so a later correction cannot be
fed to an earlier decision. Missing old versions return `UNKNOWN`, not zero.
Unchanged subsequent fetches can create an observation event without inventing
a new content version. Conflicting same-clock values and reverse chronology
fail closed; exact event replay is idempotent. A divergent mutable head is
detected before `current()`. Event and version UPDATE/DELETE are trigger-blocked.

**Not established:** independent first-seen, truthful source timestamps,
actual CFTC revisions on Oracle, provider authenticity, malicious SQLite owner
resistance, capture of real packets, current dataset budget, scale performance,
crash recovery from a *persisted* WAL, price/futures mapping, or predictive alpha.
The tests use synthetic input and `:memory:` only; a local hash is not an
external timestamp.

## Gate before any future integration with Codex Mac
1. Coordinate ownership and latest Mac branch state; no overlap with its
   collector/custody/security changes.
2. Design **additive** schema in separate staging migration, retaining legacy
   reads temporarily. No retroactive upgrade from `cot_first_seen` and no
   replacement of actual historical payloads by today's COT numbers.
3. Use a single transaction for capture envelope + version row + consumer
   projection, with explicit rollback under injected power/process failure.
   Consider persisted WAL and deterministic recovery; detect stale head.
4. Validate CFTC dataset mapping and source identity, provider publication time
   versus locally claimed receipt, actual external timestamp/witness when
   possible; retain uncertainty until independently established.
5. Obtain backup/restore evidence and concurrency/collision checks under
   locked operational conditions, then an independently authorized migration,
   never a silent change to main or Oracle.
6. Verify free margins *before* provider calls/deploy. No Cloudflare calls or
   new real credentials are implied.

**Current decision: v0.2 fixture PASS; Oracle integration NO-GO.**
The original Mac handoff remains
`research/cot/COT-REVISION-V01-MAC-HANDOFF-20261122.md`.
