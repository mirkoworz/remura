# REMURA V30.16 — staging release gate
Candidate code commit: 874a82b8a1322ef03f61d153299dbf1ea6037fd4.
Base: f2c1bda8cae7a6fb9e8c342b8995027690f29014.
No deploy, Cloudflare change, outbound Telegram request or new spending performed by this gate.

## Offline evidence
SQLite 3.46.1, in-memory synthetic base tables. Both actual migration bytes verified against Git blob SHA-1:
- telegram-outbox-v3012.sql: 948a718facf3ed1b865a0593960f30bd709fed45
- telegram-publication-v3014.sql: e0d0e0ce9d3bc071cba6e1944466c6e4059191e5
12/12 assertions passed: old data private; no source no enable; contributor cannot enable; OWNER enable; only eligible new level queues; recovery owner and epoch checks; only one claim; UNKNOWN not retried; expired pending not recovered; OFF still records; re-enable no backlog; new epoch sends.
Owner toggle/claim SQL transcribed from candidate; synthetic base schema is NOT complete D1/Access integration. No production readiness attestation.

## Worker dependency closure (13 modules, all under research/contributors)
```
staging_contributors_v110_lab.mjs e6cfb01aa235aa0f9b03ff42e6b7a06c266e7a75
level_attempt_journal_v076_lab.mjs ea905642f82c752e47ef6b714c2e4a63324e651b
telegram_transport_v3012_lab.mjs bb1d1b3b5f9433d0a635da3d2ff10a7d332e9f73
telegram_owner_v3015_lab.mjs e698e81afba0fe9a15e5ff573c737463351010c5
telegram_recovery_v3016_lab.mjs b340e18b522babd532abbf156574d7b661789e8b
staging_levels_store_v110_lab.mjs 842382b932ce3336da4b94ae05efc16bfd36fe22
contributors_ui_v110_lab.mjs 187e8098f110ddba0cc60fcbfbe77c956dc5ddf7
d1_lab_adapter.mjs d004c3d3177e3e085394209285a44afa011f149c
telegram_dispatch_v3012_lab.mjs ea5b993a67ac846da95ace09f6cd61557255fa7b
cot_archive_v110_lab.mjs cbefc64afed63fdaaa3369ff50dd16490574630b
contributors_style_v110_lab.mjs 7bc8e15b892d8dc7d67a44ed6e1bf5395bf31342
contributors_browser_v110_lab.mjs f11222acdb8a99467d4e9298e31bfa79825ce2a4
telegram_message_v3011_lab.mjs 44492d1e5c5e585729941ea5b04fdd2e07971ad2
```

## Next authorized stages (not authorized by this document)
1. Verify current Cloudflare Workers, D1, billing Free and headroom; verify current staging Worker/version, bindings, actual schema and migration history read-only; coordinate with other REMURA branches.
2. Prepare verified build from pinned candidate, local module/route tests, rollback package. Verify no schema conflicts and current staging users/receipts. Confirm D1 Time Travel point; do not restore unnecessarily.
3. With explicit approval and a short staging-only maintenance window, close intake, run two migrations in order, verify OFF / empty allowlist / no historic queues / preserved identity and receipts. Deploy pinned staging candidate with external gate OFF; re-open intake only after checks. Old version must still work on additive schema; verify rollback before release.
4. Configure secrets TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID privately (never GitHub, screenshots, chat), env gate TELEGRAM_BRIDGE_V3012 initially absent. No bot send.
5. Verify exact user-supplied feed ticker, native contract, scale, source group and permission to share contributed levels. Do not invent or activate a mapping from the candidate root list alone. Approve catalog and Telegram allowlist separately. Current source list is unverified.
6. Only with fresh explicit approval, controlled one real message to existing group, then activate policy by OWNER if proven. No access to group chat messages. No cron. Unknown/SENDING never automatically retried. Manual recovery current epoch, pending only, 15 min, one at a time.
7. Stop: OWNER disables policy; already in-flight send may complete. Emergency external gate OFF. Rollback staging Worker if needed; preserve additive D1 records. Never touch Oracle, live OWNER or science.
