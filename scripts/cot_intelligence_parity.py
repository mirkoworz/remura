#!/usr/bin/env python3
"""REMURA Filone B v21.0 LAB — strict OFFLINE CFTC public/private parity.

Reads TWO local JSON snapshot files only. No network, DB, secrets, writes or deploy.
A matching snapshot is NOT proof that historic values were available at capture.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path

SCHEMA = "remura-cot-intelligence-snapshot-v1"
PUBLIC_SOURCE = "official_public_cftc_socrata"
PRIVATE_SOURCE = "existing_private_cftc_cache"
CLOCK_PUBLIC = "public_api_read_at_not_official_publication"
CLOCK_PRIVATE = "first_local_capture_not_official_publication"
EXPECTED = {
    "tff": ("099741","096742","097741","232741","090741","092741","112741",
            "13874A","209742","124603","098662"),
    "disagg": ("088691","084691","067651")
}
FIELDS = ("oi","first_long","first_short","second_long","second_short")
MAX_FILE_BYTES=8_000_000

def utc_stamp(value: str) -> dt.datetime:
    if not isinstance(value,str) or not value.endswith(("Z","+00:00")):
        raise ValueError("UTC_TIMESTAMP_REQUIRED")
    try:
        x=dt.datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError:
        raise ValueError("INVALID_UTC_TIMESTAMP") from None
    if x.tzinfo is None or x.utcoffset()!=dt.timedelta(0):
        raise ValueError("UTC_TIMESTAMP_REQUIRED")
    return x.astimezone(dt.timezone.utc)

def calendar_date(value):
    if type(value) is not str:
        raise ValueError("INVALID_REPORT_DATE")
    try: x=dt.date.fromisoformat(value)
    except ValueError: raise ValueError("INVALID_REPORT_DATE") from None
    if value!=x.isoformat():raise ValueError("INVALID_REPORT_DATE")
    return x

def read_local(path):
    p=Path(path).expanduser().resolve(strict=True)
    if not p.is_file() or not 0<p.stat().st_size<=MAX_FILE_BYTES:
        raise ValueError("INVALID_OFFLINE_FILE")
    with p.open("r",encoding="utf-8") as f:
        data=json.load(f,parse_constant=lambda _: (_ for _ in ()).throw(ValueError("NONFINITE_JSON")))
    return data

def validate(snapshot,source,now):
    if type(snapshot) is not dict or snapshot.get("schema")!=SCHEMA or snapshot.get("source")!=source:
        raise ValueError("INVALID_SNAPSHOT_SOURCE")
    clock=CLOCK_PUBLIC if source==PUBLIC_SOURCE else CLOCK_PRIVATE
    rows=snapshot.get("rows")
    if snapshot.get("captureClock")!=clock or type(rows) is not list or type(snapshot.get("rowCount")) is not int or snapshot["rowCount"]!=len(rows) or not rows or len(rows)>5000 or snapshot.get("truncated") is not False:
        raise ValueError("INVALID_OR_TRUNCATED_SNAPSHOT")
    if source==PUBLIC_SOURCE:
        read=utc_stamp(snapshot.get("readAtUtc"))
        if read>now+dt.timedelta(minutes=5):
            raise ValueError("PUBLIC_READ_IN_FUTURE")
        raw=json.dumps(rows,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode("utf-8")
        computed=hashlib.sha256(raw).hexdigest()
        if computed!=snapshot.get("dataSha256"):
            raise ValueError("PUBLIC_ROWS_CHECKSUM_MISMATCH")
    else: read=None
    indexed={}
    for row in rows:
        if not isinstance(row,dict):raise ValueError("INVALID_CFTC_ROW")
        kind,code,date=row.get("dataset"),row.get("code"),row.get("report_date")
        if kind not in EXPECTED or code not in EXPECTED[kind]:
            raise ValueError("UNEXPECTED_CFTC_CONTRACT")
        day=calendar_date(date)
        if day>now.date():raise ValueError("FUTURE_CFTC_REPORT")
        for col in FIELDS:
            value=row.get(col)
            if type(value) not in (int,float) or not math.isfinite(value) or value<0 or value>1e11:
                raise ValueError("INVALID_CFTC_FIELD")
        if row["oi"]<=0 or any(row[col]>2*row["oi"] for col in FIELDS[1:]):
            raise ValueError("INVALID_OPEN_INTEREST_POSITION")
        seen=row.get("first_seen_at")
        if source==PUBLIC_SOURCE and seen is not None:
            raise ValueError("FORGED_PUBLIC_LOCAL_CLOCK")
        if source==PRIVATE_SOURCE and seen is not None:
            clock_val=utc_stamp(seen)
            if clock_val>now+dt.timedelta(minutes=5):
                raise ValueError("FUTURE_PRIVATE_CAPTURE")
        key=(kind,code,date)
        if key in indexed:raise ValueError("DUPLICATE_CFTC_ROW")
        indexed[key]=row
    return indexed,read

def reconcile(public,private,dates,now_utc):
    now=utc_stamp(now_utc)
    if type(dates) not in (list,tuple) or len(dates)!=2:
        raise ValueError("EXACTLY_TWO_REPORT_DATES_REQUIRED")
    older,newer=sorted(calendar_date(x) for x in dates)
    if not 5<=(newer-older).days<=9 or newer>now.date():
        raise ValueError("INVALID_WEEKLY_COMPARISON")
    pub,read=validate(public,PUBLIC_SOURCE,now)
    priv,_=validate(private,PRIVATE_SOURCE,now)
    results=[]
    for day in (older,newer):
        iso=day.isoformat()
        for dataset,codes in EXPECTED.items():
            counts={"matched":0,"mismatched":0,"missing_public":0,"missing_private":0,
                    "capture_known":0,"capture_unknown":0,"capture_before_report":0}
            mismatches=[]
            for code in codes:
                key=(dataset,code,iso)
                a=pub.get(key);b=priv.get(key)
                if a is None:counts["missing_public"]+=1
                if b is None:counts["missing_private"]+=1
                if a is not None and b is not None:
                    mismatched=[field for field in FIELDS if abs(a[field]-b[field])>1e-9]
                    if mismatched:
                        counts["mismatched"]+=1
                        mismatches.append({"code":code,"fields":mismatched})
                    else: counts["matched"]+=1
                    if b.get("first_seen_at") is None:counts["capture_unknown"]+=1
                    else:
                        counts["capture_known"]+=1
                        local=utc_stamp(b["first_seen_at"])
                        if local<dt.datetime.combine(day,dt.time.min,dt.timezone.utc):
                            counts["capture_before_report"]+=1
            results.append({"dataset":dataset,"reportDate":iso,"expected":len(codes),
                            **counts,"mismatchedKeys":mismatches})
    matched=sum(r["matched"] for r in results)
    expected=sum(r["expected"] for r in results)
    usable=all(r["matched"]==r["expected"] and r["capture_before_report"]==0 for r in results)
    return {
        "schema":"remura-cot-offline-parity-v1",
        "state":"value_parity_only" if usable else "incomplete_or_different",
        "nowUtc":now.isoformat().replace("+00:00","Z"),
        "publicReadAtUtc":read.isoformat().replace("+00:00","Z"),
        "publicRowsSha256Verified":True,
        "reportDates":[older.isoformat(),newer.isoformat()],
        "expectedKeys":expected,"matchedKeys":matched,
        "coverage":results,
        "limitations":[
            "Matches against public values at publicReadAtUtc ONLY; revisions after first local capture cannot be excluded",
            "first_seen_at is local custody metadata, NOT official CFTC release clock or immutable price-time availability",
            "An offline JSON private snapshot is not a verified connection to live collector",
            "No inference of profitable trades, directional prices or backtest validity"
        ]
    }

def main():
    p=argparse.ArgumentParser(description="Offline comparison: CFTC public read vs REMURA cached snapshot")
    p.add_argument("--public",required=True,help="Existing public CFTC JSON snapshot on local disk")
    p.add_argument("--private",required=True,help="Existing offline JSON export of copied REMURA SQLite")
    p.add_argument("--report-dates",required=True,help="Two known report dates, e.g. 2026-11-10,2026-11-17")
    p.add_argument("--now-utc",required=True,help="Explicit UTC clock, e.g. 2026-11-23T19:00:00Z")
    a=p.parse_args()
    result=reconcile(read_local(a.public),read_local(a.private),
                     a.report_dates.split(","),a.now_utc)
    print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))

if __name__=="__main__":
    main()
