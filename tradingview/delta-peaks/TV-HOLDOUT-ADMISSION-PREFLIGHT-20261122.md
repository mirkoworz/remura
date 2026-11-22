# REMURA TradingView v0.8.186 LAB — holdout admission preflight
**Prepared:** 22 Nov 2026, Europe/Rome. **Status:** NO-GO for empirical admission absent real evidence. **Docs only.**

## Freeze and clock
The binding scientific protocol remains `CVD-PROSPECTIVE-PROTOCOL-V2.md` (unchanged).
Development: [2026-11-16T00:00:00Z, 2026-11-23T00:00:00Z).
Holdout 1: [2026-11-23T00:00:00Z, 2026-11-30T00:00:00Z).
Holdout 2: [2026-11-30T00:00:00Z, 2026-12-07T00:00:00Z).
Start of a date window is **not** evidence that a receiver or an independently anchored stream exists. Do not advance the calendar to claim an observation.
No modifying V2, no tuning on holdout, no backfill, no later outcomes in an earlier fold.

## Per-decision admission contract (fail closed)
1. Immutable source artifact: exact TradingView export, declared venue, symbol,
   interval, authenticated collector/receipt path and content digest. Missing raw
   source means UNKNOWN, not an invented candidate.
2. Decision identity linked to the original M5 bar and price-only comparator:
   bar closing UTC, observed receipt UTC, decision UTC, fold, candidate ID and
   conflict/duplicate detection; no merging aggregate counts with decisions.
3. Timeliness requires receipt **no later than M5 close +120 s and strictly
   before the following M5 close**. Late, missing, conflict and unverified
   candidates are counted separately; never retroactively promoted.
4. Independent anchoring and *first-seen* quality recorded as separate fields.
   Local signatures/Ed25519 and SHA-256 alone do **not** prove external time,
   independence or historical availability. An absent witness remains UNKNOWN.
5. Assignment uses preregistered FIFO and within-fold stratification; a blocked,
   incomplete, pending or missing pair remains assigned, never replaced after
   observing the future. Denominator, coverage and failure reasons preserved.
6. Primary analysis is CVD vs price-only at **60 minutes**; 4h and 24h are
   secondary; round-trip cost scenarios 0/1/2 pip are assumptions, not broker
   executions. Do not make profitability or alpha claims.

## 23 November gate
- **Admit** an individual decision only after all required original evidence,
  identity, source/clock fields, timing and mapping are checked against the
  frozen V2 rules. Independently attested vs only locally observed must remain
  distinguishable in output; no invented certification.
- **Quarantine** conflicting timestamps or provenance failures. Report count
  and reason, not fabricated zeros.
- **NO-GO** for holdout inference if no authenticated prospective acquisitions,
  no independent first-seen witness, or insufficient M5 coverage. A window may
  open while the study remains NO-GO.
- Do not inspect early outcomes or retrain during holdout 1/2. Do not turn a
  failed hypothesis into a fresh threshold based on holdout results.
- Nothing here starts an export, workflow, provider call, deploy, or PR merge.

**Result at preparation:** admission specification prepared; actual TradingView
acquisitions, independently attested timestamps, coverage and predictive
advantage **not verified**.
