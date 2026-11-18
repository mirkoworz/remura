# REMURA v0.8.162 LAB — pinned bootstrap source census
18/11/2026 — sessione successiva alle 13:37 CET. PR #102 DRAFT.

Four reviewed source files are pinned by SHA256 and exact byte length, anchored at v0.8.161 ce91243cca1c37e940c98bf5a382311565dd7b35. The read-only verifier opens directory components via file descriptors; rejects wrong owners, writable group/other directories, special modes, unexpected files, symlinks, hardlinks, drift and changed named inode. It provides verified immutable source bytes, does not execute or import them. Existing package, portable kit and science pins unchanged. Ten tests use actual source bytes in disposable directories, not fake module content; CI pending.

This is NOT privileged bootstrap installation or runtime import closure. It intentionally excludes the LAB mutating journal and legacy updater from the candidate source set. Historical stage parser contains build-only dynamic import paths, which must never be admitted in privileged mode; OS interpreter, stdlib, system commands, ACL/mount constraints, protected launcher and independent verifier pin still need target review. No direct execution of downloaded scripts. Future root-owned provisioning needs separate owner approval. No live operations or new artifact.

v0.8.161 CI 44305971176 and Wrangler 44305971293 observed completed success. Existing containment receipt and maintenance gates remain. No new archive or quota evidence, no change to B/E or Ampere.
