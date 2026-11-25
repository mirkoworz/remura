"""REMURA V29.2 LAB — 25/11/2026 Europe/Rome.
Offline-only incremental D1 TEST page contract. No network, storage or CLI.
Use the existing inventory/account guard and native validator at integration.
A cursor is a *candidate*, never a durable checkpoint until atomic custody.
"""
import hashlib
import json

PAGE = 4
SYMBOL = "FX:EURUSD"
VERSION = "0.9.1-cvd-lab"
COLUMNS = ("event_key", "received_at_ms", "bar_close_ms", "symbol",
           "timeframe", "event_type", "version", "is_timely", "raw_json")
SQL = ("SELECT " + ", ".join(COLUMNS) +
       " FROM tv_flow_events WHERE symbol=? AND timeframe=? AND version=?"
       " AND received_at_ms>=? AND received_at_ms<=?"
       " AND (received_at_ms>? OR (received_at_ms=? AND event_key>?))"
       " ORDER BY received_at_ms,event_key LIMIT ?")

def request_page(start, cutoff, cursor=None):
    if type(start) is not int or type(cutoff) is not int or not 0 < start <= cutoff:
        raise ValueError("window")
    if cursor is None:
        cursor = (start - 1, "")
    if (type(cursor) is not tuple or len(cursor) != 2 or
        type(cursor[0]) is not int or not start - 1 <= cursor[0] <= cutoff or
        type(cursor[1]) is not str or len(cursor[1]) > 200):
        raise ValueError("cursor")
    return {"sql": SQL, "params": [SYMBOL, "5", VERSION, start, cutoff,
                                    cursor[0], cursor[0], cursor[1], PAGE]}

def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result

def _invalid_constant(_):
    raise ValueError("nonfinite_json")

def inspect_page(rows, start, cutoff, cursor=None):
    """Return in-memory custody candidates, never prospective decisions.
    Native semantic validation remains a separate mandatory gate.
    Any invalid page raises; caller must retain previous checkpoint.
    """
    request_page(start, cutoff, cursor)
    previous = cursor if cursor is not None else (start - 1, "")
    if type(rows) is not list or len(rows) > PAGE:
        raise ValueError("page_size")
    records = []
    for row in rows:
        if type(row) is not dict or set(row) != set(COLUMNS):
            raise ValueError("columns")
        r, c, key = row["received_at_ms"], row["bar_close_ms"], row["event_key"]
        if (type(r) is not int or type(c) is not int or
            not start <= r <= cutoff or c <= 0 or c % 300000 or
            type(key) is not str or key != "|".join((SYMBOL, "5", str(c), VERSION)) or
            (r, key) <= previous or row["symbol"] != SYMBOL or
            row["timeframe"] != "5" or row["version"] != VERSION or
            type(row["is_timely"]) is not int or row["is_timely"] != 0):
            raise ValueError("scope_or_clock")
        text = row["raw_json"]
        if type(text) is not str:
            raise ValueError("raw_type")
        raw = text.encode("utf-8")
        if not 1 <= len(raw) <= 20000:
            raise ValueError("raw_size")
        obj = json.loads(raw, object_pairs_hook=_unique, parse_constant=_invalid_constant)
        if type(obj) is not dict or obj.get("schema") != "remura.tv.flow.cvd.preview.v1":
            raise ValueError("schema")
        s = obj.get("snapshot")
        if (type(s) is not dict or s.get("symbol") != SYMBOL or
            s.get("timeframe") != "5" or s.get("version") != VERSION or
            s.get("bar_close_ms") != c or s.get("event_type") != row["event_type"] or
            type(obj.get("cvd")) is not dict):
            raise ValueError("identity")
        metadata = {k: row[k] for k in COLUMNS if k != "raw_json"}
        records.append({"metadata": metadata, "original": raw,
                        "sha256": hashlib.sha256(raw).hexdigest(),
                        "prospective_admitted": False})
        previous = (r, key)
    return records, previous, len(rows) == PAGE

def same_record(a, b):
    """Exact idempotence check. A mismatch must stop the private transaction."""
    return a["metadata"] == b["metadata"] and a["original"] == b["original"]
