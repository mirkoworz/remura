"""Conservative logical bounds on CVD coverage missingness; research ONLY.

Wraps the immutable 09-Nov-2026 preregistration's admission function. This
module changes NONE of that protocol's thresholds, universe, dates or SHA.
It answers only how wide candidate-label prevalence can be when unobserved
CVD scans remain UNKNOWN. The bounds are NOT confidence intervals, predictive
probabilities, outcomes, effect sizes, or returns. Self-reported witness
metadata do not authenticate actual broker or CFTC source timestamps.

No broker/network/SQLite/VPS, files, credentials, notifications or trades.
"""
from __future__ import annotations

import json
import sys

from scripts import shark_cvd_incremental_protocol as protocol

SCHEMA = "remura-track-b-cvd-missingness-logical-bounds-v1"
LABELS = (
    ("aligned", "sameCohortCvdAlignedCandidates"),
    ("fullScanNegative", "sameCohortCvdFullScanNegativeCandidates"),
    ("invertedDirectionPlacebo", "sameCohortInvertedDirectionPlaceboCandidates"),
)


def audit(records, *, as_of, expected_protocol_sha256):
    """Return exact worst-case label shares on the SAME admitted core cohort.

    For a label with k observed candidates, u UNKNOWN labels and n admitted
    core observations, its possible share lies in [k/n, (k+u)/n].
    Endpoints for different labels cannot all occur simultaneously. This is
    a deterministic missing-data identification interval, not statistical
    uncertainty; no missing-at-random assumption is made.
    """
    data = protocol.assess(
        records, as_of=as_of,
        expected_protocol_sha256=expected_protocol_sha256,
    )
    n = data["rowsCoreAdmitted"]
    unknown = data["sameCohortCvdUnknownCoverage"]
    known = sum(data[field] for _, field in LABELS)
    if n != known + unknown:
        # Never quietly omit an unclassified cell from the denominator.
        raise ValueError("cvd_classification_denominator_mismatch")

    shares = {}
    for name, field in LABELS:
        count = data[field]
        shares[name] = {
            "observedCandidateCount": count,
            "lowerPct": round(100 * count / n, 2) if n else None,
            "upperPct": round(100 * (count + unknown) / n, 2) if n else None,
        }
    return {
        "schema": SCHEMA,
        "status": "LOGICAL_LABEL_BOUNDS_ONLY_NOT_TRADING_EVIDENCE",
        "protocolSha256": data["protocolSha256"],
        "prospectiveStartUtc": data["prospectiveStartUtc"],
        "rowsReceived": data["rowsReceived"],
        "coreAdmitted": n,
        "excluded": data["rowsExcluded"],
        "exclusionReasons": data["exclusionReasons"],
        "distinctCotReportDates": data["coreDistinctCotReportDates"],
        "cvdLabeledBySubmittedMetadata": known,
        "cvdUnknownCoverage": unknown,
        "labeledCoveragePct": round(100 * known / n, 2) if n else None,
        "logicalCandidateShareBoundsPct": shares,
        "boundsAreSimultaneouslyAttainable": False,
        "unknownTreatedAsNegative": False,
        "missingAtRandomAssumed": False,
        "independentSourceAttestation": False,
        "independentlyRecordedOutcomes": False,
        "profitabilityOrCausalEffectEstimated": False,
        "realInstitutionalAggressorVolumeObserved": False,
        "cvdResearchMayBeEnabled": False,
        "liveSignalsOrOrdersAuthorized": False,
        "brokerCallsMade": 0,
        "writesMade": False,
    }


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if args == ["--self-check"]:
        return protocol.main(["--self-check"])
    if args != ["--audit-stdin"]:
        print("usage: python -m scripts.shark_cvd_missingness_bounds "
              "--self-check|--audit-stdin")
        return 2
    try:
        raw = sys.stdin.buffer.read(protocol.MAX_STDIN_BYTES + 1)
        if not raw or len(raw) > protocol.MAX_STDIN_BYTES:
            raise ValueError("invalid_input_size")
        data = json.loads(raw)
        output = audit(
            data["records"], as_of=data["asOfUtc"],
            expected_protocol_sha256=data["protocolSha256"],
        )
    except (KeyError, TypeError, ValueError, UnicodeError, OverflowError):
        print("REMURA_CVD_MISSINGNESS=NO_GO_INVALID_INPUT")
        return 2
    print("REMURA_CVD_MISSINGNESS=" +
          json.dumps(output, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
