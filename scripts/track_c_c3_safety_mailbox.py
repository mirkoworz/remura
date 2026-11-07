"""REMURA Track C C3: OFFLINE synthetic, bounded, non-blocking research mailbox.

This is a DESIGN/CHAOS rehearsal, NOT installed in any production collector.
It accepts metadata only (no price, positions, account, broker symbol, token,
full source document, signal or PnL), does not open a file, run any worker,
connect to provider, use secrets or issue notifications.

Live isolation requires future explicit separate-process durable handoff after
core-source commit, with independent limits, replay protection and monitoring.
This in-memory mailbox is NOT durable and is NOT that production handoff.

The *existing* optional atomic COT witness intentionally aborts a dataset on
research failure. DO NOT enable it on LIVE; any future implementation must
provide separately tested failure isolation while preserving genuine core
observations and truthful UNKNOWN status for missing research receipts.
"""
from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta, timezone
import re

MODE = "OFFLINE_SYNTHETIC_C3_NON_BLOCKING_MAILBOX_ONLY"
SYMBOLS = frozenset(("EURUSD", "XAUUSD"))
SOURCES = frozenset(("cot", "ctrader", "retail"))
MAX_PENDING = 16
MAX_TOTAL_OFFERED = 4500
MAX_AGE = timedelta(minutes=3)
HEX = re.compile(r"[0-9a-f]{64}\Z")
RESEARCH_UNAVAILABLE = "UNKNOWN_NO_PROSPECTIVE_PROOF"
SOURCE_EXISTS = "CORE_SOURCE_UNAFFECTED_IN_SIMULATION"


def _instant(text):
    if type(text) is not str or len(text) != 20 or not text.endswith("Z"):
        raise ValueError("explicit_zulu_second_clock_required")
    try:
        return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError("invalid_utc_clock") from exc


class SyntheticResearchMailbox:
    """Bounded rehearsal with NO callback at the core collector boundary.

    Payloads are metadata allowlisted EXACTLY to prevent accidental provider
    or client content retention. No automatic retries or delayed backfill.
    """

    def __init__(self, *, mode=None, enabled=False, max_pending=MAX_PENDING):
        if mode != MODE or type(enabled) is not bool:
            raise ValueError("explicit_synthetic_mode_and_boolean_enable_required")
        if type(max_pending) is not int or not 1 <= max_pending <= MAX_PENDING:
            raise ValueError("bounded_synthetic_queue_required")
        self.enabled = enabled
        self.limit = max_pending
        self.pending = deque()
        self.keys = set()
        self.total = 0
        self.refused = 0
        self.failed = 0
        self.completed = 0

    def offer(self, metadata, *, now):
        """Never calls a research worker. Returns only safe state metadata.

        This is explicitly called in laboratory code OUTSIDE the original
        collector transaction. It does not guarantee delivery or persistence.
        """
        moment = _instant(now)
        if not self.enabled:
            self.refused += 1
            return RESEARCH_UNAVAILABLE
        if (type(metadata) is not dict or set(metadata) != {
                "symbol", "source", "seenAtUtc", "originalSha256"}):
            self.refused += 1
            return RESEARCH_UNAVAILABLE
        symbol = metadata["symbol"]
        source = metadata["source"]
        sha = metadata["originalSha256"]
        try:
            seen = _instant(metadata["seenAtUtc"])
        except (ValueError, TypeError):
            self.refused += 1
            return RESEARCH_UNAVAILABLE
        if (type(symbol) is not str or symbol not in SYMBOLS
                or type(source) is not str or source not in SOURCES
                or type(sha) is not str or HEX.fullmatch(sha) is None
                or not timedelta(0) <= moment-seen <= MAX_AGE):
            self.refused += 1
            return RESEARCH_UNAVAILABLE
        key = (symbol,source,metadata["seenAtUtc"],sha)
        if (key in self.keys or len(self.pending) >= self.limit
                or self.total >= MAX_TOTAL_OFFERED):
            self.refused += 1
            return RESEARCH_UNAVAILABLE
        self.pending.append(key)
        self.keys.add(key)
        self.total += 1
        return "SYNTHETIC_METADATA_STAGED_ONLY"

    def consume_for_test(self, worker, *, now):
        """Execute a RESEARCH-ONLY worker OUTSIDE any core transaction.

        Worker failure is contained and the item becomes UNKNOWN, not
        retroactively validated. No real thread/process isolation is proven.
        """
        current = _instant(now)
        if not callable(worker):
            raise ValueError("synthetic_research_worker_required")
        if not self.pending:
            return RESEARCH_UNAVAILABLE
        key = self.pending.popleft()
        self.keys.remove(key)
        try:
            stamp = _instant(key[2])
            if not timedelta(0) <= current-stamp <= MAX_AGE:
                raise ValueError("stale_synthetic_research_event")
            accepted = worker(tuple(key))
            if accepted is not True:
                raise ValueError("unverified_research_worker_result")
        except Exception:
            self.failed += 1
            return RESEARCH_UNAVAILABLE
        self.completed += 1
        return "SYNTHETIC_RESEARCH_RECEIPT_ONLY"

    def summary(self):
        return {
            "schema": "remura-track-c3-mailbox-rehearsal-v1",
            "state": "SYNTHETIC_ONLY_NOT_PERSISTENT_NOT_LIVE",
            "pending": len(self.pending),
            "offered": self.total,
            "refusedOrDropped": self.refused,
            "workerFailures": self.failed,
            "syntheticCompleted": self.completed,
            "liveEnabled": False,
            "crossProcessDurabilityVerified": False,
            "researchFailureCouldBlockCore": False,
            "liveIsolationProven": False,
            "sourceProviderAuthenticityVerified": False,
            "realCostsChecked": False,
            "tradingEdge": "NOT_ESTABLISHED",
            "cvd": "UNKNOWN",
            "apiRequestsAdded": 0,
            "notificationsEnabled": False,
            "ordersEnabled": False,
        }
