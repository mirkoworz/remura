#!/usr/bin/env python3
"""Private cTrader OAuth bootstrap for REMURA (Tailscale Serve, accounts scope only).

The authorization code is redeemed on the private server within its short life.
No tokens, codes, client secrets, or account data are returned to the browser.
"""
from __future__ import annotations

import datetime as dt
import json
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from ctrader_tokens import path_for, safe_write
from price_feed import utcnow

START_PATH = "/private-api/ctrader/start"
CALLBACK_PATH = "/private-api/ctrader/callback"
GRANT_URL = "https://id.ctrader.com/my/settings/openapi/grantingaccess/"
TOKEN_URL = "https://openapi.ctrader.com/apps/token"
MAX_REPLY_BYTES = 20_000


def settings(env):
    """Require a private HTTPS Tailscale callback and explicit opt-in."""
    if env.get("CTRADER_OAUTH_ENABLED", "0") != "1":
        raise ValueError("L'autorizzazione cTrader non e' stata abilitata sul server privato.")
    client_id = env.get("CTRADER_CLIENT_ID", "").strip()
    client_secret = env.get("CTRADER_CLIENT_SECRET", "").strip()
    redirect = env.get("CTRADER_REDIRECT_URI", "").strip()
    if not client_id or not client_secret or not redirect:
        raise ValueError("Configurazione OAuth cTrader privata incompleta.")
    try:
        parts = urlsplit(redirect)
        safe = (parts.scheme == "https" and parts.hostname and
                parts.hostname.endswith(".ts.net") and
                parts.port in (None, 443) and not parts.username and
                not parts.password and not parts.query and not parts.fragment and
                parts.path == CALLBACK_PATH)
    except ValueError:
        safe = False
    if not safe:
        raise ValueError("Callback cTrader: usare HTTPS Tailscale Serve con il percorso ufficiale REMURA.")
    return client_id, client_secret, redirect


def authorization_url(client_id, redirect_uri):
    """Trading permission is NEVER offered by REMURA."""
    return GRANT_URL + "?" + urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "accounts",
        "product": "web",
    })


def exchange_code(db_path, code, client_id, client_secret, redirect_uri,
                  now=None, requester=None):
    """Exchange once and persist restrictive private credentials; never echo secrets."""
    if not isinstance(code, str) or not (6 <= len(code) <= 2048):
        raise ValueError("Codice OAuth cTrader non valido.")
    now = now or utcnow()
    url = TOKEN_URL + "?" + urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret,
    })
    request = Request(url, method="GET", headers={"Accept": "application/json"})
    try:
        if requester is None:
            with urlopen(request, timeout=20) as response:
                payload = json.loads(response.read(MAX_REPLY_BYTES).decode("utf-8"))
        else:
            payload = requester(request)
    except (OSError, ValueError, UnicodeError, TimeoutError):
        raise RuntimeError("Autorizzazione cTrader non riuscita. Ripetere l'accesso.") from None
    if (not isinstance(payload, dict) or payload.get("errorCode") or
            not isinstance(payload.get("accessToken"), str) or
            not isinstance(payload.get("refreshToken"), str) or
            not payload["accessToken"] or not payload["refreshToken"] or
            payload.get("tokenType", "bearer").lower() != "bearer"):
        raise RuntimeError("cTrader ha rifiutato il codice di autorizzazione.")
    try:
        expires = int(payload["expiresIn"])
    except (TypeError, KeyError, ValueError):
        raise RuntimeError("Scadenza token cTrader non valida.") from None
    if not (3600 <= expires <= 365 * 86400):
        raise RuntimeError("Scadenza token cTrader fuori dai limiti.")
    safe_write(path_for(db_path), {
        "accessToken": payload["accessToken"],
        "refreshToken": payload["refreshToken"],
        "expiresAt": (now + dt.timedelta(seconds=expires)).isoformat(),
    })
    return True
