"""REMURA Track B OFFLINE opt-in: reuse SAME original cTrader documents.

Never imported by LIVE, no broker request, scheduling, orders or notifications.
Detector runs in disposable memory SQLite; TWO pilot attempts published together
to a pre-existing PRIVATE immutable SQLite table. No multi-database atomicity
with the price collector, independently trusted timestamps or proven edge.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sqlite3

from scripts import shark_cot_asof_witness as witness
from scripts import shark_cvd_same_source_preflight as preflight
from scripts import shark_cvd_scan_coverage as scan

SCHEMA = "remura-track-b-same-original-cvd-adapter-v1"
PILOT = ("EURUSD", "XAUUSD")
MAX_WORK = timedelta(seconds=30)
COLUMNS = ("symbol", "closed_at", "attempted_at", "state", "source_hmac",
           "session_prefix_hmac", "new_confirmations", "reason", "schema_version")


def _utc_now():
    return datetime.now(timezone.utc)


def capture(db, price_rows, pilot_documents, *, secret, enabled=False):
    """Called explicitly only with in-memory originals at actual scan time.

    A missing original is a NOT_EVALUABLE observation (UNKNOWN); missing
    invocation is never backfilled. Failures before COMMIT create NO attempt.
    Do not pass the LIVE database. Opt-in does not authorize VPS activation.
    """
    if enabled is not True:
        return {"schema": SCHEMA, "status": "DISABLED_BY_DEFAULT",
                "scanAttemptsRecorded": 0, "cvdDetectorEvaluated": False,
                "extraBrokerRequests": 0, "liveEnabled": False,
                "tradingEdgeEstablished": False}
    if not isinstance(db, sqlite3.Connection) or db.in_transaction:
        raise ValueError("existing_private_sqlite_outside_transaction_required")
    now = witness._clock(_utc_now())
    proof = preflight.prepare(price_rows, pilot_documents, clock=now)
    if proof["pilotOutsideAllowedCvdClock"]:
        raise ValueError("expired_cvd_window_remains_unknown")
    if proof["pilotIncompleteTickVolume"]:
        raise ValueError("incomplete_tick_volume_cannot_be_evaluated")
    if tuple(scan.PILOT) != PILOT or not scan._protected(db):
        raise ValueError("frozen_pilot_or_immutable_private_schema_missing")
    if db.execute("PRAGMA query_only").fetchone()[0]:
        raise ValueError("private_ledger_must_be_writable")
    closed = witness._parse(price_rows[0][1])
    if (closed < witness._parse(proof["prospectiveStartUtc"]) or
            not closed <= now <= closed + scan.GRACE):
        raise ValueError("not_a_current_prospective_slot")
    # Existing recorder COMMITS; never invoke it on the real ledger before
    # both pilot results are known. Keep all intermediate writes in RAM.
    temp = sqlite3.connect(":memory:")
    try:
        scan.ensure_schema(temp)
        for symbol in PILOT:
            scan.record(temp, symbol=symbol, slot_closed_at=witness._iso(closed),
                        source_document=pilot_documents.get(symbol),
                        secret=secret, clock=now)
        rows = temp.execute(
            "SELECT " + ",".join(COLUMNS) + " FROM " + scan.TABLE +
            " ORDER BY symbol").fetchall()
    finally:
        temp.close()
    if (len(rows) != 2 or tuple(r[0] for r in rows) != PILOT or
            any(r[1] != witness._iso(closed) or
                r[2] != witness._iso(now) or r[8] != scan.SCHEMA
                for r in rows)):
        raise ValueError("staged_scan_attempts_do_not_match_original_slot")
    end = witness._clock(_utc_now())
    if end < now or end - now > MAX_WORK or end > closed + scan.GRACE:
        raise ValueError("processing_delay_or_host_clock_changed")
    # Bound lock waiting; do not retry late or retroactively fill gaps.
    db.execute("PRAGMA busy_timeout=250")
    db.execute("BEGIN IMMEDIATE")
    try:
        if not scan._protected(db):
            raise ValueError("private_immutability_removed")
        for symbol in PILOT:
            latest = db.execute(
                "SELECT MAX(closed_at) FROM " + scan.TABLE +
                " WHERE symbol=?", (symbol,)).fetchone()[0]
            if latest is not None and witness._parse(latest) >= closed:
                raise ValueError("duplicate_or_retroactive_cvd_attempt")
        count = db.execute(
            "SELECT count(*) FROM " + scan.TABLE).fetchone()[0]
        if count + len(rows) > scan.MAX_ROWS:
            raise ValueError("private_cvd_capacity_exceeded")
        db.executemany(
            "INSERT INTO " + scan.TABLE + " (" + ",".join(COLUMNS) +
            ") VALUES (?,?,?,?,?,?,?,?,?)", rows)
        db.commit()
    except BaseException:
        db.rollback()
        raise
    evaluated = sum(r[3] == "EVALUATED" for r in rows)
    return {
        "schema": SCHEMA, "status": "ISOLATED_PILOT_ATTEMPTS_COMMITTED",
        "priceDenominatorInput": proof["fullPriceOnlyDenominator"],
        "cvdPilotMarkets": 2, "cvdMarketsUncovered": 32,
        "scanAttemptsRecorded": 2, "evaluatedAttempts": evaluated,
        "unknownAttempts": 2 - evaluated, "cvdDetectorEvaluated": evaluated > 0,
        "shaSameOriginalDocumentChecked": True,
        "missingOrZeroNewIsNotNegativeControl": True,
        "crossDatabaseAtomicityEstablished": False,
        "independentBrokerFirstSeenVerified": False,
        "extraBrokerRequests": 0, "liveEnabled": False,
        "stagingOrReleaseAuthorized": False, "tradingEdgeEstablished": False,
    }
