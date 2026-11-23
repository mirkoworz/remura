#!/usr/bin/env python3
"""REMURA V20: offline post-checkpoint audit of real saved sentiment history.

This is NOT a market forecast, price feed, first-seen proof or CVD receiver.
No network, secrets, broker calls, D1, Firestore, deployment or filesystem writes.
Capital DEMO output is strictly aggregate-only (never per-symbol or path).
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median


def utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith('Z'):
        raise ValueError('Expected ISO-8601 UTC timestamp ending in Z')
    try:
        d = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('Invalid UTC timestamp') from exc
    return d.astimezone(timezone.utc)


def valid_pct(record: dict) -> bool:
    x, y = record.get('lPct'), record.get('sPct')
    return (type(x) in (int, float) and type(y) in (int, float)
            and 0 <= x <= 100 and 0 <= y <= 100 and abs(x+y-100) <= 1.01)


def scan(folder: Path, since: datetime, as_of: datetime, *, public: bool) -> dict:
    if not folder.is_dir() or folder.is_symlink():
        raise ValueError('Missing or invalid history folder')
    files = sorted(folder.glob('*.json'))
    if not files:
        raise ValueError('No existing histories')
    counts = {'series_total': 0, 'observations_retained': 0, 'series_updated_after_checkpoint': 0,
              'new_records_retained_after_checkpoint': 0, 'changed_long_pct_since_checkpoint': 0,
              'unchanged_long_pct_since_checkpoint': 0, 'changed_payload_since_checkpoint': 0,
              'no_new_checkpoint_records': 0, 'stale_over_24h': 0, 'invalid_series': 0}
    gap_hours = []
    public_movers, public_stale = [], []
    increase = decrease = same = 0
    for file in files:
        if not file.is_file() or file.is_symlink() or file.stat().st_size > 1_000_000:
            raise ValueError('Invalid or oversized history file')
        try:
            data = json.loads(file.read_text(encoding='utf-8'))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError('Invalid history JSON') from exc
        if not isinstance(data, dict) or data.get('symbol') != file.stem:
            raise ValueError('Invalid symbol/history identity')
        records = data.get('records')
        if not isinstance(records, list) or not records:
            raise ValueError('Missing records')
        stamps = []
        for r in records:
            if not isinstance(r, dict) or not valid_pct(r):
                raise ValueError('Invalid sentiment record')
            stamps.append(utc(r.get('t')))
        if any(right <= left for left, right in zip(stamps, stamps[1:])):
            raise ValueError('Non-monotonic or duplicate timestamps')
        if stamps[-1] > as_of:
            raise ValueError('Future snapshot relative to audit cutoff')
        counts['series_total'] += 1
        counts['observations_retained'] += len(records)
        if as_of - stamps[-1] > timedelta(hours=24):
            counts['stale_over_24h'] += 1
            if public:
                public_stale.append(file.stem)
        prior_indexes = [i for i, t in enumerate(stamps) if t <= since]
        new_indexes = [i for i, t in enumerate(stamps) if since < t <= as_of]
        if not new_indexes:
            counts['no_new_checkpoint_records'] += 1
            continue
        counts['series_updated_after_checkpoint'] += 1
        counts['new_records_retained_after_checkpoint'] += len(new_indexes)
        if not prior_indexes:
            counts['invalid_series'] += 1
            continue
        prev_index = prior_indexes[-1]
        now_index = new_indexes[-1]
        before, after = records[prev_index], records[now_index]
        delta = round(after['lPct'] - before['lPct'], 5)
        if delta == 0:
            counts['unchanged_long_pct_since_checkpoint'] += 1
            same += 1
        else:
            counts['changed_long_pct_since_checkpoint'] += 1
            if delta > 0: increase += 1
            else: decrease += 1
        if {k:v for k,v in before.items() if k!='t'} != {k:v for k,v in after.items() if k!='t'}:
            counts['changed_payload_since_checkpoint'] += 1
        gap_hours.append((stamps[now_index] - stamps[prev_index]).total_seconds() / 3600)
        if public and delta:
            public_movers.append({'symbol': file.stem, 'delta_long_pp': delta})
    if counts['invalid_series']:
        raise ValueError('Missing baseline in one or more updated histories')
    counts['median_checkpoint_gap_hours'] = round(median(gap_hours), 3) if gap_hours else None
    counts['changed_long_direction_counts'] = {'increased': increase, 'decreased': decrease, 'unchanged': same}
    if public:
        counts['stale_public_series'] = sorted(public_stale)
        counts['largest_public_long_pp_changes'] = sorted(
            public_movers, key=lambda x: (-abs(x['delta_long_pp']), x['symbol']))[:6]
    return counts


def build_report(public_dir: Path, since: str, as_of: str, private_dir: Path | None = None) -> dict:
    start, end = utc(since), utc(as_of)
    if start >= end:
        raise ValueError('As-of must follow checkpoint')
    result = {'version': 'REMURA_V20_INCREMENTAL_20261123',
              'checkpoint_utc': since, 'audit_cutoff_utc': as_of,
              'source_times_not_attested_first_seen': True,
              'performance_or_alpha_measured': False,
              'new_observations_are_not_independent_trades': True,
              'myfxbook_retail_public': scan(public_dir, start, end, public=True)}
    if private_dir is not None:
        result['capital_demo_aggregate_only'] = scan(private_dir, start, end, public=False)
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--myfxbook-dir', required=True, type=Path)
    ap.add_argument('--capital-dir', type=Path)
    ap.add_argument('--since', required=True, help='Checkpoint ISO UTC ending Z')
    ap.add_argument('--as-of', required=True, help='Audit cutoff ISO UTC ending Z')
    a = ap.parse_args()
    print(json.dumps(build_report(a.myfxbook_dir, a.since, a.as_of, a.capital_dir),
                     ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
