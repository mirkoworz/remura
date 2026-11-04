"""Track B: lossless, compact, prospective PRICE-ONLY scan-batch ledger.

OFFLINE RESEARCH ONLY. Nothing imports this from the LIVE private server.
A future opt-in adapter must first call shark_price_only_universe.prepare()
for every ACTUALLY scanned symbol, *without* a COT filter, then seal once
per observed UTC 15-min slot. Full scans require EXACTLY the 34 symbols.
Targeted scans have a distinct scope and NEVER enter the full denominator.

One compressed record stores all 34 original validated observations. This
avoids the old 50k *per-symbol* record bottleneck (~15.3 days) without any
deletion, synthetic backfill, unverified sampling or extra broker GET.
Each immutable zlib blob has a SHA256 over versioned canonical JSON. Hashes
are checks of local integrity, not independent signatures of market data.

Does NOT claim to offer operational archiving, cloud backup, measured Oracle
quotas, complete 15-minute broker observation or a proven trading edge.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
import sqlite3
import zlib

from scripts import shark_cot_asof_witness as witness
from scripts import shark_price_only_universe as price_only

TABLE = "research_price_only_batches"
SCHEMA = "remura-price-only-compact-batches-v1"
ALGORITHM = "scan-v162-unbiased-price-only-batch-v1"
MAX_BATCHES = 100_000
MAX_COMPRESSED_BYTES = 120_000
MAX_UNCOMPRESSED_BYTES = 50_000
MAX_SEAL_DELAY = timedelta(minutes=3)
FULL_SCOPE = "FULL_34"
ALLOWED_STATES = set(price_only.STATES) | {"PRICE_UNIVERSE_NOT_RECORDED"}
HEX = re.compile(r"^[a-f0-9]{64}$")


def ensure_schema(db):
    """Explicit opt-in only, NEVER on LIVE v1.62."""
    if not isinstance(db, sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    with db:
        db.execute(f"""CREATE TABLE IF NOT EXISTS {TABLE} (
            scan_slot TEXT NOT NULL,
            scope TEXT NOT NULL,
            scope_count INTEGER NOT NULL CHECK(scope_count BETWEEN 1 AND 34),
            eligible_count INTEGER NOT NULL CHECK(eligible_count BETWEEN 0 AND 34),
            uncertain_count INTEGER NOT NULL CHECK(uncertain_count BETWEEN 0 AND 34),
            sealed_at TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL,
            payload_zlib BLOB NOT NULL,
            algorithm TEXT NOT NULL,
            PRIMARY KEY(scan_slot, scope)
        ) WITHOUT ROWID""")
        for action in ("UPDATE", "DELETE"):
            db.execute(f"""CREATE TRIGGER IF NOT EXISTS research_compact_no_{action.lower()}
                BEFORE {action} ON {TABLE}
                BEGIN SELECT RAISE(ABORT, 'immutable_scan_batch'); END""")


def _slot(raw):
    dt = witness._parse(raw)
    if dt.second or dt.microsecond or dt.minute % 15:
        raise ValueError("scan_slot_not_15min")
    return witness._iso(dt)


def _validate_row(item, target_slot):
    if not isinstance(item, (list, tuple)) or len(item) != 16:
        raise ValueError("invalid_source_row")
    (symbol,slot,observed,recorded,state,integrity,freshness,closed,
     side,pstate,h1,h4,m15,digest,complete,algorithm) = item
    if (symbol not in price_only.prices_monitored()
            or _slot(slot) != target_slot
            or state not in ALLOWED_STATES
            or algorithm != price_only.ALGORITHM
            or integrity not in price_only.ALLOWED_QUALITY
            or freshness not in price_only.ALLOWED_FRESHNESS
            or type(complete) is not int or complete not in (0, 1)
            or any(type(x) is not int or x not in (-1, 0, 1)
                   for x in (side,h1,h4,m15))
            or pstate not in (None,"watch","partial","confirmed")
            or (digest is not None
                and (not isinstance(digest,str) or not HEX.fullmatch(digest)))):
        raise ValueError("invalid_price_only_evidence")
    observed_time=witness._parse(observed)
    sealed_time=witness._parse(recorded)
    if (not target_slot <= witness._iso(observed_time)
            or observed_time > witness._parse(target_slot)+timedelta(minutes=15)
            or not observed_time <= sealed_time
            or sealed_time-observed_time > timedelta(seconds=price_only.MAX_DELAY.total_seconds())):
        raise ValueError("observed_event_not_real_time")
    if closed is not None:
        candle_close=witness._parse(closed)
        if candle_close>observed_time or candle_close.minute%15 or candle_close.second:
            raise ValueError("unclosed_or_misaligned_bar")
    if state=="PRICE_CONTEXT_READY" and (digest is None or closed is None
                                            or not side or not h1 or not h4):
        raise ValueError("ready_candidate_has_no_price_proof")
    if state=="PRICE_UNIVERSE_NOT_RECORDED" and (digest is not None or
                                                complete or any((side,h1,h4,m15))):
        raise ValueError("failed_scan_has_fabricated_evidence")
    return list(item)


def missing_row(*, symbol, scan_at, clock=None):
    """Explicit unknown scan cell; NEVER use for an unobserved historical day.

    This is only for a current full scan when one symbol's LOCAL price
    observation failed validation. Thus a bad symbol still appears in the
    denominator, marked unknown rather than silently omitted.
    """
    if symbol not in price_only.prices_monitored():
        raise ValueError("not_monitored")
    at=witness._parse(scan_at)
    now=witness._clock(clock)
    if not at <= now <= at + price_only.MAX_DELAY:
        raise ValueError("historical_or_future_scan")
    slot=witness._iso(datetime.fromtimestamp(
        int(at.timestamp())//900*900,tz=timezone.utc))
    return (symbol,slot,witness._iso(at),witness._iso(now),
            "PRICE_UNIVERSE_NOT_RECORDED","missing","missing",None,
            0,None,0,0,0,None,0,price_only.ALGORITHM)


def _scope(symbols, *, full):
    if len(symbols)!=len(set(symbols)):
        raise ValueError("duplicate_market_in_batch")
    catalog=set(price_only.prices_monitored())
    if not symbols or any(s not in catalog for s in symbols):
        raise ValueError("unknown_market_or_empty_scan")
    if full:
        if set(symbols)!=catalog:
            raise ValueError("full_scan_must_contain_34_markets")
        return FULL_SCOPE
    if len(symbols)==len(catalog):
        raise ValueError("use_full_scope_for_34_symbols")
    digest=hashlib.sha256(
        ",".join(sorted(symbols)).encode()).hexdigest()[:20]
    return "TARGET_"+digest


def prepare_batch(rows, *, full, clock=None):
    """Pure sanitizer and compressor; no database mutation."""
    if not isinstance(rows,(list,tuple)) or not 1<=len(rows)<=34:
        raise ValueError("batch_size_invalid")
    now=witness._clock(clock)
    target=_slot(rows[0][1])
    normalized=[_validate_row(row,target) for row in rows]
    symbols=[row[0] for row in normalized]
    scope=_scope(symbols,full=full)
    if not witness._parse(target)<=now<=(
            witness._parse(target)+timedelta(minutes=15)+MAX_SEAL_DELAY):
        raise ValueError("batch_not_current")
    for row in normalized:
        when=witness._parse(row[2])
        if now<when or now-when>MAX_SEAL_DELAY:
            raise ValueError("batch_contains_stale_observations")
    ordered=sorted(normalized,key=lambda row:row[0])
    document={"schema":SCHEMA,"algorithm":ALGORITHM,
              "scanSlot":target,"scope":scope,"observations":ordered}
    raw=json.dumps(document,sort_keys=True,ensure_ascii=True,
                   separators=(",",":"),allow_nan=False).encode("utf-8")
    if len(raw)>MAX_UNCOMPRESSED_BYTES:
        raise ValueError("unbounded_json_batch")
    compressed=zlib.compress(raw,level=6)
    if len(compressed)>MAX_COMPRESSED_BYTES:
        raise ValueError("unbounded_compressed_batch")
    counts=Counter(row[4] for row in normalized)
    return {
        "slot":target,"scope":scope,"marketCount":len(ordered),
        "candidateCount":counts["PRICE_CONTEXT_READY"],
        "unknownCount":counts["PRICE_UNIVERSE_NOT_RECORDED"],
        "digest":hashlib.sha256(raw).hexdigest(),
        "compressed":compressed,"sealed":witness._iso(now),
        "counts":dict(sorted(counts.items())),
        "rawBytes":len(raw),"compressedBytes":len(compressed),
    }


def seal(db,rows,*,full,clock=None):
    """Atomically insert immutable compressed batch; never delete hot rows."""
    if not isinstance(db,sqlite3.Connection) or not db.in_transaction:
        raise ValueError("scan_transaction_required")
    prepared=prepare_batch(rows,full=full,clock=clock)
    existing=db.execute(
        f"SELECT payload_sha256 FROM {TABLE} "
        "WHERE scan_slot=? AND scope=?",
        (prepared["slot"],prepared["scope"])).fetchone()
    if existing:
        # Duplicate scanning may produce different timestamps. Original
        # snapshot wins, no overwrite or post-hoc content revision.
        return {"schema":SCHEMA,"status":"DUPLICATE_BATCH",
                "newBatches":0,"storedMarkets":0,
                "noCotFiltering":True,"brokerCalls":0,
                "edge":"NOT_ESTABLISHED"}
    if db.execute(f"SELECT count(*) FROM {TABLE}").fetchone()[0]>=MAX_BATCHES:
        raise ValueError("compact_batch_capacity_reached")
    db.execute(
        f"INSERT INTO {TABLE} "
        "(scan_slot,scope,scope_count,eligible_count,uncertain_count,sealed_at,"
        "payload_sha256,payload_zlib,algorithm) VALUES (?,?,?,?,?,?,?,?,?)",
        (prepared["slot"],prepared["scope"],prepared["marketCount"],
         prepared["candidateCount"],prepared["unknownCount"],
         prepared["sealed"],prepared["digest"],prepared["compressed"],ALGORITHM))
    return {
        "schema":SCHEMA,"status":"COMPACT_BATCH_SEALED",
        "newBatches":1,"storedMarkets":prepared["marketCount"],
        "eligiblePriceCandidates":prepared["candidateCount"],
        "unverifiableMarketObservations":prepared["unknownCount"],
        "compressedBytes":prepared["compressedBytes"],
        "uncompressedBytes":prepared["rawBytes"],
        "isFullMarketDenominator":full,
        "noCotFiltering":True,"brokerCalls":0,
        "edge":"NOT_ESTABLISHED","ordersEnabled":False,
        "alertsEnabled":False,
    }


def _decode(comp, sha):
    if not isinstance(comp,bytes) or len(comp)>MAX_COMPRESSED_BYTES:
        raise ValueError("invalid_compressed_payload")
    # Limit output while decompressing (zip bomb protection).
    decoder=zlib.decompressobj()
    raw=decoder.decompress(comp,MAX_UNCOMPRESSED_BYTES+1)
    if (len(raw)>MAX_UNCOMPRESSED_BYTES or not decoder.eof
            or decoder.unused_data or decoder.unconsumed_tail):
        raise ValueError("corrupt_or_oversize_archive")
    raw+=decoder.flush()
    if (len(raw)>MAX_UNCOMPRESSED_BYTES or
            hashlib.sha256(raw).hexdigest()!=sha):
        raise ValueError("archive_integrity_failed")
    try:
        return json.loads(raw)
    except (ValueError,UnicodeError) as e:
        raise ValueError("invalid_archived_json") from e


def verify(db, *, scan_slot, scope=FULL_SCOPE):
    """Read-only roundtrip verification: return aggregate counters only."""
    if not isinstance(db,sqlite3.Connection):
        raise ValueError("sqlite_required")
    row=db.execute(
        f"SELECT scope_count,eligible_count,uncertain_count,payload_sha256,"
        f"payload_zlib FROM {TABLE} WHERE scan_slot=? AND scope=?",
        (_slot(scan_slot),scope)).fetchone()
    if row is None:
        return {"schema":SCHEMA,"status":"NOT_RECORDED"}
    count,eligible,unknown,sha,compressed=row
    doc=_decode(compressed,sha)
    observed=doc.get("observations",[])
    validated=[_validate_row(x,_slot(scan_slot)) for x in observed]
    if (len(validated)!=count or doc.get("schema")!=SCHEMA
            or doc.get("algorithm")!=ALGORITHM
            or doc.get("scanSlot")!=_slot(scan_slot)
            or doc.get("scope")!=scope
            or len(set(x[0] for x in validated))!=len(validated)
            or (scope==FULL_SCOPE and
                set(x[0] for x in validated)!=set(price_only.prices_monitored()))
            or sum(x[4]=="PRICE_CONTEXT_READY" for x in validated)!=eligible
            or sum(x[4]=="PRICE_UNIVERSE_NOT_RECORDED" for x in validated)!=unknown):
        raise ValueError("archive_metadata_mismatch")
    return {"schema":SCHEMA,"status":"ARCHIVE_VERIFIED",
            "marketObservations":count,"eligibleCandidates":eligible,
            "unknownObservations":unknown,"retrospectiveBackfill":False,
            "brokerCalls":0,"edge":"NOT_ESTABLISHED"}


def summary(db):
    if not isinstance(db,sqlite3.Connection):
        raise ValueError("sqlite_required")
    result=db.execute(
        f"SELECT count(*),COALESCE(sum(scope_count),0),"
        f"COALESCE(sum(eligible_count),0),"
        f"COALESCE(sum(uncertain_count),0),"
        f"COALESCE(sum(length(payload_zlib)),0) FROM {TABLE}").fetchone()
    full=db.execute(
        f"SELECT count(*),COALESCE(sum(scope_count),0),"
        f"COALESCE(sum(eligible_count),0),"
        f"COALESCE(sum(uncertain_count),0) FROM {TABLE} WHERE scope=?",
        (FULL_SCOPE,)).fetchone()
    batches,observed,eligible,unknown,compressed=result
    remaining=max(0,MAX_BATCHES-batches)
    return {"schema":SCHEMA,"immutableBatches":batches,
            "totalMarketObservations":observed,
            "fullScanBatches":full[0],
            "fullScanDenominator":full[1],
            "fullScanPriceCandidates":full[2],
            "fullScanUnknowns":full[3],
            "targetedScansExcludedFromMainDenominator":batches-full[0],
            "compressedBytes":compressed,
            "remainingBatchCapacity":remaining,
            "theoreticalFullScanDaysAt15Min":round(remaining/96,2),
            "capacityExhausted":remaining==0,
            "losslessBatchVerificationRequired":True,
            "old50kRowCapBypassedWithoutDeletingRows":True,
            "newBrokerCalls":0,"profitabilityVerified":False,
            "storageBudgetCertifiedOnOracle":False}
