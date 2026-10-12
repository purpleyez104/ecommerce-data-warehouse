#!/usr/bin/env bash

set -euo pipefail

readonly SPARK_SQL_BIN=${SPARK_SQL_BIN:-spark-sql}
readonly ODS_TABLE='ecommerce_ods.ods_order'
readonly EXPECTED_RESULT=$'100\t100\t88\t69\t31\t8402600\t30000\t8372600\t0'

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

command -v "${SPARK_SQL_BIN}" >/dev/null 2>&1 \
  || fail "spark-sql command not found: ${SPARK_SQL_BIN}"

result_file=$(mktemp)
trap 'rm -f "${result_file}"' EXIT

read -r -d '' quality_sql <<SQL || true
SELECT concat_ws(
  '\\t',
  CAST(COUNT(*) AS STRING),
  CAST(COUNT(DISTINCT order_id) AS STRING),
  CAST(COUNT(DISTINCT dt) AS STRING),
  CAST(SUM(CASE WHEN order_status = 'PAID' THEN 1 ELSE 0 END) AS STRING),
  CAST(SUM(CASE WHEN order_status = 'CANCELED' THEN 1 ELSE 0 END) AS STRING),
  CAST(SUM(gross_amount_cents) AS STRING),
  CAST(SUM(discount_amount_cents) AS STRING),
  CAST(SUM(payable_amount_cents) AS STRING),
  CAST(SUM(
    CASE
      WHEN order_id IS NULL
        OR order_no IS NULL
        OR order_status IS NULL
        OR order_status NOT IN ('PAID', 'CANCELED')
        OR gross_amount_cents IS NULL
        OR discount_amount_cents IS NULL
        OR payable_amount_cents IS NULL
        OR gross_amount_cents - discount_amount_cents <> payable_amount_cents
        OR created_at IS NULL OR to_timestamp(created_at) IS NULL
        OR business_date IS NULL OR trim(business_date) = ''
        OR dt IS NULL OR dt NOT RLIKE '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
        OR business_date <> dt
        OR business_date <> date_format(to_timestamp(created_at), 'yyyy-MM-dd')
        OR extract_time IS NULL OR trim(extract_time) = ''
        OR batch_id IS NULL
        OR source_table IS NULL
        OR source_table <> 'ecommerce_oltp_m2_acceptance.biz_order'
        OR (dt = '2026-09-17' AND batch_id <> 'm3pilot_20260921_01')
        OR (dt <> '2026-09-17' AND batch_id <> 'm3hist_20260921_01')
      THEN 1 ELSE 0
    END
  ) AS STRING)
)
FROM ${ODS_TABLE};
SQL

if ! "${SPARK_SQL_BIN}" -S -e "${quality_sql}" >"${result_file}"; then
  fail "Spark SQL execution failed"
fi

declare -a parsed_rows=()
while IFS= read -r output_line; do
  output_line=${output_line%$'\r'}
  if [[ "${output_line}" =~ ^[0-9]+$'\t'[0-9]+$'\t'[0-9]+$'\t'[0-9]+$'\t'[0-9]+$'\t'[0-9]+$'\t'[0-9]+$'\t'[0-9]+$'\t'[0-9]+$ ]]; then
    parsed_rows+=("${output_line}")
  fi
done < "${result_file}"

[[ ${#parsed_rows[@]} -eq 1 ]] \
  || fail "expected exactly one parseable nine-column result row, found ${#parsed_rows[@]}"

actual_result=${parsed_rows[0]}
echo "Expected: ${EXPECTED_RESULT}"
echo "Actual:   ${actual_result}"

[[ "${actual_result}" == "${EXPECTED_RESULT}" ]] \
  || fail "biz_order ODS fixed baseline mismatch"

echo "ODS_ORDER_QUALITY: PASS"
