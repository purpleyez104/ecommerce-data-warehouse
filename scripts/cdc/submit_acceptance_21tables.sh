#!/usr/bin/env bash
# 已有 21 表作业 RUNNING 时请勿执行！重复启动 initial 可能重新写入 Snapshot。
set -euo pipefail
if [[ "${1:-}" != '--submit' ]]; then
  echo '仅在首次部署/确认没有重复 CDC 作业时使用：bash submit_acceptance_21tables.sh --submit' >&2
  exit 2
fi
if [[ "${CONFIRM_NEW_CDC_APPLICATION:-}" != 'YES' ]]; then
  echo '必须先人工检查 YARN 现存 Application，确认无重复，再设置 CONFIRM_NEW_CDC_APPLICATION=YES' >&2
  exit 2
fi
CFG='/home/yee/.secrets/cdc-m2/mysql-21tables-to-kafka.yaml'
[[ -r "$CFG" ]] || { echo "未找到私密配置：$CFG" >&2; exit 1; }
FLINK_HOME=/data/module/flink-1.20.5-cdc \
bash /data/module/flink-cdc-3.6.0-1.20/bin/flink-cdc.sh \
  -t yarn-application \
  -Dpipeline.jars=file:///data/module/flink-cdc-3.6.0-1.20/lib/flink-cdc-dist-3.6.0-1.20.jar \
  -Dexecution.checkpointing.interval=30s \
  -Dexecution.checkpointing.storage=filesystem \
  -Dexecution.checkpointing.dir=hdfs://hadoop201:8020/user/hive/warehouse/ecommerce/flink/checkpoints/m2_21tables \
  "$CFG" \
  --flink-home /data/module/flink-1.20.5-cdc
