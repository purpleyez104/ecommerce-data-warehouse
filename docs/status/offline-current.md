# Offline Current Status

更新时间：2026-09-27
状态口径：`VERIFIED / DOING / DESIGNED / HISTORY / UNKNOWN`

本文件描述截至 2026-09-27 用户确认的离线链路事实与当前开发方向。Runtime 结论来自 Development Chat 的 File Fact Ledger 与验收输出；仓库文件存在本身不等于 `VERIFIED`。100 单链路已完成 Pilot / Acceptance 使命，当前开发入口切换到与实时链路共用的 Shared V2 Source Data Build。

## VERIFIED

### `hist-v1-001` 历史源数据

- 冻结范围为 100 orders、319 order items、626 quantity。
- 订单状态为 69 `PAID`、31 `CANCELED`。
- 历史业务日期为 2026-06-22～2026-09-17，共 88 个业务日期。
- 金额为 8,402,600 gross cents、30,000 discount cents、8,372,600 payable cents。
- MySQL 后续已有实时链路产生的第 101 单及第 320 条 item；它们不属于 `hist-v1-001`，不得混入历史初始化。

### ODS order

- `ecommerce_ods.ods_order` 已完成 MySQL `biz_order` → DataX → HDFS staging ORC + Snappy → Spark SQL validation → HDFS publish → Hive partition registration。
- 最终结果为 100 rows、100 unique orders、88 partitions、8,372,600 payable cents，与 `hist-v1-001` 一致。
- DataX 未使用持久 CSV/Text 中间层。

### DWD order

- `ecommerce_dwd.dwd_order` 为订单最新状态快照事实，粒度为一行一个订单，不是订单状态事件历史表。
- 表为 EXTERNAL、ORC + Snappy、按 `dt` 分区；ODS 时间字符串在 DWD 转换为 `TIMESTAMP`。
- 单日 pilot `dt=2026-09-17` 已通过 `PRECHECK → BUILD → VERIFY`：1 row、1 unique order、83,400 gross/payable cents、0 mismatch，结果为 `PASS`。
- 剩余 87 个历史分区通过一次 Spark 历史批量任务构建完成。
- 历史全量结果为 ODS 100 rows ↔ DWD 100 rows、100 unique orders、88 partitions、69 `PAID`、31 `CANCELED`、8,402,600 gross cents、30,000 discount cents、8,372,600 payable cents、0 mismatch，结果为 `PASS`。
- 当前已形成 `MySQL hist-v1-001 → ODS order → DWD order` 的限定范围一致性闭环；当前离线业务链路的真实终点是 Hive DWD，不包含 Doris 离线 Serving。

### 离线计算与 YARN 并发

- Hive 负责 Metastore、Table 与 Partition 管理；Spark SQL on YARN 是当前正式离线 ETL、数据质量校验与 DWD 加工引擎。
- `yarn.scheduler.capacity.maximum-am-resource-percent` 已从 `0.10` 调整为 `0.25`，并通过 `yarn rmadmin -refreshQueues` 刷新。
- 调整后 `AMResourceLimit memory=5120 MB`、`numPendingApplications=0`，随后 Spark DWD 单日及历史任务成功完成。
- 限定环境已验证 2 个长期 Flink Application 与 1 个 Spark offline job 可以在 YARN 并存；该结论不外推为一般容量或性能保证。

## DOING

### V2 Source Data Build

- 正式源库切换为 `ecommerce_oltp`；`ecommerce_oltp_m2_acceptance` 保留为 Pilot、CDC、R1/R2/M3 历史验收环境，不删除，也不再作为正式离线开发源。
- 当前首先核对 `ecommerce_oltp` 的正式 21 表 DDL，再冻结各表数据量、时间范围、状态分布、跨表比例、CSV 字段、依赖与生成顺序。
- V2 正式数据路径冻结为 Python Generator → CSV → MySQL `LOAD DATA` → `ecommerce_oltp`。
- 该 Source Data Build 同时是 Realtime V2 的历史初始化基线；SOURCE GATE 通过前，实时链路不再沿 Pilot 源库继续逐表开发。
- 具体规模、时间范围、状态比例和跨表比例尚未给出数值，当前不得描述为已生成、已装载或已通过 Source Gate。
- 正式 V2 数据进入 `ecommerce_ods`、`ecommerce_dwd` 前，必须对现有 100 单 Pilot 数据执行有边界、可回滚的初始化重置；本决策不授权当前执行数据库清理。

## DESIGNED

