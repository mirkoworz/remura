"""Track B: future-only PRIVATE CVD M15 evaluation-attempt coverage ledger.

An event-only ledger cannot prove that absence of an event means an actual
scan happened. This research-only companion records EACH explicitly invoked
pilot-market M15 detector evaluation (including non-evaluable attempts),
not just positive divergences. Every usable evaluation reruns the ORIGINAL
CLV*tick-volume detector on the supplied, already-closed ORIGINAL OHLC data.
A local zero-new-confirmation result is NOT an institutional/trading negative.

OFFLINE only, explicit caller, private SQLite. No scheduler, cloud, server,
broker GET, secret persistence, prices, event IDs, orders or alert side effects.
An observed attempt is host-clock evidence, not an externally certified
scheduler invocation or end-to-end broker coverage. No historical backfill.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import re
import sqlite3

from scripts import cvd_divergence as detector
from scripts import shark_cot_asof_witness as witness
from scripts import shark_cvd_source_lineage as lineage
from scripts import shark_cvd_prefix_lineage as prefix

TABLE = "research_cvd_scan_attempts"
SCHEMA = "remura-track-b-cvd-scan-attempt-coverage-v2"
TRIGGERS = ("research_cvd_scan_no_update", "research_cvd_scan_no_delete")
PILOT = ("EURUSD", "XAUUSD")
STEP = timedelta(minutes=15)
GRACE = timedelta(minutes=3)
MAX_ROWS = 10000
MAX_AUDIT_DAYS = 7
HEX = re.compile(r"^[0-9a-f]{64}$")


def ensure_schema(db):
    """Explicit opt-in on a separate PRIVATE database, never on LIVE."""
    if not isinstance(db, sqlite3.Connection) or db.in_transaction:
        raise ValueError("standalone_private_sqlite_required")
    with db:
        db.execute(f"""CREATE TABLE IF NOT EXISTS {TABLE} (
            symbol TEXT NOT NULL CHECK(symbol IN ('EURUSD','XAUUSD')),
            closed_at TEXT NOT NULL,
            attempted_at TEXT NOT NULL,
            state TEXT NOT NULL CHECK(state IN ('EVALUATED','NOT_EVALUABLE')),
            source_hmac TEXT,
            session_prefix_hmac TEXT,
            new_confirmations INTEGER,
            reason TEXT NOT NULL,
            schema_version TEXT NOT NULL CHECK(schema_version='{SCHEMA}'),
            PRIMARY KEY(symbol,closed_at),
            CHECK((state='EVALUATED' AND source_hmac IS NOT NULL
                   AND new_confirmations >= 0 AND reason='DETECTOR_OK')
               OR (state='NOT_EVALUABLE' AND new_confirmations IS NULL
                   AND reason IN ('SOURCE_ABSENT','DATA_INVALID',
                                  'DATA_MISSING','DATA_STALE',
                                  'DATA_PARTIAL','DATA_INSUFFICIENT')))
        ) WITHOUT ROWID""")
        for op, name in zip(("UPDATE", "DELETE"), TRIGGERS):
            db.execute(f"""CREATE TRIGGER IF NOT EXISTS {name}
                BEFORE {op} ON {TABLE}
                BEGIN SELECT RAISE(ABORT,'immutable_cvd_attempt'); END""")


def _protected(db):
    present = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (TABLE,)).fetchone()
    if not present:
        return False
    names = {row[0] for row in db.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name=?",
        (TABLE,))}
    if not set(TRIGGERS).issubset(names):
        raise ValueError("cvd_attempt_immutability_triggers_missing")
    return True


def record(db, *, symbol, slot_closed_at, source_document, secret, clock=None):
    """Stamp the CURRENT M15 evaluation attempt, not historical conclusions.

    Requires an explicit 15-minute UTC closed slot and call within 3 minutes.
    None source is an observed UNKNOWN attempt, not an evaluated negative.
    For non-None sources, the original detector is actually run; caller-supplied
    status/count/digest are never trusted. Cannot certify the source collection
    clock independently, even when the detector reports 'ok'.
    """
    if not isinstance(db, sqlite3.Connection) or db.in_transaction:
        raise ValueError("standalone_private_sqlite_required")
    if symbol not in PILOT or not _protected(db):
        raise ValueError("pilot_or_schema_unavailable")
    now = witness._clock(clock)
    closed = witness._parse(slot_closed_at)
    if (closed.second or closed.microsecond or closed.minute % 15
            or not closed <= now <= closed + GRACE):
        raise ValueError("not_a_current_closed_m15_attempt")
    # Validate HMAC key even when this particular source is missing.
    lineage._mac(secret, "0"*64)
    state, count, reason, mac, session_mac = (
        "NOT_EVALUABLE", None, "SOURCE_ABSENT", None, None)
    if source_document is not None:
        doc = source_document
        if (not isinstance(doc, dict) or doc.get("symbol") != symbol
                or doc.get("provider") != "ctrader"
                or not isinstance(doc.get("providerSymbol"), str)
                or not doc["providerSymbol"].strip()
                or doc.get("timezone") != "UTC"
                or doc.get("sourceTimeframe") != "M15"
                or not isinstance(doc.get("timeframes"), dict)
                or witness._parse(doc.get("lastComplete")) + STEP != closed):
            raise ValueError("original_source_identity_or_slot_mismatch")
        # The OHLC rows must come from the actual source document. Do not
        # reconstruct older records or trust a precomputed detector result.
        # The CVD detector needs fewer M15 than the price/H1/H4 evidence
        # auditor (which requires >=55). Do not silently make the detector's
        # 15-candle warm-up look like a missing scan by using that stricter
        # price-audit minimum here.
        bars = doc["timeframes"].get("M15")
        if not isinstance(bars, list) or not 1 <= len(bars) <= 4320:
            raise ValueError("m15_source_missing_or_unbounded")
        normalized = []
        for bar in bars:
            if not isinstance(bar, dict):
                raise ValueError("non_mapping_original_m15")
            at = witness._parse(bar.get("t"))
            normalized.append({**bar, "t": int(at.timestamp()*1000)})
        if witness._parse(bars[-1]["t"]) + STEP != closed:
            raise ValueError("original_last_m15_does_not_match_slot")
        market = {"symbol": symbol, "provider": "ctrader",
                  "providerSymbol": doc["providerSymbol"],
                  "frames": {"M15": normalized}}
        analysis = detector.analyze(market, now=int(now.timestamp()*1000))
        if analysis.get("algorithm") != detector.VERSION:
            raise ValueError("detector_version_mismatch")
        mac = lineage._mac(secret, lineage._document_sha(doc))
        if analysis["status"] == "ok":
            state = "EVALUATED"
            reason = "DETECTOR_OK"
            # Detector returns ALL already-known session events; count only
            # NEW confirmations on THIS closed slot, not repeated old ones.
            count = sum(witness._parse(ev["confirmedAt"]) == closed
                        for ev in analysis["events"])
            # Stamp the ORIGINAL causal M15-session prefix AT THE SCAN, not
            # from subsequently mutated cached prices. Reuse the exact
            # canonical prefix algorithm captured by Squalincome.
            # Short detector warm-up sources (<55 archived M15) cannot
            # satisfy that independent prefix contract: keep evaluation
            # but its cross-snapshot lineage remains N/D, never "same".
            if len(bars) >= 55:
                session_mac = prefix._mac(
                    secret, prefix._sha(doc, witness._iso(closed)))
        elif analysis["status"] in {
                "invalid", "missing", "stale", "partial", "insufficient"}:
            reason = "DATA_" + analysis["status"].upper()
        else:
            raise ValueError("unrecognized_detector_status")
    # Never retroactively insert a slot older than the newest stored one for
    # this market, even if caller backdates clock. Duplicate also blocked.
    with db:
        last = db.execute(
            f"SELECT MAX(closed_at) FROM {TABLE} WHERE symbol=?",
            (symbol,)).fetchone()[0]
        if last is not None and witness._parse(last) >= closed:
            raise ValueError("duplicate_or_backfilled_scan_attempt")
        if db.execute(f"SELECT count(*) FROM {TABLE}").fetchone()[0] >= MAX_ROWS:
            raise ValueError("private_cvd_coverage_capacity_reached")
        db.execute(f"""INSERT INTO {TABLE}
            (symbol,closed_at,attempted_at,state,source_hmac,
             session_prefix_hmac,new_confirmations,reason,schema_version)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (symbol, witness._iso(closed), witness._iso(now), state,
             mac, session_mac, count, reason, SCHEMA))
    return {"schema": SCHEMA, "status": state,
            "newConfirmationsOnThisClosedSlot": count,
            "isAProvenNegativeTradingControl": False,
            "sourceClockIndependentlyAuthenticated": False,
            "brokerCalls": 0, "ordersEnabled": False, "alertsEnabled": False}


