"""Track B: offline cost-aware chronological research backtest engine.

Pre-recorded, genuinely observed signals ONLY; this engine never infers their
historical availability from pivot timestamps. Closed M15, broker continuity,
prior ATR, next open, costs, stop-first ambiguous bars and purge/embargo.
Do not treat synthetic test returns as market evidence or deployment signals.
"""
from __future__ import annotations

from collections import Counter
from datetime import timedelta
import math

from scripts.shark_science_gate import _utc

STEP = timedelta(minutes=15)
SCHEMA = "remura-shark-walkforward-research-v1"
MIN_OBSERVATIONS = 30
MAX_EVENTS = 20000


def _finite(value, positive=False):
    return (type(value) in (float, int) and math.isfinite(value) and
            (value > 0 if positive else value >= 0))


def _series(doc):
    if (not isinstance(doc, dict) or doc.get("provider") != "ctrader" or
            not isinstance(doc.get("providerSymbol"), str) or
            not doc["providerSymbol"].strip()):
        raise ValueError("unverified_broker")
    bars = doc.get("M15")
    if not isinstance(bars, list) or len(bars) < 16 or len(bars) > 20000:
        raise ValueError("invalid_m15_length")
    output = []
    last = None
    for bar in bars:
        if not isinstance(bar, dict):
            raise ValueError("invalid_bar")
        t = _utc(bar.get("t"))
        o, h, l, c = (bar.get(k) for k in ("o", "h", "l", "c"))
        if (t.minute % 15 != 0 or t.second or t.microsecond or
                (last is not None and t <= last) or
                not all(_finite(x, True) for x in (o, h, l, c)) or
                h < max(o, c) or l > min(o, c)):
            raise ValueError("invalid_ohlc_or_time")
        output.append((t, o, h, l, c))
        last = t
    return output


def _atr_before(bars, observed, end_index, period=14):
    """ATR is computed ONLY from 15 candles that have closed by observation."""
    if end_index < period:
        return None
    prior = bars[end_index-period:end_index+1]
    if prior[-1][0] + STEP > observed:
        return None
    if any(prior[i][0] - prior[i-1][0] != STEP for i in range(1, len(prior))):
        return None
    trs = []
    for i in range(1, len(prior)):
        bar, prev = prior[i], prior[i-1]
        trs.append(max(bar[2]-bar[3], abs(bar[2]-prev[4]),
                       abs(bar[3]-prev[4])))
    value = sum(trs)/len(trs)
    return value if value > 0 and math.isfinite(value) else None


def _costs(raw):
    if not isinstance(raw, dict):
        raise ValueError("cost_model_required")
    out = {}
    for field in ("spreadBps", "slippageEachSideBps", "commissionRoundTripBps"):
        value = raw.get(field)
        if not _finite(value) or (field == "spreadBps" and value == 0):
            raise ValueError("missing_or_invalid_cost_" + field)
        out[field] = float(value)
    return out


