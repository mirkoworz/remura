#!/usr/bin/env bash
# Offline integrated test runner. No npm install, no deploy, no Cloudflare calls.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
node -e 'if(Number(process.versions.node.split(".")[0])<22)throw Error("Node 22+ required"); require("node:sqlite")'
# New integration only; previously passed checks intentionally not repeated.
node --test test-integrated-v3019.mjs
