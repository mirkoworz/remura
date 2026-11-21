#!/usr/bin/env bash
# REMURA Contributors v0.71 LAB — 21/11/2026 12:42 CET.
# Only the 24 never-executed v0.70 integration cases; no historical suites.
set -euo pipefail
umask 077
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
BRANCH="$(git branch --show-current || true)"
if [[ "$BRANCH" != "research/contributors-private-worker-v071-20261121" && "$BRANCH" != "" ]]; then
  echo "STOP: validation is restricted to the isolated v0.71 branch or detached HEAD" >&2
  exit 12
fi
if [[ -n "$(git status --porcelain -- research/contributors)" ]]; then
  echo "STOP: contributors subtree contains uncommitted changes" >&2
  exit 13
fi
node -e "import('node:sqlite').then(m=>{if(typeof m.DatabaseSync!=='function')process.exit(1)})"
node --test research/contributors/test_protected_read_integrated_v070_lab.mjs
