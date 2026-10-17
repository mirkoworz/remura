#!/usr/bin/env bash
# Ubuntu 24.04 LTS VPS bootstrap. Run from the reviewed REMURA checkout:
# sudo bash deploy/bootstrap-ubuntu.sh
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Run with sudo." >&2
  exit 2
fi
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
for path in scripts/private_server.py scripts/ctrader_feed.py scripts/price_store.py deploy/remura-private.service; do
  if [ ! -f "$ROOT/$path" ]; then
    echo "Missing expected source: $path" >&2
    exit 3
  fi
done
if ! grep -q '^ID=ubuntu$' /etc/os-release; then
  echo "Bootstrap supports Ubuntu only." >&2
  exit 3
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends python3 python3-venv python3-pip ca-certificates git rsync
if ! id -u remura >/dev/null 2>&1; then
  useradd --system --home-dir /opt/remura --shell /usr/sbin/nologin --user-group remura
fi
install -d -m 0755 -o root -g root /opt/remura
install -d -m 0700 -o remura -g remura /opt/remura/private

# Protected private/ and local/ directories are always excluded, including on upgrades.
# rsync changes only deployed code ownership; no recursive chown of private secrets.
rsync -a --chown=root:root --delete \
  --exclude='.git/' --exclude='private/' --exclude='local/' \
  --exclude='.env' --exclude='.env.*' --exclude='__pycache__/' \
  --exclude='*.pyc' --exclude='.venv/' \
  "$ROOT/" /opt/remura/

if [ ! -x /opt/remura/.venv/bin/python ]; then
  python3 -m venv /opt/remura/.venv
fi
/opt/remura/.venv/bin/python -m pip install --disable-pip-version-check --no-input ctrader-open-api
if [ ! -f /opt/remura/private/remura.env ]; then
  install -m 0600 -o remura -g remura \
    /opt/remura/deploy/remura.env.example /opt/remura/private/remura.env
fi
chmod 0600 /opt/remura/private/remura.env
chown remura:remura /opt/remura/private/remura.env

install -m 0644 -o root -g root \
  /opt/remura/deploy/remura-private.service /etc/systemd/system/remura-private.service
systemctl daemon-reload
systemctl enable --now remura-private.service
echo
echo "REMURA VPS installed, HTTP only on 127.0.0.1:8765."
echo "Collectors default to OFF until accounts-only cTrader approval."
echo "Local health: curl --fail http://127.0.0.1:8765/private-api/health"
echo "NEXT: install Tailscale, sign in, use Tailscale Serve (never Funnel)."
