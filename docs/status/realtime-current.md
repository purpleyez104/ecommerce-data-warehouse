# Realtime Current Status

更新时间：2026-09-27
状态口径：`VERIFIED / DOING / DESIGNED / HISTORY / UNKNOWN`

本文件记录已发生的实时链路事实，不是实时健康报告。Application、Job、Checkpoint 或 Doris 的当前在线状态必须重新查询后才能确认。

## VERIFIED

- 2026-09-21 冻结范围内，隔离库 21 表初始 Snapshot 为 MySQL 1,178 行 / Kafka 1,178 条；100 单订单主键与最终状态对账通过。详见 [R1 Snapshot 冻结记录](../acceptance/r1_snapshot_acceptance_frozen.md)。
- 历史 R2/R3 范围内观察到 `biz_product_change_event` 的 `op=c/d`、`biz_order` 的一次合法 `CREATED → CANCELED` `op=u`，以及 CDC、Order DWD 从 Checkpoint 恢复后继续完成 Checkpoint；`chk-396` 与 `chk-179` 仅是已验证恢复点，不代表当前最新 Checkpoint。
- 历史订单 DWD 结果为 Doris 101 单、69 `PAID`、32 `CANCELED`、101 个不同订单 ID。详见 [R1/R2 验收记录](../acceptance/realtime_r1_r2_verified.md)。
- 历史订单明细 DWD 首次装载完成 MySQL / Doris 320 行、320 个不同 `order_item_id`、101 个订单、627 件商品的精确对账；应付、原价、优惠、退款金额和退款数量一致，孤儿明细与非法金额记录均为 0。
- 历史订单明细增量验收中，`order_item_id=2456670014000320` 的 `updated_at` 更新产生 Kafka `op=u`、offset 1185，并在 Doris 对同一主键完成更新，行数与不同明细数保持 320。
- 上述 `VERIFIED` 都是历史限定范围，只证明订单事实和订单明细事实的实时 DWD 闭环；不证明当前在线、21 表全字段一致、跨分区/乱序、物理 DELETE、R2/R3 更新故障恢复或端到端 Exactly-Once。

## DOING

- 当前工作区已有 `flink/jobs/r1/r1-order-dwd-job/`、Doris `dwd_order` DDL 和两份只读订单对账脚本；服务器已执行的 `flink/jobs/r3/r3-order-item-dwd-job/` 与 `tests/realtime/inspect-source-contract.sh` 尚未同步到当前 worktree。
- `scripts/realtime/check_order_dwd_consistency.sh` 与 `tests/realtime/check_dwd_order_consistency.sh` 状态均为 `implemented / not_run`。
- M8/M9 保持 `in progress`。R1～R3 已结束并转为 Pilot History；`R4 Payment DWD` 已暂停，不再基于 acceptance 源库和 Pilot Topic 逐表扩展。
- 当前与离线链路共同进入 Shared V2 Source Data Build；Realtime V2 在 SOURCE GATE 通过前不启动 Formal CDC 或 Domain DWD/DIM 开发。

## DESIGNED

- 正式 Flink 业务作业形态为 Java DataStream Jar + YARN Application Mode。
- 正式业务源统一为 `ecommerce_oltp`；历史初始化使用 Python Generator → 21 CSV → `LOAD DATA`，实时增量生成器必须通过 MySQL Transaction 产生 Binlog，禁止直接写 Kafka。
- 正式 CDC 在 Source Gate 后按“停止源写入 → Initial Snapshot → Kafka Snapshot Gate → 冻结基线 → 启动 Incremental Business Generator”顺序初始化。
- 正式 CDC 覆盖一期 7 域 21 表；正式 Kafka Topic Namespace 必须先完成 Topic Inventory 后命名，不复用 `ods_cdc_m2_clean_v1` 或其他污染 Topic。
- V2 Partition/Key 原则为 Same Business Key → Same Partition → Ordered Events；具体 Partition 数待数据规模冻结。正式 `event_version` 尚待设计，不能复制 Pilot 的 `kafka_offset` Sequence。
- Flink 工程按业务域组织 Domain Applications，业务转换逻辑分业务维护，Kafka Source、CDC Parser、Router、Checkpoint、Doris Sink、提交与恢复框架复用；不再一张表一个长期 Application。
- Realtime V2 Gate 为 CDC Gate、Realtime Model Gate、Recovery Gate 和 Offline ↔ Realtime Reconciliation；实时 DWS/ADS 必须复用共享 Metrics Contract。

## HISTORY

- `R1`、`R1-7`、`R2` 只表示历史验收切片，不是项目阶段编号。
- `ecommerce_oltp_m2_acceptance`、`ods_cdc_m2_clean_v1`、`all-to-zero`、`kafka_offset` Sequence 与现有 Pilot Checkpoint Root 均定位为 `PILOT / ACCEPTANCE / HISTORY`，不得作为正式 V2 入口。
- `OrderDwdJob`、`OrderItemDwdJob` 不删除，定位为 `VERIFIED PROTOTYPE / FRAMEWORK REFERENCE`，用于提取通用框架，不复制为 21 套工程。
- `R4 Payment DWD` 逐表计划已被 Shared V2 Source Data Build 与 Domain-based DWD/DIM 路线替代。
- 旧 Topic `cdc_m2_21tables_acceptance` 曾含额外历史订单，不作为当前订单 DWD 输入。
- R3 的 Java 17 编译产物与早期 `r1-order-dwd-job.zip` 已被 Java 11 target 的最终工程版本替代。

## UNKNOWN / CONFLICT

- CDC、Order DWD、OrderItem DWD Application / Flink Job、各自最新 Checkpoint 与 Doris BE 当前是否在线：`UNKNOWN`；本阶段记录的 Application ID 只是历史证据。
- 私有 CDC YAML 的可公开模板、首次提交脚本最终内容和当前恢复入口：`UNKNOWN`；历史 Checkpoint 路径不能作为下一次恢复的默认路径。
- 21 表完整最终 DDL、全字段对账、跨分区版本排序、物理 DELETE、旧消息乱序覆盖和 R2/R3 更新故障恢复均未验证。
- 正式 Realtime V2 的 CDC、Kafka Raw、DWD/DIM、DWS/ADS、Doris Serving 与增量业务生成器均未实现或验证。
- 正式 Topic 名、Partition 数、Key、`event_version`、Checkpoint Root、Doris 初始化重置对象和离实时差异阈值仍为 `UNKNOWN / DECISION_REQUIRED`。
- R3 Doris DDL、R2/R3 验收 SQL/Python 是否已在服务器固化为脚本文件：`UNKNOWN`；不得根据 Chat-only 命令自行补写历史文件。

## NEXT

1. 与离线共同核对 MySQL `ecommerce_oltp` 正式 21 表 DDL，并冻结数据规模、时间范围、状态分布、跨表比例和 21 CSV Contract。
2. 开发并验收 Python → CSV → `LOAD DATA` → `ecommerce_oltp`，通过 Shared SOURCE GATE。
3. SOURCE GATE 后审计现有 Kafka Topic / Checkpoint，依次冻结 Formal CDC Topic Namespace、Partition/Key Strategy 与 `event_version`，再进入 21 表 Initial Snapshot 和 CDC Gate。
