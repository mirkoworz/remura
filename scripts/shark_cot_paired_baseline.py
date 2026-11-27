"""REMURA Track B: matched, cost-stressed COT observation baseline, offline.

Reads existing authentic validation cohorts/outcomes; never creates backdated
signals, makes network/broker requests, writes a database, or exposes OHLC,
broker IDs, timestamps or positions. The historical COT first-seen timestamp
must predate the Squalincome observation. This is *descriptive*, not a
walk-forward proof, causal attribution, or verified live fill simulation.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import math
import sqlite3

SCHEMA = "remura-cot-paired-baseline-v1"
PILOT = {"EURUSD": ("tff", "099741"), "XAUUSD": ("disagg", "088691")}
HORIZONS = (1, 4, 24)
MIN_SAMPLES = 30
MIN_WEEKS = 8
MAX_DELAY = timedelta(minutes=45)
UTC = timezone.utc


def _utc(value):
    """Accept actual SQLite UTC +00:00 or Z, but never naive/local times."""
    if not isinstance(value, str) or len(value) > 48:
        raise ValueError("bad_datetime")
    try:
        t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("bad_datetime") from exc
    if t.tzinfo is None or t.utcoffset() != timedelta(0):
        raise ValueError("not_utc")
    return t.astimezone(UTC)


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _cost(raw):
    if not isinstance(raw, dict):
        raise ValueError("cost_model_required")
    keys = ("spreadBps", "slippageEachSideBps", "commissionRoundTripBps")
    if any(not _finite(raw.get(k)) or raw[k] < 0 for k in keys):
        raise ValueError("invalid_costs")
    if raw["spreadBps"] <= 0:
        raise ValueError("spread_required")
    return float(raw["spreadBps"] + 2*raw["slippageEachSideBps"]
                 + raw["commissionRoundTripBps"])


def _table_names(db):
    return {r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}


def _seen(db):
    source = {}
    for dataset, code, date, at in db.execute(
            "SELECT dataset,code,report_date,first_seen_at FROM cot_first_seen"):
        if (dataset, code) not in PILOT.values():
            continue
        try:
            stamp = _utc(at)
            key = (dataset, code, date)
            source[key] = max(source.get(key, stamp), stamp)
        except (ValueError, TypeError, OverflowError):
            pass
    return source


def _prior_cot_known(seen, dataset, code, report_date, observed):
    """Direction uses two consecutive report weeks, BOTH already observed."""
    for (kind, market, older), known_at in seen.items():
        if kind != dataset or market != code or known_at > observed:
            continue
        try:
            prior = datetime.fromisoformat(older).date()
        except (TypeError, ValueError):
            continue
        if 6 <= (report_date-prior).days <= 10:
            return True
    return False


def _mean(items):
    return round(sum(items)/len(items), 4) if items else None


def _summarize(items):
    n = len(items)
    weeks = len({x["week"] for x in items})
    qualified = n >= MIN_SAMPLES and weeks >= MIN_WEEKS
    wins_cot = sum(x["cot"] > 0 for x in items)
    wins_long = sum(x["long"] > 0 for x in items)
    # Only paired within precisely the same observation/horizon,
    # with identical cost assumptions for long and COT strategy.
    return {
        "samples": n, "distinctCotWeeks": weeks,
        "meanCotNetBps": _mean([x["cot"] for x in items]),
        "meanLongNetBps": _mean([x["long"] for x in items]),
        "meanCotMinusLongBps": _mean([x["cot"]-x["long"] for x in items]),
        "cotNetPositive": wins_cot, "longNetPositive": wins_long,
        "cotHitPct": round(100*wins_cot/n, 2) if qualified else None,
        "longHitPct": round(100*wins_long/n, 2) if qualified else None,
        "sampleGate": "DESCRIPTIVE_ONLY" if qualified else "INSUFFICIENT",
    }



def _verified_cases(db, now):
    """PRIVATE row-level provenance gate shared by baseline and robustness.

    Never return these cases from an API or log them: times and historical
    returns are retained only in memory during offline research.
    """
    necessary = {"cot_first_seen", "squalincome_validation_cohorts",
                 "squalincome_validation_outcomes"}
    absent = sorted(necessary - _table_names(db))
    if absent:
        return [], Counter(), 0, absent
    seen = _seen(db)
    reasons = Counter()
    cases = []
    records = db.execute(
        "SELECT c.symbol,c.report_date,c.observed_at,c.price_time,"
        "c.cot_side,c.relationship,c.broker_symbol,c.entry_at,c.entry_open,"
        "o.horizon_hours,o.evaluated_at,o.directional_bps,o.long_benchmark_bps "
        "FROM squalincome_validation_cohorts c "
        "JOIN squalincome_validation_outcomes o "
        "ON c.symbol=o.symbol AND c.report_date=o.report_date AND c.stage=o.stage "
        "WHERE c.stage='observation' "
        "ORDER BY c.symbol,c.report_date,o.horizon_hours").fetchall()
    used = set()
    for (sym, week, observed, price_closed, side, relation, broker,
         entry_at, entry_open, hours, evaluated, directional, long_bps) in records:
        if sym not in PILOT:
            reasons["unsupported_market"] += 1
            continue
        if hours not in HORIZONS or type(hours) is not int:
            reasons["unsupported_horizon"] += 1
            continue
        key = (sym, week, hours)
        if key in used:
            reasons["duplicate_cohort_horizon"] += 1
            continue
        used.add(key)
        try:
            obs = _utc(observed)
            price = _utc(price_closed)
            entry = _utc(entry_at)
            outcome = _utc(evaluated)
            repdate = datetime.fromisoformat(week).date()
            if (repdate.isoformat() != week or repdate > obs.date()
                    or obs.date() - repdate > timedelta(days=14)
                    or not price <= obs <= entry < outcome <= now
                    or obs - price > timedelta(hours=3)
                    or entry - obs > MAX_DELAY
                    or entry.minute % 15 or entry.second or entry.microsecond
                    or outcome < entry + timedelta(hours=hours)
                    or type(side) is not int or side not in (-1, 1)
                    or relation not in ("aligned", "divergent")
                    or not isinstance(broker, str) or not broker.strip()
                    or not _finite(entry_open) or entry_open <= 0
                    or not _finite(directional) or not _finite(long_bps)
                    or not math.isclose(directional, side*long_bps,
                                        rel_tol=1e-5, abs_tol=0.0001)):
                reasons["invalid_cohort_or_outcome"] += 1
                continue
            cot_first = seen.get((*PILOT[sym], week))
            if cot_first is None:
                reasons["cot_first_seen_missing"] += 1
                continue
            if cot_first > obs:
                reasons["cot_first_seen_future"] += 1
                continue
            # Weekly delta needs the PREVIOUS known report as well. A later
            # historical backfill cannot be treated as available at obs.
            if not _prior_cot_known(seen, *PILOT[sym], repdate, obs):
                reasons["cot_previous_week_not_known"] += 1
                continue
            cases.append({
                "symbol": sym, "week": week, "observed": obs,
                "entry": entry, "evaluated": outcome,
                "horizon": hours, "side": side, "relationship": relation,
                "cotGrossBps": float(directional),
                "longGrossBps": float(long_bps),
            })
            reasons["paired_valid"] += 1
        except (ValueError, TypeError, OverflowError):
            reasons["invalid_cohort_or_outcome"] += 1
    return cases, reasons, len(records), []


def evaluate(db, *, as_of, costs):
    """Paired observational COT vs long, both charged the same explicit costs.

    No execution claims: selected cohorts are conditioned on COT readiness,
    so this is NOT a neutral-universe strategy comparison.
    """
    if not isinstance(db, sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    now = _utc(as_of)
    if not isinstance(costs, dict) or set(costs) != set(PILOT):
        raise ValueError("exact_pilot_costs_required")
    priced = {symbol: _cost(costs[symbol]) for symbol in PILOT}
    cases, reasons, received, absent = _verified_cases(db, now)
    if absent:
        return {"schema": SCHEMA, "status": "UNAVAILABLE",
                "missingTables": absent,
                "edge": "NOT_ESTABLISHED", "newBrokerCalls": 0}
    pairs = defaultdict(list)
    for case in cases:
        cost = priced[case["symbol"]]
        pairs[case["horizon"]].append({
            "week": case["week"],
            "cot": case["cotGrossBps"]-cost,
            "long": case["longGrossBps"]-cost,
        })
    return {
        "schema": SCHEMA, "status": "DESCRIPTIVE_ONLY",
        "received": received, "reasons": dict(sorted(reasons.items())),
        "horizons": [{"hours": hours, **_summarize(pairs[hours])}
                     for hours in HORIZONS],
        "selection": "same_original_observation_and_horizon",
        "costModel": "mandatory_explicit_per_symbol_bps_both_arms",
        "cotAvailability": "conservative_first_seen_not_official_release",
        "dataGaps": [
            "No point-in-time revisions of historical COT values.",
            "No independent broker-quote snapshot verification or real fills.",
            "Overlapping symbols/COT weeks are correlated; not out-of-sample.",
            "Contiguous M15 and original cost estimates rely on prior validation."
        ],
        "edge": "NOT_ESTABLISHED", "returnsExecutable": False,
        "cvdAvailableAtCaptured": False, "alertsEnabled": False,
        "newBrokerCalls": 0,
    }
