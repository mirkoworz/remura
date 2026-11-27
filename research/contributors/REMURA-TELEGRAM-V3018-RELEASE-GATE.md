# REMURA V30.18 — staging release gate, 27/11/2026
Source 4dc5dd59acac87c1bb9a763dc82a1b15d5b4b6ed; bundle commit 3b0b2bbecad598d2e199f3027cd8be3ae9865f1a; blob 1951d3c41a704735889169315a904757938facec.
16-module closure; 126701 characters. Offline execution using TextEncoder stub. 24/24 candidate aliases pass original normalization and new mapping validator; all three browser scripts parse; 6/6 render and role checks passed. Initial render assertion incorrectly expected dynamically assigned toggle text in static HTML; corrected to check actual control id. No actual D1 or Access session tested. Earlier targeted checks 12/12 in LAB.

## Deploy boundary
Deploy only staging Worker, keeping Telegram policy OFF and existing bindings/secrets. No SQL migration needed for Worker update. Inactive catalog SQL is optional separate step, not authorized yet. No real feed symbol verification or permissions verification. Aliases are internal manual-chart labels. Unknown rollover and adjustment explicitly disclosed in message. No scientific eligibility until downstream exclusion of CHART_ONLY_* and CONTINUOUS is verified. The other science branch is untouched.

## Before any catalog activation
Verify platform/feed chart profiles and permission to share derived levels. Verify current quota, billing, Worker version and policy OFF. Confirm chart observations cannot enter contract-specific science; if uncertain keep inactive. No activation or Telegram allowlist authorized by this gate. For first publication, separately authorize a single bounded controlled test, not general enable. Do not replay old receipts. No blind retries.

## Rollback
While no new aliases are active, revert only staging Worker to the immediately preceding deployed V30.16 version (record real version ID before deploying). If later aliases active, disable Telegram policy and deactivate those catalog entries before reverting; previous formatter does not understand continuous sentinel. Preserve all receipts and outbox, no restore or deletion. Never modify production or Oracle.
