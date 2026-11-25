"""REMURA V29.4 LAB — 25/11/2026.
Durable custody transaction + bounded pull orchestration. No CLI, no scheduler.
Caller must open a new dedicated private SQLite DB, verify permissions and
supply a verified TEST transport; never use the production prices DB.
"""
import json
from v292_d1_oracle_page_contract import inspect_page, request_page

def initialize(db):
    if db.in_transaction:
        raise ValueError("transaction_active")
    db.execute("""CREATE TABLE IF NOT EXISTS tv_test_custody(
       event_key TEXT PRIMARY KEY, metadata TEXT NOT NULL,
       original BLOB NOT NULL, sha256 TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS tv_test_cursor(
       id INTEGER PRIMARY KEY CHECK(id=1),
       received_ms INTEGER NOT NULL, event_key TEXT NOT NULL)""")
    db.commit()

def cursor(db):
    row=db.execute("SELECT received_ms,event_key FROM tv_test_cursor WHERE id=1").fetchone()
    return tuple(row) if row else None

def pull_once(db, fetch, start, cutoff, *, enabled=False):
    """Exactly one injected SELECT; disabled unless explicit opt-in.
    fetch must verify EU TEST identity and use read-only credentials.
    No skips, overwrite, retry or automatic checkpoint after a failure.
    """
    if enabled is not True:
        raise ValueError("disabled")
    if db.in_transaction:
        raise ValueError("transaction_active")
    previous=cursor(db)
    query=request_page(start,cutoff,previous)
    rows=fetch(query)
    records,next_cursor,full=inspect_page(rows,start,cutoff,previous)
    inserted=0
    db.execute("BEGIN IMMEDIATE")
    try:
        if cursor(db)!=previous:
            raise ValueError("cursor_changed")
        for rec in records:
            m=rec["metadata"]
            key=m["event_key"]
            value=(json.dumps(m,sort_keys=True,separators=(",",":")),
                   rec["original"],rec["sha256"])
            existing=db.execute("SELECT metadata,original,sha256 FROM tv_test_custody WHERE event_key=?",(key,)).fetchone()
            if existing is not None:
                if tuple(existing)!=value:
                    raise ValueError("custody_conflict")
                continue
            db.execute("INSERT INTO tv_test_custody VALUES (?,?,?,?)",(key,*value))
            inserted+=1
        if records:
            db.execute("INSERT INTO tv_test_cursor VALUES (1,?,?) ON CONFLICT(id) DO UPDATE SET received_ms=excluded.received_ms,event_key=excluded.event_key",next_cursor)
        db.commit()
    except BaseException:
        db.rollback()
        raise
    return {"received":len(records),"inserted":inserted,"more_possible":full,
            "prospective_admitted":False}

def verified_test_fetch(account_id, token, *, enabled=False):
    """Build one-shot network adapter using existing pinned helpers.
    Imports deliberately deferred. Requires helper deployment/verification.
    No access on import. No retries; errors must be sanitized at runtime.
    """
    if enabled is not True:
        raise ValueError("disabled")
    from urllib.parse import quote
    from cloudflare_d1_readonly_audit import api_request,require_account_id,require_account_token
    from d1_test_target_preflight_v1 import inspect_verified_inventory,TEST_DB,MAIN_DB
    account=quote(require_account_id(account_id),safe="")
    token=require_account_token(token)
    base="/accounts/"+account+"/d1/database"
    ids=inspect_verified_inventory(api_request("GET",base+"?page=1&per_page=100",token))
    if ids[TEST_DB]==ids[MAIN_DB]:
        raise ValueError("test_not_isolated")
    used=False
    def fetch(query):
        nonlocal used
        if used:
            raise ValueError("one_shot")
        from v292_d1_oracle_page_contract import SQL
        if query.get("sql")!=SQL:
            raise ValueError("select_only")
        used=True
        response=api_request("POST",base+"/"+quote(ids[TEST_DB],safe="")+"/query",token,query)
        result=response.get("result")
        if response.get("success") is not True or type(result) is not list or len(result)!=1 or result[0].get("success") is not True:
            raise ValueError("query_failed")
        rows=result[0].get("results")
        if type(rows) is not list:
            raise ValueError("query_shape")
        return rows
    return fetch