def _simulate(signal, doc, rows, cost, asof, horizon, stop_atr, target_atr):
    """Return a private internal result; never expose prices or raw IDs."""
    try:
        if (signal.get("provider") != "ctrader" or
                signal.get("brokerSymbol") != doc["providerSymbol"] or
                signal.get("qualityVerified") is not True or
                signal.get("observationVerified") is not True or
                type(signal.get("side")) is not int or signal["side"] not in (-1, 1)):
            return None, "invalid_signal_lineage"
        confirmed = _utc(signal["confirmedAt"])
        observed = _utc(signal["availableAt"])
        if confirmed > observed or observed > asof:
            return None, "signal_not_known_asof"
        if observed - confirmed > timedelta(minutes=90):
            return None, "stale_detection"
        eligible_cvd = (signal.get("cvdQualityVerified") is True and
                        signal.get("cvdAlgorithm") == "cvd-divergence-proxy-m15-v1" and
                        signal.get("cvdState") == "confirmed_technical_not_trade_signal" and
                        signal.get("cvdSide") == ("bullish" if signal["side"] == 1 else "bearish"))
        if eligible_cvd:
            cvd_confirmed = _utc(signal["cvdConfirmedAt"])
            cvd_known = _utc(signal["cvdAvailableAt"])
            eligible_cvd = cvd_confirmed <= cvd_known <= observed
        # A later CVD detection cannot retrospectively qualify this entry.
        future = next((i for i, b in enumerate(rows) if b[0] > observed), None)
        if future is None or rows[future][0] - observed > timedelta(minutes=45):
            return None, "no_executable_next_open"
        # First entry candle must not have been open when observation occurred.
        # The immediately preceding row may still be forming at observedAt.
        # Search backwards for the last bar that was FULLY CLOSED then.
        last_closed = next((i for i in range(future-1, -1, -1)
                            if rows[i][0] + STEP <= observed), None)
        if last_closed is None or last_closed < 14:
            return None, "missing_closed_atr_history"
        atr = _atr_before(rows, observed, last_closed)
        if atr is None:
            return None, "invalid_prior_atr"
        # A closed ATR window is not enough: the last known candle and the
        # simulated next opening must also be connected by every M15 slot.
        # Otherwise missing candles in the observation/entry bridge could
        # silently turn an unexecutable gap into a favourable simulated fill.
        # Do not synthesize/interpolate any M15 or shift the entry backwards.
        if any(rows[i][0] - rows[i-1][0] != STEP
               for i in range(last_closed + 1, future + 1)):
            return None, "entry_history_gap"
        if future + horizon > len(rows):
            return None, "outcome_pending"
        future_rows = rows[future:future+horizon]
        if any(future_rows[i][0] - future_rows[i-1][0] != STEP
               for i in range(1, len(future_rows))):
            return None, "future_session_gap"
        start = future_rows[0][0]
        entry = future_rows[0][1]
        side = signal["side"]
        stop = entry - side*stop_atr*atr
        target = entry + side*target_atr*atr
        exit_mid, last_bar = None, None
        for bar in future_rows:
            # Stop takes precedence if stop and target are both touched in M15.
            stopped = bar[3] <= stop if side == 1 else bar[2] >= stop
            reached = bar[2] >= target if side == 1 else bar[3] <= target
            if stopped or reached:
                exit_mid = stop if stopped else target
                last_bar = bar
                break
        if last_bar is None:
            last_bar = future_rows[-1]
            exit_mid = last_bar[4]
        exit_time = last_bar[0] + STEP
        if exit_time > asof:
            return None, "outcome_not_yet_observable"
        gross_bps = side*(exit_mid-entry)*10000/entry
        total_cost = (cost["spreadBps"] + 2*cost["slippageEachSideBps"] +
                      cost["commissionRoundTripBps"])
        net_bps = gross_bps - total_cost
        risk_bps = stop_atr*atr*10000/entry
        if not math.isfinite(net_bps) or risk_bps <= 0:
            return None, "invalid_numeric_outcome"
        return {"observed": observed, "entry": start, "exit": exit_time,
                "netR": net_bps/risk_bps, "grossBps": gross_bps,
                "netBps": net_bps, "cvd": eligible_cvd,
                "symbol": signal["symbol"]}, None
    except (KeyError, TypeError, ValueError, OverflowError):
        return None, "invalid_signal"


def _fold(row, train_end, validate_end, embargo):
    observed, matured = row["observed"], row["exit"]
    if observed < train_end:
        return "train" if matured <= train_end-embargo else "purged"
    if observed < validate_end:
        return ("validation" if observed >= train_end+embargo and
                matured <= validate_end-embargo else "purged")
    return "test" if observed >= validate_end+embargo else "purged"


