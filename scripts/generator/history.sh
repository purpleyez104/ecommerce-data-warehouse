#!/usr/bin/env bash
# 用法: bash history.sh <run-id> <count> <seed> <anchor-ISO> <--dry-run|--preflight|--apply>
set -euo pipefail
if [[ $# -ne 5 ]]; then
  echo 'usage: bash history.sh <run-id> <count> <seed> <anchor-ISO> <--dry-run|--preflight|--apply>' >&2
  exit 2
fi
RUN_ID=$1;COUNT=$2;SEED=$3;ANCHOR=$4;ACTION=$5
[[ $RUN_ID =~ ^[A-Za-z0-9_-]{1,16}$ && $COUNT =~ ^[1-9][0-9]*$ && $SEED =~ ^[0-9]+$ ]] || { echo 'invalid run-id/count/seed' >&2; exit 2; }
case "$ACTION" in
  --dry-run) FLAG=() ;;
  --preflight) FLAG=(--preflight-only) ;;
  --apply) FLAG=(--apply) ;;
  *) echo 'invalid action' >&2; exit 2 ;;
esac
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../mock/generator/ecommerce_generator_v1" && pwd)
PY="$ROOT/.venv/bin/python"
[[ -x "$PY" ]] || { echo '缺少虚拟环境 Python' >&2; exit 1; }
if [[ $ACTION != --dry-run ]]; then
  : "${MYSQL_HOST:?}" "${MYSQL_DATABASE:?}" "${MYSQL_USER:?}" "${MYSQL_PASSWORD:?}"
fi
cd "$ROOT"
"$PY" -m ecommerce_generator --mode history --count "$COUNT" --history-days 90 \
  --run-id "$RUN_ID" --seed "$SEED" --anchor "$ANCHOR" "${FLAG[@]}"
