# Offline Current Status

更新时间：2026-10-21
状态口径：`VERIFIED / DOING / DESIGNED / HISTORY / UNKNOWN`

本文件描述截至 2026-10-21 已核对的离线链路事实与当前开发方向。Runtime 结论来自 Development Chat 的 File Fact Ledger、YARN/Application 终态与验收输出；仓库文件存在本身不等于 `VERIFIED`。100 单链路已完成 Pilot / Acceptance 使命，Shared Source Data Build、批量 ODS、M4/M5 离线建模质量、M6 Doris Serving/调度与 M7 Spark 性能实验均已通过对应 Runtime 验收。

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
- 当前已形成 `MySQL hist-v1-001 → ODS order → DWD order` 的历史限定范围一致性闭环；该 Pilot 终点不代表当前正式链路终点。正式 V2 已推进到 Doris 离线 Serving。

### 离线计算与 YARN 并发

- Hive 负责 Metastore、Table 与 Partition 管理；Spark SQL on YARN 是当前正式离线 ETL、数据质量校验与 DWD 加工引擎。
- `yarn.scheduler.capacity.maximum-am-resource-percent` 已从 `0.10` 调整为 `0.25`，并通过 `yarn rmadmin -refreshQueues` 刷新。
- 调整后 `AMResourceLimit memory=5120 MB`、`numPendingApplications=0`，随后 Spark DWD 单日及历史任务成功完成。
- 限定环境已验证 2 个长期 Flink Application 与 1 个 Spark offline job 可以在 YARN 并存；该结论不外推为一般容量或性能保证。

### M5 退款事实与 Aggregate Contract 修正

- M5-02 已确认不新增 `dwd_refund_request`；现有 `dwd_refund` 改为每个退款申请一行，成功资金结果可空。DWS 计算退款申请数、成功申请数、成功金额和退款件数，ADS 使用交易/行为日期并集，避免单侧空日丢失。
- 当前申请粒度 `dwd_refund`、DWS/ADS 已完成真实集群受控迁移；60/60 Model Gate、首次及幂等重跑后的 18/18 Aggregate Gate 均无违规。15 项核心摘要重跑前后完全一致，旧表与 HDFS 备份均保留。证据见 `docs/acceptance/m5-refund-contract-migration-acceptance.md`。

## VERIFIED

### M5 首批六域正式指标与质量

- M5-01 已确认现有编号直接作为稳定 `metric_id`，首版 `definition_version=1.0.0`。
- 2026-10-19 已完成 6 张 DWS + 1 张 ADS 的六域 Runtime；最终首次与幂等重跑后的 41/41 Aggregate Gate 均无违规。Cohort 证据见 `docs/acceptance/m5-cohort-metrics-acceptance.md`。
- Metric Registry 已发布 36 个具有正式输出和 Runtime 验收的 `metric_id + definition_version`；`TF-05`、`TR-13`、`TR-14` 均已绑定正式输出，排行和 `TBD` 指标继续保持未发布。
- `P1-QUALITY-01` 当前保存 40 条唯一 Aggregate 规则，`FAIL=0`；`P1-RECONCILIATION-01` 当前覆盖 10 项代表性指标，90 日共 900 行，`FAIL=0`。

### Formal ODS 本地 Pipeline