def audit(db, *, as_of, days=1):
    """Read-only, bounded per-market coverage. Absences remain UNKNOWN.

    Anchors each market at its FIRST visible recorded attempt in the window,
    not at an inferred feature-flag date. Calendar gaps may be weekend/market
    closures, missing invocations or broker issues; never infer which.
    """
    if not isinstance(db, sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    if type(days) is not int or not 1 <= days <= MAX_AUDIT_DAYS:
        raise ValueError("invalid_coverage_window")
    now = witness._parse(as_of)
    common = {
        "schema": SCHEMA,
        "pilotMarkets": list(PILOT),
        "calendarSlotsAreNotBrokerOrScheduledScans": True,
        "noRecordBeforeFirstAttemptMeansUnknown": True,
        "negativeTradingControlsAdmissible": 0,
        "noNewLocalConfirmationIsNotNoInstitutionalActivity": True,
        "independentDataCollectionAttested": False,
        "outOfSampleEdgeEstablished": False,
        "brokerCalls": 0, "alertsEnabled": False, "ordersEnabled": False,
    }
    if not _protected(db):
        return {**common, "status": "NO_SCAN_ATTEMPT_LEDGER",
                "markets": {sym: None for sym in PILOT}}
    began = not db.in_transaction
    if began:
        db.execute("BEGIN")
    try:
        start = now - timedelta(days=days)
        # The trailing 3 minutes are not yet finalized for the last slot.
        last_slot = datetime.fromtimestamp(
            int((now-GRACE).timestamp())//900*900, tz=now.tzinfo)
        rows = db.execute(
            f"""SELECT symbol,closed_at,attempted_at,state,source_hmac,
                       session_prefix_hmac,new_confirmations,reason,schema_version FROM {TABLE}
                WHERE substr(closed_at,1,19)>=?
                  AND substr(closed_at,1,19)<=?
                ORDER BY symbol,closed_at LIMIT ?""",
            (start.strftime("%Y-%m-%dT%H:%M:%S"),
             last_slot.strftime("%Y-%m-%dT%H:%M:%S"),
             MAX_ROWS+1)).fetchall()
        if len(rows) > MAX_ROWS:
            raise ValueError("cvd_coverage_audit_unbounded")
        by_symbol = {sym: [] for sym in PILOT}
        for sym, closed, attempted, state, mac, session_mac, count, reason, version in rows:
            at, seen = witness._parse(closed), witness._parse(attempted)
            if (sym not in by_symbol or version != SCHEMA
                    or witness._iso(at) != closed
                    or witness._iso(seen) != attempted
                    or not at <= seen <= at+GRACE or seen > now
                    or not start <= at <= last_slot):
                raise ValueError("cvd_coverage_time_or_schema_corrupt")
            if state == "EVALUATED":
                if (reason != "DETECTOR_OK" or not isinstance(mac, str)
                        or not HEX.fullmatch(mac) or type(count) is not int
                        or count < 0
                        or (session_mac is not None and
                            (not isinstance(session_mac, str)
                             or not HEX.fullmatch(session_mac)))):

                    raise ValueError("cvd_evaluated_proof_corrupt")
            elif (state != "NOT_EVALUABLE" or count is not None or
                  reason not in ("SOURCE_ABSENT", "DATA_INVALID",
                                 "DATA_MISSING", "DATA_STALE",
                                 "DATA_PARTIAL", "DATA_INSUFFICIENT") or
                  (mac is not None and
                   (not isinstance(mac, str) or not HEX.fullmatch(mac))) or
                  session_mac is not None):
                raise ValueError("cvd_missing_proof_corrupt")
            by_symbol[sym].append((at, state, count))
        result = {}
        for sym, values in by_symbol.items():
            if not values:
                result[sym] = None  # No observed attempt is NOT zero missed.
                continue
            first = values[0][0]
            expected = int((last_slot-first)//STEP)+1
            observed = len(values)
            if expected < observed or any(
                    values[i][0] <= values[i-1][0]
                    for i in range(1, observed)):
                raise ValueError("duplicate_or_nonmonotonic_scan_proofs")
            evaluated = sum(s == "EVALUATED" for _,s,_ in values)
            result[sym] = {
                "scope": "from_first_visible_attempt_not_activation",
                "calendarSlotsSinceFirstVisibleAttempt": expected,
                "recordedAttempts": observed,
                "calendarSlotsWithoutRecordedAttempt": expected-observed,
                "locallyEvaluableSlots": evaluated,
                "locallyNotEvaluableAttempts": observed-evaluated,
                "localZeroNewConfirmationSlots": sum(
                    s=="EVALUATED" and n==0 for _,s,n in values),
                "localSlotsWithNewConfirmations": sum(
                    s=="EVALUATED" and n>0 for _,s,n in values),
                "newTechnicalConfirmations": sum(
                    n for _,s,n in values if s=="EVALUATED"),
                "coverageCompleteFromBeforeFirstAttempt": False,
                "noNewConfirmationIsVerifiedInstitutionalNegative": False,
            }
        return {**common, "status": "LOCAL_ATTEMPT_COVERAGE_ONLY",
                "markets": result}
    finally:
        if began:
            db.rollback()
