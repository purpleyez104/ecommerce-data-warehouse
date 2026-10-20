# Project 1 简历证据当前台账

日期：2026-10-19  
状态：`DOING`

本文件按 `docs/design/project1-completion-remediation-plan.md` 的 Stage 10 要求，持续汇总可用于最终简历和面试发布的证据候选。只有具有代码、命令或验收记录支持的 Runtime 结果才能进入 `VERIFIED`；本台账不是最终简历文案，也不把未完成 Stage 提升为已完成。

## VERIFIED 候选数据

| Evidence ID | 可陈述事实 | 证据入口 | 使用边界 |
| --- | --- | --- | --- |
| `P1-RESUME-SOURCE-01` | 构建 21 张 MySQL 业务表，固定 90 天输入装载 1,328,502 行，并通过 45 条 Source Gate | `docs/acceptance/source-load-gate-acceptance.md` | 仅表示正式 Source Build，不代表 CDC 完成 |
| `P1-RESUME-REPLAY-01` | Day 61～90 共执行 1,210,882 个业务操作，形成 30/30 Daily Acceptance；中断后根据 Ledger 与 Checkpoint 恢复且未重复写入 | `docs/acceptance/source-load-gate-acceptance.md` | 隔离 Replay 环境；不外推为生产规模 |
| `P1-RESUME-ODS-01` | 21 张业务 ODS 完成 Day 60～90 发布，最终 1,632,345 行，1,498/1,498 Gate 通过 | `docs/acceptance/formal-ods-smoke-acceptance.md` | 固定 Replay Baseline |
| `P1-RESUME-BEHAVIOR-01` | 独立 Behavior ODS 发布 3,000,000 条事件、90 个分区，95/95 Gate 通过 | `docs/acceptance/behavior-ods-acceptance.md` | 仅离线 ODS，不代表 Kafka/Flink |
| `P1-RESUME-MODEL-01` | 建成 6 DIM、8 DWD、6 DWS、1 ADS；退款申请粒度修正后 Model Gate 60/60、最终 Aggregate Gate 41/41 | `docs/acceptance/m5-refund-contract-migration-acceptance.md`、`docs/acceptance/m5-cohort-metrics-acceptance.md` | 当前 Hive/Spark 离线模型 |
| `P1-RESUME-METRIC-01` | 发布 36 个版本化 Metric Registry 指标，持久化 40 条质量规则且零失败 | `docs/acceptance/m5-stage-gate-assessment.md` | 未冻结指标不在发布范围 |
| `P1-RESUME-RECON-01` | 完成 10 项指标 × 90 日跨层对账，共 900 行且零差异 | `docs/acceptance/m5-cohort-metrics-acceptance.md` | 当前为离线层间对账，不是离实时对账 |
| `P1-RESUME-DORIS-01` | 将 90 日 ADS 写入 Doris，幂等重跑后保持 90 个唯一业务日，并完成 90 行 × 22 字段逐行对账 | `docs/acceptance/m6-doris-offline-serving-acceptance.md` | 离线 Serving；不代表实时 Doris 或调度 DAG |
| `P1-RESUME-SCHEDULER-01` | DolphinScheduler 3.4.2 使用 MySQL JDBC Registry，成功/失败任务及全角色重启后复跑均通过 | `docs/acceptance/m1-dolphinscheduler-jdbc-acceptance.md` | 组件能力；正式 DAG 已实现并验证至 Quality Gate，但 Doris EOF 与最终对账未完成 |
| `P1-RESUME-TEST-01` | 当前统一 Unit Test 入口通过 120/120 | `tests/run_unit.sh`、`docs/status/offline-current.md` | 证明本地自动化范围，不替代集群 Runtime |

## 暂不进入最终简历数字

- Business Generator 的 213 秒是特定环境单次运行事实，不是性能优化结论。
- 历史 100 单和实时 R1～R3 只作为 Pilot / History，不用于宣称正式实时链路完成。
- YARN Application 成功只有同时绑定结果核对和 Gate 时，才能支撑业务完成结论。

## 尚缺证据

| 范围 | 当前状态 | 需要补齐的简历证据 |
| --- | --- | --- |
| DolphinScheduler 正式 DAG | `in progress` | 业务日期/观察窗口参数、依赖、失败阻断、重试和分层回补已形成证据；Doris EOF、调度后对账与质量失败注入待完成 |
| Spark Benchmark | `pending` | 固定规模下优化前后 Plan、扫描量、Shuffle、Stage 与耗时 |
| 正式实时链路 | `in progress` | Formal CDC、Kafka/Flink、Checkpoint/恢复、Doris Upsert 与离实时对账 |
| 轻量 Data Governance | `planned` | Metadata Snapshot、Table-level Lineage、Metric/Quality/Reconciliation/Task 关联 |
| 可复现发布 | `pending` | 新环境最小复现、Evidence Index、去敏摘要和最终简历结论映射 |

## 使用规则

最终简历表述必须引用上述 Evidence ID，并保留环境、固定输入和验证边界。后续 Stage Gate 通过后在本文件追加证据；不得用计划值、静态文件、历史 Pilot 或单次耗时填补缺失结论。