- 已新增确定性 Replay Builder：使用 90 日输入重建第 61 日切换点 Bootstrap，并输出 30 个左闭右开 Daily Package、操作流、表级水位、受影响业务日期、Expected Result、31 个 ODS Batch Contract 与 SHA-256 Replay Manifest。现有正式终态 Generator 未改变。
- 已新增 MySQL Replay Planner：严格校验 Replay/Package/ODS Contract Hash、表名、字段、主键、时间窗口与 `operation_time + LOAD_TABLE_ORDER` 顺序，并在强制 `--dry-run` 下生成 `plan.json` 和事务化 `replay.sql`。真实 P0 `day_61` Smoke 生成 28 个操作（19 INSERT、9 UPDATE），计划明确记录 `execution_authorized=false`、`database_contacted=false`。
- 已新增 MySQL Replay Executor：必须同时提供 `--execute` 与匹配的 `--confirm-day`，密码只从 `MYSQL_PASSWORD` 读取且不进入参数、日志或结果；Daily 操作与 45-rule Source Gate 位于同一事务，Client/Gate 失败返回非零且不生成成功结果。该入口已部署到服务器独立目录；Day 61 Planner Dry-run 识别 19,456 个操作，Business Hash、Expected Result 与订单状态分布核对通过，`database_contacted=false`、`execution_authorized=false`，拒绝路径退出码为 2。
- 初次 Day 61 执行在业务写入前因 MySQL 身份失败，数据库仍保持 Day 60；获得单独授权后，`ecommerce_user@localhost` 仅增加隔离库的 `SELECT / INSERT / UPDATE / CREATE TEMPORARY TABLES` 临时权限。随后 Day 61 成功提交 19,456 个操作，Executor 记录 `database_contacted=true`、`committed_after_source_gate=true`。
- Day 61 提交后独立验收为 45/45 规则、0 违规；21 表精确计数全部匹配 Expected Result，合计 453,809 行。订单状态为 21,783 `PAID`、8,970 `CANCELED`、315 `CREATED`，`local_infile=OFF`。
- 2026-10-16，旧 r2 链路的 Day 62 Package 四个输入文件的服务器端 SHA-256 与本地固定清单一致；Planner Dry-run 记录 `operation_count=22995`、`database_contacted=false`、`execution_authorized=false`。Executor 随后提交 22,995 个操作并记录 `committed_after_source_gate=true`；事务内及提交后独立 Source Gate 均为 45/45 规则、0 违规。21 表合计 471,317 行，订单状态为 22,686 `PAID`、9,373 `CANCELED`、326 `CREATED`，`local_infile=OFF`。该逐日链路停在 Day 62，后续由下述 r6 Batch Ledger/Range Executor 接续验证，不把 r2 状态外推到 r6。
- 独立运行目录已逐文件无差异复制到数据盘 `/data/ecommerce-replay-runtime-20261015/`，源/目标均为 31 个文件、47M，目标目录 mode `0700`；后续从该路径继续。`/home/yee/ecommerce-replay-runtime-20261015/` 暂作为已验收备份保留，尚未删除。MySQL `datadir` 仍为 `/var/lib/mysql/`，本 Step 未迁移数据库物理文件。
- `c690b325...` 与 `4abcd890...` 分别保留为初始 r2 和 r3 修复过程的历史 Baseline。根据 `DR-044`，当前正式 Replay Baseline 使用相同固定参数、Dataset `v2.3-replay-formal-20260105-r2`、Business Hash `ecea32d620bfbf44671ff2c1e1ff765fe4638f330f621229b9dd8f543578deb5` 和 Replay Manifest SHA-256 `5e09633896125c487a9a2d55632507621eb058679f4e30bc83c313c42e46533c`：Bootstrap 438,869 行，30 个 Daily Package 共 1,210,882 个操作（889,622 INSERT、321,260 UPDATE）。
- 2026-10-17 当前 worktree 使用同一固定参数重生成 146 个文件、638,956,763 bytes，Business Hash、Replay Manifest SHA-256、30 个 Package Manifest 和操作总数均与 r6 Runtime Bundle 一致，证明当前版本可精确复现正式输入。
- 2026-10-15 使用 Seed `20260105`、Dataset `v2.3-behavior-replay-formal-20260105-r1` 和 Business r2 Entity Manifest 完成 Behavior 60/30 Bundle：3,000,000 条事件中 Bootstrap 895,324 条、30 个 Daily Package 2,104,676 条，Bundle 938,470,211 bytes，Content SHA-256 为 `a074cab5cc0b7bf82582242b097cc24534a8f2917485c493743574d98f8baf5e`。独立审计通过，记录 `external_system_contacted=false`。
- Seed `20260105` 推导的 `biz_coupon_event` 为 129,691 行，Replay 终态 Source Contract 合计 1,328,491 行。历史 Source Gate 的 Seed `20260928`、1,328,502 行证据保持不变；两者是不同固定输入，不得混称为同一次 Runtime 验收。
- 已新增 21 表 ODS Batch Runner：绑定 Replay Manifest Hash，生成不含 Secret 的私有 Job、Validation/Publish SQL 与分区计划，状态机为 `planned → staged → validated → publish_ready`；任一失败进入 `failed` 并保持 `publish_allowed=false`。
- 已新增 Spark SQL Renderer，覆盖必需字段 Projection、PK 非空/唯一、总行数、逐业务日期行数、业务日期集合、审计字段及受影响 `dt` 的合并覆盖/分区注册计划；Dry-run 不授权真实 Publish。
- 2026-10-15 当时的本地统一入口共 56 个 Unit Tests 通过，其中 Business Generator 5 个、Behavior 6 个、DataX 17 个、MySQL 28 个；该日尚未发布 ODS 分区或执行 ODS Gate，后续状态已由 2026-10-17 隔离 Smoke 更新。
- 2026-10-15 对 `hadoop201` 执行只读复核：隔离库 21 表精确行数全部匹配 Day 60 `expected_result.json`，`MISMATCH_COUNT=0`，`local_infile=OFF`；事务内与提交后证据文件均为 45 条规则、0 违规、`EXIT_STATUS=0`，未发现 Day 61 执行结果。该复核不证明服务持续在线或 Day 61 已执行。
- 2026-10-16 新增数据库 Batch Ledger 与 Day 61～90 Range Executor。Daily 操作、Ledger 和 45-rule Gate 在同一事务；Range 在写库前完成 30 日 Preflight，按日保存 Checkpoint，并可通过 `--resume` 对照 Acceptance、Ledger 和实时 Gate 断点恢复。隔离 Integration Test 已证明 Day 72 首次提交、同日幂等返回 `already_applied`，以及强制 Day 73 Gate 失败时 Ledger 与业务写入均回滚。
- r6 环境位于数据盘 `/data/ecommerce-replay-runtime-20261016-r6/`，目标库为 `ecommerce_oltp_replay_20260105_r6`。Day 60 Bootstrap 与 Day 61～90 Replay 已完成：Range State 为 `verified`，30 条 Ledger 覆盖 Day 61～90、操作总数 1,210,882，30/30 Acceptance 完整，最终独立 Source Gate 为 45/45、0 违规，`local_infile=OFF`。Day 75 在提交后、Acceptance 落盘前被 signal 中断；修复后的 Resume 通过 Ledger 识别 `already_applied` 并补齐证据，没有重复业务写入。`ecommerce_user@localhost` 对 r6 的临时权限已回收，正式库和旧 r5/r4/r2 权限未修改。
- 2026-10-17 在独立 MySQL `ecommerce_oltp_ods_20260105_r1` 与 Hive `ecommerce_ods_replay_20260105_r1` 完成 Day 60 Bootstrap + Day 61 Incremental ODS Smoke。Day 60 ODS Gate 为 1,000 个断言结果；Day 61 Source Replay 为 19,675 operations、45/45 Source Gate、0 违规，发布后 ODS Gate 为 1,034 个断言结果。增量 Publish 使用批次隔离的两阶段 ORC merge；隔离库临时 grants 已撤销，hadoop202 临时 Secret 文件已删除。证据见 `docs/acceptance/formal-ods-smoke-acceptance.md`。
- Day 61 同日恢复重跑复用 `r4` staging，不接触 MySQL、DataX 或 Secret；状态历史为 `planned → staged_reused → validated → published`，重跑后独立 Gate 再次通过 1,034 项断言且目标仍为 457,571 行。后续 Day 62～90 与跨日恢复状态已由 2026-10-18 Stage Gate 更新。
- 2026-10-17 正式 `ecommerce_oltp` 终态 Snapshot 已发布到正式 `ecommerce_ods` 21 张 EXTERNAL ORC + Snappy 表，显式根路径为 `/warehouse/ecommerce/ods/`。Source 21 表实时行数仍与 Manifest 一致，合计 1,328,502；Runner 状态为 `published`，独立 ODS Gate 通过 1,476/1,476 项断言、0 失败。旧 Pilot 三表已保留为 `pilot_20260921_*`，原 EXTERNAL 数据和 88 个历史分区未删除。临时正式库 `SELECT` grant 已回收，hadoop202 Secret 配置已删除。证据见 `docs/acceptance/formal-ods-bootstrap-acceptance.md`。
- 2026-10-18 隔离 Source/ODS 完成 Day 62～90 逐日交替回放：29/29 Checkpoint、Range State `verified`，Source Ledger Day 61～90 共 30 条、1,210,882 operations，最终 Source 21 表合计 1,328,491 行。Day 63 DataX 中断后按精确 `batch_id` 清理未发布 staging 并从 Checkpoint 恢复，未重放 Day 62。Day 90 独立 ODS Gate 使用最终 Source 分组计数与 31 日快照合约，验证目标 1,632,345 行，1,498/1,498 条断言成功。临时 grant 与全部 Secret runtime 文件已回收；Milestone 3 Stage Gate 完成。
- 2026-10-18 Behavior 60/30 Bundle 已通过独立第 22 张 ODS 表 `ecommerce_ods.ods_behavior_event` 完成 Runtime Gate：Dataset `v2.3-behavior-replay-formal-20260105-r1` 共 3,000,000 行，发布为 2025-12-01～2026-02-28 的 90 个 `dt` 分区，HDFS 目标为 `/warehouse/ecommerce/ods/ods_behavior_event`。最终 Gate Application `application_1792297746029_0005` 为 `FINISHED / SUCCEEDED`，95/95 项断言通过并输出 `BEHAVIOR_ODS_GATE_PASS`；证据见 `docs/acceptance/behavior-ods-acceptance.md`。
- 2026-10-18 首批 6 张 DIM、8 张 DWD 已在 `ecommerce_dim` / `ecommerce_dwd` 完成 Spark on YARN 构建；Model Gate Application `application_1792309323393_0007` 为 `FINISHED / SUCCEEDED`，59/59 条断言通过。精确行数覆盖 60 个类目、30 个券模板、24,000 条身份映射、6,000 条商品 SCD2、40,000 用户、80,000 访客及 3,000,000 条 Behavior DWD 等 14 张表；证据见 `docs/acceptance/m4-dim-dwd-model-gate-acceptance.md`。
- 2026-10-18 两张日粒度 DWS 与一张 ADS 已在 `ecommerce_dws` / `ecommerce_ads` 完成 Spark on YARN 构建；Aggregate Gate 首次和幂等重跑后均为 18/18 条断言无违规，重跑 Application `application_1792325482148_0003`、Gate Application `application_1792325482148_0004` 均为 `FINISHED / SUCCEEDED`，重跑前后 8 项核心结果完全一致。证据见 `docs/acceptance/m4-dws-ads-aggregate-gate-acceptance.md`。
- 2026-10-21 当前完整统一测试共 155 项通过：Business 6、Behavior 6、DataX/ODS 33、Model 19、Governance 6、Quality 5、Reconciliation 4、Doris 6、Scheduler 18、Benchmark 9、Realtime Foundation 6、MySQL 37。