- 正式源模型继续采用 7 个业务域、21 张 `biz_*` 业务表；Generator 必须统一覆盖一期业务表，而不是逐表补小样本。
- 工程实施改为按层批量推进：21 表 Source → 批量 ODS → ODS Gate → DWD/DIM → Model Gate → DWS → ADS → Doris。
- ODS 复用边界为“一套代码 + 多表配置”：通用 DataX Job Generator、Stage Runner、Spark Validation 和 Publish；每表提供 source/target、columns、primary key、partition、extract 与 quality rule。
- DWD/DIM 的业务转换 SQL 分表维护；Spark submit、日志、锁、失败保护、参数解析和 precheck 统一复用。
- 主要验收门禁收敛为 Source Gate、ODS Gate、Model Gate；取消重复逐表端到端验收，不取消必要测试、失败传播和最终整链路验收。
- 正式数据库继续使用 `ecommerce_oltp`、`ecommerce_ods`、`ecommerce_dwd`、`ecommerce_dim`、`ecommerce_dws`、`ecommerce_ads`，不新增 `_v2` database。

## HISTORY

- `hist-v1-001`、100 单生成器及其 ODS/DWD 文件统一作为 `PILOT / ACCEPTANCE / HISTORY` 保留；其 Runtime 证据继续有效，但不再作为 V2 正式数据开发入口。
- `ecommerce_oltp_m2_acceptance` 保留为历史验收环境，不删除。
- 逐表执行 `order → ODS → DWD → 验收`、再处理 `order_item`、payment、refund 的 Pilot 推进方式已停止。
- 旧 100 单生成器、Python 逐条 INSERT MySQL 和 `generate_and_insert.py` 不进入 V2 正式生成路径。
- `ods_order_item_create.sql` 保持 F2 `CONFIRMED_CREATED / NOT EXECUTED`，不再继续执行；该文件不得提升为 VERIFIED，也不自动成为 V2 正式 ODS 设计。
- Hive/Beeline 触发的 MapReduce 聚合只属于早期 stage 校验；当前正式离线计算方式已改为 Spark SQL on YARN。
- 初版 `offline_m3_03_stage_orders.sh` 因 SSH 消耗 stdin 导致日期循环异常，已被后续修正版替代。
- 初版 `build_dwd_order.sh` 因使用 `grep 'created_at timestamp'` 解析 Beeline 表格输出而误判正确字段，已被 TSV2 字段解析版本替代。
- `application_1790148204235_0004` 最终为 `KILLED / KILLED`，资源分配为 0，未执行 SQL 或写入 DWD，仅保留为故障历史。

## UNKNOWN / CONFLICT

- 以下已执行文件在 ECS 的实际路径未知：`offline_m3_source_preflight.sh`、`offline_m3_02_make_order_job.py`、`m3_cleanup_nonbaseline_orders.sql`、最终修正版 `offline_m3_03_stage_orders.sh`。
- `offline-m4-01-dwd-order.md` 是否进入 ECS repository：`UNKNOWN`。
- `capacity-scheduler.xml.bak-20260923-am` 是否真实创建：`UNKNOWN`。
- `ods_order_item_create.sql` 是否已上传至 ECS repository：`UNKNOWN`；Hive DDL 明确为 `NOT EXECUTED`。
- Handoff 标记为已验证的 ODS/DWD 工程文件当前未出现在本 worktree；在取得真实文件内容前，不根据 ECS 路径或文件名自行重建。
- 当前 ECS 服务是否仍保持 Handoff 验收时的在线状态不在本次离线基线证明范围内。
- V2 21 表正式 DDL 与当前 `ecommerce_oltp` 实际结构尚未核对完成。
- V2 数据规模、时间范围、状态分布和跨表比例：`DECISION_REQUIRED`。
- V2 初始化重置的精确对象、备份/回滚、执行命令与验收方法：`DECISION_REQUIRED`；不得直接清理现有数据库。
- `BI / Agent` 是否进入当前 V2 正式交付，还是继续遵循 `DR-029` 作为 M0～M10 之后规划：`DECISION_REQUIRED`。

## NEXT

1. 核对 `ecommerce_oltp` 当前正式 21 表 DDL。
2. 冻结 V2 数据规模、时间范围、状态分布、跨表比例，以及 21 张 CSV 的字段、依赖与生成顺序。
3. 在上述 Contract 完成后开发新的 Python CSV Generator；不继承旧 100 单生成器，不包含数据库逐条写入职责。
4. Generator、CSV、`LOAD DATA` 和 Source Gate 完成前，不进入批量 ODS 实施。
5. 不继续执行 `ods_order_item_create.sql`，不删除旧 acceptance 环境，不把 Pilot 数据与 V2 正式数据混用。
