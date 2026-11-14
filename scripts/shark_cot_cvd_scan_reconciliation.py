"""Track B offline: reconcile ORIGINAL COT+OHLC observation to M15 CVD scans.

This is a bounded PRIVATE two-database research audit. ORIGINAL COT+price
signals must already pass shark_causal_pair_audit (immutable local evidence).
An original M15 close is joined to the actual, separately stamped CVD
evaluation attempt on that exact slot. Both original full OHLC SHA and private
HMAC must match and the attempt must precede the ORIGINAL signal observation.
In addition, a FIXED seven-slot window (latest close plus previous six M15)
checks whether all evaluation attempts existed before the same original
observation. Earlier documents are NOT presumed source-identical merely
because the slot clocks and original detector statuses are present.

The detector's "new confirmations on this exact closed M15" is NOT a proof
of no CVD in previous slots, no institutional activity, or lack of a future
trading outcome. Even a positive technical count lacks directional event
lineage unless separately verified by shark_cvd_cot_price_triage.

NO production import, network, broker calls, schema changes, orders, alerts,
credentials persistence, raw market prices/IDs/timestamps in output, or edge.
"""
from __future__ import annotations

from collections import Counter
from datetime import timedelta
import hmac
import sqlite3

from scripts import shark_causal_pair_audit as cotprice
from scripts import shark_cot_asof_witness as witness
from scripts import shark_cvd_scan_coverage as scans
from scripts import shark_cvd_source_lineage as lineage
from scripts import shark_cvd_prefix_lineage as prefix

SCHEMA = "remura-track-b-cot-price-cvd-scan-asof-join-v3"
MAX_ROWS = scans.MAX_ROWS
# Six previous M15 closes plus the last close for the original COT signal.
# A fixed 90-minute lookback, NOT a tuned threshold or an institutional
# negative-label window. Older intraday pivots may still influence CVD.
WINDOW_PRIOR_SLOTS = 6
WINDOW_SLOTS = WINDOW_PRIOR_SLOTS + 1


def _report(status, *, valid_pairs=None, groups=None, **extra):
    return {
        "schema": SCHEMA, "status": status,
        "validOriginalCotPricePairs": valid_pairs,
        "joinedScanGroups": groups,
        "preSignalWindowGroups": None,
        "preSignalWindowM15Slots": WINDOW_SLOTS,
        "preSignalWindowSpanMinutes": WINDOW_PRIOR_SLOTS*15,
        "windowEarlierSourcesCryptographicallyLinked": False,
        "windowFullEvaluationProvesNoHistoricalDivergence": False,
        "windowIsCompleteTradingNegativeControl": False,
        "matchedScansProveDirectionalCvdSignal": False,
        "zeroNewTechnicalConfirmationsProveNoPriorCvd": False,
        "noLocalScanIsAnInstitutionalNegative": False,
        "institutionalNegativeControlsAdmissible": 0,
        "independentSamplingEstablished": False,
        "independentBrokerClockVerified": False,
        "crossDatabaseAtomicCommit": False,
        "netOutcomesAdmissible": 0, "edge": "NOT_ESTABLISHED",
        "brokerCalls": 0, "ordersEnabled": False, "alertsEnabled": False,
        **extra,
    }


