#!/usr/bin/env python3
"""Track B: one-shot whole-universe COT lineage scan; no deployment or broker I/O.

Opt-in on the authorized Oracle host. Loads EXACTLY two hash-verified public
research source files into memory, then reads the PRIVATE operational SQLite
in mode=ro / query_only / read transaction. Never edits app, DB, cron, VPS
service, repository, H1 process or credentials. Only aggregate, public market
symbols and counters leave the process. Not proof of profitability.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import types
import urllib.request

PIN = "ad4c90298fc48e891fb2b7aa2c973a8ae3f4e679"
BASE = ("https://raw.githubusercontent.com/mirkoworz/remura/"
        + PIN + "/scripts/")
BLOBS = {
    "shark_cot_paired_baseline": "5126cb474887e2b261b8d0ae1f848eaeb59602de",
    "shark_universe_lineage": "562abf9ce87d7f370fb234eaa4a7fb5f03c9ae37",
}
DB_PATH = "/opt/remura/private/remura-prices.sqlite3"
MAX_SOURCE_BYTES = 30 * 1024


class DenyRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise ValueError("redirect_not_allowed")


def _fetch(name):
    if name not in BLOBS:
        raise ValueError("research_module_not_allowed")
    req=urllib.request.Request(
        BASE+name+".py", method="GET",
        headers={"User-Agent":"REMURA-COT-universe-private-probe/1",
                 "Accept":"text/plain"})
    op=urllib.request.build_opener(
        urllib.request.ProxyHandler({}),DenyRedirects())
    with op.open(req,timeout=12) as response:
        if response.status!=200:
            raise ValueError("source_unavailable")
        return response.read(MAX_SOURCE_BYTES+1)


def blob_hash(raw):
    if not isinstance(raw,bytes):
        raise ValueError("raw_source_bytes_only")
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()


def verified_modules(fetch=None):
    if sys.version_info < (3,10):
        raise ValueError("python_310_required")
    fetch=_fetch if fetch is None else fetch
    data={}
    for name, expected in BLOBS.items():
        raw=fetch(name)
        if (not isinstance(raw,bytes) or not 1<=len(raw)<=MAX_SOURCE_BYTES
                or blob_hash(raw)!=expected):
            raise ValueError("source_integrity_failed")
        data[name]=raw
    sys.dont_write_bytecode=True
    package=types.ModuleType("scripts")
    package.__path__=[]
    sys.modules["scripts"]=package
    for name,raw in data.items():
        mod=types.ModuleType("scripts."+name)
        mod.__package__="scripts"
        sys.modules[mod.__name__]=mod
        setattr(package,name,mod)
        exec(compile(raw,"<verified-REMURA-universe>","exec"),mod.__dict__)
    return package.shark_universe_lineage


def run(*, fetch=None, database=DB_PATH, as_of=None):
    module=verified_modules(fetch)
    now=datetime.now(timezone.utc) if as_of is None else as_of
    if (not isinstance(now,datetime) or now.tzinfo is None or
            now.utcoffset().total_seconds()!=0):
        raise ValueError("invalid_utc_asof")
    path=Path(database)
    if not path.is_file():
        raise ValueError("sqlite_absent")
    report=module.audit_path(
        path,as_of=now.isoformat().replace("+00:00","Z"))
    if (report.get("schema")!="remura-shark-universe-lineage-v1"
            or report.get("brokerCalls")!=0
            or report.get("edge")!="NOT_ESTABLISHED"):
        raise ValueError("bad_audit_response")
    return report


def main():
    try:
        result=run()
        print("REMURA_TRACK_B_UNIVERSO_COT=COMPLETATO")
        print(json.dumps(result,sort_keys=True,separators=(",",":"),
                         ensure_ascii=True))
        return 0
    except Exception:
        print("REMURA_TRACK_B_UNIVERSO_COT=NON_COMPLETATO")
        print("MOTIVO=LETTURA_O_INTEGRITA_NON_VERIFICABILI")
        return 1


if __name__=="__main__":
    raise SystemExit(main())
