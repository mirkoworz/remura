#!/usr/bin/env python3
"""cTrader OAuth token rotation for a PRIVATE always-on REMURA service.

OAuth refresh is performed ONLY on the private host using official Spotware
/apps/token endpoint. The access/refresh tokens are stored in an ignored,
chmod-0600 JSON file, never committed, served, logged or put in URL of this app.
The initial OAuth user consent MUST be completed manually after approval.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import tempfile
import urllib.error
import urllib.parse
import urllib.request

from price_feed import UTC, utcnow

TOKEN_NAME = "ctrader-tokens.json"
REFRESH_MARGIN = dt.timedelta(days=2)


def path_for(db_path,source="primary"):
    if source not in ("primary","backup"):
        raise ValueError("Invalid cTrader source")
    name=TOKEN_NAME if source=="primary" else "ctrader-backup-tokens.json"
    return Path(db_path).expanduser().resolve().parent/name


def read_file(path):
    if not Path(path).is_file():
        return None
    try:
        data=json.loads(Path(path).read_text("utf-8"))
        return data if isinstance(data,dict) else None
    except (OSError,ValueError):
        return None


def safe_write(path,payload):
    """Atomic replace in ignored private directory, restrictive permissions."""
    dest=Path(path).resolve()
    dest.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    filename=None
    try:
        with tempfile.NamedTemporaryFile(prefix=".ctrader-",suffix=".tmp",
                                         dir=dest.parent,delete=False,mode="w",encoding="utf-8") as fh:
            filename=Path(fh.name)
            os.chmod(filename,0o600)
            json.dump(payload,fh,ensure_ascii=False,separators=(",",":"))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(filename,dest)
        os.chmod(dest,0o600)
    finally:
        if filename and filename.exists():
            filename.unlink()


def refresh(client_id,client_secret,refresh_token,now=None,requester=None):
    """Never include an OAuth token in exceptions, API logs or HTTP responses."""
    if not all((client_id,client_secret,refresh_token)):
        raise RuntimeError("Missing private cTrader OAuth refresh credentials.")
    now=now or utcnow()
    params=urllib.parse.urlencode({
        "grant_type":"refresh_token",
        "refresh_token":refresh_token,
        "client_id":client_id,
        "client_secret":client_secret,
    })
    url="https://openapi.ctrader.com/apps/token?"+params
    request=urllib.request.Request(url,method="POST",headers={"Accept":"application/json"})
    try:
        if requester is None:
            with urllib.request.urlopen(request,timeout=20) as response:
                payload=json.loads(response.read(20_000).decode("utf-8"))
        else:
            payload=requester(request)
    except (OSError,ValueError,urllib.error.URLError):
        raise RuntimeError("cTrader OAuth refresh failed; reconnect locally without sharing tokens.") from None
    if not isinstance(payload,dict) or payload.get("errorCode") or not payload.get("accessToken") or not payload.get("refreshToken"):
        raise RuntimeError("cTrader OAuth rejected the refresh attempt.")
    expires=payload.get("expiresIn")
    try:
        expires=int(expires)
    except (TypeError,ValueError):
        raise RuntimeError("cTrader OAuth returned no expiry duration.") from None
    if expires<3600 or expires>365*86400:
        raise RuntimeError("Invalid cTrader OAuth expiry.")
    return {
        "accessToken":str(payload["accessToken"]),
        "refreshToken":str(payload["refreshToken"]),
        "expiresAt":(now+dt.timedelta(seconds=expires)).isoformat(),
    }


def access_token(db_path,env=None,now=None,requester=None,source="primary"):
    env=os.environ if env is None else env
    now=now or utcnow()
    file=path_for(db_path,source=source)
    stored=read_file(file)
    if stored and stored.get("accessToken") and stored.get("refreshToken"):
        try:
            expiry=dt.datetime.fromisoformat(str(stored["expiresAt"]))
            if expiry.tzinfo is None:
                raise ValueError("Expiry missing timezone")
            if expiry > now+REFRESH_MARGIN:
                return str(stored["accessToken"])
        except (ValueError,KeyError,TypeError):
            pass
        updated=refresh(env.get("CTRADER_CLIENT_ID"),env.get("CTRADER_CLIENT_SECRET"),
                        stored["refreshToken"],now=now,requester=requester)
        safe_write(file,updated)
        return updated["accessToken"]
    # The user has explicitly authorised the app and installed an INITIAL refresh
    # token on the private computer. Refresh immediately to verify, rotate and
    # persist it; no need to know when the initial access token was issued.
    initial=env.get("CTRADER_REFRESH_TOKEN","")
    if initial:
        updated=refresh(env.get("CTRADER_CLIENT_ID"),env.get("CTRADER_CLIENT_SECRET"),
                        initial,now=now,requester=requester)
        safe_write(file,updated)
        return updated["accessToken"]
    legacy=env.get("CTRADER_ACCESS_TOKEN","")
    if legacy:
        return legacy  # Legacy/testing: will eventually expire without a refresh token.
    raise RuntimeError("cTrader OAuth token missing; app approval and accounts-only authorisation required.")
