#!/usr/bin/env python3
"""REMURA Private: local-only web app + automatic cTrader collector.

Run python scripts/private_server.py on a trusted always-on machine/VPS.
DEFAULTS: 127.0.0.1:8765, NO external network exposure, collector disabled
until explicit opt-in and approved Spotware read-only credentials.

For iPhone reachability, put an authenticated private reverse proxy/tunnel
(e.g. Cloudflare Tunnel + Access policy limited to one email) IN FRONT.
Never use an anonymous/Quick Tunnel, public bind, or GitHub Pages for this.
"""
from __future__ import annotations

import datetime as dt
import importlib.util
import json
import mimetypes
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from price_feed import MARKETS, UTC, utcnow
from price_store import connect, get_status, set_status, latest, ingest, api_document, symbols_available
from ctrader_tokens import access_token, path_for, read_file

ROOT=Path(__file__).resolve().parents[1]
STORE=ROOT/"private"/"remura-prices.sqlite3"
SERVER_HOST="127.0.0.1"
SAFE_ASSETS={
    "index.html","asset.html","catalogo.html","forex.html","fonti.html","mercati.html",
    "nav.js","nav.css","retail.js","retail.css","insights.js","insights.css","insights-core.js","cot-indices-core.js",
    "sentiment-core.js","sentiment-trend-core.js","sentiment-trend.js","sentiment-trend.css",
    "sources.js","sources.css","capital-cloud-config.js","capital-cloud.js",
    "impostazioni.html","impostazioni.js","feed-health-core.js","price.js","price.css","price-core.js","sw.js",
    "manifest.webmanifest","icon.svg",
}
STATUS_PATH="/private-api/health"
UPDATE_STATUS_PATH="/private-api/autoupdate"
RETAIL_LATEST="/private-api/retail/latest.json"
IG_LATEST="/private-api/ig/latest.json"
CAPITAL_LATEST="/private-api/capital/latest.json"
CAPITAL_HISTORY_RE=re.compile(r"^/private-api/capital/history/([A-Z0-9]{3,8})[.]json$")
RETAIL_HISTORY_RE=re.compile(r"^/private-api/retail/history/([A-Z0-9]{3,8})[.]json$")
PRICE_RE=re.compile(r"^/private-api/prices/([A-Z0-9]{3,8})$")


def safe_update_status(db_path):
    """Expose only public updater state, never private credentials."""
    file=Path(db_path).resolve().parent/"autoupdate-state.json"
    if not file.is_file() or file.stat().st_size>8192:
        return {"enabled":False,"state":"not_configured"}
    try:data=json.loads(file.read_text("utf-8"))
    except (OSError,ValueError):return {"enabled":False,"state":"unavailable"}
    if not isinstance(data,dict):return {"enabled":False,"state":"unavailable"}
    keys=("enabled","state","installedSha","targetSha","failedSha","skippedSha","manualSha","lastCheck","lastSuccess","message")
    return {k:data[k] for k in keys if k in data and
            (isinstance(data[k],bool) if k=="enabled" else isinstance(data[k],str))}

def source_configured(env=None,db_path=None):
    env=os.environ if env is None else env
    basic=all(env.get(name) for name in ("CTRADER_CLIENT_ID","CTRADER_CLIENT_SECRET","CTRADER_ACCOUNT_ID"))
    authorised=bool(env.get("CTRADER_REFRESH_TOKEN") or env.get("CTRADER_ACCESS_TOKEN"))
    if db_path is not None and read_file(path_for(db_path)):
        authorised=True
    return basic and authorised


def resolve_asset(url_path):
    path=urlsplit(url_path).path
    if path=="/":
        path="/index.html"
    filename=path.removeprefix("/")
    if filename not in SAFE_ASSETS or "/" in filename or "\\" in filename:
        return None
    candidate=ROOT/filename
    return candidate if candidate.is_file() else None


