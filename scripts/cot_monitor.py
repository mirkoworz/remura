#!/usr/bin/env python3
"""REMURA private CFTC cache: bounded official futures-only records.

Public CFTC snapshots only, never accounts, API keys or trading requests.
Collection and monitoring are separate: no signals, orders, or push here.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sqlite3
import urllib.parse
import urllib.request

from price_feed import UTC, utcnow
from price_store import connect, set_status, get_status

SOURCES=("https://publicreporting.cftc.gov", "https://publicreportinghub.cftc.gov")
DATASETS={
    "tff":{
        "id":"gpe5-46if",
        "codes":("099741","096742","097741","232741","090741","092741","112741",
                 "13874A","209742","124603","098662"),
        "keys":("asset_mgr_positions_long","asset_mgr_positions_short",
                "lev_money_positions_long","lev_money_positions_short"),
    },
    "disagg":{
        "id":"72hh-3qpy",
        "codes":("088691","084691","067651"),
        "keys":("m_money_positions_long_all","m_money_positions_short_all",
                "prod_merc_positions_long","prod_merc_positions_short"),
    }
}
COMMON=("report_date_as_yyyy_mm_dd","cftc_contract_market_code","open_interest_all")
MAX_BYTES=6_000_000
KEEP_DAYS=420
REQUEST_DAYS=410

def build_url(dataset, now=None,host=SOURCES[0]):
    """Only static allowlisted dataset IDs and market codes enter the URL."""
    now=now or utcnow()
    config=DATASETS[dataset]
    cutoff=(now-dt.timedelta(days=REQUEST_DAYS)).date().isoformat()+"T00:00:00"
    codes=",".join("'"+code+"'" for code in config["codes"])
    where="report_date_as_yyyy_mm_dd >= '"+cutoff+"' AND cftc_contract_market_code IN ("+codes+")"
    query=urllib.parse.urlencode({
        "$select":",".join(COMMON+config["keys"]),
        "$where":where,
        "$order":"report_date_as_yyyy_mm_dd DESC",
        "$limit":"3000",
    })
    if host not in SOURCES:raise ValueError("CFTC source not allowed")
    return host+"/resource/"+config["id"]+".json?"+query

def download(dataset, now=None, opener=urllib.request.urlopen):
    problems=[]
    for host in SOURCES:
        request=urllib.request.Request(build_url(dataset,now,host),
            headers={"Accept":"application/json","User-Agent":"REMURA-CFTC-read-only/1.0"})
        try:
            with opener(request,timeout=20) as result:
                data=result.read(MAX_BYTES+1)
            if len(data)>MAX_BYTES:raise ValueError("CFTC response too large")
            records=json.loads(data)
            if not isinstance(records,list) or not records or len(records)>3000:
                raise ValueError("CFTC response missing or oversized")
            return records
        except (OSError,ValueError,TypeError,TimeoutError) as exc:
            problems.append(type(exc).__name__)
    raise RuntimeError("CFTC sources unavailable: "+"/".join(problems))

def normalize(dataset, records, now=None):
    now=now or utcnow()
    if dataset not in DATASETS or not isinstance(records,list):raise ValueError("Invalid CFTC dataset")
    config=DATASETS[dataset]
    approved=set(config["codes"])
    earliest=(now-dt.timedelta(days=KEEP_DAYS)).date()
    rows={}
    for raw in records:
        if not isinstance(raw,dict):continue
        code=str(raw.get("cftc_contract_market_code","")).upper().zfill(6)
        stamp=str(raw.get("report_date_as_yyyy_mm_dd",""))[:10]
        if code not in approved:continue
        try:
            report=dt.date.fromisoformat(stamp)
            if not earliest<=report<=now.date():continue
            values=tuple(float(raw[k]) for k in ("open_interest_all",)+config["keys"])
            if not all(math.isfinite(v) and 0<=v<=10**11 for v in values) or values[0]<=0:
                continue
            if any(v>values[0]*2 for v in values[1:]):continue
        except (ValueError,TypeError,KeyError,OverflowError):
            continue
        # Verify duplicate dataset/contract/report records are consistent.
        key=(dataset,code,stamp)
        if key in rows and rows[key]!=values:raise ValueError("Conflicting CFTC row")
        rows[key]=values
    if not rows:raise ValueError("No valid tracked CFTC futures reports")
    return rows

def ensure_table(db):
    db.execute("""CREATE TABLE IF NOT EXISTS cot_reports (
        dataset TEXT NOT NULL, code TEXT NOT NULL, report_date TEXT NOT NULL,
        oi REAL NOT NULL, first_long REAL NOT NULL, first_short REAL NOT NULL,
        second_long REAL NOT NULL, second_short REAL NOT NULL,
        PRIMARY KEY(dataset,code,report_date))""")
    db.commit()

def collect_once(db_path, now=None, fetch=download):
    """At most 2 official dataset requests (with one fallback host each).

    Leave older good records untouched when a dataset fetch fails.
    """
    now=now or utcnow()
    db=connect(db_path)
    ensure_table(db)
    saved={}
    errors={}
    try:
        for dataset in DATASETS:
            try:
                records=normalize(dataset,fetch(dataset,now),now)
                with db:
                    db.executemany(
                        """INSERT INTO cot_reports(dataset,code,report_date,oi,first_long,first_short,second_long,second_short)
                        VALUES(?,?,?,?,?,?,?,?)
                        ON CONFLICT(dataset,code,report_date) DO UPDATE SET
                            oi=excluded.oi,first_long=excluded.first_long,first_short=excluded.first_short,
                            second_long=excluded.second_long,second_short=excluded.second_short""",
                        [(kind,code,date,*v) for (kind,code,date),v in records.items()])
                    db.execute("DELETE FROM cot_reports WHERE report_date < ?",
                        ((now-dt.timedelta(days=KEEP_DAYS)).date().isoformat(),))
                saved[dataset]=len(records)
                set_status(db,**{"cot_"+dataset+"_last_success":now.isoformat(),
                                  "cot_"+dataset+"_state":"ok"})
            except (RuntimeError,ValueError,OSError,TypeError,sqlite3.Error):
                errors[dataset]="unavailable"
                set_status(db,**{"cot_"+dataset+"_state":"error"})
        set_status(db,cot_last_attempt=now.isoformat())
        return {"saved":saved,"errors":errors}
    finally:db.close()

def public_status(db_path, enabled=False, now=None):
    """Bounded read-only private endpoint: no positions/credentials exposed."""
    now=now or utcnow()
    db=connect(db_path)
    try:
        ensure_table(db)
        current=get_status(db)
        markets={}
        ready=True
        for dataset,config in DATASETS.items():
            count,contracts,date=db.execute(
                "SELECT count(*),count(DISTINCT code),max(report_date) FROM cot_reports WHERE dataset=?",
                (dataset,)).fetchone()
            recent=False
            if date:
                try:recent=0<=(now.date()-dt.date.fromisoformat(date)).days<=14
                except ValueError:pass
            state=current.get("cot_"+dataset+"_state","not_collected")
            status="ready" if recent and state=="ok" and contracts==len(config["codes"]) else (
                "disabled" if not enabled else "partial" if count else "waiting")
            if status!="ready":ready=False
            markets[dataset]={"status":status,"lastReportDate":date,
                              "contracts":contracts,"expectedContracts":len(config["codes"]),
                              "records":count}
        return {"schema":"remura-cot-status-v1","enabled":bool(enabled),
                "state":"ready" if ready and enabled else ("disabled" if not enabled else "waiting"),
                "datasets":markets,"lastAttempt":current.get("cot_last_attempt")}
    finally:db.close()

if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser(description="Sync official CFTC snapshots to REMURA private SQLite")
    parser.add_argument("--database",required=True)
    args=parser.parse_args()
    result=collect_once(args.database)
    print(json.dumps(result,separators=(",",":")))
