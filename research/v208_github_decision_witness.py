#!/usr/bin/env python3
"""REMURA V20.8: verify PRIVATE forward choices against PUBLIC hash-only GitHub witnesses.

Only an explicitly requested read-only GET of two fixed GitHub API endpoints per
decision. Never sends decisions, nonce, private data, broker metadata, or prices
to GitHub. No broker/Cloudflare/Oracle connections or collector writes.

An authenticated GitHub Actions push run is an external first-seen time for the
PUBLIC SHA-256 commitment -- NOT proof that a real CVD feed produced the choice.
Entries are conservatively timed from run.created_at, never Git commit dates.
"""
from __future__ import annotations

import argparse
import base64
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import urllib.request

from v207_forward_cvd_evaluation import (
    SCHEMA as DECISION_SCHEMA, checked_costs, evaluate, _decisions,
)
from v204_private_cvd_price_coverage import read_local_price_db, utc

UTC = timezone.utc
REPOSITORY = "mirkoworz/remura"
REPOSITORY_ID = 1422235455
ANCHOR_BRANCH = "research/remura-v208-github-decision-witness-20261123"
ANCHOR_WORKFLOW = ".github/workflows/remura-v208-anchor-witness.yml"
COMMITMENT_SCHEMA = "remura-v208-forward-commitment-v1"
MAX_DECISIONS_PER_AUDIT = 5
MAX_RESPONSE_BYTES = 500_000
HEX64 = re.compile(r"[a-f0-9]{64}")
HEX40 = re.compile(r"[a-f0-9]{40}")
NONCE = re.compile(r"[a-f0-9]{32,64}")