def retail_document(db_path,path):
    """Read only valid aggregate files inside private/myfxbook, never public repo files."""
    db_path=Path(db_path).resolve()
    source=db_path.parent/"myfxbook"/"data"/"myfxbook"
    if path==RETAIL_LATEST:
        filepath=source/"latest.json"
        symbol=None
    else:
        match=RETAIL_HISTORY_RE.fullmatch(path)
        if not match or match.group(1) not in MARKETS:
            return None
        symbol=match.group(1)
        filepath=source/"history"/(symbol+".json")
    if not filepath.is_file() or filepath.stat().st_size>3_000_000:
        return None
    try:
        data=json.loads(filepath.read_text("utf-8"))
    except (OSError,ValueError):
        return None
    if not isinstance(data,dict):
        return None
    if symbol is None:
        if data.get("status")!="ok" or not isinstance(data.get("symbols"),dict):
            return None
        return {"status":"ok","source":"Myfxbook Community Outlook",
                "updatedAt":data.get("updatedAt"),
                "symbols":{s:v for s,v in data["symbols"].items() if s in MARKETS}}
    if data.get("symbol")!=symbol or not isinstance(data.get("records"),list):
        return None
    return {"symbol":symbol,"source":"Myfxbook Community Outlook",
            "records":data["records"][-2250:]}



def capital_document(db_path,path):
    """Release numeric-only Capital aggregates from private disk, not credentials."""
    private=Path(db_path).resolve().parent/"capital"
    if path==CAPITAL_LATEST:
        filename=private/"latest.json"
        symbol=None
    else:
        match=CAPITAL_HISTORY_RE.fullmatch(path)
        if not match or match.group(1) not in MARKETS:
            return None
        symbol=match.group(1)
        filename=private/"history"/(symbol+".json")
    if not filename.is_file() or filename.stat().st_size>3_000_000:
        return None
    try:
        content=json.loads(filename.read_text("utf-8"))
    except (ValueError,OSError):
        return None
    if not isinstance(content,dict):
        return None
    if symbol is None:
        if content.get("status")!="ok" or content.get("environment")!="demo":
            return None
        items=content.get("symbols")
        if not isinstance(items,dict):
            return None
    else:
        if content.get("symbol")!=symbol or not isinstance(content.get("records"),list):
            return None
        items={symbol:content["records"]}
    def validated(item):
        if not isinstance(item,dict):
            return None
        try:
            long=float(item.get("lPct"))
            short=float(item.get("sPct"))
        except (TypeError,ValueError):
            return None
        if not (math.isfinite(long) and math.isfinite(short) and
                0<=long<=100 and 0<=short<=100 and abs(long+short-100)<=0.51):
            return None
        t=item.get("t")
        if not isinstance(t,str) or not 15<=len(t)<=40:
            return None
        return {"t":t,"lPct":long,"sPct":short,"metric":"client_positions"}
    if symbol is None:
        cleaned={k:v for k,row in items.items() if k in MARKETS
                 if (v:=validated(row)) is not None}
        if not cleaned:
            return None
        return {"status":"ok","source":"Capital.com Client Sentiment",
                "environment":"demo","updatedAt":content.get("updatedAt"),
                "symbols":cleaned}
    records=[value for item in items[symbol]
             if (value:=validated(item)) is not None]
    return {"symbol":symbol,"source":"Capital.com Client Sentiment",
            "records":records[-1100:]} if records else None


