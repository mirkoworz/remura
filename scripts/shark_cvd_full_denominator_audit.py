"""Track B OFFLINE: full 34-market price denominator vs 2-market private CVD scans.

Read two INDEPENDENT SQLite snapshots, each already query_only=ON. Never
consume the real LIVE SQLite, fetch broker data, enable a recorder, or write a
research result. This is a prospective research COVERAGE witness only.

A zero-new-confirmation CVD scan is NOT a genuine negative cohort. Even a
matching HMAC is only a local statement about identical source bytes. No COT,
sentiment, independently timed fills, statistics, trading edge or ROI here.
"""
from __future__ import annotations

from collections import Counter
from datetime import timedelta
import hmac
import sqlite3

from scripts import shark_cot_asof_witness as witness
from scripts import shark_price_only_compact as compact
from scripts import shark_cvd_scan_coverage as scans
from scripts import shark_cvd_source_lineage as lineage
from scripts import shark_cvd_incremental_protocol as protocol

SCHEMA="remura-track-b-cvd-full-denominator-readiness-v1"
MAX_DAYS=7
MAX_BATCHES=7*96
MAX_CVD_ROWS=scans.MAX_ROWS
PRICE_TRIGGERS=("research_compact_no_update",
                "research_compact_no_delete")
START=witness._parse(protocol.START)


def _readable(db):
    if not isinstance(db,sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    if db.execute("PRAGMA query_only").fetchone()[0] != 1:
        raise ValueError("query_only_snapshot_required")


def _exists_and_protected(db,table,triggers):
    found=db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,)).fetchone()
    if not found:
        return False
    names={row[0] for row in db.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' "
        "AND tbl_name=?",(table,))}
    if not set(triggers).issubset(names):
        raise ValueError("missing_research_immutable_triggers")
    return True


def _result(status, counts=None, **extra):
    counts=Counter() if counts is None else counts
    return {
        "schema":SCHEMA,
        "status":status,
        "effectiveStudyStartUtc":protocol.START,
        "protocolSha256":protocol.FROZEN_PROTOCOL_SHA256,
        "expectedFullPriceUniverseMarkets":len(protocol.FROZEN_UNIVERSE),
        "existingCvdPilotMarkets":len(scans.PILOT),
        "existingCvdUnsupportedMarkets":
            len(set(protocol.FROZEN_UNIVERSE)-set(scans.PILOT)),
        "full34Batches":counts["batches"],
        "full34MarketCells":counts["cells"],
        "full34PriceReadyCells":counts["ready"],
        "full34PriceOtherOrUnknownCells":counts["priceUnknown"],
        "readyCellsOutsideExistingCvdPilot":counts["notCovered"],
        "pilotReadyCellsWithMissingScan":counts["missing"],
        "pilotReadyCellsWithLateOrFutureScan":counts["late"],
        "pilotReadyCellsWithUnusableScan":counts["unusable"],
        "pilotReadyCellsWithDifferentSource":counts["sourceMismatch"],
        "pilotReadyCellsWithSameDocumentLocalEvaluation":counts["matched"],
        "pilotMatchedZeroNewLocalConfirmations":counts["localZero"],
        "pilotMatchedNewTechnicalConfirmations":counts["localNew"],
        "genuineFull34CvdNegativeControlsAdmitted":0,
        "localZeroNewConfirmationIsCertifiedNoCvd":False,
        "localPositiveCountEstablishesDirectionalCvd":False,
        "localSourceHmacIsIndependentBrokerTimeProof":False,
        "independentCrossDatabaseAtomicCommit":False,
        "complete34MarketCvdCaptureEstablished":False,
        "cotRetailAsOfCausalJoinEstablished":False,
        "futureOutcomeAndActualTradingCostsEstablished":False,
        "newCollectorOrBrokerCalls":0,
        "writesPerformed":False,
        "canEnableCvdResearch":False,
        "tradeOrNotificationAuthorized":False,
        "profitabilityOrStatisticalEdgeEstablished":False,
        **extra,
    }