def audit(db_main, db_private, *, as_of, days=1, secret):
    """Aggregate mutually exclusive status of each admitted COT+OHLC signal.

    Scans after original observed_at, after as_of, or from a different full
    source document cannot retroactively qualify any Squalincome signal.
    A confirmed technical event in the scan may not be the same event or
    direction as the COT side; event-level lineage remains a separate gate.

    Caller may supply already-started read transactions. This function starts
    two read snapshots when needed, never commits caller transactions.
    """
    if (not isinstance(db_main, sqlite3.Connection)
            or not isinstance(db_private, sqlite3.Connection)):
        raise ValueError("two_sqlite_connections_required")
    if type(days) is not int or not 1 <= days <= cotprice.MAX_DAYS:
        raise ValueError("invalid_bounded_audit_window")
    now = witness._parse(as_of)
    # Fail closed on key errors EVEN when evidence tables are unavailable.
    lineage._mac(secret, "0"*64)
    main_started = not db_main.in_transaction
    private_started = not db_private.in_transaction
    if main_started:
        db_main.execute("BEGIN")
    if private_started:
        db_private.execute("BEGIN")
    try:
        original = []
        cot = cotprice.audit(
            db_main, as_of=witness._iso(now), days=days,
            _verified_pairs=original)
        total = cot["locallyJoinedCausalPairs"]
        if total is None:
            return _report("COT_PRICE_EVIDENCE_UNAVAILABLE")
        if total != len(original):
            raise ValueError("original_signal_sink_inconsistent")
        if not scans._protected(db_private):
            return _report("CVD_SCAN_ATTEMPT_EVIDENCE_UNAVAILABLE",
                           valid_pairs=total)
        # Fetch no more than the maximum bounded append-only scan ledger.
        # One row per market / M15 slot (protected by SQLite PK).
        # COT observations can be up to 3h after their original M15 close.
        # Include that allowed lag PLUS the fixed 90m pre-signal window;
        # otherwise boundary cohorts could falsely appear to have no scans.
        low = (now-timedelta(days=days)-cotprice.cot.MAX_CLOSE_DELAY
               -WINDOW_PRIOR_SLOTS*scans.STEP).strftime("%Y-%m-%dT%H:%M:%S")
        high = now.strftime("%Y-%m-%dT%H:%M:%S")
        rows = db_private.execute(
            f"""SELECT symbol,closed_at,attempted_at,state,source_hmac,
                       session_prefix_hmac,new_confirmations,reason,schema_version FROM {scans.TABLE}
                WHERE substr(closed_at,1,19)>=?
                  AND substr(closed_at,1,19)<=?
                ORDER BY symbol,closed_at LIMIT ?""",
            (low, high, MAX_ROWS+1)).fetchall()
        if len(rows)>MAX_ROWS:
            raise ValueError("scan_attempt_rows_over_limit")
        indexed = {}
        for sym, closed, attempted, state, mac, session_mac, count, reason, version in rows:
            t = witness._parse(closed)
            at = witness._parse(attempted)
            if (sym not in scans.PILOT or version != scans.SCHEMA
                    or witness._iso(t) != closed
                    or witness._iso(at) != attempted
                    or t.minute % 15 or t.second or t.microsecond
                    or not t <= at <= t+scans.GRACE):
                raise ValueError("scan_attempt_clock_or_schema_corrupt")
            if state == "EVALUATED":
                if (reason != "DETECTOR_OK" or
                        not isinstance(mac, str) or not scans.HEX.fullmatch(mac)
                        or type(count) is not int or count < 0
                        or (session_mac is not None
                            and (not isinstance(session_mac, str)
                                 or not scans.HEX.fullmatch(session_mac)))):
                    raise ValueError("evaluated_scan_evidence_invalid")
            elif state == "NOT_EVALUABLE":
                if (reason not in ("SOURCE_ABSENT", "DATA_INVALID",
                                   "DATA_MISSING", "DATA_STALE",
                                   "DATA_PARTIAL", "DATA_INSUFFICIENT")
                        or count is not None or session_mac is not None
                        or (mac is not None
                            and (not isinstance(mac, str)
                                 or not scans.HEX.fullmatch(mac)))):
                    raise ValueError("unknown_scan_evidence_invalid")
            else:
                raise ValueError("unknown_scan_state")
            key = (sym, t)
            if key in indexed:
                raise ValueError("duplicate_scan_slot")
            indexed[key] = (at, state, mac, count, session_mac)
        names = (
            "MATCHED_EVALUATION_NEW_LOCAL_CVD",
            "MATCHED_EVALUATION_ZERO_NEW_LOCAL_CVD",
            "UNKNOWN_MISSING_ATTEMPT",
            "UNKNOWN_ATTEMPT_NOT_YET_KNOWN_AT_SIGNAL",
            "UNKNOWN_ATTEMPT_NOT_EVALUABLE",
            "UNKNOWN_DIFFERENT_PRICE_SOURCE",
        )
        counts = Counter({n: 0 for n in names})
        windows = Counter({n: 0 for n in (
            "WINDOW_ALL_7_LOCALLY_EVALUATED_EARLIER_SOURCES_UNLINKED",
            "WINDOW_ALL_7_M15_PREFIXES_VERIFIED_LOCAL_ONLY",
            "UNKNOWN_WINDOW_PREFIX_MISMATCH",
            "UNKNOWN_WINDOW_MISSING_ATTEMPT",
            "UNKNOWN_WINDOW_LATE_ATTEMPT",
            "UNKNOWN_WINDOW_NOT_EVALUABLE",
            "UNKNOWN_WINDOW_LAST_SOURCE_MISMATCH",
            "UNKNOWN_WINDOW_NOT_PILOT",
        )})
        # These main prefixes must have been captured in the ORIGINAL
        # Squalincome transaction. Never regenerate from today's OHLC.
        main_prefixes = prefix.verified_main_prefixes(
            db_main, pairs=original, as_of=witness._iso(now))
        for sym, week, closed, observed, sha, cot_side in original:
            # Do NOT re-read mutable prices or use historical COT cache.
            close_time = witness._parse(closed)
            original_seen = witness._parse(observed)
            entry = indexed.get((sym, close_time))
            # Window data are a *separate* conservative denominator screen,
            # not event-level CVD, direction or a verified negative cohort.
            if sym not in scans.PILOT:
                windows["UNKNOWN_WINDOW_NOT_PILOT"] += 1
            else:
                window = [indexed.get(
                    (sym, close_time-scans.STEP*i))
                    for i in range(WINDOW_SLOTS)]
                if any(row is None for row in window):
                    windows["UNKNOWN_WINDOW_MISSING_ATTEMPT"] += 1
                elif any(row[0] > original_seen or row[0] > now
                         for row in window):
                    windows["UNKNOWN_WINDOW_LATE_ATTEMPT"] += 1
                elif any(row[1] != "EVALUATED" for row in window):
                    windows["UNKNOWN_WINDOW_NOT_EVALUABLE"] += 1
                elif not hmac.compare_digest(
                        window[0][2], lineage._mac(secret, sha)):
                    windows["UNKNOWN_WINDOW_LAST_SOURCE_MISMATCH"] += 1
                else:
                    # BOTH sides of every prefix proof were immutably
                    # captured: private when each scan actually ran, main
                    # within the later original Squalincome transaction.
                    # Missing proofs do not imply matching OHLC history.
                    if (main_prefixes is None or
                            any(row[4] is None for row in window) or
                            any(main_prefixes.get((
                                sym, week, closed, observed,
                                witness._iso(close_time-scans.STEP*i))) is None
                                for i in range(WINDOW_SLOTS))):
                        windows[
                            "WINDOW_ALL_7_LOCALLY_EVALUATED_EARLIER_SOURCES_UNLINKED"
                        ] += 1
                    elif any(not hmac.compare_digest(
                            row[4], prefix._mac(secret, main_prefixes[(
                                sym, week, closed, observed,
                                witness._iso(close_time-scans.STEP*i))]))
                            for i, row in enumerate(window)):
                        windows["UNKNOWN_WINDOW_PREFIX_MISMATCH"] += 1
                    else:
                        # Confirms SAME UTC-session M15 price/tick history
                        # for 7 slots ONLY; not independent broker timing,
                        # H1/H4 identity, full-session CVD completeness,
                        # direction, or a negative trading control.
                        windows[
                            "WINDOW_ALL_7_M15_PREFIXES_VERIFIED_LOCAL_ONLY"
                        ] += 1
            if entry is None:
                counts["UNKNOWN_MISSING_ATTEMPT"] += 1
                continue
            attempted, state, private_mac, confirmations, _prefix_mac = entry
            if attempted > original_seen or attempted > now:
                counts["UNKNOWN_ATTEMPT_NOT_YET_KNOWN_AT_SIGNAL"] += 1
            elif state != "EVALUATED":
                counts["UNKNOWN_ATTEMPT_NOT_EVALUABLE"] += 1
            elif not hmac.compare_digest(
                    private_mac, lineage._mac(secret, sha)):
                counts["UNKNOWN_DIFFERENT_PRICE_SOURCE"] += 1
            elif confirmations:
                counts["MATCHED_EVALUATION_NEW_LOCAL_CVD"] += 1
            else:
                counts["MATCHED_EVALUATION_ZERO_NEW_LOCAL_CVD"] += 1
        if sum(counts.values()) != total:
            raise ValueError("nonconserving_original_signal_denominator")
        if sum(windows.values()) != total:
            raise ValueError("nonconserving_presignal_window_denominator")
        return _report(
            "LOCAL_M15_SCAN_TO_ORIGINAL_COT_PRICE_AUDITED_ONLY",
            valid_pairs=total,
            groups=dict(sorted(counts.items())),
            preSignalWindowGroups=dict(sorted(windows.items())),
            windowObservedSlotsOnlyNotCertifiedInstitutionalNoSignal=True,
            windowDoesNotCoverAllSessionPivotHistory=True,
            windowProofMatchesOnlyOriginalUTCSessionM15Prefixes=True,
            windowFullOHLCAndBrokerCollectionTimeIndependentlyVerified=False,
            allMatchedScansStillOnlyTechnicalCLVTickProxy=True,
            full34PriceOnlyDenominatorChanged=False,
            originalSignalMarketUniverse="original_cot_price_pairs_not_34_markets",
            acceptedRealPriceOnlyNegativeControls=0,
        )
    finally:
        if private_started:
            db_private.rollback()
        if main_started:
            db_main.rollback()