### M6 Doris 离线 Serving 与 DolphinScheduler 组件门禁

- `ecommerce_serving.ads_daily_business_overview` 已使用 `UNIQUE KEY(business_date)` + Merge-on-Write 建表；Spark 3.5.9 + Doris Connector 26.0.0 已完成单日和 90 日装载。
- `2025-12-01..2026-02-28` 首次及幂等重跑后均为 90 行、90 个业务日期；Hive/Doris 90 行 × 22 字段逐行一致，SHA-256 为 `b3969f7d60e054e7f656f65cb7c7261aa8cf413758f20a1144e09f335b6570ce`。
- DolphinScheduler 3.4.2 按 `DR-049` 使用 MySQL JDBC Registry。Master/API/Alert、双 Worker、API Health、成功/失败 Shell Workflow 及受控重启后复跑均已通过。
- 正式 Workflow Instance `12` 的 DataX/ODS、DIM/DWD、DWS/ADS 与质量 Task 成功；`doris_load` 在一次自动重试后仍失败，实例最终为 `FAILURE`，`serving_reconciliation` 未运行，证明自动重试与失败阻断生效。修正后的 Doris Application `application_1792417296391_0002` 和双向逐行对账 `application_1792417296391_0003` 是独立运行证据，不外推为调度内恢复成功。
- 集群三节点同时安装 Java 8、11、17，默认 Java 为 17，Hadoop 守护进程使用 Java 11。Doris Connector 正式 DAG 仅通过 Spark 任务参数为 YARN AM/Executor 固定 Java 8，不修改系统默认或其他任务。
- M6 Stage Gate 为 `VERIFIED`：除正式 DAG 自动重试/失败阻断与 Instance `17` 成功终态外，专用质量失败 Workflow Instance `18` 将 `ads_daily_business_overview.business_key_unique` 显式注入为唯一失败规则，Quality Task 非零失败且 `retry=0`，Doris/Reconciliation 未创建或运行；验证前后 Doris 均为 90 行/90 日期，金额汇总和最大 `load_time` 不变。专用 Workflow Code `187464279901408` 验证后已切换为 `OFFLINE`。
- 2026-10-19 补数 Instance `14` 使用显式业务日期 `2026-02-27`：21 表 DataX/ODS 在一次自动重试后 `SUCCESS`，历史分区 ODS Ready Gate `SUCCESS`。`dim_dwd_build` 因 `dim_category.business_key_unique` 失败；为按用户要求收尾，自动重试被停止为 `KILL`，实例终态为 `STOP`。DWS/ADS、Quality、Doris 和 Serving Reconciliation 均未启动；关机前 YARN 活动 Application 数为 0。
- 2026-10-20 根因确认：`dim_user`、`dim_visitor`、`dim_category`、`dim_coupon_template` 是 Type 1 当前态维度，Instance `14` 错误追加了 `dt=2026-02-27` 全量快照，导致全表业务键重复；不应把粒度改成“业务键 + 快照日”来绕过 Gate。
- 四个误建分区已复制到 HDFS 回滚根 `/warehouse/ecommerce/model/.rollback/m6-ds-backfill-20260227-r2/`，并分别通过目录数、文件数、字节数一致性核对后从 Hive Metastore 删除。清理后四表都只剩 `dt=2026-02-28`，行数/唯一键分别为 `40,000/40,000`、`80,000/80,000`、`60/60`、`30/30`；`dwd_behavior_event` 仍为 3,000,000 行、3,000,000 个唯一 `event_id`，范围 `2025-12-01..2026-02-28`。
- 独立 `ecommerce_aggregate_backfill` 已发布为 Workflow Code `187427451612864`，固定执行 `Model Ready Gate → DWS/ADS → Quality → Doris → Reconciliation`，显式排除 DataX、ODS 和 DIM/DWD 重建；`business_date` 与 `model_as_of_date` 分离，避免历史回补把 Cohort 表混成多个观察窗口。
- Instance `17` 使用 `business_date=2026-02-27`、`model_as_of_date=2026-02-28`：Model Ready、DWS/ADS、40-rule Quality Gate 均为 `SUCCESS`。Doris Load 初始两次在全局 Kryo 的最终 `DirectTaskResult` 解码时发生 `java.io.EOFException`；HDFS 目标路径 90/90 Blocks 健康、三节点 Spark/Kryo JAR Hash 一致，Java 8 Driver 假设复测无效并撤回。相同 89 日只读输入使用任务级 `JavaSerializer` 后得到 89 行/89 日期，随后仅恢复失败 Doris Task，输出 `DORIS_PASS`。Serving Reconciliation 首次确认 21 个业务字段一致，唯一差异为 Hive 微秒级 `load_time` 与 Doris `DATETIME` 秒级精度；两侧规范到秒后仅恢复对账 Task，输出 `SERVING_RECONCILIATION_PASS`。Instance `17` 最终五 Task 全部 `SUCCESS`，Workflow 于 2026-10-20 20:46:00 结束，未重跑 DataX/ODS/DIM/DWD。

