# REMURA v0.8.159 LAB — locked bytes and authenticated rollback
18/11/2026 — sessione successiva alle 13:29 CET. PR #102 DRAFT.

v0.8.158 CI independently observed GREEN Telemetry 44304674966/job 134803012404, Wrangler 44304674932. Existing exact signed owner candidate remains unchanged.

Integrate the actual v1.65 deterministic TAR into the descriptor-anchored lock boundary by reusing existing CI output, checking 155 member byte digests via the refactored existing parser, after removing the disposable staged pathname. The parser accepts immutable bytes and returns its checked application map; the old path interface remains available only as before. No artifact handoff triggered by this commit.

Authenticated LAB journal mode uses a 32-byte independently supplied key, HMAC-SHA256 and domain, transaction and fixed release manifest binding. Exact pinned 90-path application/rollback and abrupt process exit after 45 modifications now exercise authenticated mode. New adversarial fixture rejects wrong key, wrong transaction, unsigned downgrade and tampered mode before any mutation. Old checksum-only mode retained for historical synthetic fixtures; never suitable for privileged installation. No keys or journals published.

Limitations: HMAC cannot prevent replay of an earlier valid journal within the same transaction; independent durable monotonic witness/phase and crash reconciliation remain required. Real key custody, authenticated journal semantics, trusted code bootstrap, secure path mutation, actual historical lock integration, live collector snapshot and service health are not attested. The journal still uses a disposable local lock, not the historical live lock. No root execution, installation, timer/service changes, data access, new resources or scientific protocol changes.

Operational containment proposal (not executed): persistent systemd mask of the old autoupdate service only, after explicit owner authorization and confirmation it is inactive; don't force-replace an existing unit file or stop anything. If the unit cannot be masked safely, stop and inspect alternate approved containment. Timer remains disabled, collector untouched. Manual root execution of old Python/scripts remains outside systemd mask; trust bootstrap and operational prohibition remain mandatory.
