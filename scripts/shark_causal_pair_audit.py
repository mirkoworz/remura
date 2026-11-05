"""REMURA Track B — offline causal *local-proof* COT + OHLC join.

An immutable Squalincome COT-link is NOT sufficient just because a separate
price-evidence row has the same market/date. The ORIGINAL observed_at and M15
close must match exactly; each COT value-version must have its own immutable
witness at or before observation, the price source must have been verified in
the original observation transaction, and BOTH proof commits must be no later
than as_of. No current mutable cot_reports or prices are consulted.

This evaluates Squalincome signal-associated evidence only. The 34-market
price-only FULL scan denominator is independently audited in
shark_sample_admission; neither source is silently filtered by the other.

No scheduled action, production import, schema writes, CVD fabrication,
account/broker data, order, alert or statistical edge assertion.
"""
from __future__ import annotations

from collections import Counter
from datetime import timedelta
import hashlib
import json
import re
import sqlite3

from scripts import shark_cot_asof_witness as witness
from scripts import shark_signal_evidence as cot
from scripts import shark_price_asof_evidence as price
from scripts import shark_universe_lineage as universe

SCHEMA = "remura-track-b-causal-local-cot-price-join-v1"
HEX = re.compile(r"^[0-9a-f]{64}$")
MAX_DAYS = 7
MAX_ROWS = 5000
NEEDED = {
    cot.TABLE: ("research_squalincome_links_no_update",
                "research_squalincome_links_no_delete"),
    price.TABLE: ("research_price_asof_no_update",
                  "research_price_asof_no_delete"),
    witness.TABLE: ("research_cot_asof_no_update",
                    "research_cot_asof_no_delete"),
}
NO_OUTCOME = "NO_INDEPENDENT_FORWARD_OUTCOMES_COSTS_OR_OOS_PROOF"


def _result(status, **kwargs):
    return {
        "schema": SCHEMA,
        "status": status,
        "source": "authentic_prospective_signal_links_not_full_price_universe",
        "historicalCOTReportsReinterpreted": False,
        "priceDocumentReadFromCurrentCache": False,
        "cotValuesReadFromCurrentCache": False,
        "witnessIsLocalNotIndependentCFTCPublicationProof": True,
        "independentHistoricalBrokerCollectionTimeKnown": False,
        "originalSignalDirectionIndependentlyReproduced": False,
        "cvdProxyEventTimeCausallyJoined": False,
        "cvdAggressorVolumeMeasured": False,
        "realExecutionCostsAvailable": False,
        "independentOutOfSampleValidated": False,
        "institutionalPredictiveCohortsAdmissible": 0,
        "netTradingOutcomesAdmissible": 0,
        "edge": "NOT_ESTABLISHED",
        "institutionalEdgeGateReason": NO_OUTCOME,
        "brokerCalls": 0,
        "ordersEnabled": False,
        "notificationsEnabled": False,
        **kwargs,
    }


def _time(s):
    return witness._parse(s)


def _proof_valid(db, source, observed, *, market, report):
    """Validate digest, membership of known COT legs and pre-observation time."""
    try:
        versions = json.loads(source)
    except (ValueError, TypeError):
        raise ValueError("cot_version_blob_unreadable") from None
    if (not isinstance(source, str) or len(source)>1700
            or not isinstance(versions,list) or len(versions) not in (2,4)):
        raise ValueError("cot_version_set_unbounded")
    canonical=json.dumps(versions,sort_keys=True,separators=(",",":"))
    if canonical!=source:
        raise ValueError("cot_version_blob_not_canonical")
    spec=universe.contracts(market)
    if spec is None:
        raise ValueError("cot_symbol_not_mapped")
    _,legs=spec
    if len(versions)!=2*len(legs):
        raise ValueError("cot_legs_incomplete")
    weeks=set()
    proof_keys=set()
    for v in versions:
        if (not isinstance(v,dict)
                or set(v)!={"dataset","code","week","digest","witnessed"}):
            raise ValueError("cot_source_proof_invalid")
        ds,code,week,digest,seen=(v[k] for k in (
            "dataset","code","week","digest","witnessed"))
        if (not isinstance(ds,str) or not isinstance(code,str)
                or (ds,code) not in legs
                or not isinstance(week,str) or not isinstance(digest,str)
                or not HEX.fullmatch(digest)):
            raise ValueError("cot_leg_or_digest_invalid")
        instant=_time(seen)
        if instant>observed or not 0 <= (observed-instant).days <= 30:
            return False, "COT_VALUE_WITNESSED_AFTER_SIGNAL_OR_TOO_OLD"
        rows=db.execute(
            f"SELECT witnessed_at FROM {witness.TABLE} "
            "WHERE dataset=? AND code=? AND report_date=? "
            "AND value_digest=? AND evidence_kind='observed_local_values'",
            (ds,code,week,digest)).fetchall()
        if len(rows)!=1 or rows[0][0]!=seen:
            return False, "COT_VALUE_VERSION_WITNESS_NOT_MATCHED"
        weeks.add(week)
        key=(ds,code,week)
        if key in proof_keys:
            raise ValueError("duplicate_cot_proof_leg")
        proof_keys.add(key)
    if len(weeks)!=2 or report not in weeks:
        raise ValueError("cot_week_pair_invalid")
    prior=next(iter(weeks-{report}))
    current_date=_time(report+"T00:00:00Z").date()
    earlier=_time(prior+"T00:00:00Z").date()
    if not 6 <= (current_date-earlier).days <=10:
        raise ValueError("cot_prior_week_invalid")
    if (current_date>observed.date()
            or (observed.date()-current_date).days>cot.MAX_COT_AGE_DAYS):
        return False, "COT_WEEK_NOT_KNOWN_AT_OBSERVATION"
    if proof_keys != {(ds,code,week) for ds,code in legs for week in weeks}:
        raise ValueError("cot_leg_week_matrix_incomplete")
    return True, None


