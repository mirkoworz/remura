#!/usr/bin/env python3
# REMURA v0.8.80 LAB — 14/11/2026 18:30 CET
"""V2 archive: strict V1 validation; no overlapping interim scientific result."""
from cvd_archive_preview_v1 import validate_windows
from cvd_radar_preview_v1 import aggregate_radar
from cvd_outcome_readiness_v1 import summarize
from cvd_nonoverlap_preview_v2 import compare
from cvd_oos_protocol_preview_v2 import FOLDS,clock,evaluate_folds,digest

def assemble(windows,*,as_of_ms):
    valid,stats=validate_windows(windows,as_of_ms=as_of_ms)
    bounds=[(w["start_ms"],w["end_ms"]) for w in windows]
    # Arbitrary partial research windows may expose interim outcomes.
    # Suppress descriptive comparisons for any registered period, even after closure.
    research=any(a<clock(e) and b>=clock(s) for a,b in bounds for _,s,e in FOLDS)
    blocked={"status":"WITHHELD_REGISTERED_PERIOD","scientific_admission":False}
    return {"schema":"remura.tv.cvd.archive.aggregate.preview.v2","version":"0.8.80-lab",
            **stats,"scope":"EXPLICIT_WINDOWS_NOT_MARKET_CALENDAR",
            "provenance_attested":False,"conflict_ledger_available":False,
            "protocol_sha256":digest(),
            "radar":aggregate_radar(valid,as_of_ms=as_of_ms),
            "outcomes":dict(blocked) if research else summarize(valid,as_of_ms=as_of_ms),
            "nonoverlap_benchmark":dict(blocked) if research else compare(valid,as_of_ms=as_of_ms),
            "prospective_folds":evaluate_folds(valid,bounds,as_of_ms=as_of_ms),
            "scientific_admission":False,"orders_enabled":False}
