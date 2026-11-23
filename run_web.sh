#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [[ -d benx_venv ]]; then
    source benx_venv/bin/activate
fi
exec python3 benx.py --web
