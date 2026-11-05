"""REMURA Track B: PRIVATE read-only triage of COT+OHLC+CVD proxy evidence.

TWO separate databases, TWO read snapshots, not an atomic cross-DB commit.
The main database's COT+OHLC observations must pass the existing genuine
Squalincome as-of witness audit. Private CVD events must have a source HMAC
inserted IN THE SAME TRANSACTION as the newly detected event, the original
CLV*tick detector must have been replayed from that document, and the HMAC
must match the original price proof SHA. The detection must have been
observed BEFORE/AT the Squalincome original observation, not merely share
a symbol or M15 boundary.

This is a strict SAME SNAPSHOT filter; an event from a different valid price
snapshot is UNKNOWN, not necessarily false. No private event identifiers,
source digests, prices, timestamps or broker mapping are returned.
No notifications, orders, profit, genuine buy/sell aggressor volume, CFTC
timestamp authority, executed spread or statistically validated edge.
No production imports, cron, network, credentials or schema writes.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import timedelta
import sqlite3

from scripts import shark_causal_pair_audit as cotprice
from scripts import shark_cot_asof_witness as witness
from scripts import shark_cvd_ledger as cvd
from scripts import shark_cvd_source_lineage as source

SCHEMA = "remura-track-b-cot-price-cvd-exact-snapshot-triage-v1"
MAX_DAYS = 7
MAX_PRIVATE_EVENTS = cvd.MAX_EVENTS


def _result(status, **kwargs):
    return {
        "schema":SCHEMA,"status":status,
        "marketUniverse":"genuine_squalincome_cot_price_pairs_only",
        "full34PriceOnlyDenominatorChanged":False,
        "cvdMethod":"CLV_times_ctrader_tick_volume_PROXY",
        "cvdAggressorFlowMeasured":False,
        "sourceTimeIndependentlyAuthenticated":False,
        "cotCFTCReleaseTimeExternallyNotarized":False,
        "crossDatabaseAtomicCommit":False,
        "exactSourceDocumentIsCausalMarketEdge":False,
        "institutionalPredictiveCohortsAdmissible":0,
        "netWalkForwardOutcomesAdmissible":0,
        "tradingEdgeEstablished":False,
        "brokerCalls":0,"alertsEnabled":False,"ordersEnabled":False,
        **kwargs,
    }


def audit(db_main,db_cvd,*,as_of,days=1,secret):
    """Audit local HMAC source matches without opening any network channel.

    The secret must be supplied privately by future authorized runtime, never
    in GitHub or JSON. A simulated positive match is not a trading outcome.
    """
    if (not isinstance(db_main,sqlite3.Connection)
            or not isinstance(db_cvd,sqlite3.Connection)):
        raise ValueError("two_sqlite_connections_required")
    if type(days) is not int or not 1<=days<=MAX_DAYS:
        raise ValueError("invalid_triple_audit_window")
    now=witness._parse(as_of)
    # Validates private key even on unavailable DBs; do not give a false
    # readiness result when the secret is absent or accidentally changed.
    source._mac(secret,"0"*64)
    main_started=not db_main.in_transaction
    private_started=not db_cvd.in_transaction
    if main_started:
        db_main.execute("BEGIN")
    if private_started:
        db_cvd.execute("BEGIN")
    try:
        accepted=[]
        cot_result=cotprice.audit(db_main,as_of=witness._iso(now),
                                  days=days,_verified_pairs=accepted)
        if cot_result["locallyJoinedCausalPairs"] is None:
            return _result("COT_PRICE_PROOFS_UNAVAILABLE",
                validLocalCotPricePairs=None,
                privateCvdEvents=None, sourceBoundCvdEvents=None,
                exactSnapshotTriples=None, distinctSignalsWithExactCVD=None)
        if len(accepted)!=cot_result["locallyJoinedCausalPairs"]:
            raise ValueError("local_cot_pair_sink_mismatch")
        tables={name for (name,) in db_cvd.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        if "research_cvd_observations" not in tables:
            return _result("PRIVATE_CVD_LEDGER_UNAVAILABLE",
                validLocalCotPricePairs=len(accepted),
                privateCvdEvents=None, sourceBoundCvdEvents=None,
                exactSnapshotTriples=None, distinctSignalsWithExactCVD=None)
        triggers={x[0] for x in db_cvd.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' "
            "AND tbl_name='research_cvd_observations'")}
        if not {"research_cvd_no_update",
                "research_cvd_no_delete"}.issubset(triggers):
            raise ValueError("private_cvd_event_triggers_missing")
        seen=db_cvd.execute(
            "SELECT key,symbol,side,confirmed_at,detected_at "
            "FROM research_cvd_observations ORDER BY detected_at,key "
            "LIMIT ?",(MAX_PRIVATE_EVENTS+1,)).fetchall()
        if len(seen)>MAX_PRIVATE_EVENTS:
            raise ValueError("private_cvd_events_unbounded")
        if not source._has_protected_schema(db_cvd):
            return _result("PRIVATE_CVD_DOCUMENT_BINDINGS_UNAVAILABLE",
                validLocalCotPricePairs=len(accepted),
                privateCvdEvents=len(seen),sourceBoundCvdEvents=None,
                exactSnapshotTriples=None,distinctSignalsWithExactCVD=None)
        bound=db_cvd.execute(
            f"SELECT count(*) FROM {source.TABLE}").fetchone()[0]
        if bound>len(seen):
            raise ValueError("source_bindings_without_real_cvd_event")
        by_market=defaultdict(list)
        for event in seen:
            key,sym,side,confirmed,detected=event
            if side not in ("bullish","bearish"):
                raise ValueError("private_cvd_side_invalid")
            by_market[sym].append(event)
        triple_count=0
        distinct=0
        orientations=Counter()
        for sym,week,closed,observed_at,sha,cot_side in accepted:
            original=witness._parse(observed_at)
            closed_time=witness._parse(closed)
            matching=0
            for key,_,side,confirmed_at,detected_at in by_market[sym]:
                # Must have been confirmed on closed prices not later than
                # the original signal's last M15 close.
                if witness._parse(confirmed_at)>closed_time:
                    continue
                candidate=source.match(
                    db_cvd,event_key=key,original_price_sha=sha,
                    observed_at=observed_at,as_of=witness._iso(now),
                    secret=secret)
                if candidate["state"]!="EXACT_LOCAL_SOURCE_AND_CHRONOLOGY":
                    continue
                matching+=1
                orientations["SAME_TECHNICAL_DIRECTION" if (
                    (side=="bullish" and cot_side==1) or
                    (side=="bearish" and cot_side==-1)
                ) else "OPPOSITE_TECHNICAL_DIRECTION"]+=1
            if matching:
                distinct+=1
                triple_count+=matching
        return _result(
            "EXACT_LOCAL_COT_PRICE_CVD_SOURCE_MATCHES_AUDITED_NOT_PREDICTIVE",
            validLocalCotPricePairs=len(accepted),
            privateCvdEvents=len(seen),
            sourceBoundCvdEvents=bound,
            oldOrUnboundCvdEvents=len(seen)-bound,
            exactSnapshotTriples=triple_count,
            distinctSignalsWithExactCVD=distinct,
            orientations=dict(sorted(orientations.items())),
            sameSourceHMACAndChronologyVerified=True,
            localEvidenceOnly=True,
            coverageFromBothDatabasesNotExternallyCertified=True,
            observationsFromDifferentValidPriceSnapshotsMayBeExcluded=True,
        )
    finally:
        if private_started:
            db_cvd.rollback()
        if main_started:
            db_main.rollback()