### Source Data Build 后续接续

- 正式源库切换为 `ecommerce_oltp`；`ecommerce_oltp_m2_acceptance` 保留为 Pilot、CDC、R1/R2/M3 历史验收环境，不删除，也不再作为正式离线开发源。
- `ecommerce_oltp` 的 21 张正式 `biz_*` 表已部署并完成装载验收；历史验收库 `ecommerce_oltp_m2_acceptance` 仍只作为 Pilot/CDC 历史环境。
- 服务器工作目录中的旧 19 表 `generator/` 与旧 21 表 Pilot `tools/ecommerce_generator_v1/` 已按用户指示删除；仓库历史归档不受影响。
- `mysql/ddl/001_ecommerce_oltp.sql` 已部署；DDL 采用订单到优惠券的单向物理 FK，券反向订单引用由索引与 Source Gate 校验。
- V2 正式数据路径冻结为 Python Generator → CSV → MySQL `LOAD DATA` → `ecommerce_oltp`。
- 该 Source Data Build 同时是正式实时链路的历史初始化基线；Source Gate 已通过，可进入 Formal CDC Contract 与初始化设计，但不能复用 Pilot Topic 直接外推完成状态。
- 正式数据规模已确认为 90 天、100,000 笔订单、285,000 条订单明细、实测 1,328,502 条 OLTP 记录和 3,000,000～5,000,000 条行为事件；Business 数据已完成目标 MySQL 装载与 Source Gate。M7 性能实验已使用隔离数据集真实构建 900,000 笔订单、2,565,000 条订单明细和 9,000,000 条行为事件。
- 正式 V2 数据进入 `ecommerce_ods`、`ecommerce_dwd` 前，必须对现有 100 单 Pilot 数据执行有边界、可回滚的初始化重置；本决策不授权当前执行数据库清理。