def commitment(row: dict) -> str:
    if type(row) is not dict:
        raise ValueError("bad_private_decision")
    nonce = row.get("decision_nonce")
    if type(nonce) is not str or NONCE.fullmatch(nonce) is None:
        raise ValueError("private_random_nonce_128bits_required")
    if row.get("anchor", {}).get("kind") != "github_commit":
        raise ValueError("unexpected_anchor_type")
    if "workflow_run_id" not in row["anchor"]:
        raise ValueError("missing_github_run_witness")
    # Only NON-ANCHOR private data is frozen. Includes the unpredictable nonce
    # to hide low-entropy BUY/SELL and event-time guesses from public observers.
    # A canonical encoding prevents reordering JSON keys after publication.
    serialized = json.dumps(
        {k: v for k, v in row.items() if k != "anchor"},
        ensure_ascii=False, sort_keys=True, separators=(",",":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def manifest_for(row: dict) -> dict:
    """Local hash-only payload that COULD be published after manual approval."""
    return {"schema": COMMITMENT_SCHEMA, "commitment_sha256": commitment(row)}


def get_github_json(url: str) -> dict:
    if not url.startswith(f"https://api.github.com/repos/{REPOSITORY}/"):
        raise ValueError("non_github_endpoint_rejected")
    req = urllib.request.Request(
        url, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "remura-v208-forward-witness-readonly/1",
        }, method="GET"
    )
    # No retries, no authorization headers or tokens, short bounded body/time.
    try:
        with urllib.request.urlopen(req, timeout=7) as response:
            if response.geturl().split("?")[0] != url.split("?")[0]:
                raise ValueError("github_redirect_disallowed")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except (OSError, TimeoutError) as exc:
        raise ValueError("github_witness_unavailable_or_rate_limited") from None
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError("oversize_github_witness")
    try:
        obj = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise ValueError("invalid_github_witness_json") from None
    if type(obj) is not dict:
        raise ValueError("bad_github_response")
    return obj


def _git_run(run: dict, run_id: int, as_of: datetime) -> tuple[str,str]:
    if (type(run) is not dict or run.get("id") != run_id or
        run.get("status") != "completed" or run.get("conclusion") != "success" or
        run.get("event") != "push" or run.get("head_branch") != ANCHOR_BRANCH or
        run.get("path") != ANCHOR_WORKFLOW):
        raise ValueError("untrusted_github_run")
    repo = run.get("repository")
    if (type(repo) is not dict or repo.get("id") != REPOSITORY_ID or
        repo.get("full_name") != REPOSITORY):
        raise ValueError("wrong_github_repository")
    sha = run.get("head_sha")
    if type(sha) is not str or HEX40.fullmatch(sha) is None:
        raise ValueError("unverifiable_witness_sha")
    known = utc(run.get("created_at"))
    if known > as_of or known.year < 2026:
        raise ValueError("future_or_unreasonable_witness")
    return sha, known.strftime("%Y-%m-%dT%H:%M:%SZ")


def _manifest_api(manifest_response: dict, digest: str, filename: str) -> None:
    if (manifest_response.get("path") != filename or
        manifest_response.get("type") != "file" or
        manifest_response.get("encoding") != "base64"):
        raise ValueError("wrong_immutable_git_path_or_encoding")
    content = manifest_response.get("content")
    if type(content) is not str or len(content) > 5000:
        raise ValueError("invalid_manifest_size")
    try:
        raw = base64.b64decode(content, validate=False)
        if len(raw) > 512:
            raise ValueError("oversize_manifest")
        obj = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise ValueError("invalid_manifest_json") from None
    if (type(obj) is not dict or set(obj) != {"schema","commitment_sha256"} or
        obj["schema"] != COMMITMENT_SCHEMA or obj["commitment_sha256"] != digest):
        raise ValueError("decision_does_not_match_historic_manifest")


def witness_ledger(ledger: dict, *, as_of: datetime, fetch_json=get_github_json) -> dict:
    """Return normalized ledger ONLY when every PRIVATE row is GitHub witnessed.

    The only network destinations are fixed GET URLs for GitHub run metadata
    and historical contents pinned to the exact head SHA. Never publish rows.
    """
    if type(ledger) is not dict or ledger.get("schema") != DECISION_SCHEMA:
        raise ValueError("bad_forward_ledger")
    rows = ledger.get("decisions")
    if type(rows) is not list or not 1 <= len(rows) <= MAX_DECISIONS_PER_AUDIT:
        raise ValueError("missing_or_too_many_forward_decisions")
    normalized = copy.deepcopy(ledger)
    seen: set[int] = set()
    for row in normalized["decisions"]:
        digest = commitment(row)
        run_id = row["anchor"].get("workflow_run_id")
        if type(run_id) is not int or not 1 <= run_id < 10**15 or run_id in seen:
            raise ValueError("invalid_or_reused_github_run_id")
        seen.add(run_id)
        run_url = (f"https://api.github.com/repos/{REPOSITORY}/actions/runs/{run_id}")
        run = fetch_json(run_url)
        sha, observed_at = _git_run(run, run_id, as_of)
        filename = f"research/forward-anchors/{digest}.json"
        file_url = (f"https://api.github.com/repos/{REPOSITORY}/contents/"
                    f"{filename}?ref={sha}")
        manifest = fetch_json(file_url)
        _manifest_api(manifest, digest, filename)
        original_sha = row["anchor"].get("sha")
        if original_sha is not None and original_sha != sha:
            raise ValueError("claimed_sha_disagrees_with_github")
        # Ignore self-asserted commit times; force server-created time.
        # This time must pass all causality/freshness rules of V20.7.
        row["anchor"] = {
            "kind": "github_commit", "sha": sha,
            "committed_at_utc": observed_at,
        }
    _decisions(normalized, as_of)
    return normalized


def verified_evaluation(ledger: dict | None, prices: dict | None, *,
                        as_of: datetime, costs: dict | None = None,
                        fetch_json=get_github_json) -> dict:
    if ledger is None:
        report = evaluate(None, prices, as_of=as_of, costs=costs)
        report["github_hash_only_witness_verified"] = False
        report["underlying_cvd_receipt_provenance_independently_verified"] = False
        return report
    witnessed = witness_ledger(ledger, as_of=as_of, fetch_json=fetch_json)
    report = evaluate(witnessed, prices, as_of=as_of, costs=costs)
    # A server-created GitHub run anchors the HASH of this decision, not its
    # origin from an actual TradingView execution or any broker identity.
    report["anchor_sha_and_time_claims_externally_verified"] = True
    report["github_hash_only_witness_verified"] = True
    report["underlying_cvd_receipt_provenance_independently_verified"] = False
    report["scientific_alpha_established"] = False
    return report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-decision-ledger", type=Path)
    p.add_argument("--github-readonly", action="store_true",
                   help="Explicitly allow max 10 anonymous read-only GETs to GitHub")
    p.add_argument("--private-sqlite", type=Path,
                   help="Open existing PRIVATE cTrader prices SQLite strictly read-only")
    p.add_argument("--spread-pips", type=float)
    p.add_argument("--slippage-pips-per-side", type=float)
    args = p.parse_args()
    if args.private_decision_ledger and not args.github_readonly:
        p.error("External witness requires --github-readonly; no requests executed")
    if args.github_readonly and not args.private_decision_ledger:
        p.error("Do not enable GitHub fetch without a local private ledger")
    try:
        costs = checked_costs(args.spread_pips, args.slippage_pips_per_side)
        private = (json.loads(args.private_decision_ledger.read_text(encoding="utf-8"))
                   if args.private_decision_ledger else None)
        prices = read_local_price_db(args.private_sqlite) if args.private_sqlite else None
        report = verified_evaluation(private, prices, as_of=datetime.now(UTC), costs=costs)
    except (ValueError, KeyError, TypeError, FileNotFoundError, OSError, UnicodeError):
        p.error("Witness, private data or forward causality failed verification; details redacted")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
