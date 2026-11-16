# REMURA v0.8.89 LAB — 16/11/2026 10:29 CET
"""Pure aggregate receipt-window audit; no D1, network, file writes or scientific outcomes.
V1 historical receipts require explicit separately verified workflow window.
V2 receipts must match independently supplied window. No provider provenance implied.
"""
from cvd_pilot_analytic_reader_v1 import SYMBOL,VERSION,M5,MIN_CLOSE_MS
from cvd_oos_protocol_preview_v2 import digest
from cloudflare_d1_readonly_audit import AuditError
def need(ok):
    if not ok:raise AuditError("receipt_evidence_denied")
def n(v,lo=0,hi=10**15):
    return type(v) is int and lo<=v<=hi
def aggregate_receipts(records):
    need(type(records) is list and 1<=len(records)<=32)
    seen=set(); prior=None; entries=[]
    for item in records:
        need(type(item) is dict and set(item)=={"run_id","start_ms","end_ms","observed_ms","report"})
        run,a,b,now,r=(item[k] for k in ("run_id","start_ms","end_ms","observed_ms","report"))
        need(n(run,1) and run not in seen and all(n(x,MIN_CLOSE_MS) for x in (a,b,now)))
        need(a%M5==0 and b%M5==0 and a<=b and b+120000<=now and (b-a)//M5+1<=12)
        need(prior is None or a>prior)
        need(type(r) is dict and r.get("schema") in ("remura.tv.cvd.first.receipt.preview.v1","remura.tv.cvd.first.receipt.preview.v2"))
        need(r.get("symbol")==SYMBOL and r.get("sender_version")==VERSION and r.get("protocol_sha256")==digest())
        if r["schema"].endswith(".v2"):
            w=r.get("window")
            need(type(w) is dict and set(w)=={"start_close_ms","end_close_ms","as_of_ms"} and w["start_close_ms"]==a and w["end_close_ms"]==b and n(w["as_of_ms"],b+120000,now))
        else:need("window" not in r)
        for flag in ("scientific_admission","orders_enabled","notifications_enabled","outcomes_computed","conflict_ledger_available","independent_provenance"):
            need(r.get(flag) is False)
        need(r.get("scope")=="REQUESTED_SLOTS_NOT_MARKET_CALENDAR")
        count=(b-a)//M5+1
        got,missing,dup,lag=(r.get(k) for k in ("valid_unique_bars","missing_requested_slots","duplicate_rows","max_lag_ms"))
        need(n(r.get("requested_slots"),1,12) and r["requested_slots"]==count and n(got,0,count) and n(missing,0,count) and got+missing==count and n(dup,0,100000))
        need((got==0 and lag is None) or (got>0 and n(lag)))
        status="NO_MATCHING_ROWS" if got==0 else "COMPLETE_REQUESTED_WINDOW" if missing==0 else "PARTIAL_REQUESTED_WINDOW"
        need(r.get("status")==status)
        c=r.get("collection")
        need(type(c) is dict and c.get("target")=="EU_D1_TEST_ONLY" and c.get("query_meta_scope")=="THIS_COLLECTION_ONLY_NOT_ACCOUNT_USAGE" and c.get("account_quota_utilization") is None and c.get("raw_logged") is False and c.get("raw_persisted") is False and c.get("inventory_requests")==1 and c.get("select_requests")==1 and n(c.get("query_rows_read"),0,20000) and type(c.get("query_rows_written")) is int and c["query_rows_written"]==0)
        seen.add(run);prior=b
        entries.append((count,got,missing,dup,lag,c["query_rows_read"]))
    return {"windows":len(entries),"requested_slots":sum(e[0] for e in entries),"valid_unique_bars":sum(e[1] for e in entries),"missing_requested_slots":sum(e[2] for e in entries),"duplicate_rows":sum(e[3] for e in entries),"max_lag_ms":max((e[4] for e in entries if e[4] is not None),default=None),"collection_rows_read":sum(e[5] for e in entries),"collection_rows_written":0,"scope":"DISJOINT_REQUESTED_SLOTS_ONLY","account_quota_utilization":None,"independent_provenance":False,"scientific_admission":False,"outcomes_computed":False,"orders_enabled":False,"notifications_enabled":False}
