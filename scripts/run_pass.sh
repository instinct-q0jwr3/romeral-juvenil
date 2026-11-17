#!/usr/bin/env bash
set -euo pipefail
python3 scripts/fetch_build.py "$@"
python3 scripts/verify_schedule.py