def ig_document(db_path):
    """Read a strictly filtered local snapshot, never expose private IG credentials."""
    source=Path(db_path).resolve().parent/"ig"/"latest.json"
    if not source.is_file() or source.stat().st_size>250_000:
        return None
    try:
        data=json.loads(source.read_text("utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data,dict) or data.get("status")!="ok":
        return None
    symbols=data.get("symbols")
    if not isinstance(symbols,dict):
        return None
    checked={}
    for symbol,item in symbols.items():
        if symbol not in MARKETS or not isinstance(item,dict):
            continue
        try:
            l=float(item.get("lPct"))
            short=float(item.get("sPct"))
        except (TypeError,ValueError):
            continue
        if not (math.isfinite(l) and math.isfinite(short) and
                0<=l<=100 and 0<=short<=100 and abs(l+short-100)<=1):
            continue
        stamp=item.get("t")
        if not isinstance(stamp,str) or len(stamp)>40:
            continue
        checked[symbol]={"t":stamp,"lPct":l,"sPct":short,"metric":"client_positions"}
    if not checked:
        return None
    return {"status":"ok","source":"IG Client Sentiment",
            "environment":data.get("environment") if data.get("environment") in ("demo","live") else "unknown",
            "updatedAt":data.get("updatedAt"),"symbols":checked}


def http_handler(db_path):
    class Handler(BaseHTTPRequestHandler):
        server_version="REMURA-Private/1.0"
        sys_version=""

        def log_message(self, format, *args):
            # Never log URL parameters, OAuth tokens, browser cookies or secrets.
            sys.stderr.write("REMURA private HTTP: request served\n")

        def response(self, code, body, mime="application/json; charset=utf-8", cacheable=False):
            if isinstance(body,dict):
                payload=json.dumps(body,separators=(",",":"),ensure_ascii=False).encode("utf-8")
            elif isinstance(body,bytes):
                payload=body
            else:
                payload=str(body).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type",mime)
            self.send_header("Content-Length",str(len(payload)))
            self.send_header("Cache-Control","public, max-age=300" if cacheable else "no-store, max-age=0")
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("Referrer-Policy","strict-origin-when-cross-origin")
            self.send_header("X-Frame-Options","DENY")
            self.send_header("Cross-Origin-Resource-Policy","same-origin")
            self.end_headers()
            if self.command!="HEAD":
                try:
                    self.wfile.write(payload)
                except (ConnectionResetError,BrokenPipeError):
                    pass

        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            path=urlsplit(self.path).path
            if path==UPDATE_STATUS_PATH:
                self.response(200,safe_update_status(db_path))
                return
            if path==CAPITAL_LATEST or CAPITAL_HISTORY_RE.fullmatch(path):
                data=capital_document(db_path,path)
                if data is None:self.response(503,{"error":"capital_not_collected"})
                else:self.response(200,data)
                return
            if path==IG_LATEST:
                data=ig_document(db_path)
                if data is None:self.response(503,{"error":"ig_not_collected"})
                else:self.response(200,data)
                return
            if path==RETAIL_LATEST or RETAIL_HISTORY_RE.fullmatch(path):
                data=retail_document(db_path,path)
                if data is None:self.response(503,{"error":"retail_not_collected"})
                else:self.response(200,data)
                return
            if path==STATUS_PATH or PRICE_RE.fullmatch(path):
                db=connect(db_path)
                try:
                    if path==STATUS_PATH:
                        status=get_status(db)
                        self.response(200,{
                            "name":"REMURA Private",
                            "collector":status.get("collector","disabled"),
                            "ctraderPreflight":ctrader_preflight(db_path),
                            "collectorLastCount":status.get("last_count"),
                            "collectorLastRejected":status.get("last_rejected"),
                            "lastSuccess":status.get("last_success"),
                            "lastAttempt":status.get("last_attempt"),
                            "lastError":status.get("last_error"),
                            "retailStatus":status.get("retail_status","disabled"),
                            "retailLastSuccess":status.get("retail_last_success"),
                            "capitalStatus":status.get("capital_status","disabled"),
                            "capitalLastSuccess":status.get("capital_last_success"),
                            "igStatus":status.get("ig_status","disabled"),
                            "igLastSuccess":status.get("ig_last_success"),
                            "instruments":symbols_available(db),
                            "serverTime":utcnow().isoformat(),
                        })
                        return
                    match=PRICE_RE.fullmatch(path)
                    symbol=match.group(1) if match else ""
                    if symbol not in MARKETS:
                        self.response(404,{"error":"unknown_symbol"})
                        return
                    body=api_document(db,symbol)
                    if body is None:
                        self.response(503,{"error":"price_not_collected","symbol":symbol,
                                           "message":"Il feed cTrader non ha ancora raccolto questo strumento."})
                    else:
                        self.response(200,body)
                finally:
                    db.close()
                return

            file=resolve_asset(path)
            if file is None:
                self.response(404,{"error":"not_found"})
                return
            mimetype,_=mimetypes.guess_type(str(file))
            if file.suffix==".webmanifest":
                mimetype="application/manifest+json"
            self.response(200,file.read_bytes(),(mimetype or "application/octet-stream"),
                          cacheable=file.suffix in (".css",".js",".svg",".png",".ico"))
    return Handler


def collector_batches(symbols, size=5):
    """Bound each UTC quarter to a small group; never start 35*30 API calls."""
    if not isinstance(size,int) or not 1<=size<=8:
        raise ValueError("Batch size must be 1..8")
    unique=list(dict.fromkeys(symbols))
    if any(symbol not in MARKETS for symbol in unique):
        raise ValueError("Unexpected REMURA symbol")
    return [unique[i:i+size] for i in range(0,len(unique),size)]


def safe_ctrader_reason(payload, process_code=0):
    """Limited diagnostic vocabulary: never show raw provider bodies or credentials."""
    if not isinstance(payload,dict):
        return "La sorgente cTrader non ha restituito un archivio valido."
    errors=payload.get("errors")
    if not isinstance(errors,dict):
        errors={}
    reasons=[str(v) for v in errors.values() if isinstance(v,str)]
    if any("Ticker non disponibile o ambiguo" in value for value in reasons):
        return "Alcuni simboli non corrispondono ai ticker del broker. Serve una mappatura privata."
    if any("non è autorizzato" in value for value in reasons):
        return "Conto cTrader non autorizzato dal token o ambiente demo/live non coerente."
    if any("Timeout della raccolta" in value for value in reasons):
        return "Timeout delle richieste storiche cTrader: riduci numero mercati o controlla la rete."
    if any("cTrader ha segnalato un errore API" in value for value in reasons):
        return "API cTrader ha rifiutato una richiesta: verifica account, token o limiti."
    if any("Nessuna candela storica" in value for value in reasons):
        return "cTrader non ha restituito candele per i ticker richiesti."
    if any("Connessione cTrader interrotta" in value for value in reasons):
        return "Connessione cTrader interrotta."
    if any("Risposta cTrader inattesa" in value for value in reasons):
        return "Formato di risposta cTrader non atteso."
    return "Nessuna candela verificata. Controllare SDK, OAuth e simboli del broker."


def ctrader_preflight(db_path=None):
    """Safe health checks; never include account ID, symbols, tokens or URLs."""
    try:
        installed=importlib.util.find_spec("ctrader_open_api") is not None
    except (ImportError,ValueError):
        installed=False
    selected=os.environ.get("CTRADER_ENV","demo").lower()
    ready=source_configured(db_path=db_path)
    return {"sdk":"installed" if installed else "missing",
            "configuration":"ready" if ready else "incomplete",
            "environment":selected if selected in ("demo","live") else "invalid",
            "enabled":os.environ.get("REMURA_COLLECTOR_ENABLED","0")=="1"}


def collector_command(symbols, days, output):
    script=ROOT/"scripts"/"ctrader_feed.py"
    args=[sys.executable,str(script),"--days",str(days),
          "--symbols",*symbols,"--output",str(output)]
    private_aliases=ROOT/"private"/"ctrader-symbols.json"
    if private_aliases.is_file():
        args+=["--symbol-map",str(private_aliases)]
    return args


def collect_once(db_path, symbols, days=2, runner=subprocess.run, now=None):
    """Isolated child process: Twisted reactor and cTrader TCP live outside HTTP server.

    No secrets in args; all cTrader credentials are inherited via environment.
    No file is written under the public asset allowlist.
    """
    now=now or utcnow()
    if not source_configured(db_path=db_path):
        db=connect(db_path)
        try:set_status(db,collector="awaiting_approval",last_error="App cTrader/token non configurati")
        finally:db.close()
        return {"saved":{},"errors":{"configuration":"ctrader not configured"}}
    check=ctrader_preflight(db_path)
    if check["sdk"]!="installed":
        db=connect(db_path)
        try:set_status(db,collector="missing_sdk",last_error="SDK ctrader-open-api assente nel Python della VPS.")
        finally:db.close()
        return {"saved":{},"errors":{"sdk":"missing"}}
    db=connect(db_path)
    try:
        set_status(db,collector="collecting",last_attempt=now.isoformat())
    finally:
        db.close()
    private_dir=Path(db_path).resolve().parent
    private_dir.mkdir(parents=True,exist_ok=True)
    temp_path=None
    try:
        with tempfile.NamedTemporaryFile(prefix="remura-ctrader-",suffix=".json",
                                         dir=private_dir,delete=False) as temp:
            temp_path=Path(temp.name)
        temp_path.chmod(0o600)
        # Access token is passed to the child through private environment only.
        # Refresh token is rotated on disk automatically when near expiry.
        token=access_token(db_path)
        env=dict(os.environ)
        env["CTRADER_ACCESS_TOKEN"]=token
        env.pop("CTRADER_REFRESH_TOKEN",None)
        command=collector_command(symbols,days,temp_path)
        process=runner(command,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL,timeout=12*60,check=False)
        if not temp_path.is_file() or temp_path.stat().st_size<50:
            raise RuntimeError("Collettore senza risposta valida da cTrader.")
        if temp_path.stat().st_size>15_000_000:
            raise RuntimeError("Risposta del collettore troppo grande.")
        payload=json.loads(temp_path.read_text("utf-8"))
        db=connect(db_path)
        try:
            report=ingest(db,payload,now=utcnow())
            count=len(report["saved"])
            errors=len(report["errors"])+len(payload.get("errors",{}))
            reason=safe_ctrader_reason(payload,getattr(process,"returncode",0))
            set_status(db,
                       collector=("running" if count else "no_data"),
                       last_success=(utcnow().isoformat() if count else get_status(db).get("last_success","")),
                       last_error=("" if count else reason),
                       last_count=str(count),
                       last_rejected=str(errors))
        finally:
            db.close()
        return report
    except (ValueError,RuntimeError,TimeoutError,subprocess.SubprocessError, OSError, json.JSONDecodeError):
        db=connect(db_path)
        try:
            set_status(db,collector="failed",last_error="Lettore cTrader terminato senza archivio valido: verificare SDK, OAuth e connessione.")
        finally:
            db.close()
        return {"saved":{},"errors":{"collector":"No usable output"}}
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def retail_once(db_path,runner=subprocess.run):
    """Reuse the existing official Myfxbook API collector in a PRIVATE cwd.

    No Git commits, no data writes to public repository, no credentials in stdout.
    """
    db=connect(db_path)
    if not (os.environ.get("MYFXBOOK_EMAIL") and os.environ.get("MYFXBOOK_PASSWORD")):
        try:set_status(db,retail_status="awaiting_credentials")
        finally:db.close()
        return False
    try:set_status(db,retail_status="collecting")
    finally:db.close()
    target=Path(db_path).resolve().parent/"myfxbook"
    target.mkdir(parents=True,exist_ok=True,mode=0o700)
    command=[sys.executable,str(ROOT/"scripts"/"update_myfxbook.py")]
    try:
        run=runner(command,cwd=target,stdin=subprocess.DEVNULL,
                   stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                   timeout=120,check=False)
        latest_file=target/"data"/"myfxbook"/"latest.json"
        data=retail_document(db_path,RETAIL_LATEST)
        if run.returncode!=0 or data is None:
            raise RuntimeError("Nessun aggiornamento Myfxbook convalidato.")
        db=connect(db_path)
        try:set_status(db,retail_status="running",retail_last_success=utcnow().isoformat(),
                       retail_last_error="")
        finally:db.close()
        return True
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError):
        db=connect(db_path)
        try:set_status(db,retail_status="failed",retail_last_error="Myfxbook non aggiornato.")
        finally:db.close()
        return False


def ig_once(db_path,runner=subprocess.run):
    """Collect optional IG client sentiment locally; never commit or log secrets."""
    credentials=("IG_API_KEY","IG_IDENTIFIER","IG_PASSWORD")
    db=connect(db_path)
    if not all(os.environ.get(name) for name in credentials):
        try:set_status(db,ig_status="awaiting_credentials")
        finally:db.close()
        return False
    try:set_status(db,ig_status="collecting")
    finally:db.close()
    output=Path(db_path).resolve().parent/"ig"/"latest.json"
    env=dict(os.environ)
    env["REMURA_IG_OUTPUT"]=str(output)
    command=[sys.executable,str(ROOT/"scripts"/"update_ig.py")]
    try:
        run=runner(command,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,
                   stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                   timeout=120,check=False)
        data=ig_document(db_path)
        if run.returncode!=0 or data is None:
            raise RuntimeError("IG unavailable.")
        db=connect(db_path)
        try:set_status(db,ig_status="running",ig_last_success=utcnow().isoformat(),
                       ig_last_error="")
        finally:db.close()
        return True
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError):
        db=connect(db_path)
        try:set_status(db,ig_status="failed",ig_last_error="IG non aggiornato.")
        finally:db.close()
        return False



