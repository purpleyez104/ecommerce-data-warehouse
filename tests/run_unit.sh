#!/usr/bin/env bash
set -euo pipefail

repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

if command -v python3 >/dev/null 2>&1 && python3 --version >/dev/null 2>&1; then
  python_bin=python3
elif command -v python >/dev/null 2>&1 && python --version >/dev/null 2>&1; then
  python_bin=python
else
  echo "ERROR: Python 3 is required" >&2
  exit 2
fi

cd "$repo"

PYTHONPATH="$repo/mock/generator/business_generator/src${PYTHONPATH:+:$PYTHONPATH}" \
  "$python_bin" -m unittest discover \
  -s mock/generator/business_generator/tests -p 'test_*.py' -v

PYTHONPATH="$repo/mock/generator/business_generator/src${PYTHONPATH:+:$PYTHONPATH}" \
  "$python_bin" -m py_compile \
  mock/generator/business_generator/src/business_generator/replay.py \
  mysql/scripts/plan_replay_bootstrap.py \
  mysql/scripts/replay_daily_package.py \
  datax/scripts/run_ods_batch.py \
  spark/scripts/render_ods_batch_sql.py

PYTHONPATH="$repo/mock/generator/behavior_generator/src${PYTHONPATH:+:$PYTHONPATH}" \
  "$python_bin" -m unittest discover \
  -s mock/generator/behavior_generator/tests -p 'test_*.py' -v

PYTHONPATH="$repo/mock/generator/behavior_generator/src${PYTHONPATH:+:$PYTHONPATH}" \
  "$python_bin" -m py_compile \
  mock/generator/behavior_generator/src/behavior_generator/replay.py

"$python_bin" -m unittest discover -s tests/datax -p 'test_*.py' -v

PYTHONPATH="$repo/mock/generator/business_generator/src${PYTHONPATH:+:$PYTHONPATH}" \
  "$python_bin" -m unittest discover -s tests/mysql -p 'test_*.py' -v
