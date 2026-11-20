# REMURA v0.8.150 LAB — owner recovery and signed receipt
18/11/2026 — sessione delle 10:25 CET. PR #102 DRAFT.

Existing v0.8.149 preflight unchanged; verified commit and portable blob for owner Oracle invocation. No installation permission or coherent snapshot claimed.

Extend existing prices/COT v2 verifier with opt-in --recover-memory: reconstruct a separate in-memory SQLite connection from authenticated decrypted bytes, run full integrity_check, compare the schema summary. No disk recovery or live restore. Requires Python SQLite deserialize support, sufficient memory and verified iSH compatibility. Tmpfs and RAM can swap; no guarantee of no persistent plaintext at OS level. Existing hash-only mode remains unchanged.

With --recover-memory --receipt-dir and --signer, optionally create a local no-overwrite canonical JSON envelope containing a detached GPG signature using the exact owner-selected signing fingerprint. Independent verify-receipt checks ciphertext pin, generation, signer and signature. The receipt records owner attestation, not independently proven data origin, trusted time, antirollback chain or authorization to install/restore. Never publish private ciphertext digests or receipts. Existing receipts 001–005 unchanged. No scheduling or real data invocation.

One synthetic GPG test exercises separate disposable owner/public keyrings, actual encryption/decryption, independent SQLite integrity, signature verification, tamper rejection and no-overwrite. CI pending. No claims of real iPhone/Oracle recovery. Next: actual preflight result, resources/compatibility and B-shard custody. No changes to live collector, active alert, B protocol or Contributors.
