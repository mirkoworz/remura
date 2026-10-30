"""Lossless Myfxbook JSON storage primitives. Standard library, no network access.

Both the collector and the replacement synchronizer MUST use the same advisory
lock before touching the private archive. Invalid existing JSON is never empty.
"""
import contextlib
import datetime as dt
import fcntl
import json
import math
import os
from pathlib import Path
import tempfile

UTC = dt.timezone.utc


@contextlib.contextmanager
def archive_lock(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    lock = root / ".myfxbook.lock"
    fd = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def read_json(path):
    path = Path(path)
    if path.is_symlink():
        raise ValueError("Refusing to read a symbolic link")
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except FileNotFoundError:
        return None
    if not isinstance(value, dict):
        raise ValueError("Invalid JSON document shape")
    return value


def atomic_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("Refusing to overwrite a symbolic link")
    descriptor, temp = tempfile.mkstemp(prefix=".myfxbook-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            os.fchmod(handle.fileno(), 0o600)
            json.dump(obj, handle, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def _parse_date(raw):
    if not isinstance(raw, str):
        raise ValueError("Timestamp must be a string")
    try:
        value = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid timestamp") from exc
    if value.tzinfo is None:
        raise ValueError("Missing timestamp timezone")
    return value.astimezone(UTC)


def timestamp(row):
    if not isinstance(row, dict):
        raise ValueError("History entry must be an object")
    parsed = _parse_date(row.get("t"))
    for key in ("lPct", "sPct", "lLots", "sLots", "lPos", "sPos"):
        value = row.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("Invalid history metric: " + key)
        if not math.isfinite(value) or value < 0:
            raise ValueError("Nonfinite/negative history metric: " + key)
    if row["lPct"] > 100 or row["sPct"] > 100:
        raise ValueError("Invalid sentiment percentage")
    return parsed


def validate_history(doc, symbol):
    if doc is None:
        return []
    if doc.get("symbol") != symbol or not isinstance(doc.get("records"), list):
        raise ValueError("History schema/symbol mismatch")
    for row in doc["records"]:
        timestamp(row)
    return doc["records"]


def combine(private_rows, incoming_rows, *, cutoff=None, max_points=None):
    """Union by absolute timestamp, keeping private observations on conflicts."""
    items = {}
    for row in private_rows:
        items.setdefault(timestamp(row), row)
    for row in incoming_rows:
        items.setdefault(timestamp(row), row)
    if cutoff is not None:
        items = {at: row for at, row in items.items() if at >= cutoff}
    ordered = [items[at] for at in sorted(items)]
    return ordered[-max_points:] if max_points is not None else ordered


def history_document(symbol, rows):
    return {"symbol": symbol, "source": "Myfxbook Community Outlook",
            "sampling": "observed at recorded timestamps (not guaranteed 20m)",
            "records": rows}


def update_collection(root, observed, supported, *, cutoff, max_points, legacy=None, latest=None):
    """Atomic, locked collection save; commit latest AFTER its history records.

    Any corrupt existing history aborts BEFORE changing any history or latest.
    Caller fetches the API data and supplies actual timestamped observations.
    """
    root = Path(root)
    legacy = legacy or {}
    tracked = sorted(set(observed) & set(supported))
    with archive_lock(root):
        prepared = {}
        for symbol in tracked:
            destination = root / "history" / (symbol + ".json")
            private = read_json(destination)
            if private is None:
                old_rows = legacy.get(symbol, [])
                if not isinstance(old_rows, list):
                    raise ValueError("Invalid legacy rows")
            else:
                old_rows = validate_history(private, symbol)
            rows = combine(old_rows, [observed[symbol]], cutoff=cutoff, max_points=max_points)
            prepared[destination] = history_document(symbol, rows)
        previous_latest = read_json(root / "latest.json")
        if latest is not None:
            if latest.get("status") != "ok" or not isinstance(latest.get("symbols"), dict):
                raise ValueError("Invalid latest snapshot")
            new_time = _parse_date(latest.get("updatedAt"))
            old_time = (_parse_date(previous_latest.get("updatedAt"))
                        if previous_latest is not None else None)
        else:
            new_time = old_time = None
        for destination, document in prepared.items():
            atomic_json(destination, document)
        if latest is not None and (old_time is None or new_time >= old_time):
            atomic_json(root / "latest.json", latest)
        return len(prepared)


def merge_repository(root_private, root_public):
    """Union repository history into private, never replacing newer private data.

    The private latest.json is authoritative: seed only when missing.
    Must not be run alongside the old rsync timer.
    """
    private = Path(root_private)
    public = Path(root_public)
    if private.resolve() == public.resolve():
        raise ValueError("Source and destination must differ")
    if not public.is_dir() or public.is_symlink():
        raise ValueError("Repository source directory missing/unsafe")
    with archive_lock(private):
        planned = {}
        history = public / "history"
        if not history.is_dir() or history.is_symlink():
            raise ValueError("Repository history directory missing/unsafe")
        for source in sorted(history.glob("*.json")):
            symbol = source.stem
            if not (3 <= len(symbol) <= 12 and symbol.isalnum() and symbol.isupper()):
                raise ValueError("Invalid history filename")
            source_rows = validate_history(read_json(source), symbol)
            destination = private / "history" / source.name
            target_rows = validate_history(read_json(destination), symbol)
            merged = combine(target_rows, source_rows)
            if merged != target_rows:
                planned[destination] = history_document(symbol, merged)
        latest = private / "latest.json"
        if read_json(latest) is None:
            source_latest = read_json(public / "latest.json")
            if source_latest is not None:
                if source_latest.get("status") != "ok" or not isinstance(source_latest.get("symbols"), dict):
                    raise ValueError("Invalid repository latest")
                planned[latest] = source_latest
        for dest, data in planned.items():
            atomic_json(dest, data)
        return len(planned)
