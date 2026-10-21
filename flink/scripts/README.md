# Flink 提交、恢复与只读盘点脚本

正式 Java DataStream Jar 的 YARN Application 提交、最终状态检查、Savepoint 和恢复入口放在本目录。

当前仅实现 `inventory_realtime_runtime.py`：它使用调用方显式提供的 Kafka Broker、Topic Namespace、YARN/HDFS CLI 和 Checkpoint/Savepoint Root，执行只读 Inventory 并向标准输出返回 `realtime-runtime-inventory/v1` JSON。脚本不会创建 Topic、提交或终止 Application，也不会写入、恢复或清理 HDFS 资产。

示例（连接地址和 CLI 路径必须按目标环境填写）：

```bash
python flink/scripts/inventory_realtime_runtime.py \
  --bootstrap-server '<broker-host>:<port>' \
  --topic-namespace 'ecommerce.realtime.v1' \
  --checkpoint-root 'hdfs:///warehouse/ecommerce/realtime/v1/checkpoints' \
  --savepoint-root 'hdfs:///warehouse/ecommerce/realtime/v1/savepoints' \
  --kafka-topics-command '<kafka-bin>/kafka-topics.sh' \
  --yarn-command '<hadoop-bin>/yarn' \
  --hdfs-command '<hadoop-bin>/hdfs'
```

任一查询失败、超时或 Root 不安全时返回非零状态。输出仅表示查询时刻的资产清单，不等于 Application 健康、Checkpoint 可恢复或 Formal Realtime Runtime 已通过验收。
