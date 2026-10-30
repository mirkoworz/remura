#!/usr/bin/env python3
"""Offline, lossless repository-to-private Myfxbook history reconciliation.

Not a drop-in for the old rsync service until reviewed deployment. No API calls.
"""
import argparse
from pathlib import Path
from myfxbook_store import merge_repository


def main():
    parser = argparse.ArgumentParser(
        description="Merge Myfxbook archives without overwriting private observations")
    parser.add_argument("--source", type=Path, required=True,
                        help="Repository data/myfxbook directory")
    parser.add_argument("--destination", type=Path, required=True,
                        help="Private data/myfxbook directory")
    parser.add_argument("--apply", action="store_true",
                        help="Required to modify private files")
    args = parser.parse_args()
    if not args.apply:
        parser.error("No changes without explicit --apply; old rsync timer must remain disabled")
    changed = merge_repository(args.destination, args.source)
    print(f"MERGE_COMPLETED=YES FILES_UPDATED={changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
