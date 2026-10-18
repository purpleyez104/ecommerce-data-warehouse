# Spark 提交脚本

`render_ods_batch_sql.py` 根据 21 表 ODS Contract 与版本化 Batch Contract 生成 Validation SQL、Publish SQL 和受影响分区计划。Validation 覆盖必需字段 Projection、PK 非空/唯一、总行数、逐业务日期行数、业务日期集合和审计字段；Bootstrap 直接覆盖完整分区，Incremental 先把“目标分区未命中本批 PK 的旧行 + 本批最新行”写入批次隔离的 `_merge` ORC，再从独立物理边界覆盖目标分区。`render_ods_gate_sql.py` 根据独立期望生成最终 ODS Gate。SQL 不在本地执行；目标环境已完成 ORC Schema、Hive 分区发布和 Gate 验证。

当前 Milestone 3 入口状态为 `verified`：Day 60～90 已完成 Spark Validation / Publish，最终 Gate 为 1,498/1,498 项断言通过。该结论不表示 Milestone 4～7 的 DIM/DWD/DWS/ADS、Doris 服务、调度或性能实验已完成。