### M7 Spark 性能实验

- 隔离 Hive `ecommerce_benchmark` 只读复用已验收 DIM/DWD；Setup 行数和唯一键断言输出 `M7_BENCHMARK_SETUP_PASS`。
- 六个 Smoke 与 18 个 Measured Applications 全部成功，三组方案结果指纹一致；Physical Plan 分别证明 `PartitionFilters`、`SortMergeJoin`、`BroadcastHashJoin` 和两阶段 `HashAggregate`。
- 三次运行中位数显示：分区裁剪 Input 9,274,966 → 3,311,644 bytes、Tasks 99 → 3、Duration 35,672 → 32,979 ms；Broadcast Join Shuffle 6,114,668 → 12,186 bytes，但 Duration 42,587 → 43,333 ms；两阶段聚合 Shuffle 409,103 → 6,316,203 bytes、Duration 38,456 → 39,625 ms。
- 结论边界：分区裁剪验证为有效；Broadcast Join 只证明资源效率改善；两阶段聚合在当前 `COUNT/SUM` 场景中没有收益。完整证据见 `docs/acceptance/m7-spark-performance-acceptance.md`。

## DESIGNED

- Behavior 60/30 Bundle 已以独立第 22 张 ODS 表 `ods_behavior_event` 接入离线链路并完成 Runtime Gate。未来 Kafka Raw 仍须共用事件 Schema 和 `event_id` 去重语义，但 Kafka/Flink Gate 不由本次离线验收替代。
- `DR-037`、`DR-041`、`DR-044` 已确认正式 90 天观察窗口和当前 Replay Baseline；Business Source 与 ODS 的 Day 60～90 时间推进式 Runtime、正式终态 Snapshot ODS Bootstrap、Behavior ODS Runtime 和对应最终 Gate 已完成。Kafka、CDC Runtime 和对应 Gate 仍为 `not_run`。
- 当前 6 张 DIM、8 张 DWD、6 张 DWS 与 1 张 ADS 均有正式 Runtime。M5-02 修正版使用独立 M5 Location，旧 `dwd_refund`、`dws_trade_day` 和 ADS 表保留为 `m5_20261018_history_*`，迁移前 HDFS 备份另行保留。
- 正式源模型继续采用 7 个业务域、21 张 `biz_*` 业务表；Generator 必须统一覆盖一期业务表，而不是逐表补小样本。
- 工程实施改为按层批量推进：21 表 Source → 批量 ODS → ODS Gate → DWD/DIM → Model Gate → DWS → ADS → Doris。
- ODS 复用边界为“一套代码 + 多表配置”：通用 DataX Job Generator、Stage Runner、Spark Validation 和 Publish；每表提供 source/target、primary key、partition、extract 与 quality rule，columns 统一引用 Business Generator 的 `TABLE_COLUMNS`，字段类型以正式 MySQL DDL 为准。
- 通用 DataX Job Generator、Snapshot Contract Generator、Stage Runner、Spark Validation/Publish Renderer 与 21 表 Contract 已完成实现；正式 Snapshot Runtime、Day 60～90 时间推进式业务分区发布、跨日恢复和独立 ODS Gate 已验证。
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
- Behavior Generator 已强制读取 Business Generator 的版本化 Entity Manifest；正式 60/30 Bundle 的跨源身份、Session、商品生效时间和事件唯一性本地检查为 `VERIFIED`，且 3,000,000 行已进入 HDFS/Hive `ods_behavior_event` 并通过 Gate；Kafka Raw Layer 仍为 `not_run`。
- M7 Spark 性能结论仅适用于记录的 Spark 3.5.9、隔离数据集、SQL 和三次测量；不得外推为 Flink/Kafka/Doris 性能、生产容量或其他数据形态下的通用提升。
- V2 初始化重置的精确对象、备份/回滚、执行命令与验收方法：`DECISION_REQUIRED`；不得直接清理现有数据库。
- `BI / Agent` 是否进入当前 V2 正式交付，还是继续遵循 `DR-029` 作为 M0～M10 之后规划：`DECISION_REQUIRED`。

## NEXT

1. M5-01、M5-02、六域 Aggregate Runtime、36 项 Metric Registry、40 条持久化质量结果和 10 项跨层 Reconciliation 已完成。
2. M5 Stage Gate 已通过；`TR-13/TR-14` Cohort Contract、Runtime、Gate、质量和对账均为 `VERIFIED`。
3. M6 与 M7 Stage Gate 均已完成；下一入口为 M8 外部只读 Topic/Checkpoint Inventory 与 Formal Realtime 设计评审收口，不重复运行已验收 Benchmark。
4. `ecommerce_benchmark` 与版本化 HDFS Root 当前保留用于复现；任何清理、重置或重新装载仍需要新的 Database Operation 授权。
