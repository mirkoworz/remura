#!/usr/bin/env python3
# REMURA v0.8.76 LAB — 14/11/2026 17:10 CET
"""Private, explicit, in-memory D1 TEST -> B snapshot -> HTML/notice.
No scheduler, file writes, stdout, production connection or notification transport.
Inputs are trusted caller snapshots, not proof of independent provenance.
"""
import sqlite3
from datetime import datetime,timezone
from urllib.parse import quote
from cvd_archive_preview_v1 import assemble,MIN_CLOSE_MS
from cvd_telemetry_preview_v1 import M5
from cvd_test_batch_reader_v1 import unpack,MAX_SLOTS
from cvd_test_fold_reader_v1 import fetch_page
from cloudflare_d1_readonly_audit import AuditError,api_request,require_account_id,require_account_token
from d1_test_target_preflight_v1 import MAIN_DB,TEST_DB,inspect_verified_inventory
from research_dossier_preview_v1 import dossier
from research_dashboard_preview_v1 import render,notification_preview
MAX_PAGES=5
MAX_OBSERVED_READS=20000
DAY=86400000

def validate_inputs(core,private,secret,retail_root,authorized_at):
    for db in ([core] if private is None else [core,private]):
        if not isinstance(db,sqlite3.Connection) or db.in_transaction or db.execute("PRAGMA query_only").fetchone()[0]!=1:
            raise ValueError("query_only_private_snapshot_required")
    if (core is private or (private is None)!=(secret is None) or
        (retail_root is None)!=(authorized_at is None)):
        raise ValueError("private_source_scope")
    if secret is not None and (type(secret) is not bytes or len(secret)<16):
        raise ValueError("private_secret_scope")

def plan(now):
    if type(now) is not int or now<MIN_CLOSE_MS+120000:
        raise AuditError("no_mature_test_window")
    end=(now-120000)//M5*M5
    # Include the three-minute handoff buffer preceding the one-day B cohort.
    start=max(MIN_CLOSE_MS,(now-DAY-180000)//M5*M5)
    pages=[(t,min(end,t+(MAX_SLOTS-1)*M5)) for t in range(start,end+1,MAX_SLOTS*M5)]
    if not 1<=len(pages)<=MAX_PAGES:
        raise AuditError("runtime_scope")
    return pages

def preview(core,windows,*,now,origin="LOCAL_SNAPSHOT",private=None,secret=None,
            retail_root=None,authorized_at=None):
    validate_inputs(core,private,secret,retail_root,authorized_at)
    # Require exact planned windows, including empty responses; no silent gaps.
    if type(windows) is not list or any(type(w) is not dict for w in windows):
        raise ValueError("runtime_windows")
    expected=plan(now)
    if [(w.get("start_ms"),w.get("end_ms")) for w in windows]!=expected:
        raise ValueError("runtime_window_scope")
    archive=assemble(windows,as_of_ms=now)
    # Do not discard conflict evidence before validation. Exact duplicates
    # remain available to the decision adapter, which deduplicates as-of.
    rows=[r for w in windows for r in w["rows"]]
    at=datetime.fromtimestamp(now//1000,tz=timezone.utc).replace(microsecond=(now%1000)*1000).isoformat().replace("+00:00","Z")
    r=dossier(core,[],as_of_utc=at,days=1,origin=origin,cvd_rows=rows,auxiliary=True,
              private_cvd_db=private,cvd_secret=secret,retail_root=retail_root,retail_authorized_at=authorized_at)
    notice=notification_preview(r)
    return {"schema":"remura.tv.private.runtime.preview.v1","version":"0.8.76-lab",
            "origin":origin,"status":"LOCAL_PREVIEW_ONLY","html":render(r),"notice":notice,
            "coverage":{"requested_slots":archive["requested_slots"],"valid_unique_bars":archive["valid_unique_bars"],
                        "missing_requested_slots":archive["missing_requested_slots"],
                        "first_requested_close_ms":expected[0][0],"last_requested_close_ms":expected[-1][1],
                        "basis":"MATURE_REQUESTED_SLOTS_NOT_MARKET_CALENDAR",
                        "latest_immature_bars_not_queried":True,"legacy_fxcm_export_supplied":False},
            "raw_export_returned":False,"independent_provenance":False,"notifications_enabled":False,
            "orders_enabled":False,"edge":"NOT_ESTABLISHED"}

def collect_test_preview(core,account_id,token,*,now,explicit=False,private=None,secret=None,
                         retail_root=None,authorized_at=None):
    if explicit is not True:
        raise AuditError("explicit_runtime_test_read_required")
    validate_inputs(core,private,secret,retail_root,authorized_at)
    pages=plan(now)
    account=require_account_id(account_id); token=require_account_token(token)
    base="/accounts/"+quote(account,safe="")+"/d1/database"
    ids=inspect_verified_inventory(api_request("GET",base+"?page=1&per_page=100",token))
    if ids[MAIN_DB]==ids[TEST_DB]:
        raise AuditError("test_not_isolated")
    windows=[]; reads=0
    for a,b in pages:
        rows,stats=unpack(fetch_page(account,ids[TEST_DB],token,a,b,now))
        if stats[0] is None or stats[1]!=0:
            raise AuditError("runtime_query_usage_unknown")
        reads+=stats[0]
        if reads>MAX_OBSERVED_READS:
            raise AuditError("runtime_observed_budget_exceeded")
        windows.append({"start_ms":a,"end_ms":b,"rows":rows})
    result=preview(core,windows,now=now,private=private,secret=secret,retail_root=retail_root,authorized_at=authorized_at)
    result["collection"]={"target":"EU_D1_TEST_ONLY","inventory_requests":1,"select_requests":len(pages),
        "rows_read":reads,"rows_written":0,"account_quota_utilization":None,
        "snapshot_atomic_across_pages":False,"raw_persisted":False,"raw_logged":False}
    return result
