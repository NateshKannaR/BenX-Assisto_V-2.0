#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

python3 -m venv benx_venv
benx_venv/bin/python -m pip install -r requirements.txt
exec benx_venv/bin/python benx.py "$@"
