"""REMURA v0.8.177 LAB — 18/11/2026, sessione successiva alle 18:24 CET.
Validate an explicitly chosen receipt-only window against existing evidence.
No selection by signals, no query, schedule, automatic retry or dispatch.
Calendar scope is not evidence of market hours or actual collection.
"""
from cvd_receipt_window_audit_v1 import aggregate_receipts,need,n,M5,MIN_CLOSE_MS
from cvd_oos_protocol_preview_v2 import FOLDS,clock,digest
from datetime import datetime,timezone

def utc_minute(ms):
    return datetime.fromtimestamp(ms//1000,tz=timezone.utc).strftime("%Y-%m-%dT%H:%MZ")

def preview(records,*,start_ms,end_ms,audit_ms):
    need(all(n(t,MIN_CLOSE_MS,4102444800000) for t in (start_ms,end_ms,audit_ms)))
    need(start_ms%M5==end_ms%M5==0 and start_ms<=end_ms
         and end_ms+120000<=audit_ms and (end_ms-start_ms)//M5+1<=12)
    need(type(records) is list and len(records)<=32)
    if records:aggregate_receipts(records)
    need(all(r["observed_ms"]<=audit_ms for r in records))
    need(all(end_ms<r["start_ms"] or start_ms>r["end_ms"] for r in records))
    folds=[name for name,s,e in FOLDS if clock(s)<=start_ms<=end_ms<clock(e)]
    need(len(folds)==1)
    return {"schema":"remura.tv.cvd.receipt.request.preview.lab.v1",
            "protocol_sha256":digest(),"fold":folds[0],
            "inputs":{"start_utc":utc_minute(start_ms),"end_utc":utc_minute(end_ms),
                      "mode":"receipt-only","confirmation":"READ_CVD_TEST_BATCH_ONLY"},
            "requested_slots":(end_ms-start_ms)//M5+1,
            "existing_evidence_overlap":False,"inventory_requests_planned":1,
            "select_requests_planned":1,"actual_rows_read":None,
            "account_quota_utilization":None,"fresh_account_budget_required":True,
            "market_session_attested":False,"owner_dispatch_required":True,
            "dispatch_authorized":False,"network_requests":0,"outcomes_computed":False,
            "scientific_admission":False,"orders_enabled":False,"notifications_enabled":False}
