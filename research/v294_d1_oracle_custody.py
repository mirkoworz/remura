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
    names={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if names-{"tv_test_custody","tv_test_cursor"}:
        raise ValueError("not_dedicated_db")
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

def pull_once(db, fetch, start, cutoff, *, enabled=False, replay_cursor=None, reconciliation=False):
    """Exactly one injected SELECT; disabled unless explicit opt-in.
    fetch must verify EU TEST identity and use read-only credentials.
    No skips, overwrite, retry or automatic checkpoint after a failure.
    """
    if enabled is not True:
        raise ValueError("disabled")
    if db.in_transaction:
        raise ValueError("transaction_active")
    previous=cursor(db)
    scan_cursor=replay_cursor if reconciliation else previous
    if not reconciliation and replay_cursor is not None:
        raise ValueError("unexpected_replay_cursor")
    query=request_page(start,cutoff,scan_cursor)
    rows=fetch(query)
    records,next_cursor,full=inspect_page(rows,start,cutoff,scan_cursor)
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
        if records and not reconciliation:
            db.execute("INSERT INTO tv_test_cursor VALUES (1,?,?) ON CONFLICT(id) DO UPDATE SET received_ms=excluded.received_ms,event_key=excluded.event_key",next_cursor)
        db.commit()
    except BaseException:
        db.rollback()
        raise
    return {"received":len(records),"inserted":inserted,"more_possible":full,
            "prospective_admitted":False,"reconciliation":reconciliation,
            "next_replay_cursor":next_cursor if reconciliation else None}

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
        params=query.get("params")
        if type(params) is not list or len(params)!=9:
            raise ValueError("select_params")
        if query!=request_page(params[3],params[4],(params[5],params[7])):
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
