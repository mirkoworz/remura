"""REMURA v0.8.176 LAB — 18/11/2026, sessione successiva alle 18:16 CET.
Read-only calendar attribution of already collected aggregate receipts.
No raw rows, new D1 calls, directional radar, returns or fold outcome.
Receipt audit time is NOT the receipt clock of each underlying bar.
"""
from cvd_receipt_window_audit_v1 import aggregate_receipts,need,n,M5,MIN_CLOSE_MS
from cvd_oos_protocol_preview_v2 import FOLDS,clock,digest

def summarize(records,*,audit_ms):
    need(n(audit_ms,MIN_CLOSE_MS) and type(records) is list and len(records)<=32)
    validated=aggregate_receipts(records) if records else None
    need(all(item["observed_ms"]<=audit_ms for item in records))
    buckets={name:[] for name,_,_ in FOLDS}
    unallocated=[]
    for item in records:
        name=next((name for name,start,end in FOLDS
                   if clock(start)<=item["start_ms"]<=item["end_ms"]<clock(end)),None)
        if name is None:
            # Cannot split counts across folds without underlying rows.
            unallocated.append(item)
        else:
            buckets[name].append(item)
    def metrics(items):
        if not items:
            return dict(windows=0,requested_slots=0,valid_unique_bars=0,
                        missing_requested_slots=0,duplicate_rows=0,max_lag_ms=None,
                        collection_rows_read=0,collection_rows_written=0)
        a=aggregate_receipts(items)
        return {k:a[k] for k in ("windows","requested_slots","valid_unique_bars",
                "missing_requested_slots","duplicate_rows","max_lag_ms",
                "collection_rows_read","collection_rows_written")}
    result={}
    for name,start,end in FOLDS:
        a,b=clock(start),clock(end)
        items=buckets[name]
        values=metrics(items)
        result[name]=dict(values,start_utc=start,end_exclusive_utc=end,
             calendar_status="NOT_STARTED" if audit_ms<a else "IN_PROGRESS" if audit_ms<b else "CALENDAR_ENDED",
             receipt_evidence_status="SCOPED_RECEIPTS_ONLY" if items else "NO_RECEIPT_EVIDENCE",
             audit_windows_observed_after_fold_end=sum(x["observed_ms"]>=b for x in items),
             market_coverage_attested=False,per_bar_fold_receipt_clock_attested=False)
    other=metrics(unallocated)
    for k in ("windows","requested_slots","valid_unique_bars","missing_requested_slots","duplicate_rows","collection_rows_read","collection_rows_written"):
        need(sum(x[k] for x in result.values())+other[k]==(validated[k] if validated else 0))
    return {"schema":"remura.tv.cvd.receipt.fold.attribution.lab.v1",
            "protocol_sha256":digest(),"audit_ms":audit_ms,"folds":result,
            "unallocated_outside_or_crossing_fold":other,
            "scope":"EXISTING_DISJOINT_AGGREGATE_RECEIPT_WINDOWS_ONLY",
            "new_network_reads":0,"account_quota_utilization":None,
            "independent_provenance":False,"conflict_ledger_available":False,
            "independent_blinding_attested":False,"outcomes_computed":False,
            "scientific_admission":False,"orders_enabled":False,"notifications_enabled":False}
