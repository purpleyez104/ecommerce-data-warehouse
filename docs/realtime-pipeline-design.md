# 实时链路架构规范（Milestone 8 设计输入）

状态：总体技术路线已确认；正式业务实时链路 `planned`，Topic/Schema/窗口/表模型待 Milestone 8 评审。更新时间：2026-09-20。

本文件展开[最终工程架构](final-architecture-v1.0.md)的实时视图，并以[业务源设计](business-source-design.md)及[指标口径](metrics.md)为上游。它不是 Milestone 8 已通过评审或 Milestone 9 已运行的证明。

## 数据流与责任

```text
模拟业务服务 → MySQL 21 张 biz_* 表 → Binlog → Flink CDC → Kafka Raw CDC
独立行为源 ───────────────────────────────→ Kafka 行为事件
Kafka 输入 → Flink Java DataStream Jar（YARN Application）
            ├→ Kafka 标准事件（待设计）
            ├→ HDFS/Hive 长期归档（待设计）
            └→ Doris 实时服务表（待设计）
```

- 交易状态与关键历史必须先进入 MySQL；Flink CDC 从 ROW/FULL Binlog 采集 Snapshot 和后续 INSERT/UPDATE/DELETE，不能由生成器伪造 CDC。独立行为事件与交易 CDC 应保留不同来源标识和可解释的关联键。
- Kafka Raw CDC 只承担传输和短期重放，不是长期数仓存储。`ods_cdc_xxx` 与按表 Topic 是 M1 技术验证示例，不是正式命名或划分；Debezium JSON 的 `before/after/op/source` 是已验证格式示例，正式 Schema、兼容演进、Key 和保留期仍待评审。
- Flink 正式业务处理采用 Java DataStream API、打包为 Jar、运行于 YARN Application Mode。SQL Client + YARN Session 保留用于 Kafka SQL 技术验证，不作为正式业务部署模式。`yarn-application` 下 SQL `INSERT` 曾有 `No ExecutorFactory` 限制；不能把 SQL Session 的成功直接外推到正式 Application。
- Doris 4.0.8 FE 位于 `hadoop201`（HTTP `18030`），BE 位于 `hadoop202/203`。Flink Doris Connector 26.1.1 的临时写入、Upsert、Checkpoint 和指定恢复场景已通过；正式实时 Key 模型、分区、分桶、更新/撤回语义仍待设计。Doris 不替代 Hive 的历史与重算责任。

## 运行与 Java 边界

Flink Client 使用 Java 17；当前 YARN Container 与 Flink Doris User Jar 使用 Java 11 兼容边界。正式 Jar 的依赖、序列化、状态、连接器组合和目标字节码必须在固定版本下重新验证。提交命令退出 0 仅表示提交成功，作业成败须核查 YARN application final state、Flink 作业状态和目标端结果；故障后不能仅凭 Checkpoint 配置宣称端到端 Exactly-Once。

## 待 Milestone 8 冻结的契约

| 范围 | 必须形成的结论 |
| --- | --- |
| Kafka | Raw/标准事件 Topic 划分、Key、Partition、副本、保留、压缩、Schema 和演进 |
| Flink | CDC 与计算作业拆分、业务事件时间、Watermark、窗口、允许迟到、去重键、状态 TTL、撤回与补偿 |
| 维度和指标 | 历史/当前维度版本、首批实时指标稳定发布 ID、与离线一致的公式和时间归属 |
| 状态与恢复 | Checkpoint/Savepoint、重启策略、源端继续写入后的恢复、一致性目标与可重放边界 |
| 存储和对账 | HDFS/Hive 归档、Doris 实时表 Key/分区/分桶、离实时差异阈值及资源预算 |

上述未决项不得由本文件的示意图推导成默认值。现有[ENV-05](acceptance/env-05-cdc-acceptance.md)只证明单隔离测试表的 Snapshot、Binlog c/u/d 与指定 TaskManager 故障恢复；M1 Step 10 的 Kafka SQL 基础链路存在重复输出备注，Step 12 的 Doris 连接器验证也不能替代正式 21 表、行为流与指标的端到端可靠性验收。

## Milestone 9 验收边界

只有 Milestone 8 评审通过后，才实现正式 Topic、Java Jar、Doris 表和回补/归档任务。固定输入至少覆盖 Snapshot 与持续 Binlog、INSERT/UPDATE/DELETE、重复和乱序、源端不停写时的 Flink 中断与恢复、Doris 重放/Upsert、离线 T+1 对账。保存版本、运行参数、YARN/Flink 最终状态、关键结果和已知差异；未解释的重复、丢失、迟到或对账差异均阻断 `verified`。
