#!/usr/bin/env bash
# Upgrade a reviewed checkout and preserve private SQLite, symbols, environment and OAuth.
# sudo bash deploy/update-ubuntu.sh
set -euo pipefail
if [ "$(id -u)" -ne 0 ]; then echo "Use sudo." >&2; exit 2; fi
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ ! -x /opt/remura/.venv/bin/python ]; then
  echo "Not installed: run deploy/bootstrap-ubuntu.sh first." >&2
  exit 3
fi
python3 -m unittest discover -s "$ROOT/tests" -p 'test_private_server.py' -q
python3 -m unittest discover -s "$ROOT/tests" -p 'test_ctrader_tokens.py' -q
rsync -a --chown=root:root --delete \
  --exclude='.git/' --exclude='private/' --exclude='local/' \
  --exclude='.env' --exclude='.env.*' --exclude='__pycache__/' \
  --exclude='*.pyc' --exclude='.venv/' \
  "$ROOT/" /opt/remura/
/opt/remura/.venv/bin/python -m pip install --disable-pip-version-check --no-input ctrader-open-api
install -m 0644 -o root -g root /opt/remura/deploy/remura-private.service \
  /etc/systemd/system/remura-private.service
systemctl daemon-reload
systemctl restart remura-private
systemctl is-active --quiet remura-private || exit 1
echo "REMURA upgraded. Private user data and secrets preserved."
