# REMURA TradingView v0.8.188 — scientific admission firewall LAB
**22 novembre 2026 — Europe/Rome.** No production/UI update, no live signal.

## New work, independent of historical test suites
- Branch `research/tv-no-signal-without-proof-v0188-20261122`.
- `scientific_admission_firewall_v0188_lab.py`: per-decision and aggregate
  **offline** acceptance review combining the existing V2-pinned M5 CVD
  classification with separate Myfxbook and COT evidence statuses and
  explicit futures/spot mapping plus market-hour coverage claims.
- `test_scientific_admission_firewall_v0188_lab.py`: **18 new tests**,
  [GitHub Actions 45018607314](https://github.com/mirkoworz/remura/actions/runs/45018607314)
  completed SUCCESS, `REMURA_TV_V0188_FIREWALL=18_18_PASS`, job log read.
- Decision gating rejects prospective CVD values with receipt after the
  decision, CVD bars closing after the decision, missing or late M5 receipts,
  wrong decision identity, out-of-fold records and unknown required market
  coverage. A synthetic witness string, content digest or source mapping
  label can never autonomously grant independent verification.
- Emits reason codes and aggregate *submitted-decision* denominator, not
  assumed trading-hours coverage, no price outcomes, no PnL, no buy/sell.
- The gate **always abstains** pending independent verification interfaces:
  `ABSTAIN_NO_PROSPECTIVE_SCIENTIFIC_ADMISSION`. This is intentional, not
  evidence of negative predictive performance. Missing observations stay
  UNKNOWN. It does not replace existing TradingView v0.8.186/187 modules.

## Fixed protocol
`tradingview/delta-peaks/CVD-PROSPECTIVE-PROTOCOL-V2.md` unchanged.
Development [16 Nov 00UTC, 23 Nov 00UTC), H1 [23 Nov 00UTC,
30 Nov 00UTC), H2 [30 Nov 00UTC, 7 Dec 00UTC).
Primary CVD vs price-only 60 min with prospective FIFO M5 timing
(close+120 s and before following close), 4h/24h secondary.
No fold retuning, no backfill, no price-outcome test here.

## Next admission gates (not authorized automatically)
Actual prospective CVD original and temporal witness; exact per-decision
price-only pairing; independently observed receipt per source; immutable
historical COT version by the decision; independently reviewed contract
mapping and currency orientation; complete M5 market calendar with
missingness denominators; holdout integrity and sufficient observations.
When absent, REMURA should **display unavailable or research-only** rather
than suggest a trade or institutional predictive advantage.
No claim of alpha or profit until a truly out-of-sample result is audited.

**Decision: 18/18 GREEN fixture tests; no real scientific admission or
deployment; Mac Oracle and Contributors unchanged.**
