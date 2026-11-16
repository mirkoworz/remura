# REMURA Contributors v0.28 LAB — 16/11/2026 08:22 CET
"""Internal planning ceilings, not a measurement or representation of Cloudflare billing.
No live calls, credentials, resource changes or automatic activation.
"""
from datetime import datetime,timezone
ROUTES={
 "cold_page":(4,5,0),"profile":(1,2,0),"catalog":(1,3,0),
 "receipts":(1,3,0),"queue":(1,3,0),"history":(1,3,0),
 "intent":(1,2,0),"submit":(1,6,2),"review":(1,4,2),
}
# Lab policy targets from project: invocations/day, rows/day, bytes.
TARGET={"requests":500,"rows_read":50000,"rows_written":5000,"storage_bytes":8*1024*1024}
def number(n):return type(n) is int and 0<=n<=10**12
def scenario(counts):
    if type(counts) is not dict or set(counts)-set(ROUTES) or any(not number(n) for n in counts.values()):raise ValueError("bad_scenario")
    requests,queries,write_statements=(sum(counts.get(k,0)*r[i] for k,r in ROUTES.items()) for i in range(3))
    # Count units separately: SELECT statements do not measure scanned rows; writes do not count indexes.
    return {"requests":requests,"query_statements":queries,"write_statements_upper":write_statements,
            "within_request_target":requests<=TARGET["requests"],"measured_rows":False}
def review_evidence(e,now):
    """Checks a manually supplied sanitized evidence contract; does not verify provider provenance.
    All inputs must describe this candidate and same account/window. Missing values block.
    """
    missing=[]
    required={"observed_at","candidate","complete","account_free_verified","aggregate_below_70_percent","usage","planned"}
    if type(e) is not dict or set(e)!=required:return {"status":"NO_GO","reasons":["missing_or_unknown_evidence"],"may_activate":False}
    if e["candidate"]!="0.28 LAB":missing.append("wrong_candidate")
    if e["complete"] is not True:missing.append("incomplete")
    if e["account_free_verified"] is not True:missing.append("free_plan_unverified")
    if e["aggregate_below_70_percent"] is not True:missing.append("aggregate_unknown_or_high")
    try:
        t=datetime.fromisoformat(e["observed_at"].replace("Z","+00:00"))
        if t.tzinfo is None or now.tzinfo is None or not 0<=(now-t).total_seconds()<=3600:missing.append("stale_or_future")
    except (ValueError,TypeError,AttributeError):missing.append("invalid_time")
    for field in ("usage","planned"):
        d=e[field]
        if type(d) is not dict or set(d)!=set(TARGET) or any(not number(v) for v in d.values()):missing.append(field+"_unknown")
    if not missing:
        # Storage planned means incremental bytes, not an additional full snapshot.
        for k,cap in TARGET.items():
            if e["usage"][k]+e["planned"][k]>cap:missing.append(k+"_target_exceeded")
    return {"status":"NO_GO" if missing else "EVIDENCE_SHAPE_PASS_ONLY","reasons":missing,"may_activate":False}
