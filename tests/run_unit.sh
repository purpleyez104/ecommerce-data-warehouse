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

PYTHONPATH="$repo/mock/generator/behavior_generator/src${PYTHONPATH:+:$PYTHONPATH}" \
  "$python_bin" -m unittest discover \
  -s mock/generator/behavior_generator/tests -p 'test_*.py' -v
