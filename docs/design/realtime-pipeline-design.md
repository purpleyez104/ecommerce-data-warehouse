# 实时链路架构规范（Milestone 8 设计输入）

状态：M8/M9 `in progress`；R1～R3 已完成 Pilot / Acceptance 使命并转为 History。Realtime V2 已完成方向设计但尚未开始 Formal CDC 实现，当前与离线共同进入 Shared V2 Source Data Build。当前在线、最新 Checkpoint、正式 Topic/Partition/`event_version`、全字段/跨分区/乱序与端到端 Exactly-Once 仍未验证。更新时间：2026-09-27。

本文件展开[最终工程架构](../architecture/final-architecture-v1.0.md)的实时视图，并以[业务源设计](business-source-design.md)及[指标口径](../business/metrics.md)为上游。用户已确认实时链路正在建设，但本文不是 Milestone 8 已完成评审或 Milestone 9 已验证的证明。

## 数据流与责任

```text
Historical Generator → 21 CSV → LOAD DATA → MySQL ecommerce_oltp
Incremental Business Generator → MySQL Transaction → Binlog → Flink CDC → Kafka Raw CDC
独立行为源 ───────────────────────────────→ Kafka 行为事件
Kafka 输入 → Flink Java DataStream Jar（YARN Application）
            ├→ Kafka 标准事件（待设计）
            ├→ HDFS/Hive 长期归档（待设计）
            └→ Doris 订单 / 订单明细 DWD（限定切片已实现）/ 其他实时服务表（待设计）
```

- 交易状态与关键历史必须先进入 MySQL；Flink CDC 从 ROW/FULL Binlog 采集 Snapshot 和后续 INSERT/UPDATE/DELETE，不能由生成器伪造 CDC。独立行为事件与交易 CDC 应保留不同来源标识和可解释的关联键。
- Kafka Raw CDC 只承担传输和短期重放，不是长期数仓存储。`ods_cdc_m2_clean_v1` 只作为 R1～R3 Pilot History 保留，正式 V2 不再写入；正式 Topic Namespace 必须在 Topic Inventory 后冻结。Debezium JSON 的 `before/after/op/source` 是已验证格式示例，正式 Schema、兼容演进、Key 和保留期仍待评审。
- Flink 正式业务处理采用 Java DataStream API、打包为 Jar、运行于 YARN Application Mode。SQL Client + YARN Session 保留用于 Kafka SQL 技术验证，不作为正式业务部署模式。`yarn-application` 下 SQL `INSERT` 曾有 `No ExecutorFactory` 限制；不能把 SQL Session 的成功直接外推到正式 Application。
- Doris 4.0.8 FE 位于 `hadoop201`（HTTP `18030`），BE 位于 `hadoop202/203`。Flink Doris Connector 26.1.1 的临时写入、Upsert、Checkpoint 和指定恢复场景已通过；正式实时 Key 模型、分区、分桶、更新/撤回语义仍待设计。Doris 不替代 Hive 的历史与重算责任。

## Pilot / Acceptance History

实时链路 Chat 的历史输出支持以下事实；R1/R2 的已入库边界见 [R1 实时链路验收记录](../acceptance/r1-realtime-acceptance.md) 与 [R1/R2 验收记录](../acceptance/realtime_r1_r2_verified.md)，R3 增量事实来自最新 Realtime Work Handoff：

- `ecommerce_oltp_m2_acceptance` 的 21 表初始 Snapshot 在 `ods_cdc_m2_clean_v1` 固定审计区间为 1,178 / 1,178，100 单主键和最终状态一致。
- `biz_product_change_event` 的隔离 INSERT、DELETE 已观察到 `op=c`、`op=d`；订单 R2 探针的 `CREATED → CANCELED` 已观察到 `biz_order op=u` 和状态事件 `op=c`。
- CDC 与 Order DWD 后续分别从 `chk-396`、`chk-179` 恢复成功并继续形成 Completed Checkpoint；这些只是已验证恢复点，不是当前最新 Checkpoint，当前状态未知。
- Doris `ecommerce_serving.dwd_order` 使用 `UNIQUE KEY(order_id)`、`kafka_offset` Sequence、2 副本和 2 Bucket；R2 探针后的历史汇总为 101 单、69 `PAID`、32 `CANCELED`、101 个不同订单 ID。
- `OrderItemDwdJob` Initial Load 完成 MySQL / Doris 320 行、320 个不同明细、101 个订单、627 件及金额/退款/质量对账；一次 `updated_at` 更新产生 Kafka `op=u`、offset 1185，Doris 同键更新后行数仍为 320。
- 当前 Order / OrderItem Doris 表分别使用 `UNIQUE KEY(order_id)`、`UNIQUE KEY(order_item_id)` 与 `kafka_offset` Sequence。`kafka_offset` 版本规则仅在业务事件全部位于 Partition 0 且 Topic 未重建时成立；它不是正式多分区或 Topic 重建后的版本契约。

上述实现不关闭 Milestone 8 的 Topic/Schema、事件时间、状态、恢复、归档和离实时阈值决策，也不证明当前作业在线、全字段逐行对账、乱序保护或端到端 Exactly-Once。

