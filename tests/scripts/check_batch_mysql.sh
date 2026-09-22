#!/usr/bin/env bash
# 只读：对指定批次执行项目验收 SQL 和实际明细数量核对。依赖 hadoop201 的 sudo mysql。
set -euo pipefail
RUN_ID="${1:-}"
[[ $RUN_ID =~ ^[A-Za-z0-9_-]{1,16}$ ]] || { echo 'usage: bash check_batch_mysql.sh <run-id>' >&2;exit 2; }
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
sed "s/<RUN_ID>/$RUN_ID/g" "$REPO/mysql/sql/acceptance.sql" | sudo mysql -t ecommerce_oltp_m2_acceptance
sudo mysql -t ecommerce_oltp_m2_acceptance -e "SELECT COUNT(*) AS actual_items FROM biz_order_item i JOIN biz_order o ON i.order_id=o.order_id WHERE o.order_no LIKE 'GEN1_${RUN_ID}_ORDER_%';"
