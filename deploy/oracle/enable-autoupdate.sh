#!/usr/bin/env bash
# Attiva una volta sola dopo avere installato il checkout v1.7 su Oracle.
set -Eeuo pipefail
[[ "$EUID" -eq 0 ]] || { echo "Usa sudo bash" >&2; exit 1; }
SOURCE="$(cd -- "$(dirname -- "$0")/../.." && pwd)"
test -d "$SOURCE/.git" || { echo "Esegui dal checkout GitHub scaricato" >&2; exit 1; }
test -f /opt/remura/deploy/oracle/autoupdate.py || { echo "Installa prima la v1.7" >&2; exit 1; }
SHA="$(git -C "$SOURCE" rev-parse HEAD)"
[[ "$SHA" =~ ^[0-9a-f]{40}$ ]] || exit 1
systemctl is-active --quiet remura-private.service
curl -fsS --max-time 10 http://127.0.0.1:8765/private-api/health >/dev/null
install -o root -g root -m 0644 /opt/remura/deploy/oracle/remura-autoupdate.service /etc/systemd/system/remura-autoupdate.service
install -o root -g root -m 0644 /opt/remura/deploy/oracle/remura-autoupdate.timer /etc/systemd/system/remura-autoupdate.timer
python3 /opt/remura/deploy/oracle/autoupdate.py --init-sha "$SHA"
systemctl daemon-reload
systemctl enable --now remura-autoupdate.timer
echo "REMURA: controllo aggiornamenti automatici attivo, ogni 10 minuti."