def _stats(rows):
    n = len(rows)
    wins = sum(x["netR"] > 0 for x in rows)
    positive = sum(max(0, x["netR"]) for x in rows)
    negative = sum(-min(0, x["netR"]) for x in rows)
    cumulative = peak = max_dd = 0.0
    for x in sorted(rows, key=lambda r: (r["exit"], r["observed"])):
        cumulative += x["netR"]
        peak = max(peak, cumulative)
        max_dd = max(max_dd, peak-cumulative)
    return {
        "samples": n, "netPositive": wins, "netNonPositive": n-wins,
        "meanNetR": round(sum(x["netR"] for x in rows)/n, 5) if n else None,
        "profitFactor": round(positive/negative, 5) if negative else None,
        "maxSequentialDrawdownR": round(max_dd, 5) if n else None,
        "netHitPct": round(100*wins/n, 2) if n >= MIN_OBSERVATIONS else None,
        "sampleWarning": "DESCRIPTIVE_CORRELATED_NOT_PORTFOLIO",
    }


def evaluate(signals, sources, cost_models, *, as_of, train_end, validation_end,
             embargo_bars=8, horizon_bars=4, stop_atr=1.0, target_atr=1.5):
    """Fixed protocol; no threshold search, fit, external I/O or order creation.

    Real observedAt/availableAt is mandatory: CVD theoretical confirmedAt alone
    is insufficient. Specify true historic costs or clearly label assumptions.
    """
    now, train, val = _utc(as_of), _utc(train_end), _utc(validation_end)
    if not train < val <= now:
        raise ValueError("invalid_chronological_boundaries")
    if (type(embargo_bars) is not int or not 0 <= embargo_bars <= 96 or
            type(horizon_bars) is not int or not 1 <= horizon_bars <= 16 or
            not _finite(stop_atr, True) or not _finite(target_atr, True)):
        raise ValueError("invalid_fixed_protocol")
    if (not isinstance(signals, list) or len(signals) > MAX_EVENTS or
            not isinstance(sources, dict) or not isinstance(cost_models, dict)):
        raise ValueError("invalid_input_bundle")
    if not sources or any(name not in cost_models for name in sources):
        raise ValueError("costs_required_per_symbol")
    prepared = {name: _series(doc) for name, doc in sources.items()}
    costs = {name: _costs(cost_models[name]) for name in sources}
    rows, excluded = [], Counter()
    for signal in signals:
        if not isinstance(signal, dict) or not isinstance(signal.get("symbol"), str):
            excluded["invalid_signal"] += 1
            continue
        sym = signal["symbol"]
        if sym not in prepared:
            excluded["unapproved_symbol"] += 1
            continue
        outcome, reason = _simulate(signal, sources[sym], prepared[sym],
                                    costs[sym], now, horizon_bars,
                                    stop_atr, target_atr)
        if reason:
            excluded[reason] += 1
        else:
            rows.append(outcome)
    embargo = embargo_bars*STEP
    grouped = {"train": [], "validation": [], "test": []}
    for outcome in rows:
        name = _fold(outcome, train, val, embargo)
        if name == "purged":
            excluded["purged_or_embargoed"] += 1
        else:
            grouped[name].append(outcome)
    return {
        "schema": SCHEMA, "status": "RESEARCH_ONLY", "edge": "NOT_ESTABLISHED",
        "source": "recorded_observed_signal_plus_closed_ctrader_m15",
        "costs": "explicit_per_symbol_assumptions_or_verified_inputs",
        "protocol": {"atrPeriod": 14, "holdingM15": horizon_bars,
                     "stopAtr": stop_atr, "targetAtr": target_atr,
                     "embargoM15": embargo_bars,
                     "ambiguousBar": "STOP_FIRST",
                     "entry": "first_next_M15_open_after_real_observation"},
        "received": len(signals), "excluded": dict(sorted(excluded.items())),
        "folds": {f: {"priceOnly": _stats(group),
                      "cvdFiltered": _stats([x for x in group if x["cvd"]])}
                  for f, group in grouped.items()},
        "capitalDrawdownValidated": False,
        "independentSamples": False, "ordersEnabled": False,
        "notificationEnabled": False,
    }
