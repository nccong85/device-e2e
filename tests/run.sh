#!/usr/bin/env bash
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# On Windows python3 is often the Microsoft Store stub, which exits non-zero.
PY="${E2E_PYTHON:-}"
if [ -z "$PY" ]; then
  for p in python3 python; do "$p" -c '' 2>/dev/null && { PY=$p; break; }; done
fi
[ -n "$PY" ] || { echo "no Python found: set E2E_PYTHON"; exit 1; }
status=0
bash "$HERE/plugin_test.sh" || status=1
"$PY" "$HERE/drivers_test.py" || status=1
"$PY" "$HERE/e2e_plan_test.py" || status=1
"$PY" "$HERE/procs_test.py" || status=1
exit $status
