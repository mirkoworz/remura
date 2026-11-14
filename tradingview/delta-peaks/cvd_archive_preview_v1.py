#!/usr/bin/env python3
# REMURA v0.8.68 LAB — 14/11/2026 16:46 CET
"""Offline assembly of explicit, disjoint <=72-slot CVD TEST export windows.
No D1/API/file writes; input raw export must be supplied privately by trusted caller.
Does not prove origin, conflict ledger or market-session completeness.
Never logs raw data. Recomputes outcomes once over the union, not window averages.
"""
import json
from cvd_telemetry_preview_v1 import validate,SYMBOL,VERSION,M5
from cvd_outcome_readiness_v1 import summarize,MAX_ROWS
from cvd_radar_preview_v1 import aggregate_radar
from remura_tv_bridge_preview_v1 import EXPECTED_COLUMNS

# Use UTC calculation rather than depending on a handwritten timestamp.
from datetime import datetime,timezone
MIN_CLOSE_MS=int(datetime(2026,11,14,12,40,tzinfo=timezone.utc).timestamp())*1000

def assemble(windows,*,as_of_ms):
    if type(as_of_ms) is not int or type(windows) is not list or len(windows)>140:
        raise ValueError("archive_scope")
    valid=[]; total=0; requested=0; end_prior=None
    for window in windows:
        if type(window) is not dict or set(window)!={"start_ms","end_ms","rows"}:
            raise ValueError("archive_window")
        start,end,rows=window["start_ms"],window["end_ms"],window["rows"]
        if (type(start) is not int or type(end) is not int or start<MIN_CLOSE_MS or
            start%M5 or end%M5 or start>end or end-start>=72*M5 or
            end+120000>as_of_ms or (end_prior is not None and start<=end_prior) or
            type(rows) is not list or len(rows)>100):
            raise ValueError("archive_window_scope")
        end_prior=end
        requested+=(end-start)//M5+1
        total+=len(rows)
        if total>MAX_ROWS or requested>MAX_ROWS:
            raise ValueError("archive_cap")
        seen={}
        for row in rows:
            if (type(row) is not dict or set(row)!=EXPECTED_COLUMNS or
                row["symbol"]!=SYMBOL or row["version"]!=VERSION or row["timeframe"]!="5" or
                type(row["is_timely"]) is not int or row["is_timely"]!=0):
                raise ValueError("archive_row_scope")
            t,received=row["bar_close_ms"],row["received_at_ms"]
            if (type(t) is not int or not start<=t<=end or type(received) is not int or
                received>as_of_ms or type(row["raw_json"]) is not str or
                len(row["raw_json"].encode())>20000):
                raise ValueError("archive_row_clock")
            e=json.loads(row["raw_json"])
            v=validate(e,received_ms=received)
            if v["bar_close_ms"]!=t or v["event_key"]!=row["event_key"] or e["snapshot"]["event_type"]!=row["event_type"]:
                raise ValueError("archive_row_identity")
            if t in seen:
                if seen[t][0]!=row:
                    raise ValueError("archive_conflicting_bar")
            else:
                seen[t]=(row,e,v)
        valid.extend(seen[t] for t in sorted(seen))
    return {"schema":"remura.tv.cvd.archive.aggregate.preview.v1","version":"0.8.68-lab",
            "requested_slots":requested,"valid_unique_bars":len(valid),
            "missing_requested_slots":requested-len(valid),"duplicate_rows":total-len(valid),
            "scope":"EXPLICIT_WINDOWS_NOT_MARKET_CALENDAR","provenance_attested":False,
            "conflict_ledger_available":False,
            "radar":aggregate_radar(valid,as_of_ms=as_of_ms),
            "outcomes":summarize(valid,as_of_ms=as_of_ms),
            "scientific_admission":False,"orders_enabled":False}
