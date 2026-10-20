# M6 Doris 离线 Serving 验收

日期：2026-10-20
状态：`VERIFIED`

## Contract

- Hive Source：`ecommerce_ads.ads_daily_business_overview`。
- Doris Target：`ecommerce_serving.ads_daily_business_overview`。
- 表模型：`UNIQUE KEY(business_date)` + Merge-on-Write，2 Buckets、2 Replicas。
- Writer：Spark 3.5.9 + `spark-doris-connector-spark-3.5-26.0.0.jar`。
- 凭据只从 `DORIS_FENODES`、`DORIS_USER`、`DORIS_PASSWORD` 注入，不进入仓库。

## Acceptance → Evidence

| Acceptance | 实际证据 | 结果 |
| --- | --- | --- |
| 单日写入 | `2026-02-28` 首次 Spark Application `application_1792391393185_0001` 成功 | `VERIFIED` |
| 单日幂等 | 同日重跑 `application_1792391393185_0003` 成功，仍为 1 行/1 日期 | `VERIFIED` |
| 单日全字段对账 | Hive/Doris 22 字段 SHA-256 均为 `fccd4318964b0e098c2f3514413b2c7ff3a90413194ee01eb7ea97b5c33f90b7` | `VERIFIED` |
| 90 日装载 | `2025-12-01..2026-02-28`，Application `application_1792391393185_0004` 成功 | `VERIFIED` |
| 90 日幂等 | 全范围重跑 `application_1792391393185_0006` 成功，仍为 90 行/90 日期 | `VERIFIED` |
| 90 日全字段对账 | Hive/Doris 90 行 × 22 字段逐行一致，SHA-256 均为 `b3969f7d60e054e7f656f65cb7c7261aa8cf413758f20a1144e09f335b6570ce` | `VERIFIED` |
| 正式 DAG 自动重试与阻断 | Workflow Instance `12` 最终为 `FAILURE`；`doris_load` 为 `FAILURE`、`retry=1`，且 `serving_reconciliation` 未运行 | `VERIFIED` |
| 修正后独立 Doris 阶段 | Doris YARN Application `application_1792417296391_0002` 为 `FINISHED / SUCCEEDED`；该证据不是 DolphinScheduler 内恢复 | `VERIFIED` |
| 修正后独立双向对账 | `application_1792417296391_0003` 为 `FINISHED / SUCCEEDED`；脚本要求闭区间 90 行，并对 22 字段执行 Hive→Doris、Doris→Hive 双向 `exceptAll`；该证据不是调度后对账 | `VERIFIED` |
| Instance 14 误建 DIM 分区清理 | 四个 `dt=2026-02-27` 分区先备份至 `/warehouse/ecommerce/model/.rollback/m6-ds-backfill-20260227-r2/` 并核对 HDFS 数量/字节，再精确删除；四表仅剩 `2026-02-28` 且业务键唯一 | `VERIFIED` |
| Behavior DWD 保护 | 清理后仍为 3,000,000 行、3,000,000 个唯一 `event_id`，范围 `2025-12-01..2026-02-28` | `VERIFIED` |
| Aggregate Backfill Contract | Workflow Code `187427451612864`；Instance `17` 的 Model Ready、DWS/ADS、40-rule Quality、Doris Load、Serving Reconciliation 全部成功，未重跑 DataX/ODS/DIM/DWD | `VERIFIED` |
| Aggregate Backfill Doris Load | 初始 Kryo `DirectTaskResult` 解码 EOF；HDFS 90/90 Blocks 健康、三节点 Spark/Kryo 包一致。相同 89 日输入用任务级 `JavaSerializer` 验证 89 行/89 日期后，仅恢复失败 Doris Task `41`，输出 `DORIS_PASS` | `VERIFIED` |
| Aggregate Backfill 调度后对账 | 首次字段诊断确认 21 个业务字段一致，仅 `load_time` 因 Hive 微秒与 Doris `DATETIME` 秒级精度不同而漂移；规范到秒后 Task `45` 输出 `SERVING_RECONCILIATION_PASS`，Instance `17` 最终为 `SUCCESS` | `VERIFIED` |
| 显式质量失败与下游阻断 | 专用 Workflow Code `187464279901408`、Instance `18` 将 `ads_daily_business_overview.business_key_unique` 作为唯一注入失败；质量结果为 40 条、`FAIL=1`，Quality Task 为 `FAILURE`、`retry=0`，Doris/Reconciliation 未运行 | `VERIFIED` |
| 失败场景 Doris 不变性 | 验证前后均为 90 行/90 日期、`2025-12-01..2026-02-28`，`paid_amount_cents=10374159421`、`refund_amount_cents=311199194`、最大 `load_time=2026-10-20 11:13:15` | `VERIFIED` |
| 失败验证安全收尾 | 专用 Workflow 定义验证后切换为 `OFFLINE`；正式 Workflow 未修改 | `VERIFIED` |
| 凭据回收 | 临时 Loader Env 文件已删除；仓库无密码 | `VERIFIED` |

2026-10-19 收尾状态：补数 Instance `14` 的 DataX/ODS 与 ODS Ready Gate 成功；`dim_dwd_build` 因 Type 1 DIM 被错误按历史日追加全量快照而触发 `dim_category.business_key_unique`，随后被受控停止，Workflow 终态为 `STOP`。2026-10-20 已完成四个误建分区的可恢复清理；Instance `14` 不再作为恢复入口，后续使用不包含 DataX/ODS/DIM/DWD 的独立 Aggregate Backfill DAG。

90 日汇总：`paid_amount_cents=10374159421`、`refund_amount_cents=311199194`、`cumulative_net_paid_cents=10062960227`。

## 边界

本验收已证明 Doris 离线 Serving 独立任务、正式 DAG 自动重试/失败阻断、误建 DIM 分区的可恢复清理、Aggregate Backfill 五 Task 成功终态与调度后双向对账，以及显式质量失败后的下游阻断和 Doris 不变性，M6 Stage Gate 完成。证据覆盖固定 90 日范围及一个历史目标日，不代表所有任意日期组合均已逐一执行。Connector 安装在隔离的 M6 Runtime，不修改 Spark 全局 Jar；Serving Spark Task 仅覆盖为 `JavaSerializer`，不修改集群全局 Serializer。系统默认 Java 仍为 17，Hadoop 使用 Java 11，Doris 阶段仅对 YARN AM/Executor 固定 Java 8。
