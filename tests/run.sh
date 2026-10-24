#!/usr/bin/env bash
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
status=0
bash "$HERE/plugin_test.sh" || status=1
python3 "$HERE/drivers_test.py" || status=1
python3 "$HERE/e2e_plan_test.py" || status=1
exit $status
