#!/usr/bin/env bash
# Read-only audit of the observed R2 101-order state. This is new, not yet ECS-tested.
set -euo pipefail
umask 077

SOURCE_DB=ecommerce_oltp_m2_acceptance
DORIS_DB=ecommerce_serving
BROKERS=hadoop201:9092,hadoop202:9092,hadoop203:9092
TOPIC=ods_cdc_m2_clean_v1

command -v mysql >/dev/null
command -v kafka-get-offsets.sh >/dev/null
command -v cmp >/dev/null
command -v mktemp >/dev/null

source_sql() { sudo mysql -N -B -e "$1"; }
doris_sql() { mysql --protocol=TCP -h 127.0.0.1 -P 9030 -u root -N -B -e "$1"; }

qsource="SELECT order_id,order_status,gross_amount_cents,discount_amount_cents,payable_amount_cents FROM ${SOURCE_DB}.biz_order ORDER BY order_id;"
qdoris="SELECT order_id,order_status,gross_amount_cents,discount_amount_cents,payable_amount_cents FROM ${DORIS_DB}.dwd_order ORDER BY order_id;"

src_file=$(mktemp)
dst_file=$(mktemp)
trap 'rm -f "$src_file" "$dst_file"' EXIT
source_sql "$qsource" > "$src_file"
doris_sql "$qdoris" > "$dst_file"

if ! cmp -s "$src_file" "$dst_file"; then
  echo 'FAIL: MySQL and Doris differ in order_id/status/core amount fields (rows not printed)' >&2
  exit 1
fi

source_stats=$(source_sql "SELECT COUNT(*),COALESCE(SUM(order_status='CREATED'),0),COALESCE(SUM(order_status='PAID'),0),COALESCE(SUM(order_status='CANCELED'),0),COUNT(DISTINCT order_id) FROM ${SOURCE_DB}.biz_order;")
doris_stats=$(doris_sql "SELECT COUNT(*),COALESCE(SUM(order_status='CREATED'),0),COALESCE(SUM(order_status='PAID'),0),COALESCE(SUM(order_status='CANCELED'),0),COUNT(DISTINCT order_id) FROM ${DORIS_DB}.dwd_order;")
expected=$'101\t0\t69\t32\t101'
if [[ "$source_stats" != "$expected" || "$doris_stats" != "$expected" ]]; then
  echo "FAIL: observed R2 aggregate differs; source=[$source_stats], doris=[$doris_stats]" >&2
  exit 1
fi

source_probe=$(source_sql "SELECT COUNT(*) FROM ${SOURCE_DB}.biz_order WHERE LEFT(order_no,10)='R2_ACCEPT_' AND order_status='CANCELED';")
doris_probe=$(doris_sql "SELECT COUNT(*) FROM ${DORIS_DB}.dwd_order WHERE LEFT(order_no,10)='R2_ACCEPT_' AND order_status='CANCELED' AND kafka_partition=0 AND kafka_offset=1183;")
if [[ "$source_probe" != 1 || "$doris_probe" != 1 ]]; then
  echo 'FAIL: expected R2 cancellation probe not found exactly once' >&2
  exit 1
fi

offsets=$(kafka-get-offsets.sh --bootstrap-server "$BROKERS" --topic "$TOPIC" --time -1)
printf '%s\n' "$offsets"
if ! printf '%s\n' "$offsets" | awk -F: '
  NF != 3 { bad=1 }
  $2 == 0 && $3 >= 1185 { p0=1 }
  $2 == 1 && $3 == 0 { p1=1 }
  $2 == 2 && $3 == 0 { p2=1 }
  END { exit !(NR==3 && !bad && p0 && p1 && p2) }
'; then
  echo 'FAIL: Kafka offset/partition assumption differs from observed R2 baseline' >&2
  exit 1
fi

echo 'R2_ORDER_CORE_RECONCILIATION: PASS (not full-field or exactly-once acceptance)'