def capital_once(db_path,runner=subprocess.run):
    """Isolated demo-only Capital read; persistent budget is private and not reset."""
    db=connect(db_path)
    creds=("CAPITAL_API_KEY","CAPITAL_IDENTIFIER","CAPITAL_API_PASSWORD")
    if not all(os.environ.get(k) for k in creds):
        try:set_status(db,capital_status="awaiting_credentials")
        finally:db.close()
        return False
    try:set_status(db,capital_status="collecting")
    finally:db.close()
    directory=Path(db_path).resolve().parent/"capital"
    directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    env=dict(os.environ)
    env["REMURA_CAPITAL_PRIVATE_DIR"]=str(directory)
    env["REMURA_CAPITAL_ENABLED"]="1"
    command=[sys.executable,str(ROOT/"scripts"/"update_capital.py")]
    try:
        outcome=runner(command,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                       timeout=120,check=False)
        if outcome.returncode!=0 or capital_document(db_path,CAPITAL_LATEST) is None:
            raise RuntimeError("No valid Capital demo data")
        db=connect(db_path)
        try:set_status(db,capital_status="running",
                       capital_last_success=utcnow().isoformat(),capital_last_error="")
        finally:db.close()
        return True
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError):
        db=connect(db_path)
        try:set_status(db,capital_status="failed",
                       capital_last_error="Capital demo unavailable or budget exhausted")
        finally:db.close()
        return False


