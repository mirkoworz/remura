#!/usr/bin/env python3
"""REVIEW ONLY — future root-installed SSH authorized_keys forced-command gate.

NOT INSTALLED ON ANY VPS; NOT PART OF A DEPLOYMENT.
The scanner comes from SSH stdin but must match the exact, already approved
Git blob before this program executes it. This prevents a stolen audit key
from providing arbitrary Python to a simple `python3 -` forced command.
The approved verifier itself is only a 15-file read-only identity checker;
this gate alone cannot enforce host filesystem permissions or SSH restrictions.

Future *separately authorized* server setup would require an immutable,
root-owned copy of this file, a dedicated unprivileged user with no sudo,
an authorized_keys restrict+command binding and vetted filesystem ACLs.
Never trust a copy editable by the SSH audit user.
"""
from __future__ import annotations

import hashlib
import os
import sys

APPROVED_SOURCE_GIT_BLOB = "98b0a28190647e9d321690097aae30395bc9f900"
APPROVED_ORIGINAL_COMMAND = "python3 -I - --audit-live-readonly --operator-approved"
MAX_STDIN = 32_768
REJECTION = "REMURA_AUDIT=PINNED_STDIN_REJECTED"


class UnapprovedPayload(ValueError):
    """No message contains filenames, code, credentials, or server paths."""


def approve_exact_verifier(payload: bytes, original_command: str | None) -> bytes:
    if type(original_command) is not str or original_command != APPROVED_ORIGINAL_COMMAND:
        raise UnapprovedPayload()
    if type(payload) is not bytes or not (0 < len(payload) <= MAX_STDIN):
        raise UnapprovedPayload()
    git_object = b"blob " + str(len(payload)).encode("ascii") + b"\\0" + payload
    if hashlib.sha1(git_object).hexdigest() != APPROVED_SOURCE_GIT_BLOB:
        raise UnapprovedPayload()
    return payload


def main() -> int:
    try:
        # A forced SSH command exposes the requested client command via
        # SSH_ORIGINAL_COMMAND. Reject unexpected commands before reading code.
        command = os.environ.get("SSH_ORIGINAL_COMMAND")
        if command != APPROVED_ORIGINAL_COMMAND:
            raise UnapprovedPayload()
        payload = sys.stdin.buffer.read(MAX_STDIN + 1)
        source = approve_exact_verifier(payload, command)
    except (UnapprovedPayload, OSError):
        print(REJECTION)
        return 1

    # Only the exact pinned source can reach exec; never execute unchecked data.
    # -I must be set on the SERVER-SIDE Python interpreter by authorized_keys.
    sys.argv = ["<pinned-v164-verifier>", "--audit-live-readonly", "--operator-approved"]
    namespace = {"__name__": "__main__", "__file__": "<pinned-stdin>"}
    exec(compile(source, "<pinned-stdin>", "exec"), namespace)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
