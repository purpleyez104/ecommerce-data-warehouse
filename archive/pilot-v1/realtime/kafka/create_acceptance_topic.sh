#!/usr/bin/env bash
set -euo pipefail
TOPIC=cdc_m2_21tables_acceptance
if [[ "${1:-}" != '--create' ]]; then
  echo "只读检查: kafka-topics.sh --bootstrap-server hadoop201:9092 --describe --topic $TOPIC" >&2
  echo '创建需显式传入 --create；已有 Topic 不会删除或重建。' >&2
  exit 2
fi
kafka-topics.sh --bootstrap-server hadoop201:9092 --create --if-not-exists \
  --topic "$TOPIC" --partitions 3 --replication-factor 3 \
  --config min.insync.replicas=2
kafka-topics.sh --bootstrap-server hadoop201:9092 --describe --topic "$TOPIC"
