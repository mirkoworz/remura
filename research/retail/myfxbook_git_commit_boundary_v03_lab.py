#!/usr/bin/env python3
# REMURA Retail - Git commit provenance boundary v0.3 LAB, 22 Nov 2026.
"""Four real Git objects versus the pinned EURUSD repository history.

This is a LOCAL, READ-ONLY Git-object inspection. Commit author/committer
timestamps can be selected by the producer, and cannot serve as independent
GitHub receive time or provider first-seen. No network, API, trading, or
production changes. No broad historic audit rerun.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha1
from pathlib import Path
import json
import subprocess

from myfxbook_pinned_real_replay_v02_lab import (
    PINNED_SYMBOL, ROOT, SOURCE, ReplayError, pinned_json, unique, utc, valid_row,
)

REPOSITORY = Path(__file__).resolve().parents[2]
CHECKPOINTS = (
    ("32188ca6304b86190d993159260f3baf4a801e89",
     "05351844eed9e2575e8651fe4a701d50b518dfbf",
     "2026-11-20T11:18:32Z"),
    ("f1c05654c380035aaa7ffd52103b17c293f6f03d",
     "9e5450715882e61abf2d46482c8ec444c649efa7",
     "2026-11-21T08:12:01Z"),
    ("06ebde2ce740f92fd8b44d5eb3c9d6faa57c7a07",
     "89a5b483a6131edd926ff7ffaf8526262f9cefe3",
     "2026-11-21T21:43:42Z"),
    ("7c70bb9fd0e774d45c493217382c430b448af0e2",
     "c2c4dfc6546fa26e315400995132fc60170cede1",
     "2026-11-22T01:36:15Z"),
)
SCHEMA = "remura.retail.git_commit_boundary.v03.lab"


def git(*args):
    # All arguments originate in static constants, never user-provided refs.
    try:
        out = subprocess.run(["git", *args], cwd=REPOSITORY,
                             capture_output=True, check=True, timeout=10)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ReplayError("git_object_not_available_or_invalid") from exc
    if len(out.stdout) > 500_000:
        raise ReplayError("git_output_oversized")
    return out.stdout


def blob_oid(payload):
    return sha1(b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload).hexdigest()


def review_claims(samples):
    """No local date, even one matching commit time, grants real-world admission."""
    if type(samples) is not list or len(samples) != len(CHECKPOINTS):
        raise ReplayError("invalid_pinned_sample_count")
    for sample in samples:
        if sample["sampled_at"] != sample["archived_record_at"]:
            raise ReplayError("archived_sample_clock_mismatch")
        utc(sample["sampled_at"])
    return {
        "status": "FOUR_COMMIT_CONTENT_RECONCILED_TIME_UNATTESTED",
        "total_pinned_commits": len(samples),
        "timestamp_claims_match": all(x["commit_metadata_equals_sample_clock"] for x in samples),
        "independent_github_receive_time_verified": False,
        "external_provider_first_seen_verified": False,
        "holdout_decision_admission": False,
        "institutional_edge_established": False,
        "provider_or_cloudflare_calls": 0,
        "production_modified": False,
    }


def audit():
    archive, _ = pinned_json(ROOT/"history"/"EURUSD.json",
                             "8e0ca3c9bae596c0d5145d1e9e6994cf6a39e5a9",100_000)
    records = archive.get("records")
    if archive.get("symbol") != PINNED_SYMBOL or archive.get("source") != SOURCE:
        raise ReplayError("archive_source_mismatch")
    if type(records) is not list or not 1 <= len(records) <= 3000:
        raise ReplayError("archive_records_invalid")
    by_time = {}
    last = None
    for record in records:
        stamp = valid_row(record)
        if last is not None and stamp <= last:
            raise ReplayError("archive_not_strictly_ordered")
        if record["t"] in by_time:
            raise ReplayError("duplicate_archive_record")
        by_time[record["t"]] = record
        last = stamp

    evidence = []
    previous_commit = None
    for sha, expected_blob, stamp in CHECKPOINTS:
        if git("cat-file","-t",sha).strip() != b"commit":
            raise ReplayError("not_a_commit")
        if previous_commit is not None:
            git("merge-base","--is-ancestor",previous_commit,sha)
        previous_commit = sha
        payload = git("show",sha+":data/myfxbook/latest.json")
        if blob_oid(payload) != expected_blob:
            raise ReplayError("pinned_historical_blob_changed")
        try:
            snapshot = json.loads(payload.decode("utf-8"),object_pairs_hook=unique)
        except (ValueError, UnicodeError) as exc:
            raise ReplayError("invalid_historical_json") from exc
        if (type(snapshot) is not dict or snapshot.get("status") != "ok" or
                snapshot.get("source") != SOURCE or
                snapshot.get("updatedAt") != stamp or
                type(snapshot.get("symbols")) is not dict):
            raise ReplayError("historical_snapshot_mismatch")
        row = snapshot["symbols"].get("EURUSD")
        if row is None or valid_row(row) != utc(stamp):
            raise ReplayError("historical_row_missing")
        if by_time.get(stamp) != row:
            raise ReplayError("historical_commit_record_not_in_archive")
        raw_commit_seconds=git("show","-s","--format=%ct",sha).strip().decode("ascii")
        try:
            claim_stamp=datetime.fromtimestamp(int(raw_commit_seconds),
                tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except (ValueError,OverflowError,OSError) as exc:
            raise ReplayError("invalid_git_committer_clock_claim") from exc
        evidence.append({
            "commit_sha":sha, "latest_blob_sha1":expected_blob,
            "sampled_at":stamp, "archived_record_at":row["t"],
            "commit_committer_clock_claim":claim_stamp,
            "commit_metadata_equals_sample_clock":claim_stamp == stamp,
            "retail_long_pct":row["lPct"], "retail_short_pct":row["sPct"],
        })
    return {
        "schema":SCHEMA,
        "summary":review_claims(evidence),
        "samples":evidence,
        "explanation":"Git object hashes prove these bytes are in named commits. "
          "Commit dates can be producer-authored and are not independent "
          "server receipt or public provider first-seen evidence.",
    }
