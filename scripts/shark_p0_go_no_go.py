"""Track B P0: STRICTLY OFFLINE evidence gate for a future supervised pilot.

No GitHub, Oracle, Firebase, cTrader or tailnet calls. Receives only
sanitized aggregate evidence supplied after a user has VERIFIED the
account consoles and a controlled live-overlap experiment. This module
cannot verify provenance of those assertions; even if all pass it NEVER
permits release, deploy, or enabling live research automatically.

A successful synthetic Oracle staging or green CI is not an observed
overlap with real ingestion, just as a documented free tier is not an
actual bill. Missing / stale / nonnumeric evidence is a hard BLOCK.
"""
from __future__ import annotations

from datetime import timedelta
import math

from scripts import shark_cot_asof_witness as witness

SCHEMA = "remura-track-b-supervised-pilot-evidence-gate-v1"
FRESH = timedelta(hours=24)
MAX_BILL_AGE = timedelta(days=3)
REQUIRED_MARKETS = 34
MIN_SAMPLES = 64
MIN_PAIRED_OVERLAPS = 8
# Conservative internal screening, NOT official vendor guarantees.
MAX_UTIL = 70.0
MAX_QUOTA_FRACTION = 0.8
MAX_LATENCY_INCREASE = 1.20
FIRESTORE_STANDARD = {
    "readsDaily": 50000,
    "writesDaily": 20000,
    "storedBytes": 1024**3,
    "outboundBytesMonthly": 10 * 1024**3,
}


def _number(value, *, low=0, upper=None, integer=False):
    if type(value) not in ((int,) if integer else (int,float)):
        return False
    if not math.isfinite(value) or value<low:
        return False
    return upper is None or value<=upper


def _fresh(timestamp, as_of, maximum):
    try:
        when=witness._parse(timestamp)
    except (ValueError,TypeError,AttributeError):
        return False
    return timedelta(0)<=as_of-when<=maximum


def _positive_rate(numer,denom,threshold):
    return (_number(numer) and _number(denom,low=1)
            and numer/denom<=threshold)


def evaluate(evidence, *, as_of):
    """NO_GO by default. Does not write, enable, approve or launch anything.

    Accepts metadata only, no screenshots/tokens or full endpoint output.
    A 'PRECHECK_REVIEW_ONLY' result means an OPERATOR must still review the
    independently collected evidence before any deployment decision.
    """
    now=witness._parse(as_of)
    doc=evidence if isinstance(evidence,dict) else {}
    diag=doc.get("liveDiagnostic")
    pilot=doc.get("controlledLiveOverlap")
    costs=doc.get("accountConsoleUsage")
    diag=diag if isinstance(diag,dict) else {}
    pilot=pilot if isinstance(pilot,dict) else {}
    costs=costs if isinstance(costs,dict) else {}
    blockers=[]

    if not _fresh(diag.get("observedAt"),now,FRESH):
        blockers.append("LIVE_DIAGNOSTIC_ABSENT_OR_STALE")
    if (diag.get("marketCount")!=REQUIRED_MARKETS
            or any(not _number(diag.get(k),integer=True) or diag[k]!=0
                   for k in ("m15Stale","h1Stale","h4Stale"))):
        blockers.append("TIMEFRAME_COVERAGE_NOT_34_OF_34_FRESH")
    if (not _number(diag.get("collectorBatches"),low=MIN_SAMPLES,
                    integer=True)
            or diag.get("collectorBatchFailures")!=0
            or not _number(diag.get("squalincomeScans"),low=MIN_SAMPLES,
                           integer=True)
            or diag.get("squalincomeFailures")!=0):
        blockers.append("BASELINE_COLLECTOR_AND_SQUALINCOME_NOT_CERTIFIED")
    if (diag.get("researchOffOnLive") is not True
            or not isinstance(diag.get("liveVersion"),str)
            or not diag.get("liveVersion").strip()):
        blockers.append("LIVE_FLAG_OR_VERSION_UNKNOWN")
    if (not _number(diag.get("ramUsedPercent"),upper=MAX_UTIL)
            or not _number(diag.get("diskUsedPercent"),upper=MAX_UTIL)):
        blockers.append("VPS_RESOURCE_HEADROOM_NOT_CERTIFIED")

    if (pilot.get("observedUnderRealIngest") is not True
            or not _fresh(pilot.get("measuredAt"),now,FRESH)
            or not _number(pilot.get("independentOverlapWindows"),
                           low=MIN_PAIRED_OVERLAPS,integer=True)
            or pilot.get("newBrokerCalls")!=0
            or pilot.get("scannerBusyErrors")!=0):
        blockers.append("REAL_INGEST_OVERLAP_UNMEASURED_OR_UNSAFE")
    if (not _number(pilot.get("baselinePostIngestMedianMs"),low=1)
            or not _positive_rate(
                pilot.get("pilotPostIngestMedianMs"),
                pilot.get("baselinePostIngestMedianMs"),
                MAX_LATENCY_INCREASE)):
        blockers.append("POST_INGEST_LATENCY_REGRESSION_UNVERIFIED")
    if pilot.get("unmodifiedPriceCollectionCadence") is not True:
        blockers.append("COLLECTOR_CADENCE_PRESERVATION_UNVERIFIED")

    if not _fresh(costs.get("checkedAt"),now,MAX_BILL_AGE):
        blockers.append("ACCOUNT_CONSOLE_EVIDENCE_MISSING_OR_STALE")
    oracle=costs.get("oracle")
    oracle=oracle if isinstance(oracle,dict) else {}
    if (oracle.get("alwaysFreeEligibleResourcesConfirmed") is not True
            or not _number(oracle.get("actualMonthlyCharges"),upper=0)):
        blockers.append("ORACLE_ACCOUNT_BILL_OR_ELIGIBILITY_UNKNOWN")
    github=costs.get("githubPrivateActions")
    github=github if isinstance(github,dict) else {}
    if (not _number(github.get("minutesUsed"),integer=True)
            or not _number(github.get("minutesIncluded"),low=1,integer=True)
            or not _positive_rate(github.get("minutesUsed"),
                                  github.get("minutesIncluded"),
                                  MAX_QUOTA_FRACTION)
            or not _number(github.get("actualCharges"),upper=0)):
        blockers.append("GITHUB_PRIVATE_BILLED_MINUTES_OR_COST_UNKNOWN")
    firestore=costs.get("firestoreStandard")
    firestore=firestore if isinstance(firestore,dict) else {}
    if (firestore.get("onlyFreeEligibleDatabase") is not True
            or firestore.get("billingCharge")!=0
            or any(not _number(firestore.get(metric),integer=True,
                               upper=int(quota*MAX_QUOTA_FRACTION))
                   for metric,quota in FIRESTORE_STANDARD.items())):
        blockers.append("FIRESTORE_READ_WRITE_STORAGE_OR_EGRESS_UNKNOWN")

    return {
        "schema":SCHEMA,
        "status":"NO_GO" if blockers else "PRECHECK_REVIEW_ONLY",
        "unresolvedChecks":sorted(blockers),
        "screeningLimitsAreOfficialProviderQuotes":False,
        "accountMetricsVerifiedIndependentlyByThisCode":False,
        "realIngestOverlapValidatedByThisCode":False,
        "liveResearchAutomaticallyEnabled":False,
        "releaseOrDeploymentAuthorized":False,
        "dataSource":"OPERATOR_VERIFIED_SANITIZED_METADATA_REQUIRED",
        "additionalBrokerCalls":0,
        "ordersEnabled":False,
        "tradingEdgeEstablished":False,
    }
