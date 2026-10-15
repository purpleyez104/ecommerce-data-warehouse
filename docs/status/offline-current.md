# Offline Current Status

更新时间：2026-10-15
状态口径：`VERIFIED / DOING / DESIGNED / HISTORY / UNKNOWN`

本文件描述截至 2026-10-12 用户确认的离线链路事实与当前开发方向。Runtime 结论来自 Development Chat 的 File Fact Ledger 与验收输出；仓库文件存在本身不等于 `VERIFIED`。100 单链路已完成 Pilot / Acceptance 使命，与实时链路共用的 Shared Source Data Build 已通过 Runtime 验收。

## VERIFIED

### Generator 正式规模验证

- 2026-10-12 使用 `formal.json`、显式 Seed `20260928` 和显式 `generated_at` 在 `hadoop201` 最终复跑 Business：21 张 CSV、90 天、100,000 笔订单、285,000 条订单明细、合计 1,328,502 行，耗时 213 秒；同轮输出版本化 Entity Manifest。该耗时仅为本次环境事实，不作为性能基线。
- Behavior 强制读取上述 Entity Manifest；2026-10-12 的正式规模复跑生成 3,000,000 条事件、938,435,690 bytes、256,992 条映射事件和 2,785,149 个 Session，全量检查 `bad_references=0`、`bad_sessions=0`、`duplicate_event_ids=0`，SHA-256 绑定通过。2026-10-15 的 60/30 Bundle 另见 DOING，二者为不同版本化输出。
- 当前统一测试覆盖 Business/Behavior 确定性、金额与状态时序、Entity Manifest 版本与引用、Session、SKU 生效时间以及 Replay Hash/窗口/失败路径；精确最新数量见 DOING。
- Generator 修复后对配置中的所有表数量执行 fail-fast，不再静默覆盖状态机派生事件数；正式复跑的 21 张 CSV 与修复前初次输出逐文件 SHA-256 一致。

### MySQL 正式业务源与 Shared Source Gate

- MySQL 8.0.46 的正式库 `ecommerce_oltp` 已部署 21 张 `biz_*` 表，原有 3 张技术测试表未删除或覆盖。
- 正式 bundle 已通过单 MySQL session 的 `LOAD DATA LOCAL INFILE` 装载并提交；21 表提交后精确 `COUNT(*)` 合计 1,328,502 行，与 Dataset Manifest 一致。
- 事务内和提交后独立 Shared Source Gate 均通过 45 条规则，覆盖计数、唯一性、引用、金额、支付窗口、退款、优惠券、状态链与时间关系，全部 0 违规。
- MySQL `local_infile` 只在装载期间临时启用，验收后已恢复为 `OFF`。完整证据边界见 [`source-load-gate-acceptance.md`](../acceptance/source-load-gate-acceptance.md)。

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

### Formal ODS 本地 Pipeline

