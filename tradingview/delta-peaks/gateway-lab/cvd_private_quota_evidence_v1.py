#!/usr/bin/env python3
# REMURA v0.8.85 LAB — 14/11/2026 20:39 CET
"""Explicit private quota evidence acquisition, not scheduled or activated.
Reuse existing read-only analytics and inventory validators. No SQL,
Worker invocation, broker calls, output, persistent credentials or retries.
Provider analytics may lag and are not exact billing.
"""
from datetime import datetime,timezone
import time
from urllib.parse import quote
from cloudflare_d1_readonly_audit import (AuditError,api_request,require_account_id,
    require_account_token,verify_account_token,EXPECTED_NAME)
import cloudflare_account_quota_guard as d1
import cloudflare_workers_usage_guard as workers
import cloudflare_d1_account_storage_guard as storage
import cloudflare_d1_storage_guard as test_storage

MAX_DATABASES=6 # existing 70% count guard excludes 7+
MAX_ELAPSED_MS=120000
MAX_DRIFT_MS=5000

def acquire(account_id,analytics_token,d1_token,*,explicit=False):
    if explicit is not True:raise ValueError("explicit_budget_read_required")
    account=require_account_id(account_id)
    analytics_token=require_account_token(analytics_token)
    d1_token=require_account_token(d1_token)
    if analytics_token==d1_token:raise ValueError("separate_read_tokens_required")
    started=time.time_ns()//1000000; mono=time.monotonic_ns()//1000000
    at=datetime.fromtimestamp(started/1000,tz=timezone.utc);day=at.date().isoformat()
    def guard():
        now=time.time_ns()//1000000;elapsed=time.monotonic_ns()//1000000-mono
        if (not 0<=elapsed<=MAX_ELAPSED_MS or now<started or
            abs(now-started-elapsed)>MAX_DRIFT_MS or
            datetime.fromtimestamp(now/1000,tz=timezone.utc).date()!=at.date()):
            raise AuditError("budget_capture_clock_or_day")
    guard()
    usage=d1.query_account_analytics(account,analytics_token,day)
    if usage is None:raise AuditError("budget_d1_unknown")
    reads,writes=usage
    if d1.assessment(reads,writes)!="OK":raise AuditError("budget_d1_not_ok")
    guard()
    metrics=workers.fetch_workers_analytics(account,analytics_token,at)
    if metrics is None:raise AuditError("budget_workers_unknown")
    requests=metrics["requests_estimate"]
    if workers.assess_requests(requests)!="OK":raise AuditError("budget_workers_not_ok")
    prefix="/accounts/"+quote(account,safe="")
    guard()
    verify_account_token(api_request("GET",prefix+"/tokens/verify",d1_token))
    guard()
    url=prefix+"/d1/database"
    inv=storage.parse_inventory(api_request("GET",url+"?page=1&per_page=100",d1_token))
    if not 2<=len(inv)<=MAX_DATABASES:raise AuditError("budget_inventory_headroom")
    sizes={}
    for name,uid,jurisdiction in inv:
        guard()
        meta=api_request("GET",url+"/"+quote(uid,safe=""),d1_token)
        sizes[name]=storage.read_db_size(meta,name,uid,jurisdiction)
        # Early termination on known limit breach, not partial green reports.
        if test_storage.assess_storage(sizes[name])!="OK":raise AuditError("budget_db_storage_not_ok")
    size=sizes[EXPECTED_NAME]; total=sum(sizes.values());largest=max(sizes.values())
    if storage.assessment(len(inv),total,largest)!="OK":raise AuditError("budget_account_storage_not_ok")
    guard()
    source="; SOURCE=ADAPTIVE_GRAPHQL_ESTIMATE; NOT_EXACT_BILLING"
    reports={
        "d1":f"REMURA_CF_ACCOUNT_QUOTA=OK\nUTC_DAY={day}{source}\nD1_ACCOUNT_ROWS_READ_ESTIMATE={reads}\nD1_ACCOUNT_ROWS_WRITTEN_ESTIMATE={writes}",
        "workers":f"REMURA_CF_WORKERS_USAGE=OK\nWORKERS_UTC_DAY={day}{source}\nWORKERS_ACCOUNT_REQUESTS_ESTIMATE={requests}",
        "storage":f"REMURA_D1_TEST_STORAGE=OK\nREMURA_D1_TEST_STORAGE_BYTES={size}",
        "account_storage":f"REMURA_D1_ACCOUNT_STORAGE=OK\nD1_ACCOUNT_DATABASE_COUNT={len(inv)}\nD1_ACCOUNT_STORAGE_BYTES={total}\nD1_ACCOUNT_LARGEST_DB_BYTES={largest}"}
    # Oldest request clock, not completion, and no fabricated freshness.
    return {"observed_ms":started,"complete":True,"reports":reports}
