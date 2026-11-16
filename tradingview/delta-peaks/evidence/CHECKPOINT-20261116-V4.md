# REMURA D — milestone 16/11/2026, 13:00 CET — v0.8.89 LAB
Supplement to ROADMAP.md; current checkpoint after previous 422 tree timeout. Main worker/app code untouched. Main manual reader V4 pin 08f5cdb48d430739ce3688480d95ac78aea3640b, main change aee2a9c732b30bb7a617ef2b2137138e1c2a20fb.
- V3 run 43839770016: UTC 09:05–09:20; 4/4, zero missing/duplicate; 9 read; max lag 7092ms.
- V4 run 43851249699 job 133244071571: UTC 09:25–10:20; 12/12, zero missing/duplicate; 25 read; max lag 21660ms; 158 tests; SUCCESS.
- Adjacent disjoint windows 16/16, 34 rows read, 0 written by the readers, 2 inventory + 2 SELECTs; 4 aligned, 12 disagree, 16 ER_NONE, 16 observation-only; no operational signal or outcomes. Scoped receipts, not whole-market reliability or prediction evidence. No independent provenance.
- Exact sanitized V4 receipt regression added alongside existing V3 evidence. CI pending. Prior PR comment 6914192967. No new network read, deployment or scheduler. Oracle post-trial diagnostic still absent at 13:00; last Cloudflare gate 43843829962 at 10:53 good then, not current billing/plan proof.
- Next: private volumetric storage/retention requirements and gate, no activation before Oracle and B evidence. Do not repeat same-window reads or count samples twice.
