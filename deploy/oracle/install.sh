#!/usr/bin/env bash
# REMURA Oracle Always Free / Ubuntu ARM64 bootstrap.
# Run only on the Oracle VM after reviewing the source:
#   sudo bash deploy/oracle/install.sh
set -Eeuo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Esegui con: sudo bash deploy/oracle/install.sh" >&2
  exit 1
fi
if [[ ! -f /etc/os-release ]]; then echo "Distribuzione Linux sconosciuta" >&2; exit 1; fi
# shellcheck disable=SC1091
source /etc/os-release
if [[ "${ID:-}" != "ubuntu" && "${ID_LIKE:-}" != *ubuntu* ]]; then
  echo "Questo installer e' destinato a Ubuntu Server; sistema: ${ID:-unknown}" >&2
  exit 1
fi
SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
if [[ ! -f "${SOURCE_DIR}/scripts/private_server.py" ]]; then
  echo "La directory sorgente non contiene REMURA privata" >&2
  exit 1
fi
if [[ "${SOURCE_DIR}" == "/opt/remura" ]]; then
  echo "Avvia l'installer dal checkout temporaneo, non da /opt/remura." >&2
  exit 1
fi

echo "Installazione prerequisiti (solo pacchetti Ubuntu)..."
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  python3 python3-venv python3-pip ca-certificates git rsync curl

if ! id remura >/dev/null 2>&1; then
  useradd --system --home-dir /opt/remura --shell /usr/sbin/nologin --user-group remura
fi
install -d -o remura -g remura -m 0750 /opt/remura
install -d -o remura -g remura -m 0700 /opt/remura/private

# Update only checked-in application files; preserve private data and tokens.
rsync -a --exclude='.git/' --exclude='private/' --exclude='local/' \
  --exclude='data/prices/' --exclude='.env' --exclude='.env.*' \
  --exclude='*.pem' --exclude='*.apikey' \
  "${SOURCE_DIR}/" /opt/remura/
chown -R remura:remura /opt/remura
chmod 0700 /opt/remura/private

if [[ ! -x /opt/remura/.venv/bin/python ]]; then
  runuser -u remura -- python3 -m venv /opt/remura/.venv
fi
# No PyPI dependencies are needed for the private HTTP server, COT, or IG/Myfxbook
# collectors. Install ctrader-open-api separately only after OAuth approval.

if [[ ! -f /opt/remura/private/remura.env ]]; then
  cat > /opt/remura/private/remura.env <<'ENV'
# REMURA private defaults: no collection or credentials enabled.
REMURA_COLLECTOR_ENABLED=0
REMURA_RETAIL_ENABLED=0
REMURA_IG_ENABLED=0
IG_ENV=demo
PYTHONDONTWRITEBYTECODE=1
ENV
  chown remura:remura /opt/remura/private/remura.env
  chmod 0600 /opt/remura/private/remura.env
fi

install -o root -g root -m 0644 \
  /opt/remura/deploy/oracle/remura.service /etc/systemd/system/remura-private.service
systemctl daemon-reload
systemctl enable --now remura-private.service
systemctl restart remura-private.service

echo
echo "REMURA installata su 127.0.0.1:8765. Nessuna porta app aperta a Internet."
echo "Verifica: sudo systemctl --no-pager status remura-private"
echo "Verifica API: curl -fsS http://127.0.0.1:8765/private-api/health"
echo "Prossimo passo: configura Tailscale Serve dopo il login privato."
