#!/usr/bin/env python3
"""Private cTrader OAuth bootstrap. No secrets or tokens are returned to HTTP clients."""
from __future__ import annotations

import datetime as dt
import json
import re
import urllib.parse
import urllib.request
from urllib.parse import urlsplit

from ctrader_tokens import path_for, safe_write
from price_feed import utcnow

GRANT_URL = "https://id.ctrader.com/my/settings/openapi/grantingaccess/"
TOKEN_URL = "https://openapi.ctrader.com/apps/token"


def settings(env):
    """Validate a real HTTPS tailnet redirect; never accept a public callback."""
    cid = env.get("CTRADER_CLIENT_ID", "").strip()
    secret = env.get("CTRADER_CLIENT_SECRET", "").strip()
    redirect = env.get("CTRADER_REDIRECT_URI", "").strip()
    parsed = urlsplit(redirect)
    if not cid or not secret or not redirect:
        raise ValueError("Configurazione cTrader incompleta.")
    if (parsed.scheme != "https" or not parsed.hostname or
            not parsed.hostname.endswith(".ts.net") or
            parsed.username or parsed.password or parsed.port not in (None, 443) or
            parsed.path != "/ctrader/callback" or parsed.query or parsed.fragment):
        raise ValueError("Redirect cTrader: usare HTTPS Tailscale Serve con /ctrader/callback.")
    return cid, secret, redirect


def authorization_url(env):
    cid, _, redirect = settings(env)
    query = urllib.parse.urlencode({
        "client_id": cid,
        "redirect_uri": redirect,
        "scope": "accounts",       # NEVER request trading permission
        "product": "web",
    })
    return GRANT_URL + "?" + query


def exchange_code(code, env, database, requester=None):
    """Exchange a short-lived code and atomically store tokens with chmod 0600.

    No secret, code or token is printed or included in any exception.
    GET is required by the cTrader documented authorization_code token endpoint.
    """
    cid, secret, redirect = settings(env)
    if (not isinstance(code, str) or
            not re.fullmatch(r"[A-Za-z0-9._~-]{8,512}", code)):
        raise ValueError("Codice OAuth non valido.")
    url = TOKEN_URL + "?" + urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect,
        "client_id": cid,
        "client_secret": secret,
    })
    request = urllib.request.Request(
        url, headers={"Accept": "application/json", "Cache-Control": "no-store"})
    try:
        if requester is None:
            with urllib.request.urlopen(request, timeout=15) as reply:
                payload = json.loads(reply.read(20_000).decode("utf-8"))
        else:
            payload = requester(request)
        if (not isinstance(payload, dict) or payload.get("errorCode") or
                not payload.get("accessToken") or not payload.get("refreshToken")):
            raise ValueError("Risposta OAuth non valida.")
        ttl = int(payload.get("expiresIn", 0))
        if not 3600 <= ttl <= 365 * 86400:
            raise ValueError("Durata token OAuth non valida.")
        safe_write(path_for(database), {
            "accessToken": str(payload["accessToken"]),
            "refreshToken": str(payload["refreshToken"]),
            "expiresAt": (utcnow() + dt.timedelta(seconds=ttl)).isoformat(),
        })
    except Exception:
        raise RuntimeError("cTrader OAuth non riuscito: ripetere l'autorizzazione privata.") from None
    return True
