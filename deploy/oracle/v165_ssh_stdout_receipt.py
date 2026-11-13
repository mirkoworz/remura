#!/usr/bin/env python3
"""Sanitize ONE future SSH audit receipt from the pinned REMURA v1.64 checker.

Executed only on a future private CI runner, *not* on a VPS. Input is an
untrusted stdout JSON document: no command is executed, no network, no files,
no external evidence stored. Fail closed on extra keys, duplicate JSON keys,
trailing output, wrong counts or claims that any production gate was approved.
"""
from __future__ import annotations

import json
import sys

SCHEMA = "remura-v165-independent-v164-code-identity-readonly-v1"
SOURCE_COMMIT = "883336a4e956a9e50c94dcfebf8d7ba78910fb65"
NO_GO = "NO_GO_RELEASE_AND_PROSPECTIVE_COLLECTION"
MAX_STDOUT_BYTES = 2048
REQUIRED = frozenset((
    "schema", "status", "fixedReleaseSourceCommit",
    "expectedPinnedFiles", "independentlyComparedFiles",
    "fullInstalledShaFromUpdaterVerified", "liveV165VersionAttested",
    "realSqliteBackupOrRestoreVerified", "oracleAlwaysFreeVerified",
    "privateAccessAclVerified", "authorizedRelease",
    "productionFilesModifiedByProgram", "researchC5Enabled",
    "operationalDecision",
))
MUST_REMAIN_FALSE = frozenset((
    "fullInstalledShaFromUpdaterVerified", "liveV165VersionAttested",
    "realSqliteBackupOrRestoreVerified", "oracleAlwaysFreeVerified",
    "privateAccessAclVerified", "authorizedRelease",
    "productionFilesModifiedByProgram", "researchC5Enabled",
))
CONFIRMATION = (
    "REMURA_V164_CODE_AUDIT=15_PINNED_FILES_MATCHED_AT_SCAN_ONLY\n"
    "V165_RELEASE_AUTHORIZED=NO\n"
    "V165_REMAINING_EVIDENCE_GATES=NOT_ATTESTED"
)
REJECTION = (
    "REMURA_V164_CODE_AUDIT=NOT_ATTESTED\n"
    "V165_RELEASE_AUTHORIZED=NO"
)


class UnsafeReceipt(ValueError):
    """Untrusted or inconsistent receipt."""


def _unique_keys(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise UnsafeReceipt("DUPLICATE_FIELD")
        result[k] = v
    return result


def validate(data):
    if type(data) is not dict or set(data) != REQUIRED:
        raise UnsafeReceipt("STRICT_FIELDS")
    expected = {
        "schema": SCHEMA,
        "status": "V164_PINNED_SOURCE_CONTENT_MATCH_ONLY",
        "fixedReleaseSourceCommit": SOURCE_COMMIT,
        "expectedPinnedFiles": 15,
        "independentlyComparedFiles": 15,
        "operationalDecision": NO_GO,
    }
    for key, expected_value in expected.items():
        if type(data[key]) is not type(expected_value) or data[key] != expected_value:
            raise UnsafeReceipt("INVALID_RECEIPT_VALUE")
    if any(data[key] is not False for key in MUST_REMAIN_FALSE):
        raise UnsafeReceipt("PRODUCTION_GATE_NOT_FALSE")
    return True


def parse_untrusted_stdout(raw):
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_STDOUT_BYTES:
        raise UnsafeReceipt("INVALID_BOUNDED_BYTES")
    try:
        doc = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_keys)
    except (UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise UnsafeReceipt("UNTRUSTED_JSON") from None
    validate(doc)
    return CONFIRMATION


def main():
    try:
        raw = sys.stdin.buffer.read(MAX_STDOUT_BYTES + 1)
        message = parse_untrusted_stdout(raw)
    except BaseException:
        print(REJECTION)
        return 1
    print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
