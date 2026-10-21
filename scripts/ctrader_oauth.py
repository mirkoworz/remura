#!/usr/bin/env python3
"""Private cTrader OAuth bootstrap. No secrets or tokens are returned to HTTP clients."""
from __future__ import annotations

import datetime as dt
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
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


def _safe_error_detail(description):
    """Map untrusted provider description to predefined labels, never persist it."""
    if not isinstance(description, str):
        return "UNSPECIFIED"
    value = description.casefold()[:1200]
    import re
    rules = [
        ("CLIENT_SECRET", r"client[ _-]*secret|secret[ _-]*key|invalid[ _-]*secret|secret.*invalid"),
        ("CLIENT_ID", r"client[ _-]*id|application[ _-]*id|invalid[ _-]*client"),
        ("REDIRECT_URI", r"redirect|callback|return[ _-]*uri"),
        ("EXPIRED_CODE", r"expir|timed[ _-]*out|timeout"),
        ("REUSED_CODE", r"already[ _-]*used|consum|redeem|replay|previously[ _-]*used"),
        ("AUTH_CODE", r"authori[sz]ation[ _-]*code|auth[ _-]*code|invalid[ _-]*code|code[ _-]*invalid|grant[ _-]*code"),
        ("GRANT_TYPE", r"grant[ _-]*type"),
        ("PARAMETERS", r"parameter|missing|required|malformed|invalid[ _-]*request"),
    ]
    for label, pattern in rules:
        if re.search(pattern, value):
            return label
    return "OTHER"


def _record_diagnostic(database, status):
    """Keep only a bounded category in the private directory, never provider messages."""
    location = Path(database).expanduser().resolve().parent / "ctrader-oauth-status.json"
    safe_write(location, {"result": status, "checkedAt": utcnow().isoformat()})


def exchange_code(code, env, database, requester=None):
    """Exchange once, retain only safe error categories, never tokens in logs or responses.

    A failed callback produces a private diagnostic with NO access token,
    refresh token, OAuth code, credentials, request URL or provider description.
    """
    status = "REQUEST_FAILED"
    try:
        cid, secret, redirect = settings(env)
        if (not isinstance(code, str) or
                not re.fullmatch(r"[A-Za-z0-9._~-]{8,512}", code)):
            status = "INVALID_CODE_FORMAT"
            raise ValueError("Invalid OAuth code format")
        url = TOKEN_URL + "?" + urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect,
            "client_id": cid,
            "client_secret": secret,
        })
        request = urllib.request.Request(
            url, headers={"Accept": "application/json", "Cache-Control": "no-store"})
        if requester is None:
            with urllib.request.urlopen(request, timeout=15) as reply:
                payload = json.loads(reply.read(20_000).decode("utf-8"))
        else:
            payload = requester(request)
        if not isinstance(payload, dict):
            status = "INVALID_RESPONSE"
            raise ValueError("Invalid API response")
        if payload.get("errorCode"):
            # An allowlist prevents remotely controlled error strings or secrets
            # from being written to a diagnostics file.
            allowed = {
                "ACCESS_DENIED", "INVALID_REQUEST", "INVALID_TOKEN",
                "INVALID_CLIENT", "INVALID_GRANT", "CODE_EXPIRED",
                "INTERNAL_ERROR", "RATE_LIMIT_EXCEEDED",
            }
            provider_code = str(payload["errorCode"]).upper()
            status = ("API_" + provider_code + "_DETAIL_" + _safe_error_detail(payload.get("description"))) if provider_code in allowed else "API_REJECTED"
            raise ValueError("API refused OAuth exchange")
        if not payload.get("accessToken") or not payload.get("refreshToken"):
            status = "MISSING_TOKENS"
            raise ValueError("Missing tokens")
        ttl = int(payload.get("expiresIn", 0))
        if not 3600 <= ttl <= 365 * 86400:
            status = "INVALID_TTL"
            raise ValueError("Invalid token lifetime")
        safe_write(path_for(database), {
            "accessToken": str(payload["accessToken"]),
            "refreshToken": str(payload["refreshToken"]),
            "expiresAt": (utcnow() + dt.timedelta(seconds=ttl)).isoformat(),
        })
        status = "SAVED"
        return True
    except urllib.error.HTTPError as exc:
        status = "HTTP_" + str(exc.code) if 400 <= exc.code < 600 else "HTTP_ERROR"
        raise RuntimeError("cTrader OAuth non riuscito: consultare la diagnostica privata.") from None
    except urllib.error.URLError:
        status = "NETWORK_ERROR"
        raise RuntimeError("cTrader OAuth non riuscito: consultare la diagnostica privata.") from None
    except Exception:
        raise RuntimeError("cTrader OAuth non riuscito: consultare la diagnostica privata.") from None
    finally:
        try:
            _record_diagnostic(database, status)
        except OSError:
            pass
