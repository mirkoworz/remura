#!/usr/bin/env python3
"""Track B: frozen, future-only pre-registration gate for CVD incremental claims.

This is an OFFLINE metadata audit, NOT a CVD detector, a real data extractor,
or a backtest. It refuses to turn unavailable/partial CVD evidence into a
"no divergence" control or to count future-confirmed pivots as earlier signals.
All metadata are USER-SUPPLIED and NOT independently authenticated here.

Only newly observed evidence after the frozen protocol date may enter.
No broker calls, SQLite access, trading orders, network, disk writes, or
notification side effects. No effect size, profitability, or probability is
ever estimated by this module.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import re
import sys

SCHEMA = "remura-track-b-cvd-incremental-preregistration-v1"
INPUT_SCHEMA = "remura-track-b-prospective-cvd-coverage-v1"
CVD_VERSION = "cvd-divergence-proxy-m15-v1"
START = "2026-11-09T00:00:00Z"
MAX_RECORDS = 10000
MAX_STDIN_BYTES = 2 * 1024 * 1024
STEP = timedelta(minutes=15)
MAX_RETAIL_AGE = timedelta(hours=3)
MAX_PRICE_AGE = timedelta(minutes=90)
MAX_CVD_AGE = timedelta(minutes=90)

# Frozen catalog from the existing 34-market Squalincome universe, NOT every
# valid-looking ticker. Market list can only change in a new pre-registered
# version; never select profitable instruments after seeing their outcomes.
FX_MARKETS = (
    "EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDJPY", "USDCAD", "USDCHF",
    "EURGBP", "EURJPY", "EURCHF", "EURCAD", "EURAUD", "EURNZD",
    "GBPJPY", "GBPCHF", "GBPCAD", "GBPAUD", "GBPNZD",
    "AUDJPY", "AUDCAD", "AUDCHF", "AUDNZD",
    "NZDJPY", "NZDCAD", "NZDCHF", "CADJPY", "CADCHF", "CHFJPY",
)
FX_CODES = {
    "EUR":"099741", "GBP":"096742", "JPY":"097741",
    "AUD":"232741", "CAD":"090741", "CHF":"092741",
    "NZD":"112741",
}
DIRECT_COT = {
    "XAUUSD":("disagg","088691"), "XAGUSD":("disagg","084691"),
    "USOIL":("disagg","067651"), "US500":("tff","13874A"),
    "NAS100":("tff","209742"), "US30":("tff","124603"),
}
FROZEN_UNIVERSE = tuple(sorted((*FX_MARKETS, *DIRECT_COT)))

# Fixed protocol is deliberately selected WITHOUT access to future outcomes.
# No parameter search, model tuning or mutable threshold optimisation is
# permitted under this protocol. Editing any field changes the SHA256.
PROTOCOL = {
    "schema": SCHEMA,
    "effectiveStartUtc": START,
    "study": "CVD proxy incremental value for pre-observed price+COT+retail candidates",
    "universe": "PREDECLARED_34_MARKET_SQUALINCOME_PRICE_ONLY_UNIVERSE",
    "approvedMarkets": list(FROZEN_UNIVERSE),
    "fxCftcLegCodes": dict(sorted(FX_CODES.items())),
    "directCftcContracts": {
        key: list(value) for key,value in sorted(DIRECT_COT.items())
    },
    "dataOrder": "immutable observations, point-in-time COT witness, closed cTrader M15, retail first-seen, prospectively complete CVD scan",
    "branches": [
        "CORE_PRICE_COT_RETAIL_ALL",
        "SAME_CORE_CVD_CONFIRMED_DIRECTION",
        "SAME_CORE_CVD_FULL_SCAN_NEGATIVE",
        "PLACEBO_INVERTED_CVD_DIRECTION",
    ],
    "cvdMeaning": "CLV_X_TICK_VOLUME_PROXY_NOT_AGGRESSOR_FLOW",
    "control": "full prospective CVD scan only; missing/partial coverage UNKNOWN",
    "outcomeHorizonsHours": [1, 4, 24],
    "entry": "first_next_executable_M15_open_after_observation",
    "stopAtr": 1.0,
    "targetAtr": 1.5,
    "purgeEmbargoM15": 8,
    "costModel": "per-symbol observed or explicit nonzero assumptions: spread + two-way slippage + roundtrip commissions",
    "minimumDescriptiveEpisodes": 30,
    "minimumDistinctCotWeeks": 8,
    "negativeControlNotProof": True,
    "independentProspectiveOutcomeEvidenceRequired": True,
    "noRetrospectiveCvdConfirmation": True,
    "tradingAuthorization": False,
}

# Frozen BEFORE any observations under this future-only study. Any change to
# the plan requires a consciously revised fingerprint and new protocol version.
FROZEN_PROTOCOL_SHA256 = "09d833dafdd426254bc8fedccc367e41fa451ac8f2e6c99a9dac27f7387e2905"


def protocol_bytes():
    return json.dumps(PROTOCOL,sort_keys=True,separators=(",",":"),
                      ensure_ascii=True).encode("ascii")


def protocol_sha256():
    return hashlib.sha256(protocol_bytes()).hexdigest()


def _time(s):
    if type(s) is not str or len(s) != 20 or not s.endswith("Z"):
        raise ValueError("invalid_utc")
    try:
        t = datetime.strptime(s,"%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc)
    except ValueError:
        raise ValueError("invalid_utc") from None
    return t


def _hex(value):
    return type(value) is str and re.fullmatch("[0-9a-f]{64}",value) is not None


def expected_cot_legs(symbol):
    """Frozen CFTC contracts: FX crosses need TWO independently seen legs."""
    if symbol in DIRECT_COT:
        return (DIRECT_COT[symbol],)
    if symbol not in FX_MARKETS:
        raise ValueError("symbol_outside_frozen_universe")
    return tuple(sorted(("tff",FX_CODES[ccy]) for ccy in
                        (symbol[:3],symbol[3:]) if ccy != "USD"))


def _raw_core(row, start, now):
    if type(row) is not dict or row.get("schema") != INPUT_SCHEMA:
        return None,"invalid_schema"
    if (type(row.get("symbol")) is not str or
            row["symbol"] not in FROZEN_UNIVERSE):
        return None,"outside_frozen_34_market_universe"
    if type(row.get("direction")) is not int or row["direction"] not in (-1,1):
        return None,"invalid_direction"
    try:
        observed=_time(row.get("observedAtUtc"))
        first=_time(row.get("firstRecordedAtUtc"))
        cot=_time(row.get("cotFirstSeenAtUtc"))
        price=_time(row.get("priceWitnessAtUtc"))
        closed=_time(row.get("m15ClosedAtUtc"))
        retail=_time(row.get("retailFirstSeenAtUtc"))
    except ValueError:
        return None,"invalid_source_clock"
    if observed < start or first < start or first > observed or observed > now:
        return None,"not_prospectively_recorded"
    if not (cot <= observed and
            price <= observed and
            retail <= observed and
            closed <= price and closed <= observed):
        return None,"future_core_source"
    if (observed - retail > MAX_RETAIL_AGE or
            observed - price > MAX_PRICE_AGE or
            closed.minute % 15 or closed.second or closed.microsecond):
        return None,"stale_or_unclosed_price_or_retail"
    if (row.get("cotFirstSeenVerified") is not True or
            row.get("priceQualityVerified") is not True or
            row.get("retailQualityVerified") is not True or
            row.get("provider") != "ctrader" or
            row.get("priceFrame") != "M15" or
            row.get("cotDataset") not in ("tff","disagg")):
        return None,"invalid_core_lineage"
    # Report date must be explicitly identified, not inferred from a
    # convenient pivot or guessed from a UTC date.
    report=row.get("cotReportDate")
    if type(report) is not str or not re.fullmatch(r"\d{4}-\d{2}-\d{2}",report):
        return None,"invalid_cot_report_date"
    try:
        from datetime import date
        report_date=date.fromisoformat(report)
    except ValueError:
        return None,"invalid_cot_report_date"
    if report_date > observed.date() or observed.date()-report_date > timedelta(days=21):
        return None,"cot_report_date_not_asof"
    # A COT document cannot genuinely have first been seen before the
    # Tuesday report date it describes. Prevent an invented pre-report
    # timestamp from providing fake early access to institutional data.
    if cot.date() < report_date:
        return None,"cot_first_seen_predates_report"
    # An FX cross such as EURGBP requires BOTH EUR and GBP CFTC legs to be
    # known at this decision. A single EUR witness cannot authorize the
    # full cross-market institutional hypothesis.
    expected=expected_cot_legs(row["symbol"])
    if row["cotDataset"] != expected[0][0]:
        return None,"wrong_cftc_dataset_for_market"
    legs=row.get("cotMappedLegWitnesses")
    if type(legs) is not list or len(legs) != len(expected):
        return None,"cot_legs_incomplete_or_unmapped"
    mapped=[]
    timestamps=[]
    for leg in legs:
        if (type(leg) is not dict or
                type(leg.get("dataset")) is not str or
                type(leg.get("code")) is not str or
                type(leg.get("reportDate")) is not str or
                leg["reportDate"] != report):
            return None,"cot_legs_incomplete_or_unmapped"
        try:
            when=_time(leg.get("firstSeenAtUtc"))
        except ValueError:
            return None,"cot_leg_first_seen_invalid"
        if when > observed or when.date() < report_date:
            return None,"cot_leg_not_known_asof"
        mapped.append((leg["dataset"],leg["code"]))
        timestamps.append(when)
    if sorted(mapped) != sorted(expected):
        return None,"cot_legs_incomplete_or_unmapped"
    if max(timestamps) != cot:
        return None,"cot_latest_leg_time_mismatch"
    return (observed,report),None


def _cvd_label(row,observed):
    """Full scan absence requires original prospective scan evidence.

    Even accepted witness fields are merely self-reported metadata.
    Uncertified absence stays UNKNOWN and must never become a negative.
    """
    coverage=row.get("cvdScanCoverage")
    if coverage not in ("FULL_PROSPECTIVE","PARTIAL","UNKNOWN"):
        return "UNKNOWN"
    if coverage != "FULL_PROSPECTIVE":
        return "UNKNOWN"
    try:
        witnessed=_time(row.get("cvdScanWitnessAtUtc"))
    except ValueError:
        return "UNKNOWN"
    if (witnessed < _time(START) or
            witnessed > observed or observed-witnessed > MAX_CVD_AGE or
            row.get("cvdAlgorithm") != CVD_VERSION or
            row.get("cvdQualityVerified") is not True or
            row.get("cvdOriginalClosedBarsVerified") is not True or
            not _hex(row.get("cvdSourceWitnessSha256")) or
            row.get("cvdFullMarketUniverseAtObservation") is not True):
        return "UNKNOWN"
    result=row.get("cvdResult")
    if result == "NO_CONFIRMED_DIVERGENCE":
        # This is ONLY an internally qualifying NEGATIVE CONTROL
        # CANDIDATE. It is not independent proof of complete coverage.
        return "NEGATIVE_CANDIDATE"
    if result not in ("BULLISH_CONFIRMED","BEARISH_CONFIRMED"):
        return "UNKNOWN"
    try:
        confirmed=_time(row.get("cvdConfirmedAtUtc"))
    except ValueError:
        return "UNKNOWN"
    if confirmed < _time(START) or confirmed > witnessed or confirmed > observed:
        return "UNKNOWN"
    aligned=(result == "BULLISH_CONFIRMED" and row["direction"] == 1
             or result == "BEARISH_CONFIRMED" and row["direction"] == -1)
    return "ALIGNED_CANDIDATE" if aligned else "INVERTED_PLACEBO_CANDIDATE"


def assess(records, *, as_of, expected_protocol_sha256):
    """Check forward-only collection coverage, never report trade quality."""
    now=_time(as_of)
    start=_time(START)
    if (protocol_sha256() != FROZEN_PROTOCOL_SHA256 or
            expected_protocol_sha256 != FROZEN_PROTOCOL_SHA256):
        raise ValueError("research_protocol_digest_changed")
    if type(records) is not list or len(records) > MAX_RECORDS:
        raise ValueError("invalid_records")
    excluded=Counter()
    eligible=Counter()
    dates=set()
    cot_weeks=set()
    parsed=[]
    duplicate_keys=Counter()
    for row in records:
        core,why=_raw_core(row,start,now)
        if why:
            excluded[why]+=1
            continue
        observed,report=core
        # ALL rows at a duplicated (market, decision) are quarantined.
        # Otherwise order of input could select whichever CVD result looks
        # more favourable and manufacture a positive/negative control.
        key=(row["symbol"],observed)
        duplicate_keys[key]+=1
        parsed.append((row,observed,report,key))
    for row,observed,report,key in parsed:
        if duplicate_keys[key] != 1:
            excluded["ambiguous_duplicate_observation"]+=1
            continue
        dates.add(observed.date().isoformat())
        cot_weeks.add(report)
        eligible["coreCandidates"]+=1
        label=_cvd_label(row,observed)
        eligible[label]+=1
    return {
        "schema":SCHEMA,
        "status":"PROSPECTIVE_COVERAGE_ONLY_NOT_OUTCOME_EVIDENCE",
        "protocolSha256":protocol_sha256(),
        "prospectiveStartUtc":START,
        "rowsReceived":len(records),
        "rowsCoreAdmitted":eligible["coreCandidates"],
        "rowsExcluded":sum(excluded.values()),
        "exclusionReasons":dict(sorted(excluded.items())),
        "coreDistinctCotReportDates":len(cot_weeks),
        "coreDistinctObservationDates":len(dates),
        "sameCohortCvdAlignedCandidates":eligible["ALIGNED_CANDIDATE"],
        "sameCohortCvdFullScanNegativeCandidates":eligible["NEGATIVE_CANDIDATE"],
        "sameCohortInvertedDirectionPlaceboCandidates":
            eligible["INVERTED_PLACEBO_CANDIDATE"],
        "sameCohortCvdUnknownCoverage":eligible["UNKNOWN"],
        "unobservedCvdNeverTreatedAsNegative":True,
        "eligibleCvdScanProvenanceVerifiedIndependently":False,
        "cotOriginalFirstSeenVerifiedIndependently":False,
        "priceSourceIntegrityVerifiedIndependently":False,
        "sourceTimestampsAreOperatorSuppliedMetadata":True,
        "independentlyRecordedOutcomes":False,
        "costsAndSlippageMeasured":False,
        "causalIncrementalCvdEffectEstimated":False,
        "profitProbabilityEstimated":False,
        "liveSignalsOrOrdersAuthorized":False,
        "cvdResearchMayBeEnabled":False,
        "brokerCallsMade":0,
        "writesMade":False,
    }


def main(argv=None):
    args=sys.argv[1:] if argv is None else argv
    if args==["--self-check"]:
        if protocol_sha256() != FROZEN_PROTOCOL_SHA256:
            print("REMURA_CVD_PREREGISTRATION=NO_GO_FROZEN_PROTOCOL_CHANGED")
            return 2
        print("REMURA_CVD_PREREGISTRATION="+FROZEN_PROTOCOL_SHA256)
        return 0
    if args!=["--audit-stdin"]:
        print("usage: python -B scripts/shark_cvd_incremental_protocol.py --self-check|--audit-stdin")
        return 2
    try:
        raw=sys.stdin.buffer.read(MAX_STDIN_BYTES+1)
        if not raw or len(raw)>MAX_STDIN_BYTES:
            raise ValueError("bad_input_size")
        data=json.loads(raw)
        result=assess(data["records"],as_of=data["asOfUtc"],
                      expected_protocol_sha256=data["protocolSha256"])
    except (KeyError,TypeError,ValueError,UnicodeError,OverflowError):
        print("REMURA_CVD_PREREGISTRATION=NO_GO_INVALID_INPUT")
        return 2
    print("REMURA_CVD_PREREGISTRATION="+json.dumps(
        result,sort_keys=True,separators=(",",":")))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
