# Spark 提交脚本

`render_ods_batch_sql.py` 根据 21 表 ODS Contract 与版本化 Batch Contract 生成 Validation SQL、Publish SQL 和受影响分区计划。Validation 覆盖必需字段 Projection、PK 非空/唯一、总行数、逐业务日期行数、业务日期集合和审计字段；Bootstrap 直接覆盖完整分区，Incremental 先把“目标分区未命中本批 PK 的旧行 + 本批最新行”写入批次隔离的 `_merge` ORC，再从独立物理边界覆盖目标分区。`render_ods_gate_sql.py` 根据独立期望生成最终 ODS Gate。SQL 不在本地执行；目标环境已完成 ORC Schema、Hive 分区发布和 Gate 验证。

Milestone 3 的 Day 60～90 Spark Validation / Publish 已通过最终 1,498/1,498 Gate；Milestone 4、5 的 DIM/DWD/DWS/ADS 与正式指标质量也已完成 Runtime 验收。Doris 服务、调度和性能实验仍未完成。

`render_behavior_ods_sql.py` 为独立 Behavior 60/30 Bundle 执行 Package Manifest、SHA-256、精确 Schema、行数、事件枚举、`event_id` 唯一和时间语义预检，再生成 JSONL 动态分区 Publish 与独立 Gate SQL。2026-10-18 已在目标 YARN/Hive/HDFS 环境验证完整 Bundle：3,000,000 行、90 个业务日分区、95/95 项 Gate 通过；该入口不属于 MySQL/DataX 21 表 Runner，也不证明 Kafka/Flink Runtime。