def audit(db_price,db_cvd,*,as_of,days=1,secret):
    """Compare ORIGINAL full price scan cells with matching original CVD scans.

    Full-batch payload digest, schema, the exact 34 symbols and local
    immutability guards must all verify. Only scans from the same ORIGINAL
    price document and observed at/before the price decision count as
    locally-evaluated *coverage*; no negative labels are ever admitted.

    Input should be read-only copies of research files, not open production
    DBs. Read-only snapshots are NOT a cross-DB atomic point in time.
    """
    if db_price is db_cvd:
        raise ValueError("independent_research_dbs_required")
    _readable(db_price)
    _readable(db_cvd)
    lineage._mac(secret,"0"*64)
    if (type(days) is not int or not 1<=days<=MAX_DAYS or
            protocol.protocol_sha256()!=protocol.FROZEN_PROTOCOL_SHA256):
        raise ValueError("invalid_study_protocol_or_window")
    now=witness._parse(as_of)
    if now < START:
        return _result("NOT_YET_IN_PROSPECTIVE_WINDOW")
    price_ok=_exists_and_protected(
        db_price,compact.TABLE,PRICE_TRIGGERS)
    cvd_ok=_exists_and_protected(db_cvd,scans.TABLE,scans.TRIGGERS)
    if not price_ok or not cvd_ok:
        return _result("RESEARCH_LEDGER_UNAVAILABLE",
                       priceLedgerPresent=price_ok,
                       privateCvdLedgerPresent=cvd_ok)

    # This is a bounded offline census, never a new periodic scanner.
    # Snapshot both databases so no writer can change one source DURING its
    # individual read. They are nonetheless independent (non-atomic).
    price_own=not db_price.in_transaction
    cvd_own=not db_cvd.in_transaction
    if price_own: db_price.execute("BEGIN")
    if cvd_own: db_cvd.execute("BEGIN")
    try:
        low=max(START,now-timedelta(days=days))
        batches=db_price.execute(
            f"SELECT scan_slot,scope_count,eligible_count,uncertain_count,"
            f"sealed_at,payload_sha256,payload_zlib,algorithm "
            f"FROM {compact.TABLE} WHERE scope=? AND scan_slot>=? "
            f"AND scan_slot<=? ORDER BY scan_slot LIMIT ?",
            (compact.FULL_SCOPE,witness._iso(low),witness._iso(now),
             MAX_BATCHES+1)).fetchall()
        if len(batches)>MAX_BATCHES:
            raise ValueError("price_batches_over_bound")
        scan_rows=db_cvd.execute(
            f"SELECT symbol,closed_at,attempted_at,state,source_hmac,"
            f"session_prefix_hmac,new_confirmations,reason,schema_version "
            f"FROM {scans.TABLE} WHERE closed_at>=? AND closed_at<=? "
            f"ORDER BY symbol,closed_at LIMIT ?",
            (witness._iso(low-timedelta(minutes=90)),
             witness._iso(now),MAX_CVD_ROWS+1)).fetchall()
        if len(scan_rows)>MAX_CVD_ROWS:
            raise ValueError("cvd_scans_over_bound")
        index={}
        for sym,close,seen,state,mac,prefix,count,reason,version in scan_rows:
            at=witness._parse(close)
            seen_at=witness._parse(seen)
            if (sym not in scans.PILOT or
                    version!=scans.SCHEMA or
                    witness._iso(at)!=close or witness._iso(seen_at)!=seen or
                    at.minute%15 or at.second or at.microsecond or
                    not at<=seen_at<=at+scans.GRACE or seen_at>now):
                raise ValueError("cvd_attempt_schema_or_clock_invalid")
            if state=="EVALUATED":
                if (reason!="DETECTOR_OK" or
                        type(count) is not int or count<0 or
                        type(mac) is not str or
                        not scans.HEX.fullmatch(mac) or
                        (prefix is not None and
                         (type(prefix) is not str or
                          not scans.HEX.fullmatch(prefix)))):
                    raise ValueError("cvd_evaluated_row_invalid")
            elif state=="NOT_EVALUABLE":
                if (count is not None or prefix is not None or
                        reason not in ("SOURCE_ABSENT","DATA_INVALID",
                                       "DATA_MISSING","DATA_STALE",
                                       "DATA_PARTIAL","DATA_INSUFFICIENT")):
                    raise ValueError("cvd_unknown_row_invalid")
            else:
                raise ValueError("unknown_cvd_attempt_state")
            if (sym,close) in index:
                raise ValueError("duplicated_cvd_attempt")
            index[(sym,close)]=(seen_at,state,mac,count)
        counts=Counter()
        for (slot,n,eligible,unknown,sealed,sha,payload,alg) in batches:
            # Verify payload and metadata in existing, tested compact code.
            proof=compact.verify(db_price,scan_slot=slot)
            if (proof["status"]!="ARCHIVE_VERIFIED" or
                    n!=len(protocol.FROZEN_UNIVERSE) or
                    alg!=compact.ALGORITHM or
                    proof["marketObservations"]!=n or
                    proof["eligibleCandidates"]!=eligible or
                    proof["unknownObservations"]!=unknown):
                raise ValueError("full_price_batch_metadata_mismatch")
            doc=compact._decode(payload,sha)
            at=witness._parse(slot)
            closed_at=witness._parse(sealed)
            if (witness._iso(at)!=slot or at<START or
                    not at<=closed_at<=at+timedelta(minutes=18) or
                    closed_at>now):
                raise ValueError("late_or_invalid_full_batch_seal")
            observations=doc["observations"]
            counts["batches"]+=1
            counts["cells"]+=n
            for item in observations:
                sym,_,observed,recorded,state,_,_,m15closed,*_=item
                if state!="PRICE_CONTEXT_READY":
                    counts["priceUnknown"]+=1
                    continue
                counts["ready"]+=1
                if sym not in scans.PILOT:
                    counts["notCovered"]+=1
                    continue
                # Last M15 closure as attested by the original price source.
                # A scan at a different closed M15 is not an exact match.
                key=(sym,m15closed)
                matched=index.get(key)
                if not matched:
                    counts["missing"]+=1
                    continue
                seen_at,status,mac,count=matched
                if seen_at>witness._parse(observed):
                    counts["late"]+=1
                elif status!="EVALUATED" or item[14]!=1:
                    counts["unusable"]+=1
                elif (not hmac.compare_digest(
                        lineage._mac(secret,item[13]),mac)):
                    counts["sourceMismatch"]+=1
                else:
                    counts["matched"]+=1
                    counts["localNew" if count>0 else "localZero"]+=1
        if counts["cells"]!=34*counts["batches"]:
            raise ValueError("bad_full_universe_denominator")
        if counts["ready"]+counts["priceUnknown"]!=counts["cells"]:
            raise ValueError("bad_ready_plus_unknown_balance")
        if (sum(counts[k] for k in
                ("notCovered","missing","late","unusable","sourceMismatch",
                 "matched"))!=counts["ready"]):
            raise ValueError("unbalanced_cvd_ready_cells")
        return _result("PILOT_CVD_COVERAGE_AUDITED_NOT_FULL_34_GO",counts,
                       evaluatedSourceProofIsLocalOnly=True,
                       fullPriceBatchesHaveOriginalHashVerified=True)
    finally:
        if price_own: db_price.rollback()
        if cvd_own: db_cvd.rollback()
