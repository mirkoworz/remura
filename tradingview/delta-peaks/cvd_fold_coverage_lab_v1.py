"""REMURA v0.8.175 LAB — 18/11/2026, sessione successiva alle 18:08 CET.
Coverage-only audit of the immutable V2 prospective calendar.
No outcomes, scores, selected directions, trading, network or persistence.
Counts concern explicit export windows, not expected market-open bars.
"""
from cvd_archive_preview_v1 import validate_windows
from cvd_oos_protocol_preview_v2 import FOLDS,clock,digest
from cvd_telemetry_preview_v1 import M5

def coverage(windows,*,as_of_ms,synthetic=False):
    if synthetic is not True:raise ValueError("FOLD_COVERAGE_LAB_ONLY")
    valid,stats=validate_windows(windows,as_of_ms=as_of_ms)
    folds={}
    # The two-minute maturity requirement comes from the existing receipt
    # validator. This is a reporting horizon, not an outcome maturity rule.
    last_mature=(as_of_ms-120000)//M5*M5
    for name,s,e in FOLDS:
        start,end=clock(s),clock(e)
        last=min(end-M5,last_mature)
        elapsed=max(0,(last-start)//M5+1)
        requested=sum(max(0,(min(last,w["end_ms"])-max(start,w["start_ms"]))//M5+1)
                      for w in windows)
        rows=[row for row,_,_ in valid if start<=row["bar_close_ms"]<=last]
        usable=sum(0<=row["received_at_ms"]-row["bar_close_ms"]<=120000
                   and row["received_at_ms"]<end for row in rows)
        received_after_end=sum(row["received_at_ms"]>=end for row in rows)
        if not 0<=usable<=len(rows)<=requested<=elapsed:
            raise ValueError("FOLD_COVERAGE_DENOMINATOR")
        folds[name]={"calendar_status":"NOT_STARTED" if as_of_ms<start else
                     "IN_PROGRESS" if as_of_ms<end else "CALENDAR_ENDED",
                     "start_utc":s,"end_exclusive_utc":e,
                     "elapsed_calendar_slots":elapsed,"requested_slots":requested,
                     "unrequested_calendar_slots":elapsed-requested,
                     "valid_unique_bars":len(rows),"missing_requested_slots":requested-len(rows),
                     "usable_receipt_clocks_within_fold":usable,
                     "receipts_after_fold_end":received_after_end,
                     "requested_elapsed_scope_complete":None if elapsed==0 else requested==elapsed}
    outside=len(valid)-sum(x["valid_unique_bars"] for x in folds.values())
    if outside<0:raise ValueError("FOLD_POPULATION")
    return {"schema":"remura.tv.cvd.fixed.fold.coverage.lab.v1","protocol_sha256":digest(),
            "folds":folds,"export_receipt_counts":stats,"outside_fold_unique_bars":outside,
            "scope":"EXPLICIT_WINDOWS_NOT_MARKET_CALENDAR","market_coverage_attested":False,
            "independent_blinding_attested":False,"outcomes_evaluated":False,
            "scientific_admission":False,"orders_enabled":False,"notifications_enabled":False}
