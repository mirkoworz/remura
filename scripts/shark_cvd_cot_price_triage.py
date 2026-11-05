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
from scripts import shark_cvd_prefix_lineage as prefix
import hmac

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
        # Private CVD observations RECORDED AFTER the requested as_of are
        # strictly invisible, even in aggregate counts. Bound the query to
        # 90 minutes before the requested cohort window, since a technical
        # event may precede a valid Squalincome observation by that much.
        earliest=now-timedelta(days=days,minutes=90)
        low=earliest.strftime("%Y-%m-%dT%H:%M:%S")
        high=now.strftime("%Y-%m-%dT%H:%M:%S")
        seen=db_cvd.execute(
            "SELECT key,symbol,side,confirmed_at,detected_at "
            "FROM research_cvd_observations "
            "WHERE substr(detected_at,1,19)>=? "
            "AND substr(detected_at,1,19)<=? "
            "ORDER BY detected_at,key LIMIT ?",
            (low,high,MAX_PRIVATE_EVENTS+1)).fetchall()
        if len(seen)>MAX_PRIVATE_EVENTS:
            raise ValueError("private_cvd_events_unbounded")
        seen=[row for row in seen
              if earliest<=witness._parse(row[4])<=now]
        if not source._has_protected_schema(db_cvd):
            return _result("PRIVATE_CVD_DOCUMENT_BINDINGS_UNAVAILABLE",
                validLocalCotPricePairs=len(accepted),
                privateCvdEvents=len(seen),sourceBoundCvdEvents=None,
                exactSnapshotTriples=None,distinctSignalsWithExactCVD=None)
        selected_keys={row[0] for row in seen}
        # One bounded HMAC binding per real event. Do not count records
        # created in the future or unrelated old private sessions.
        binding_rows=db_cvd.execute(
            f"SELECT b.event_key,b.bound_at FROM {source.TABLE} b "
            "JOIN research_cvd_observations e ON e.key=b.event_key "
            "WHERE substr(e.detected_at,1,19)>=? "
            "AND substr(e.detected_at,1,19)<=? LIMIT ?",
            (low,high,MAX_PRIVATE_EVENTS+1)).fetchall()
        if len(binding_rows)>MAX_PRIVATE_EVENTS:
            raise ValueError("source_bindings_over_limit")
        bound=sum(1 for key,created in binding_rows
                  if key in selected_keys and witness._parse(created)<=now)
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
        main_prefix=prefix.verified_main_prefixes(
            db_main,pairs=accepted,as_of=witness._iso(now))
        private_prefix=prefix.verified_private_prefixes(
            db_cvd,events=seen,as_of=witness._iso(now))
        earlier_available=(main_prefix is not None and
                           private_prefix is not None)
        earlier_triples=0
        earlier_signals=0
        earlier_orientations=Counter()
        for sym,week,closed,observed_at,sha,cot_side in accepted:
            original=witness._parse(observed_at)
            closed_time=witness._parse(closed)
            matching=0
            earlier_matches=0
            for key,_,side,confirmed_at,detected_at in by_market[sym]:
                # Must have been confirmed on closed prices not later than
                # the original signal's last M15 close.
                detected=witness._parse(detected_at)
                if (witness._parse(confirmed_at)>closed_time
                        or not original-timedelta(minutes=90)<=detected<=original):
                    continue
                candidate=source.match(
                    db_cvd,event_key=key,original_price_sha=sha,
                    observed_at=observed_at,as_of=witness._iso(now),
                    secret=secret)
                orientation=("SAME_TECHNICAL_DIRECTION" if (
                    (side=="bullish" and cot_side==1) or
                    (side=="bearish" and cot_side==-1)
                ) else "OPPOSITE_TECHNICAL_DIRECTION")
                if candidate["state"]=="EXACT_LOCAL_SOURCE_AND_CHRONOLOGY":
                    matching+=1
                    orientations[orientation]+=1
                    continue
                # A changed full document is NOT evidence of a match.
                # An earlier-snapshot tier needs TWO immutable, prospectively
                # captured M15 session-prefix proofs with identical HMAC.
                # It never re-reads mutable OHLC or retrofits old CVD events.
                if not earlier_available:
                    continue
                prior=private_prefix.get(key)
                if prior is None:
                    continue
                cutoff,private_mac=prior
                if witness._parse(cutoff)>=closed_time:
                    continue  # same latest close, not earlier snapshot
                main_sha=main_prefix.get(
                    (sym,week,closed,observed_at,cutoff))
                if main_sha is None or not hmac.compare_digest(
                        private_mac,prefix._mac(secret,main_sha)):
                    continue
                earlier_matches+=1
                earlier_orientations[orientation]+=1
            if matching:
                distinct+=1
                triple_count+=matching
            if earlier_matches:
                earlier_signals+=1
                earlier_triples+=earlier_matches
        return _result(
            "EXACT_LOCAL_COT_PRICE_CVD_SOURCE_MATCHES_AUDITED_NOT_PREDICTIVE",
            validLocalCotPricePairs=len(accepted),
            privateCvdEvents=len(seen),
            sourceBoundCvdEvents=bound,
            oldOrUnboundCvdEvents=len(seen)-bound,
            exactSnapshotTriples=triple_count,
            distinctSignalsWithExactCVD=distinct,
            orientations=dict(sorted(orientations.items())),
            earlierSnapshotPrefixProofsAvailable=earlier_available,
            verifiedEarlierSnapshotTriples=(
                earlier_triples if earlier_available else None),
            distinctSignalsWithEarlierCVD=(
                earlier_signals if earlier_available else None),
            earlierSnapshotOrientations=(
                dict(sorted(earlier_orientations.items()))
                if earlier_available else None),
            verifiedTriplesAnyTier=(
                triple_count+earlier_triples if earlier_available else None),
            earlierTierIsSameEntireOHLCSource=False,
            earlierTierOnlyIdenticalUTCSessionM15Prefix=True,
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
