#!/usr/bin/env bash
set -euo pipefail
umask 077
export LC_ALL=C

# R1：只适用于冻结的 100 单验收基线。
# 只读；失败返回非零状态；不保存密码，也不输出订单 ID。
# 认证沿用目标 ECS 已配置的本机 MySQL sudo/socket 与 Doris MySQL client 方式。

SOURCE_DB="${SOURCE_DB:-ecommerce_oltp_m2_acceptance}"
DORIS_DB="${DORIS_DB:-ecommerce_serving}"
DORIS_HOST="${DORIS_HOST:-127.0.0.1}"
DORIS_PORT="${DORIS_PORT:-9030}"
DORIS_USER="${DORIS_USER:-root}"

SOURCE_TABLE="${SOURCE_DB}.biz_order"
DORIS_TABLE="${DORIS_DB}.dwd_order"
EXPECTED_SUMMARY=$'100\t69\t31\t100'

for command_name in cmp mktemp mysql sudo; do
  command -v "$command_name" >/dev/null || {
    echo "MISSING: $command_name" >&2
    exit 2
  }
done

summary_sql() {
  local table="$1"

  cat <<SQL
SELECT
  COUNT(*),
  COALESCE(SUM(order_status = 'PAID'), 0),
  COALESCE(SUM(order_status = 'CANCELED'), 0),
  COUNT(DISTINCT order_id)
FROM ${table};
SQL
}

rows_sql() {
  local table="$1"

  cat <<SQL
SELECT
  order_id,
  order_status,
  gross_amount_cents,
  discount_amount_cents,
  payable_amount_cents
FROM ${table}
ORDER BY order_id;
SQL
}

echo "=== 1. MySQL baseline ==="
source_summary=$(sudo mysql -N -B -e "$(summary_sql "$SOURCE_TABLE")")
printf '%s\n' "$source_summary"

if [[ "$source_summary" != "$EXPECTED_SUMMARY" ]]; then
  echo "FAIL: MySQL baseline changed" >&2
  exit 1
fi

echo "=== 2. Doris baseline ==="
doris_summary=$(
  mysql \
    --protocol=TCP \
    -h "$DORIS_HOST" \
    -P "$DORIS_PORT" \
    -u "$DORIS_USER" \
    -N -B \
    -e "$(summary_sql "$DORIS_TABLE")"
)
printf '%s\n' "$doris_summary"

if [[ "$doris_summary" != "$EXPECTED_SUMMARY" ]]; then
  echo "FAIL: Doris baseline mismatch" >&2
  exit 1
fi

echo "=== 3. Row-level reconciliation ==="
tmpdir=$(mktemp -d)
trap 'rm -rf -- "$tmpdir"' EXIT

sudo mysql -N -B \
  -e "$(rows_sql "$SOURCE_TABLE")" \
  > "$tmpdir/mysql.tsv"

mysql \
  --protocol=TCP \
  -h "$DORIS_HOST" \
  -P "$DORIS_PORT" \
  -u "$DORIS_USER" \
  -N -B \
  -e "$(rows_sql "$DORIS_TABLE")" \
  > "$tmpdir/doris.tsv"

if ! cmp -s "$tmpdir/mysql.tsv" "$tmpdir/doris.tsv"; then
  echo "FAIL: Order IDs, states or amounts differ" >&2
  exit 1
fi

echo "ORDER_DWD_CONSISTENCY: PASS"
