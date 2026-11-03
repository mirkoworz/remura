#!/usr/bin/env python3
"""REMURA v1.62 RESEARCH ONLY: pair H1 closed-bar ages at a common UTC instant.

This module is NOT imported by the LIVE server and performs no I/O. It takes
a historical 34-market full-scan diagnostic and fresh-batch frame diagnostics,
then reports ONLY counts for at most five matching markets. No broker requests,
trading signals, configuration changes, prices or symbols are emitted.

It does NOT prove the observed newer H1 candle was caused by the latest batch
or that market direction/positioning changed. A comparison is impossible when
either observation is missing, old, or internally inconsistent.
"""
from __future__ import annotations

import datetime as dt
import re

SCHEMA = "remura-h1-paired-readiness-research-v1"
H1_MAX_AGE_SECONDS = 120 * 60
MIN_H1_BARS = 55
MAX_SCAN_DISTANCE_SECONDS = 30 * 60
MAX_POST_INGEST_SECONDS = 120
MAX_CLOCK_SKEW_SECONDS = 5
_SYMBOL = re.compile(r"[A-Z0-9]{3,12}\Z")
_CLOCK = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|[+-]\d\d:\d\d)\Z")
_INTERPRETATION = "PAIRED_H1_AVAILABILITY_NOT_PROOF_OF_INGEST_CAUSALITY_OR_TRADING_EDGE"


def _clock(raw):
    """Return valid UTC-aware clock, or None; never accept local-naive times."""
    if type(raw) is not str or len(raw) > 40 or not _CLOCK.fullmatch(raw):
        return None
    try:
        value = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if value.utcoffset() is None:
            return None
        return value.astimezone(dt.timezone.utc)
    except (ValueError, OverflowError, TypeError):
        return None


def _last_close(entry, reference):
    """Require at least 55 completed H1 bars and an honest UTC close time."""
    if not isinstance(entry, dict):
        return None
    if type(entry.get("bars")) is not int or not MIN_H1_BARS <= entry["bars"] <= 100000:
        return None
    stamp = _clock(entry.get("lastClosedAt"))
    if stamp is None or (stamp - reference).total_seconds() > MAX_CLOCK_SKEW_SECONDS:
        return None
    if (reference - stamp).total_seconds() > 7 * 86400:
        return None
    return stamp


def _unverifiable(state):
    return {
        "schema": SCHEMA, "state": state, "compared": None,
        "fullScanH1ReadyAtSameUtc": None, "postIngestH1ReadyAtSameUtc": None,
        "staleToReady": None, "freshestH1Advanced": None,
        "unchangedH1": None, "fullScanAgeSeconds": None,
        "interpretation": _INTERPRETATION,
    }


def compare_paired_h1(full_scan, updated_frames, *,
                      post_scan_utc, ingest_returned_utc):
    """Pair existing, targeted H1 frame diagnostics, not broker price rows.

    full_scan: previous scan_once(..., targets=None) diagnostics summary
    updated_frames: {symbol: safe_frame_diagnostics(latest(db,symbol), now)}
                    for the <=5 post-ingest targets ONLY.
    post_scan_utc and ingest_returned_utc: server-generated timestamps.

    FAIL CLOSED: never return invented 0's for missing, old or incongruent
    snapshots. If any targeted H1 is unverifiable, ALL counters are N/D.
    All comparisons use the SAME post_scan_utc, even for the older full scan.
    """
    if (not isinstance(full_scan, dict) or
        not isinstance(updated_frames, dict) or
        not 1 <= len(updated_frames) <= 5):
        return _unverifiable("MISSING_OR_UNBOUNDED")
    keys = tuple(updated_frames)
    if (any(type(key) is not str or not _SYMBOL.fullmatch(key) for key in keys)
        or len(set(keys)) != len(keys)):
        return _unverifiable("INVALID_TARGETS")
    post = _clock(post_scan_utc)
    ingest = _clock(ingest_returned_utc)
    full = _clock(full_scan.get("lastScanAt"))
    if any(t is None for t in (full, ingest, post)):
        return _unverifiable("INVALID_CLOCKS")
    if (not full <= ingest <= post or
        (post - full).total_seconds() > MAX_SCAN_DISTANCE_SECONDS or
        (post - ingest).total_seconds() > MAX_POST_INGEST_SECONDS):
        return _unverifiable("NON_COMPARABLE_CLOCKS")
    markets = full_scan.get("markets")
    if not isinstance(markets, list) or len(markets) > 38:
        return _unverifiable("INVALID_FULL_SCAN")
    full_index = {}
    for market in markets:
        if not isinstance(market, dict):
            return _unverifiable("INVALID_FULL_SCAN")
        symbol = market.get("symbol")
        if type(symbol) is not str or not _SYMBOL.fullmatch(symbol) or symbol in full_index:
            return _unverifiable("INVALID_FULL_SCAN")
        full_index[symbol] = market.get("timeframes")
    if len(full_index) != 34 or not set(keys).issubset(full_index):
        return _unverifiable("INCOMPLETE_FULL_SCAN")

    full_ready = post_ready = advanced = unchanged = recovered = 0
    for symbol in keys:
        before = full_index[symbol]
        after = updated_frames[symbol]
        if not isinstance(before, dict) or not isinstance(after, dict):
            return _unverifiable("INCOMPLETE_H1")
        old_close = _last_close(before.get("H1"), full)
        new_close = _last_close(after.get("H1"), post)
        if old_close is None or new_close is None:
            return _unverifiable("INCOMPLETE_H1")
        if new_close < old_close:
            return _unverifiable("REGRESSED_H1")
        b = (post - old_close).total_seconds() <= H1_MAX_AGE_SECONDS
        a = (post - new_close).total_seconds() <= H1_MAX_AGE_SECONDS
        full_ready += int(b)
        post_ready += int(a)
        recovered += int(not b and a)
        advanced += int(new_close > old_close)
        unchanged += int(new_close == old_close)
    return {
        "schema": SCHEMA, "state": "COMPARABLE",
        "compared": len(keys),
        "fullScanH1ReadyAtSameUtc": full_ready,
        "postIngestH1ReadyAtSameUtc": post_ready,
        "staleToReady": recovered,
        "freshestH1Advanced": advanced,
        "unchangedH1": unchanged,
        "fullScanAgeSeconds": round((post - full).total_seconds()),
        "interpretation": _INTERPRETATION,
    }