- 已新增确定性 Replay Builder：使用 90 日输入重建第 61 日切换点 Bootstrap，并输出 30 个左闭右开 Daily Package、操作流、表级水位、受影响业务日期、Expected Result、31 个 ODS Batch Contract 与 SHA-256 Replay Manifest。现有正式终态 Generator 未改变。
- 已新增 MySQL Replay Planner：严格校验 Replay/Package/ODS Contract Hash、表名、字段、主键、时间窗口与 `operation_time + LOAD_TABLE_ORDER` 顺序，并在强制 `--dry-run` 下生成 `plan.json` 和事务化 `replay.sql`。真实 P0 `day_61` Smoke 生成 28 个操作（19 INSERT、9 UPDATE），计划明确记录 `execution_authorized=false`、`database_contacted=false`。
- 2026-10-15 使用 `replay_formal_20260105.json`、Seed `20260105` 和显式 `generated_at` 完成本地正式 Replay：Dataset `v2.3-replay-formal-20260105-r2`，Bootstrap 438,869 行，30 个 Daily Package 共 1,189,936 个操作（889,622 INSERT、300,314 UPDATE），Bundle 626,679,286 bytes，Business Hash 为 `c690b3257268e342d12772984d0dc93af806072acf4ead91c5c281b5a92293e0`。Bootstrap Source Load 与 30 个 Package Dry-run 全部通过，均为 `database_contacted=false`、`execution_authorized=false`。
- 同一 Business r2 固定参数正式重生成 146 个文件，并与原 Bundle 逐文件比较 SHA-256；差异文件数为 0，证明当前版本可精确复现该固定输入。
- 2026-10-15 使用 Seed `20260105`、Dataset `v2.3-behavior-replay-formal-20260105-r1` 和 Business r2 Entity Manifest 完成 Behavior 60/30 Bundle：3,000,000 条事件中 Bootstrap 895,324 条、30 个 Daily Package 2,104,676 条，Bundle 938,470,211 bytes，Content SHA-256 为 `a074cab5cc0b7bf82582242b097cc24534a8f2917485c493743574d98f8baf5e`。独立审计通过，记录 `external_system_contacted=false`。
- Seed `20260105` 推导的 `biz_coupon_event` 为 129,691 行，Replay 终态 Source Contract 合计 1,328,491 行。历史 Source Gate 的 Seed `20260928`、1,328,502 行证据保持不变；两者是不同固定输入，不得混称为同一次 Runtime 验收。
- 已新增 21 表 ODS Batch Runner：绑定 Replay Manifest Hash，生成不含 Secret 的私有 Job、Validation/Publish SQL 与分区计划，状态机为 `planned → staged → validated → publish_ready`；任一失败进入 `failed` 并保持 `publish_allowed=false`。
- 已新增 Spark SQL Renderer，覆盖必需字段 Projection、PK 非空/唯一、总行数、逐业务日期行数、业务日期集合、审计字段及受影响 `dt` 的合并覆盖/分区注册计划；Dry-run 不授权真实 Publish。
- 2026-10-15 本地统一入口共 53 个 Unit Tests 通过，其中 Business Generator 5 个、Behavior 6 个、DataX 17 个、MySQL 25 个。上述新增 Pipeline 结论仍仅为本地实现与本地验证；本 Step 没有连接 MySQL、Kafka、DataX、HDFS、Hive、Spark 或 Flink Runtime，没有发布任何 ODS 分区，也没有执行 ODS/CDC Gate。

### Source Data Build 后续接续

- 正式源库切换为 `ecommerce_oltp`；`ecommerce_oltp_m2_acceptance` 保留为 Pilot、CDC、R1/R2/M3 历史验收环境，不删除，也不再作为正式离线开发源。
- `ecommerce_oltp` 的 21 张正式 `biz_*` 表已部署并完成装载验收；历史验收库 `ecommerce_oltp_m2_acceptance` 仍只作为 Pilot/CDC 历史环境。
- 服务器工作目录中的旧 19 表 `generator/` 与旧 21 表 Pilot `tools/ecommerce_generator_v1/` 已按用户指示删除；仓库历史归档不受影响。
- `mysql/ddl/001_ecommerce_oltp.sql` 已部署；DDL 采用订单到优惠券的单向物理 FK，券反向订单引用由索引与 Source Gate 校验。
- V2 正式数据路径冻结为 Python Generator → CSV → MySQL `LOAD DATA` → `ecommerce_oltp`。
- 该 Source Data Build 同时是正式实时链路的历史初始化基线；Source Gate 已通过，可进入 Formal CDC Contract 与初始化设计，但不能复用 Pilot Topic 直接外推完成状态。
- 正式数据规模已确认为 90 天、100,000 笔订单、285,000 条订单明细、实测 1,328,502 条 OLTP 记录和 3,000,000～5,000,000 条行为事件；Business 数据已完成目标 MySQL 装载与 Source Gate。性能实验规模为约 900,000 笔订单和 9,000,000 条行为事件，仍为 `DESIGNED / not_run`。
- 正式 V2 数据进入 `ecommerce_ods`、`ecommerce_dwd` 前，必须对现有 100 单 Pilot 数据执行有边界、可回滚的初始化重置；本决策不授权当前执行数据库清理。

