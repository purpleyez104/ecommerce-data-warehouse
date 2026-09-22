#!/usr/bin/env bash
# 用法: bash live.sh <new-run-id> <count,0=continuous> <seed> <interval-seconds> --apply
# 非幂等重跑；只有显式 --apply 才会写 MySQL。不要复用已提交的 run-id。
set -euo pipefail
if [[ $# -ne 5 || "$5" != '--apply' ]]; then
  echo 'usage: bash live.sh <new-run-id> <count,0=continuous> <seed> <interval-seconds> --apply' >&2
  exit 2
fi
RUN_ID=$1;COUNT=$2;SEED=$3;INTERVAL=$4
[[ $RUN_ID =~ ^[A-Za-z0-9_-]{1,16}$ && $COUNT =~ ^[0-9]+$ && $SEED =~ ^[0-9]+$ && $INTERVAL =~ ^[0-9]+([.][0-9]+)?$ ]] || { echo 'invalid arguments' >&2; exit 2; }
: "${MYSQL_HOST:?}" "${MYSQL_DATABASE:?}" "${MYSQL_USER:?}" "${MYSQL_PASSWORD:?}"
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../mock/generator/ecommerce_generator_v1" && pwd)
PY="$ROOT/.venv/bin/python"
[[ -x "$PY" ]] || { echo '缺少虚拟环境 Python' >&2; exit 1; }
cd "$ROOT"
"$PY" -m ecommerce_generator --mode live --run-id "$RUN_ID" --count "$COUNT" \
  --seed "$SEED" --interval-seconds "$INTERVAL" --apply
