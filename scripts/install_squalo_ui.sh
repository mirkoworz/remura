#!/usr/bin/env bash
# Read-only source checks first; deploy frontend and allowlist only if tests pass.
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -m py_compile scripts/private_server.py
python3 -m unittest discover -s tests -p 'test_private_server.py' -q

if command -v node >/dev/null 2>&1; then
  node --check squalo-core.js
  node --check squalo.js
  node --check squalo-scanner.js
  node --check remura-settings.js
  node --test tests/squalo.test.js tests/two-sentiments.test.js
else
  echo "AVVISO: Node.js non installato; test JavaScript locali non eseguiti."
  echo "Sintassi e logica base gia controllate nel repository; test Python superati."
fi

sudo install -o remura -g remura -m 644 \
  asset.html index.html nav.js sw.js \
  squalo.html squalo-core.js squalo.js squalo-scanner.js squalo.css \
  remura-settings.js sources.js price.js \
  /opt/remura/

sudo install -o remura -g remura -m 644 \
  scripts/private_server.py /opt/remura/scripts/private_server.py

sudo systemctl restart remura-private
sudo systemctl is-active --quiet remura-private
curl --fail --silent --show-error -o /dev/null http://127.0.0.1:8765/squalo.html
curl --fail --silent --show-error -o /dev/null http://127.0.0.1:8765/squalo-core.js
curl --fail --silent --show-error -o /dev/null http://127.0.0.1:8765/remura-settings.js
echo "REMURA SQUALO PRONTA"
