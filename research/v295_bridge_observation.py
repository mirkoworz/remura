"""REMURA V29.5 LAB, 25/11/2026 Europe/Rome.
Bounded retrospective TEST observation, not a prospective decision.
No network, database writes, scheduling or individual values on stdout.
"""
import json
from v294_footprint_cvd import derive
M5=300000

def summarize(db, start_ms, asof_ms):
    if (type(start_ms) is not int or type(asof_ms) is not int or
        not 0 < start_ms <= asof_ms or asof_ms-start_ms>86400000):
        raise ValueError('window')
    # Custody table key is indexed; bounded output, no claim about rows scanned.
    # Dedicated DB only. The receipt clock belongs to D1, not local first-seen.
    rows=db.execute("SELECT metadata,original,sha256 FROM tv_test_custody WHERE json_extract(metadata,'$.bar_close_ms') BETWEEN ? AND ? AND json_extract(metadata,'$.received_at_ms')<=? LIMIT 289",(start_ms,asof_ms,asof_ms)).fetchall()
    if len(rows)>288:
        raise ValueError('window_capacity')
    records=[{'metadata':json.loads(m),'original':raw,'sha256':digest} for m,raw,digest in rows]
    features=derive(records,asof_ms)
    return {'received':len(records),'valid_footprint':len(features),
            'longest_segment':max((f['segment_bars'] for f in features),default=0),
            'mode':'retrospective_test_only','prospective_admitted':False}