`ecommerce_oltp_m2_acceptance`、`ods_cdc_m2_clean_v1`、`all-to-zero`、Pilot Checkpoint Root 和 `kafka_offset` Sequence 均不进入正式 V2。`OrderDwdJob`、`OrderItemDwdJob` 保留为 `VERIFIED PROTOTYPE / FRAMEWORK REFERENCE`，用于提取 Kafka Metadata Deserializer、CDC Parser、Source Router、Doris Sink Builder、Checkpoint 和 YARN Application 提交/恢复框架，不复制为 21 个长期 Application。

## Realtime V2 初始化与工程组织

Realtime V2 与离线共享 `ecommerce_oltp`、7 域 21 表业务模型和 Metrics Contract。初始化顺序固定为：Python → CSV → `LOAD DATA` → SOURCE GATE → 停止源写入 → 正式 Flink CDC Initial Snapshot → Kafka Snapshot Gate → 冻结 Snapshot 基线 → 启动 Incremental Business Generator → 持续 Binlog。增量生成器必须写 MySQL Transaction，禁止直接写 Kafka。

正式 CDC 覆盖一期 21 表，并验证表/库 metadata、主键、Snapshot 完整性、INSERT/UPDATE 和关键 DELETE。Partition/Key 原则为 Same Business Key → Same Partition → Ordered Events；具体 Partition 数在数据规模冻结后决定。正式 `event_version` 必须稳定判断同一业务主键的新旧事件，在冻结前不得复制 `kafka_offset` Sequence。

Flink 工程按业务域组织 Domain Applications，例如交易域统一处理 order、order_item、payment、refund。运行框架复用 Kafka Source、CDC Envelope Parser、DB/Table Router、Metadata、Checkpoint、Error Handling、Doris Sink、提交、日志和恢复；业务 Transform 分业务过程维护。实时 DWS/ADS 按指标域组织，并复用离线 Metrics Contract。

## 运行与 Java 边界

Flink Client 使用 Java 17；当前 YARN Container 与 Flink Doris User Jar 使用 Java 11 兼容边界。R3 的 Java 17 产物曾因 class major version 61 触发 `UnsupportedClassVersionError`，最终以 `javac --release 11`、major version 55 修复。正式 Jar 的依赖、序列化、状态、连接器组合和目标字节码必须在固定版本下重新验证。提交命令退出 0 仅表示提交成功，作业成败须核查 YARN application final state、Flink 作业状态和目标端结果；故障后不能仅凭 Checkpoint 配置宣称端到端 Exactly-Once。

## 待 Milestone 8 冻结的契约

| 范围 | 必须形成的结论 |
| --- | --- |
| Kafka | Raw/标准事件 Topic 划分、Key、Partition、副本、保留、压缩、Schema 和演进 |
| Flink | CDC 与计算作业拆分、业务事件时间、Watermark、窗口、允许迟到、去重键、状态 TTL、撤回与补偿 |
| 维度和指标 | 历史/当前维度版本、首批实时指标稳定发布 ID、与离线一致的公式和时间归属 |
| 状态与恢复 | Checkpoint/Savepoint、重启策略、源端继续写入后的恢复、一致性目标与可重放边界 |
| 存储和对账 | HDFS/Hive 归档、Doris 实时表 Key/分区/分桶、离实时差异阈值及资源预算 |

上述未决项不得由本文件的示意图推导成默认值。现有[ENV-05](../acceptance/env-05-cdc-acceptance.md)只证明单隔离测试表的 Snapshot、Binlog c/u/d 与指定 TaskManager 故障恢复；M1 Step 10 的 Kafka SQL 基础链路存在重复输出备注，Step 12 的 Doris 连接器验证也不能替代正式 21 表、行为流与指标的端到端可靠性验收。

[R1 全量快照冻结记录](../acceptance/r1_snapshot_acceptance_frozen.md)只证明 2026-09-21 的初始快照边界；[R1/R2 验收记录](../acceptance/realtime_r1_r2_verified.md)补充当时的 Checkpoint 恢复、正常顺序订单 Upsert 及 Doris 101 单汇总。最新 Handoff 又记录了后续恢复点和 R3 OrderItem 验收，但没有附带 R3 最终工程文件或新增 acceptance 文档。当前在线、最新 Checkpoint、全字段/乱序对账、R2/R3 更新故障恢复、正式实时指标或 Exactly-Once 结论仍未覆盖。

## Milestone 9 验收边界

当前下一开发入口为 Shared V2 Source Data Build；`R4 Payment DWD` 已暂停。SOURCE GATE 通过后，先审计现有 Topic / Checkpoint，再冻结 Formal CDC Topic Namespace、Partition/Key Strategy、`event_version` 和独立 Checkpoint Root，随后执行 21 表 Initial Snapshot 与 CDC Gate。后续集中执行 Realtime Model Gate、Incremental Simulation、Recovery Gate、实时指标验收和 Offline ↔ Realtime Reconciliation，不再逐表重复完整 Initial + Incremental + Recovery 大验收。

正式 V2 启动前必须制定可回滚的 Doris 初始化重置方案，清除或隔离 `ecommerce_serving.dwd_order`、`dwd_order_item` 中的 Pilot 数据，但继续使用正式 database 命名，不创建 `ecommerce_serving_v2`。本设计不授权当前执行数据库清理。完整 M9 固定输入仍须覆盖 Snapshot 与持续 Binlog、INSERT/UPDATE/DELETE、重复和乱序、源端不停写时的 Flink 中断与恢复、Doris 重放/Upsert、离线 T+1 对账；未解释的重复、丢失、迟到或对账差异均阻断 `verified`。
