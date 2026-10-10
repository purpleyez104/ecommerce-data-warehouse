#!/usr/bin/env bash
set -euo pipefail
export FLINK_HOME="${FLINK_HOME:-/data/module/flink-1.20.5-cdc}"
export HADOOP_CLASSPATH="$(hadoop classpath)"
ROOT="$(cd "$(dirname "$0")" && pwd)"
TOPIC='ods_cdc_m2_clean_v1'
CP='hdfs://hadoop201:8020/user/hive/warehouse/ecommerce/flink/checkpoints/order_dwd_r1_v1'
BROKERS='hadoop201:9092,hadoop202:9092,hadoop203:9092'
test -f "$ROOT/build/r1-order-dwd.jar" || { echo 'STOP: build jar first'; exit 1; }
if hdfs dfs -test -e "$CP"; then echo 'STOP: dedicated checkpoint path exists; inspect existing job before retry'; exit 1; fi
mysql --protocol=TCP -h hadoop201 -P 9030 -u root -N -B -e 'SELECT COUNT(*) FROM ecommerce_serving.dwd_order' | grep -Fxq 0 || { echo 'STOP: dwd_order is nonempty'; exit 1; }
echo 'Kafka latest offsets:'
kafka-get-offsets.sh --bootstrap-server "$BROKERS" --topic "$TOPIC" --time -1
read -r -p 'Confirm no other active R1 order DWD writer; type START to submit: ' answer
[ "$answer" = 'START' ] || { echo 'Canceled'; exit 1; }
"$FLINK_HOME/bin/flink" run-application -t yarn-application -c com.ecommerce.r1.OrderDwdJob "$ROOT/build/r1-order-dwd.jar"