def capital_loop(db_path,stop):
    while not stop.is_set():
        capital_once(db_path)
        stop.wait(next_cycle(2*60*60,180))


def ig_loop(db_path,stop):
    while not stop.is_set():
        ig_once(db_path)
        stop.wait(next_cycle(60*60,150))


def next_cycle(interval_sec,grace_sec,now=None):
    timestamp=(now or utcnow()).timestamp()
    return max(2.0,((int(timestamp)//interval_sec)+1)*interval_sec+grace_sec-timestamp)


def retail_loop(db_path,stop):
    while not stop.is_set():
        retail_once(db_path)
        stop.wait(next_cycle(20*60,90))


def seconds_to_next_quarter(now=None):
    now=now or utcnow()
    # Run shortly after UTC quarter closes so the M15 candle is final.
    stamp=now.timestamp()
    quarter=900
    next_event=((int(stamp)//quarter)+1)*quarter+90
    return max(2.0,next_event-stamp)


def collector_loop(db_path,stop,env=None):
    symbols_text=os.environ.get("REMURA_SYMBOLS","all").strip().upper()
    symbols=sorted(MARKETS) if symbols_text in ("ALL","") else list(dict.fromkeys(
        value for value in re.split(r"[,\s]+",symbols_text) if value in MARKETS
    ))
    if not symbols:
        db=connect(db_path)
        try:set_status(db,collector="invalid_symbols",last_error="REMURA_SYMBOLS non contiene mercati validi.")
        finally:db.close()
        return
    batches=collector_batches(symbols)
    cursor=0
    while not stop.is_set():
        batch=batches[cursor % len(batches)]
        cursor+=1
        db=connect(db_path)
        try:
            stored=set(symbols_available(db))
            set_status(db,collector_batch=str(cursor % len(batches)+1)+"/"+str(len(batches)),
                       collector_batch_symbols=str(len(batch)))
        finally:db.close()
        cold=[item for item in batch if item not in stored]
        warm=[item for item in batch if item in stored]
        # At most 5 symbols * 21 daily requests per new batch, vs 35*30 before.
        # 21 days give enough completed H4 candles for EMA50 on most FX markets.
        if cold:
            collect_once(db_path,cold,days=21)
        if warm and not stop.is_set():
            collect_once(db_path,warm,days=2)
        stop.wait(seconds_to_next_quarter())


def main():
    import argparse
    p=argparse.ArgumentParser(description="REMURA private localhost server and scheduled cTrader ingestion")
    p.add_argument("--port",type=int,default=8765)
    p.add_argument("--database",default=str(STORE))
    args=p.parse_args()
    if not 1024<=args.port<=65535:
        p.error("Port must be between 1024 and 65535")
    db_path=Path(args.database).expanduser().resolve()
    db=connect(db_path)
    try:
        if os.environ.get("REMURA_COLLECTOR_ENABLED","0")=="1":
            set_status(db,collector="starting")
        else:
            set_status(db,collector="disabled",last_error="Raccolta disattivata: imposta REMURA_COLLECTOR_ENABLED=1 dopo approvazione e configurazione privata.")
    finally:
        db.close()
    stop=threading.Event()
    if os.environ.get("REMURA_COLLECTOR_ENABLED","0")=="1":
        thread=threading.Thread(target=collector_loop,args=(db_path,stop),daemon=True)
        thread.start()
    if os.environ.get("REMURA_RETAIL_ENABLED","0")=="1":
        thread_retail=threading.Thread(target=retail_loop,args=(db_path,stop),daemon=True)
        thread_retail.start()
    if os.environ.get("REMURA_CAPITAL_ENABLED","0")=="1":
        thread_capital=threading.Thread(target=capital_loop,args=(db_path,stop),daemon=True)
        thread_capital.start()
    if os.environ.get("REMURA_IG_ENABLED","0")=="1":
        thread_ig=threading.Thread(target=ig_loop,args=(db_path,stop),daemon=True)
        thread_ig.start()
    server=ThreadingHTTPServer((SERVER_HOST,args.port),http_handler(db_path))
    print("REMURA Private listening ONLY on http://127.0.0.1:"+str(args.port))
    print("Do NOT expose without authentication. Use Cloudflare Tunnel with a validated Access policy for the iPhone.")
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()


if __name__=="__main__":
    main()