## DESIGNED

- `DR-037`、`DR-041` 已确认正式 90 天观察窗口按前 60 天历史初始化、后 30 天逐日双链路回放；Business/Behavior 正式规模 Bundle 与本地审计已完成，目标数据库、ODS/Kafka/CDC Runtime 和对应 Gate 仍未执行。现有本地 Bundle 与历史 Source Gate 不证明时间推进式链路已验证。
- 需要历史属性的维度按前 60 天变化历史初始化 SCD2，后 30 天关闭旧版本、插入新版本并处理迟到修正；精确 `dim_*` 映射仍待 Milestone 4 实施前冻结。
- 正式源模型继续采用 7 个业务域、21 张 `biz_*` 业务表；Generator 必须统一覆盖一期业务表，而不是逐表补小样本。
- 工程实施改为按层批量推进：21 表 Source → 批量 ODS → ODS Gate → DWD/DIM → Model Gate → DWS → ADS → Doris。
- ODS 复用边界为“一套代码 + 多表配置”：通用 DataX Job Generator、Stage Runner、Spark Validation 和 Publish；每表提供 source/target、primary key、partition、extract 与 quality rule，columns 统一引用 Business Generator 的 `TABLE_COLUMNS`，字段类型以正式 MySQL DDL 为准。
- 通用 DataX Job Generator、Stage Runner、Spark Validation/Publish Renderer 与 21 表 Contract 已完成本地实现和 17 个 DataX Targeted Tests：可变表按 `updated_at`、Append-only 表按记录水位、`biz_identity_mapping` 按日全量快照；事实/事件按行业务时间生成 `business_date`，输出固定进入 `<target_table>/batch_id=<batch_id>` staging。该结论是本地 `implemented / not_run`，不证明 DataX/HDFS/Hive Runtime、业务分区发布或 ODS Gate。
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
- 21 表 DDL、CSV 字段映射、正式库部署、`LOAD DATA`、数据库约束和 Shared Source Gate 已在记录环境中 `VERIFIED`；该结论不包含 DataX/Hive ODS 或正式 CDC。
- Behavior Generator 已强制读取 Business Generator 的版本化 Entity Manifest；正式 60/30 Bundle 的跨源身份、Session、商品生效时间和事件唯一性本地检查为 `VERIFIED`，但行为数据尚未进入正式 HDFS/Hive Bootstrap 或 Kafka Raw Layer。
- 性能实验规模约 900,000 笔订单和 9,000,000 条行为事件仍为 `DESIGNED / not_run`，不得用本轮正式规模耗时外推性能结论。
- V2 初始化重置的精确对象、备份/回滚、执行命令与验收方法：`DECISION_REQUIRED`；不得直接清理现有数据库。
- `BI / Agent` 是否进入当前 V2 正式交付，还是继续遵循 `DR-029` 作为 M0～M10 之后规划：`DECISION_REQUIRED`。

## NEXT

1. 申请新的 Database Operation 授权，在隔离 Source 装载 Dataset `v2.3-replay-formal-20260105-r2` 的 Day 60 切换点状态；不得直接重置或覆盖 Seed `20260928` 的正式 Source Gate 数据。
2. 在隔离 Source 先执行并验收 Seed `20260105` 的 `day_61`，再依次应用 `day_62`～`day_90`；不得直接对第 90 日终态库回放。
3. 在另行授权的目标环境为可注入执行器接入 DataX/Spark，验证 60 天业务分区初始化、30 天连续水位、失败隔离和受影响历史分区重建，再执行 ODS Gate。
4. ODS Gate 通过后实现 Type 1/SCD2 DIM 与 DWD，并执行 Model Gate。
5. 任何隔离库构建、重置、回滚或重新装载需要新的 Database Operation 授权；不继续执行 `ods_order_item_create.sql`，不删除旧 acceptance 环境。
