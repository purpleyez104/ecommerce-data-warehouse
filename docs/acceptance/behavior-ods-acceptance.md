# Behavior ODS 验收

状态：`VERIFIED`（Behavior 60/30 Bundle → Hive ODS 范围）
验收日期：2026-10-18

## 范围与固定输入

- Dataset：`v2.3-behavior-replay-formal-20260105-r1`，Seed `20260105`，业务窗口 2025-12-01～2026-02-28。
- Bundle：Day 1～60 Bootstrap 895,324 条，Day 61～90 Daily Package 2,104,676 条，合计 3,000,000 条事件。
- Content SHA-256：`a074cab5cc0b7bf82582242b097cc24534a8f2917485c493743574d98f8baf5e`。
- Target：`ecommerce_ods.ods_behavior_event`，EXTERNAL ORC + Snappy，HDFS `/warehouse/ecommerce/ods/ods_behavior_event`，按 `event_time` 的 Asia/Shanghai 自然日分区。
- Runtime：`/data/behavior-ods-runtime-20261018-r1/`；原始 Bundle、日志和临时生成物不提交 Git。

## Acceptance → Evidence

| Acceptance | Evidence |
| --- | --- |
| Bundle 与固定 Contract 一致 | 本地及目标环境预检通过 Package Manifest、SHA-256、精确 Schema、事件枚举、时间、身份、Session、SKU 生效时间和 `event_id` 全局唯一检查 |
| 全量事件成功发布 | Publish Application `application_1792297746029_0004` 退出 0，YARN `FINISHED / SUCCEEDED`；staging 行数为 3,000,000 |
| 业务日期分区完整 | Hive `SHOW PARTITIONS ods_behavior_event` 返回 90 个 `dt` 分区，范围为 2025-12-01～2026-02-28 |
| 最终表质量通过 | Gate Application `application_1792297746029_0005` 退出 0，YARN `FINISHED / SUCCEEDED`，95/95 项查询断言通过并输出 `BEHAVIOR_ODS_GATE_PASS` |
| ODS 物理结果存在 | `hdfs dfs -count /warehouse/ecommerce/ods/ods_behavior_event` 返回 91 个目录、210 个文件、93,526,529 bytes |

## 失败恢复与已知限制

- 首次全量尝试 `application_1792297746029_0003` 因 Spark 递归读取时同时纳入 30 个 `package_manifest.json`，在 staging 行数断言处失败；失败发生在 INSERT 前，未覆盖正式分区。
- Renderer 随后增加 `pathGlobFilter='events.jsonl'` 并保留递归读取，重新生成 SQL 后完成发布和 Gate。该修复已由 Targeted Test 覆盖。
- Publish 期间 Hive Metastore 出现一次可恢复的重连警告；Application 最终成功，独立 Gate 与分区核对均通过，因此不作为数据失败结论。
- 本验收只证明固定 Behavior Bundle 到 Hive ODS 的离线装载、分区和质量结果，不证明 Kafka/Flink、实时 Watermark/迟到处理、DWD/DIM、DWS/ADS、Doris 或 Offline ↔ Realtime Reconciliation 已完成。

## 回滚边界

- 仓库实现可通过后续 Git 变更回滚。
- Hive 表、分区或 `/warehouse/ecommerce/ods/ods_behavior_event` 的删除和重置属于外部破坏性操作，需要新的明确授权；本次未执行清理。
