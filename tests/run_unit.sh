#!/usr/bin/env bash
# 仓库根目录执行：bash tests/run_unit.sh。适配整理包中的 engineering/ 与合并后的仓库根目录。
set -euo pipefail
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
GEN="$REPO/mock/generator/ecommerce_generator_v1"
[[ -d "$GEN/src" ]] || { echo "generator source not found: $GEN" >&2; exit 2; }
[[ -d "$GEN/src" ]] || { echo 'Missing generator source' >&2;exit 1; }
PY="$GEN/.venv/bin/python"
[[ -x "$PY" ]] || PY=python3
export PYTHONPATH="$GEN/src${PYTHONPATH:+:$PYTHONPATH}"
cd "$REPO"
"$PY" -m pytest -q tests/unit