def audit(db, *, as_of, days=1):
    """Read-only bounded audit of already-recorded signal COT/price pairings.

    A co-occurring pair is counted only after verifying exact observation
    identity, real pre-observation COT digest witnesses and local OHLC proof.
    It is still NOT a verified institutional edge, executable trading cohort,
    or CVD divergence, irrespective of its population count.
    """
    if not isinstance(db,sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    if type(days) is not int or not 1<=days<=MAX_DAYS:
        raise ValueError("invalid_causal_audit_days")
    now=_time(as_of)
    since=now-timedelta(days=days)
    own=not db.in_transaction
    if own:
        db.execute("BEGIN")
    try:
        tables={name for (name,) in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        needed=set(NEEDED)
        if not needed.issubset(tables) or "squalincome_history" not in tables:
            return _result(
                "LOCAL_PROOF_TABLES_INCOMPLETE",
                observedCotLinks=None, observedPriceProofs=None,
                locallyJoinedCausalPairs=None, excludedLinks=None,
                exclusionReasons=None,
                missingTables=sorted((needed|{"squalincome_history"})-tables))
        for table,triggers in NEEDED.items():
            existing={name for (name,) in db.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='trigger' AND tbl_name=?", (table,))}
            if not set(triggers).issubset(existing):
                raise ValueError("local_proof_immutability_missing")
        # Legacy observed_at may end in 'Z' while prospective evidence
        # uses '.000000Z'. Lexical RFC3339 comparisons can silently exclude
        # an observation exactly at an as_of second. Filter on the UTC
        # calendar-second prefix, then enforce the precise time in Python.
        # Never promote a future fractional-second event.
        from_second=since.strftime("%Y-%m-%dT%H:%M:%S")
        until_second=now.strftime("%Y-%m-%dT%H:%M:%S")
        links=db.execute(
            f"SELECT symbol,cot_week,price_closed_at,observed_at,linked_at,"
            f"cot_side,price_state,source_version_evidence,evidence_digest,algorithm "
            f"FROM {cot.TABLE} WHERE substr(observed_at,1,19)>=? "
            "AND substr(observed_at,1,19)<=? "
            "ORDER BY observed_at,symbol LIMIT ?",
            (from_second,until_second,MAX_ROWS+1)).fetchall()
        price_rows=db.execute(
            f"SELECT symbol,report_date,price_time,observed_at,witnessed_at,"
            f"source_document_sha256,m15_closed_at,h1_closed_at,h4_closed_at,"
            f"last16_tick_volume_complete,algorithm "
            f"FROM {price.TABLE} WHERE substr(observed_at,1,19)>=? "
            "AND substr(observed_at,1,19)<=? "
            "ORDER BY observed_at,symbol LIMIT ?",
            (from_second,until_second,MAX_ROWS+1)).fetchall()
        if len(links)>MAX_ROWS or len(price_rows)>MAX_ROWS:
            raise ValueError("local_proof_rows_over_limit")
        links=[row for row in links if since<=_time(row[3])<=now]
        price_rows=[row for row in price_rows if since<=_time(row[3])<=now]
        prices={(p[0],p[1],p[2]):p for p in price_rows}
        if len(prices)!=len(price_rows):
            raise ValueError("duplicate_price_proof_key")
        used=set()
        counts=Counter()
        joint=0
        ready_with_tick=0
        for row in links:
            (sym,week,closed,observed_at,linked,side,pstate,
             source,digest,alg)=row
            if (alg!=cot.ALG or type(side) is not int or side not in (-1,1)
                    or pstate not in ("watch","partial","confirmed")
                    or not isinstance(source,str) or not isinstance(digest,str)
                    or not HEX.fullmatch(digest)
                    or hashlib.sha256(source.encode()).hexdigest()!=digest):
                raise ValueError("cot_link_digest_or_format_corrupt")
            obs=_time(observed_at)
            linking=_time(linked)
            closed_time=_time(closed)
            if (not obs<=linking<=obs+cot.MAX_OBSERVATION_DELAY
                    or closed_time>obs
                    or obs-closed_time>cot.MAX_CLOSE_DELAY):
                raise ValueError("cot_link_uncausal_clock")
            if linking>now:
                counts["COT_LINK_CREATED_AFTER_ASOF"]+=1
                continue
            p=prices.get((sym,week,closed))
            if p is None:
                counts["MISSING_MATCHING_PRICE_PROOF"]+=1
                continue
            used.add((sym,week,closed))
            (_,_,_,price_observed,price_witnessed,sha,
             m15,h1,h4,tick,price_algo)=p
            if price_algo!=price.ALGO or not isinstance(sha,str) or not HEX.fullmatch(sha):
                raise ValueError("price_source_sha_or_algorithm_invalid")
            pw=_time(price_witnessed)
            if (price_observed!=observed_at
                    or not obs<=pw<=obs+timedelta(seconds=price.MAX_LATENCY_SECONDS)):
                counts["PRICE_PROOF_NOT_SAME_OBSERVATION"]+=1
                continue
            if pw>now:
                counts["PRICE_PROOF_CREATED_AFTER_ASOF"]+=1
                continue
            if (_time(m15)!=closed_time or
                    not _time(h1)<=obs or not _time(h4)<=obs
                    or _time(h1)>_time(m15)+timedelta(hours=4)
                    or _time(h4)>_time(m15)+timedelta(hours=4)):
                raise ValueError("unclosed_or_inconsistent_price_proof")
            original=db.execute(
                "SELECT state,cot_side,price_state "
                "FROM squalincome_history WHERE symbol=? AND report_date=? "
                "AND price_time=? AND observed_at=?",
                (sym,week,closed,observed_at)).fetchall()
            if len(original)!=1:
                counts["ORIGINAL_SIGNAL_ROW_MISSING_OR_DUPLICATED"]+=1
                continue
            if (original[0][1]!=side or original[0][2]!=pstate
                    or original[0][0] not in ("aligned","divergent")):
                counts["ORIGINAL_SIGNAL_MISMATCH"]+=1
                continue
            valid,reason=_proof_valid(
                db,source,obs,market=sym,report=week)
            if not valid:
                counts[reason]+=1
                continue
            if type(tick) is not int or tick not in (0,1):
                raise ValueError("tick_volume_state_invalid")
            joint+=1
            if tick==1:
                ready_with_tick+=1
        unpaired=sum(1 for key in prices if key not in used)
        # Integrity and identity of untouched PRICE-only rows do not
        # authorize a COT conclusion. They remain a distinct denominator.
        total=len(links)
        if joint+sum(counts.values())!=total:
            raise ValueError("nonconserving_cot_link_denominator")
        return _result(
            "LOCAL_COT_AND_OHLC_PAIRING_AUDITED_NOT_PREDICTIVE",
            observedCotLinks=total,observedPriceProofs=len(price_rows),
            locallyJoinedCausalPairs=joint,
            locallyJoinedPairsWithCompleteTickVolume=ready_with_tick,
            priceProofsWithoutUsableCotLink=unpaired,
            excludedLinks=total-joint,
            exclusionReasons=dict(sorted(counts.items())),
            missingTables=[],
            lastAuditedAt=witness._iso(now),
            signalCohortsDistinctFrom34MarketPriceDenominator=True,
            localCOTVersionsPresentBeforeObservation=True,
            priceSourceDigestCapturedAtObservation=True,
        )
    finally:
        if own:
            db.rollback()
