#!/usr/bin/env python3
"""REMURA Capital sentiment. DEMO ONLY. Persisted daily budget, never trade."""
import datetime as dt
import fcntl
import json
import math
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://demo-api-capital.backend-capital.com"
ROOT = Path(__file__).resolve().parents[1]
PRIVATE = Path(os.getenv("REMURA_CAPITAL_PRIVATE_DIR", str(ROOT / "private/capital"))).expanduser().resolve()
MAX_DAILY = 36
MIN_INTERVAL = 7200
MAX_RESPONSE = 250000
DEFAULT_MARKETS = {"XAGUSD": "SILVER"}  # verified provider example; extend only after testing

class Stop(Exception):
    pass

def now_utc():
    return dt.datetime.now(dt.timezone.utc)

def stamp(now):
    return now.isoformat(timespec="seconds").replace("+00:00", "Z")

def write_private(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_name(path.name + ".new")
    with tmp.open("w", encoding="utf-8") as f:
        os.fchmod(f.fileno(), 0o600)
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        f.write("\n")
    os.replace(tmp, path)

def read_private(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise Stop("Corrupt private state: fail closed") from exc

def market_map(private):
    obj = read_private(private / "markets.json", DEFAULT_MARKETS)
    if not isinstance(obj, dict) or not 1 <= len(obj) <= 35:
        raise Stop("Invalid private market map")
    for symbol, market in obj.items():
        if not isinstance(symbol, str) or not re.fullmatch(r"[A-Z0-9]{3,8}", symbol):
            raise Stop("Invalid REMURA symbol")
        if not isinstance(market, str) or not re.fullmatch(r"[A-Z0-9_.-]{2,40}", market):
            raise Stop("Invalid Capital market ID")
    if len(set(obj.values())) != len(obj):
        raise Stop("Duplicate market ID")
    return obj

class Budget:
    """File locking on persistent private disk; count BEFORE every HTTP attempt."""
    def __init__(self, private, clock=now_utc):
        self.dir, self.clock = Path(private), clock
        self.dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.ledger, self.lock = self.dir / "budget.json", self.dir / "budget.lock"

    def change(self, action):
        with self.lock.open("a+b") as lock:
            os.fchmod(lock.fileno(), 0o600)
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            obj = read_private(self.ledger, {"day":"", "used":0, "lastCycle":""})
            if not isinstance(obj, dict) or type(obj.get("used")) is not int or not 0 <= obj["used"] <= MAX_DAILY or not isinstance(obj.get("day"), str):
                raise Stop("Damaged request counter")
            now = self.clock()
            today = now.date().isoformat()
            if obj["day"] > today:
                raise Stop("Clock rollback: blocked")
            if obj["day"] < today:
                obj = {"day":today, "used":0, "lastCycle":obj.get("lastCycle", "")}
            action(obj, now)
            write_private(self.ledger, obj)

    def start(self):
        def check(obj, now):
            last = obj.get("lastCycle")
            if last:
                try:
                    elapsed = (now - dt.datetime.fromisoformat(last.replace("Z","+00:00"))).total_seconds()
                except (ValueError, TypeError, AttributeError) as exc:
                    raise Stop("Damaged collection timestamp") from exc
                if elapsed < MIN_INTERVAL:
                    raise Stop("Cooldown: one collection at most every 2h")
            if obj["used"] + 2 > MAX_DAILY:
                raise Stop("Insufficient API budget")
            obj["lastCycle"] = stamp(now)
        self.change(check)

    def spend(self):
        def claim(obj, now):
            if obj["used"] >= MAX_DAILY:
                raise Stop("Daily API budget exceeded")
            obj["used"] += 1
        self.change(claim)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Stop("Redirect rejected; secrets not forwarded")

def api_json(budget, method, path, headers, payload=None, opener=None):
    if not ((method=="POST" and path=="/api/v1/session") or
            (method=="GET" and path.startswith("/api/v1/clientsentiment?marketIds="))):
        raise Stop("Trading/non-approved endpoint forbidden")
    budget.spend()
    request = urllib.request.Request(BASE+path,
        data=None if payload is None else json.dumps(payload).encode("utf-8"),
        headers=headers, method=method)
    transport = opener or urllib.request.build_opener(NoRedirect())
    try:
        with transport.open(request, timeout=15) as response:
            if response.status != 200: raise Stop("Provider status not OK")
            data = response.read(MAX_RESPONSE+1)
            if len(data)>MAX_RESPONSE: raise Stop("Too many response bytes")
            obj = json.loads(data.decode("utf-8"))
            if not isinstance(obj, dict): raise Stop("Invalid response shape")
            return obj, response.headers
    except (urllib.error.HTTPError, urllib.error.URLError, ValueError,
            UnicodeError, TimeoutError, OSError) as exc:
        # No printing original error, response body, auth header or URL.
        raise Stop("Capital API failed") from exc

def percent(value):
    if value is None or isinstance(value,bool): return None
    try: number=float(value)
    except (ValueError,TypeError): return None
    return number if math.isfinite(number) and 0 <= number <=100 else None

def parse(payload, mapping, timestamp):
    rows = payload.get("clientSentiments") if isinstance(payload,dict) else None
    if not isinstance(rows,list): raise Stop("Client sentiment array missing")
    by_market={value:key for key,value in mapping.items()}
    result={}
    for entry in rows:
        if not isinstance(entry,dict): continue
        symbol=by_market.get(entry.get("marketId"))
        if not symbol: continue
        long=percent(entry.get("longPositionPercentage"))
        short=percent(entry.get("shortPositionPercentage"))
        if long is None or short is None or abs(long+short-100)>0.51: continue
        result[symbol]={"t":timestamp, "lPct":long, "sPct":short,
                        "metric":"client_positions"}
    if not result: raise Stop("No supported valid numeric market received")
    return result

def collect(budget, mapping, key, identifier, password, opener=None, clock=now_utc):
    """Exactly 2 HTTP requests per attempt, both on the DEMO host."""
    budget.start()
    headers={"X-CAP-API-KEY":key, "Accept":"application/json",
             "Content-Type":"application/json"}
    _, token_headers=api_json(budget,"POST","/api/v1/session", headers,
        {"identifier":identifier,"password":password,"encryptedPassword":False},opener)
    cst=token_headers.get("CST")
    xst=token_headers.get("X-SECURITY-TOKEN")
    if not cst or not xst: raise Stop("Demo session tokens missing")
    path="/api/v1/clientsentiment?"+urllib.parse.urlencode(
        {"marketIds":",".join(mapping.values())},safe=",")
    response,_=api_json(budget,"GET",path,{"CST":cst,"X-SECURITY-TOKEN":xst,
                  "X-CAP-API-KEY":key,"Accept":"application/json"},opener=opener)
    observed=stamp(clock())
    return {"status":"ok", "source":"Capital.com Client Sentiment",
            "environment":"demo","metric":"client_positions",
            "updatedAt":observed,"symbols":parse(response,mapping,observed)}

def save(private, snapshot, clock=now_utc):
    cutoff=clock()-dt.timedelta(days=90)
    for symbol,item in snapshot["symbols"].items():
        path=private/"history"/(symbol+".json")
        old=read_private(path,{})
        if not isinstance(old,dict) or not isinstance(old.get("records",[]),list):
            raise Stop("Damaged history")
        records={}
        for row in old.get("records",[]):
            if not isinstance(row,dict) or not isinstance(row.get("t"),str): continue
            try: t=dt.datetime.fromisoformat(row["t"].replace("Z","+00:00"))
            except ValueError: continue
            if t.tzinfo is None or t<cutoff: continue
            if percent(row.get("lPct")) is None or percent(row.get("sPct")) is None: continue
            records[row["t"]]=row
        records[item["t"]]=item
        write_private(path,{"symbol":symbol,"source":"Capital.com Client Sentiment",
            "sampling":"observations every 2h maximum; no historical backfill",
            "records":[records[k] for k in sorted(records)][-1100:]})
    write_private(private/"latest.json",snapshot)

def main():
    if os.getenv("REMURA_CAPITAL_ENABLED")!="1":
        print("Capital demo disabled. No requests."); return 0
    key=os.getenv("CAPITAL_API_KEY","").strip()
    identifier=os.getenv("CAPITAL_IDENTIFIER","").strip()
    password=os.getenv("CAPITAL_API_PASSWORD","")
    if not all((key,identifier,password)):
        print("Capital demo awaiting credentials. No requests."); return 0
    try:
        mapping=market_map(PRIVATE)
        sample=collect(Budget(PRIVATE),mapping,key,identifier,password)
        save(PRIVATE,sample)
    except (Stop, OSError, ValueError):
        print("Capital demo skipped/failed safely; old history preserved."); return 1
    print("Capital demo numeric snapshots saved:",len(sample["symbols"]))
    return 0

if __name__=="__main__":
    sys.exit(main())
