# REMURA Experience v0.18 LAB — 20/11/2026 CET

Local synthetic explicit recovery, built without changing v0.17 dependencies. Verified local hashes: integration v0.17 f68ab553f1ff13185366431503b5b75cd350d318, journal v0.15 5748fa1fee0a9afd2be39100fdec9f2d9a54c48b, schema v0.14 c008dcd4ac5e74f7fe9ebf93d40bd8eab6bdcde6, witness v0.16 b9671ac05edfa21d41c30a13607a2dab926a6861.

Executed python -m unittest -v test_recovery_v018: 19/19 OK, 0.403 s. Code blob d849acef9fa04062fbc7081c4ca8a422ba0619b6; tests blob 11e2d18f25b0d13c2296be419da32eac9279f940. Cumulative 286 expected outcomes across 12 phases, not production validation.

## Recovery behavior
Explicit OWNER-only recovery of exactly one candidate beyond retained prior pin; compare canonical history, authenticated chain and intended digest under local cooperative lock. No autonomous adoption, reinitialization, deleting or rewriting old revisions. Approval callback must return true exactly, role rechecked before witness advancement. Supports archive-only and journal-ahead states, repeated interruption and current committed receipt without duplicate revisions. Later stale intent is rejected. Receipt is a current state check, not a persistent idempotency ledger across arbitrary revisions. Catch adapter exceptions at local interface.

## Remaining gates
Prior pin and candidate digest are retained by synthetic test harness; persistent independent authenticated intent and real identity not implemented. Whole witness rollback, distributed locks, noncooperating file mutation, real process kill and power-loss durability not resolved. Current fixture scalar payload is NOT the v0.10 distributor schema. Reviewed v0.10 distributor and v0.11 publisher contracts; next implement canonical approved snapshot binding with exact schema and validation before durable publication, check fresh revision and authorization at delivery, avoid substituting placeholder values. No claim of distributor integration yet. Exact original HTML browser transfer and Safari still outstanding. Preserve frozen levels and approved artwork.

All other tracks remain at checkpoint: Contributors v0.56, TradingView v0.8.181 (windows unchanged), Shark Science v0.4, Private Capture v0.15 hosted STOP, Oracle v1.65 not installed, Ampere Radar v0.36. Mac gates remain. No merge, deploy, credentials, additional real acquisition, private workflow, Oracle modification, new cloud resources or new cost. Budget not remeasured.
