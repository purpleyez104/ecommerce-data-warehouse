# Offline Current Status

更新时间：2026-10-12
状态口径：`VERIFIED / DOING / DESIGNED / HISTORY / UNKNOWN`

本文件描述截至 2026-10-12 用户确认的离线链路事实与当前开发方向。Runtime 结论来自 Development Chat 的 File Fact Ledger 与验收输出；仓库文件存在本身不等于 `VERIFIED`。100 单链路已完成 Pilot / Acceptance 使命，当前开发入口切换到与实时链路共用的 Shared V2 Source Data Build。

## VERIFIED

### V2 Generator 本地正式规模验证

- 2026-10-12 使用 `v2_spec.json`、显式 Seed 和显式 `generated_at` 在本机临时目录最终复跑 Business：21 张 CSV、90 天、100,000 笔订单、285,000 条订单明细、合计 1,329,480 行、147,089,462 bytes，耗时 61.365 秒；同轮输出 11,470,325 bytes 的版本化 Entity Manifest。
- Behavior 强制读取上述 Entity Manifest；最终正式规模复跑生成 3,000,000 条事件、938,435,690 bytes、256,992 条映射事件和 2,785,149 个 Session，耗时 316.287 秒；全量检查 `bad_references=0`、`bad_sessions=0`、`duplicate_event_ids=0`，SHA-256 绑定通过。
- Business Targeted Unit Test 1 项、Behavior Targeted Unit Test 2 项通过，覆盖确定性、金额守恒、支付时序、优惠券用户/事件时序、订单晚于注册、历史窗口、Entity Manifest 版本失败、实体引用、Session 和 `event_time ≤ ingest_time ≤ history_end`。
- 以上只证明当前本地 Generator 在记录参数下完成生成、实体绑定与目标检查；临时产物已清理，不证明候选 DDL 已部署、MySQL `LOAD DATA`、Source Gate 或目标 ECS Runtime 已通过。

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
- 已只读核对当前 MySQL：`ecommerce_oltp` 仅有 3 张技术测试表，没有 21 张 `biz_*`；历史验收库 `ecommerce_oltp_m2_acceptance` 有同名 21 表和 1,178 行 Pilot 数据，结构主体可作为候选稿参考，但不能视为正式库已部署。
- 服务器工作目录中的旧 19 表 `generator/` 与旧 21 表 Pilot `tools/ecommerce_generator_v1/` 已按用户指示删除；仓库历史归档不受影响。
- 已生成 `mysql/ddl/001_ecommerce_oltp.sql` 候选稿，并补齐 Business Generator 的 4 个 CSV 审计字段。DDL 采用订单到优惠券的单向物理 FK，券反向订单引用改由索引与 Source Gate 校验。上述状态均为 `implemented / not_run`。
- V2 正式数据路径冻结为 Python Generator → CSV → MySQL `LOAD DATA` → `ecommerce_oltp`。
- 该 Source Data Build 同时是 Realtime V2 的历史初始化基线；SOURCE GATE 通过前，实时链路不再沿 Pilot 源库继续逐表开发。
- 正式数据规模已确认为 90 天、100,000 笔订单、约 285,000 条订单明细、约 100 万条 OLTP 记录和 3,000,000～5,000,000 条行为事件；性能实验规模为约 900,000 笔订单和 9,000,000 条行为事件。仓库 Generator 已在本机完成正式规模生成并产生实测 Manifest；MySQL 装载、完整状态分布/跨表比例 Source Gate 和服务器 Runtime 仍待核验，当前不得描述为已装载或已通过 Source Gate。
- 正式 V2 数据进入 `ecommerce_ods`、`ecommerce_dwd` 前，必须对现有 100 单 Pilot 数据执行有边界、可回滚的初始化重置；本决策不授权当前执行数据库清理。

## DESIGNED

- 正式源模型继续采用 7 个业务域、21 张 `biz_*` 业务表；Generator 必须统一覆盖一期业务表，而不是逐表补小样本。
- 工程实施改为按层批量推进：21 表 Source → 批量 ODS → ODS Gate → DWD/DIM → Model Gate → DWS → ADS → Doris。
- ODS 复用边界为“一套代码 + 多表配置”：通用 DataX Job Generator、Stage Runner、Spark Validation 和 Publish；每表提供 source/target、columns、primary key、partition、extract 与 quality rule。
- DWD/DIM 的业务转换 SQL 分表维护；Spark submit、日志、锁、失败保护、参数解析和 precheck 统一复用。
- 主要验收门禁收敛为 Source Gate、ODS Gate、Model Gate；取消重复逐表端到端验收，不取消必要测试、失败传播和最终整链路验收。
- 正式数据库继续使用 `ecommerce_oltp`、`ecommerce_ods`、`ecommerce_dwd`、`ecommerce_dim`、`ecommerce_dws`、`ecommerce_ads`，不新增 `_v2` database。

## HISTORY

- `hist-v1-001`、100 单生成器及其 ODS/DWD 文件统一作为 `PILOT / ACCEPTANCE / HISTORY` 保留；仓库内现存参考资产集中在 `archive/pilot-v1/`，其 Runtime 证据继续有效，但不再作为 V2 正式数据开发入口。
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
- 21 表候选 DDL 与 CSV 字段映射已完成只读对照，但正式库尚未部署；候选 DDL 的隔离执行、`LOAD DATA` 与 Source Gate 仍为 `UNKNOWN / not_run`。
- Generator 的 MySQL `LOAD DATA`、数据库约束执行、完整 Source Gate 和目标 ECS Runtime：`UNKNOWN / not_run`。
- Behavior Generator 已强制读取 Business Generator 的版本化 Entity Manifest；正式规模跨源身份、Session、商品引用和事件唯一性本地检查为 `VERIFIED`。数据库 Source Gate 与目标 ECS Runtime 仍为 `UNKNOWN / not_run`。
- 性能实验规模约 900,000 笔订单和 9,000,000 条行为事件仍为 `DESIGNED / not_run`，不得用本轮正式规模耗时外推性能结论。
- V2 初始化重置的精确对象、备份/回滚、执行命令与验收方法：`DECISION_REQUIRED`；不得直接清理现有数据库。
- `BI / Agent` 是否进入当前 V2 正式交付，还是继续遵循 `DR-029` 作为 M0～M10 之后规划：`DECISION_REQUIRED`。

## NEXT

1. 实现可重复执行的 21 CSV `LOAD DATA` 与 Source Gate 脚本，覆盖数据库约束、状态分布、跨表比例、金额、时间及失败非零。
2. 获得单独数据库变更授权后，在正式库部署候选 DDL，并通过批量 `LOAD DATA` 装载 21 CSV；不使用 Python 逐条写库。
3. 执行 Source Gate；通过前不进入批量 ODS，也不启动 Formal CDC。
5. 不继续执行 `ods_order_item_create.sql`，不删除旧 acceptance 环境，不把 Pilot 数据与 V2 正式数据混用。
