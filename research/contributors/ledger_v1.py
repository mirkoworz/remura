# REMURA Contributors v0.1 LAB — 14/11/2026 23:16 CET
"""Offline prototype only. No Google login, HTTP, providers, or persistent DB.
The caller supplies a trusted principal and server clock. NEVER expose this
interface directly to clients. Every accepted submission remains unreviewed.
"""
import re
import sqlite3
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

PERIODS = frozenset({"DAY", "WEEK", "CURRENT_MONTH", "PREVIOUS_MONTH"})
KINDS = frozenset({"DELTA_PEAK", "EFFORT_RESULT", "OTHER_VOLUME_LEVEL"})
FIELDS = frozenset({"request_id", "symbol", "period", "kind", "price", "observed_utc", "note"})
MAX_DAILY = 20
MAX_TOTAL = 200
SYMBOL = re.compile(r"[A-Z0-9_]{1,16}:[A-Z0-9_.!-]{1,24}")
PRICE = re.compile(r"(?:0|[1-9][0-9]{0,7})(?:\.[0-9]{1,8})?")
STAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")

@dataclass(frozen=True)
class Principal:
    subject: str
    role: str

def _time(x):
    if type(x) is not str or not STAMP.fullmatch(x):
        raise ValueError("utc_required")
    return datetime.strptime(x, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

class OfflineLedger:
    def __init__(self, allowed_symbols, authorized_subjects):
        self._symbols = frozenset(allowed_symbols)
        self._subjects = frozenset(authorized_subjects)
        if not self._symbols or any(type(s) is not str or not SYMBOL.fullmatch(s) for s in self._symbols):
            raise ValueError("invalid_allowlist")
        self._db = sqlite3.connect(":memory:")
        self._db.execute("""CREATE TABLE entries(
            id INTEGER PRIMARY KEY, subject TEXT NOT NULL, request_id TEXT NOT NULL,
            received_utc TEXT NOT NULL, payload TEXT NOT NULL,
            UNIQUE(subject, request_id))""")

    def submit(self, principal, payload, *, received_utc):
        if (not isinstance(principal, Principal) or principal.role != "CONTRIBUTOR"
                or principal.subject not in self._subjects):
            raise PermissionError("contributor_required")
        if type(payload) is not dict or set(payload) != FIELDS:
            raise ValueError("invalid_fields")
        if any(type(v) is not str for v in payload.values()):
            raise ValueError("strings_required")
        req = payload["request_id"]
        if len(req) != 36 or str(UUID(req)) != req:
            raise ValueError("request_id")
        if payload["symbol"] not in self._symbols:
            raise ValueError("symbol_not_allowed")
        if payload["period"] not in PERIODS or payload["kind"] not in KINDS:
            raise ValueError("classification")
        price = payload["price"]
        if not PRICE.fullmatch(price) or Decimal(price) <= 0:
            raise ValueError("price")
        if len(payload["note"]) > 280 or any(ord(c) < 32 for c in payload["note"]):
            raise ValueError("note")
        observed = _time(payload["observed_utc"])
        received = _time(received_utc)
        if observed > received:
            raise ValueError("future_observation")
        normalized = dict(payload, price=format(Decimal(price).normalize(), "f"))
        encoded = json.dumps(normalized, sort_keys=True, ensure_ascii=True)
        with self._db:
            existing = self._db.execute(
                "SELECT id,payload FROM entries WHERE subject=? AND request_id=?",
                (principal.subject, req)).fetchone()
            if existing:
                if existing[1] != encoded:
                    raise ValueError("idempotency_conflict")
                return {"id": existing[0], "status": "UNREVIEWED", "duplicate": True}
            count = self._db.execute(
                "SELECT COUNT(*) FROM entries WHERE subject=? AND substr(received_utc,1,10)=?",
                (principal.subject, received_utc[:10])).fetchone()[0]
            total = self._db.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
            if count >= MAX_DAILY or total >= MAX_TOTAL:
                raise ValueError("lab_capacity")
            cur = self._db.execute(
                "INSERT INTO entries(subject,request_id,received_utc,payload) VALUES(?,?,?,?)",
                (principal.subject, req, received_utc, encoded))
            return {"id": cur.lastrowid, "status": "UNREVIEWED", "duplicate": False}

    def close(self):
        self._db.close()
