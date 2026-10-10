# File Baseline

更新时间：2026-09-27
扫描范围：Offline Current Baseline、Realtime R3 Handoff、Realtime V2 方向决策点名路径及当前 worktree
证据口径：`VERIFIED_EXECUTED / CONFIRMED_CREATED / CHAT_GENERATED / MENTIONED_ONLY / SUPERSEDED / UNKNOWN`

`FILE EXISTS ≠ VERIFIED`。Runtime 验证与当前 worktree 文件存在性分别记录；ECS 上已执行但尚未同步到 worktree 的文件，不根据名称或建议路径自行重建。

## 当前事实入口

| 路径 | 文件事实 | 用途 |
| --- | --- | --- |
| `README.md` | 当前工作区存在 | 项目总览与状态导航 |
| `docs/spec.md` | 当前工作区存在 | 项目范围、约束与验收标准 |
| `docs/plan.md` | 当前工作区存在 | Milestone 门禁与当前下一步 |
| `docs/status/offline-current.md` | 已按 2026-09-27 Offline Baseline Handoff 更新 | 当前离线状态 |
| `docs/status/realtime-current.md` | 本轮建立基线 | 当前实时状态 |
| `docs/status/file-baseline.md` | 已按本次 File Fact Ledger 更新 | 当前文件事实与冲突 |
| `docs/workflow/README.md` | 当前工作区存在 | Development Chat → Work → Repository 协作规则 |

## VERIFIED_EXECUTED：ECS 正式工程文件

以下文件已有 Development Chat 的实际成功执行证据；“worktree 缺失”只表示尚未同步，不降低其限定 Runtime 事实，也不允许凭空创建文件。

| 文件 | 类型 | ECS 实际路径 | 已验证用途 | 当前 worktree |
| --- | --- | --- | --- | --- |
| `offline_m3_01_ods_order.sql` | Engineering | `/data/projects/ecommerce-data-warehouse/hive/ods/sql/offline_m3_01_ods_order.sql` | 创建 ODS order | 缺失 |
| `dwd_order_create.sql` | Engineering | `/data/projects/ecommerce-data-warehouse/hive/dwd/ddl/dwd_order_create.sql` | 创建 DWD order | 缺失 |
| `dwd_order_precheck.sql` | Acceptance | `/data/projects/ecommerce-data-warehouse/spark/dwd/sql/dwd_order_precheck.sql` | DWD 单日预检 | 缺失 |
| `dwd_order_build.sql` | Engineering | `/data/projects/ecommerce-data-warehouse/spark/dwd/sql/dwd_order_build.sql` | DWD 单日加工 | 缺失 |
| `build_dwd_order.sh` | Engineering | `/data/projects/ecommerce-data-warehouse/scripts/offline/m4/build_dwd_order.sh` | 单日 `PRECHECK → BUILD → VERIFY` | 缺失 |
| `check_dwd_order_consistency.sql` | Acceptance | `/data/projects/ecommerce-data-warehouse/tests/offline/check_dwd_order_consistency.sql` | DWD 单日一致性检查 | 缺失 |
| `dwd_order_history_precheck.sql` | Acceptance | `/data/projects/ecommerce-data-warehouse/spark/dwd/sql/dwd_order_history_precheck.sql` | DWD 历史构建预检 | 缺失 |
| `dwd_order_history_build.sql` | Engineering | `/data/projects/ecommerce-data-warehouse/spark/dwd/sql/dwd_order_history_build.sql` | DWD 历史批量加工 | 缺失 |
| `build_dwd_order_history.sh` | Engineering | `/data/projects/ecommerce-data-warehouse/scripts/offline/m4/build_dwd_order_history.sh` | DWD 历史批量入口 | 缺失 |
| `check_dwd_order_history_consistency.sql` | Acceptance | `/data/projects/ecommerce-data-warehouse/tests/offline/check_dwd_order_history_consistency.sql` | DWD 历史全量对账 | 缺失 |
| `inspect-source-contract.sh` | Acceptance | `/data/projects/ecommerce-data-warehouse/tests/realtime/inspect-source-contract.sh` | 实时 Source Contract 验收 | 缺失 |
| `OrderDwdJob.java` | Engineering | `/data/projects/ecommerce-data-warehouse/flink/jobs/r1/r1-order-dwd-job/src/com/ecommerce/r1/OrderDwdJob.java` | Order DWD | 存在；与服务器已执行版本的逐字一致性未单独证明 |
| R1 `build.sh` | Engineering | `/data/projects/ecommerce-data-warehouse/flink/jobs/r1/r1-order-dwd-job/build.sh` | Java 11 target 编译 Order DWD | 存在；与服务器已执行版本的逐字一致性未单独证明 |
| R1 `run.sh` | Engineering | `/data/projects/ecommerce-data-warehouse/flink/jobs/r1/r1-order-dwd-job/run.sh` | YARN Application Mode 提交 Order DWD | 存在；与服务器已执行版本的逐字一致性未单独证明 |
| `r1-order-dwd.jar` | Build Artifact | `/data/projects/ecommerce-data-warehouse/flink/jobs/r1/r1-order-dwd-job/build/r1-order-dwd.jar` | 已运行的 Order DWD 构建产物 | 不因 Runtime 验证自动纳入 Git |
| `OrderItemDwdJob.java` | Engineering | `/data/projects/ecommerce-data-warehouse/flink/jobs/r3/r3-order-item-dwd-job/src/com/ecommerce/r3/OrderItemDwdJob.java` | OrderItem DWD | 缺失；Handoff 未附正文，不自行重建 |
| R3 `build.sh` | Engineering | `/data/projects/ecommerce-data-warehouse/flink/jobs/r3/r3-order-item-dwd-job/build.sh` | Java 11 target 编译 OrderItem DWD | 缺失；Handoff 未附正文，不自行重建 |
| R3 `run.sh` | Engineering | `/data/projects/ecommerce-data-warehouse/flink/jobs/r3/r3-order-item-dwd-job/run.sh` | YARN Application Mode 提交 OrderItem DWD | 缺失；Handoff 未附正文，不自行重建 |
| `r3-order-item-dwd.jar` | Build Artifact | `/data/projects/ecommerce-data-warehouse/flink/jobs/r3/r3-order-item-dwd-job/build/r3-order-item-dwd.jar` | 已运行的 OrderItem DWD 构建产物 | 不因 Runtime 验证自动纳入 Git |

## VERIFIED_EXECUTED：路径待确认或非正式仓库资产

| 文件 | 类型 | Runtime 事实 | Repository 处理 |
| --- | --- | --- | --- |
| `offline_m3_source_preflight.sh` | Acceptance | 已执行；实际路径 `UNKNOWN` | 路径确认前不移动、不新建替代品 |
| `offline_m3_02_make_order_job.py` | Engineering | 已执行；实际路径 `UNKNOWN` | 路径确认前不移动、不新建替代品 |
| `offline_m3_03_stage_orders.sh` 修正版 | Engineering | 已执行；实际路径 `UNKNOWN` | 路径确认前不移动、不新建替代品 |
| `m3_cleanup_nonbaseline_orders.sql` | Acceptance / History | 早期 12 笔非基线数据清理已执行；实际路径 `UNKNOWN` | 仅作为历史证据，路径确认前不处理 |
| `publish_m3_ods.sh` | Engineering | `/home/yee/publish_m3_ods.sh` 已执行 | 历史批次版本；取得原文件后再做维护性参数化，不重写业务语义 |
| `capacity-scheduler.xml` | Infrastructure | `maximum-am-resource-percent=0.25` 已生效并允许第三个长期 Flink Application 获得 AM Container；旧记录路径为 `/data/module/hadoop/etc/hadoop/capacity-scheduler.xml`，Realtime Handoff 记录为 `/data/module/hadoop-3.4.1/etc/hadoop/capacity-scheduler.xml` | 集群实际配置；路径关系未确认，原始配置未随 Handoff 入库 |
| `mysql-to-kafka.yaml` | Secret Engineering Configuration | `/home/yee/.secrets/cdc-r1/mysql-to-kafka.yaml` 已执行 | 包含 Secret，禁止打印、复制真实值或原样入库；公开模板尚未确认 |
| `order_dates.txt` | Runtime | `/home/yee/.local/share/ecommerce-dw/m3/order_dates.txt` 已使用 | 不作为正式 repository 文件 |
| `order_baseline_m3hist_20260921_01.tsv` | Evidence | `/home/yee/.local/share/ecommerce-dw/m3/order_baseline_m3hist_20260921_01.tsv` | Runtime evidence；本轮未复制入库 |
| `m3_publish_dates.txt` | Temp | `/home/yee/m3_publish_dates.txt` 已使用 | 不进入正式 repository |

## CONFIRMED_CREATED / NOT EXECUTED

| 文件 | Chat 实际路径 | 建议 repository 路径 | 当前状态 |
| --- | --- | --- | --- |
| `ods_order_item_create.sql` | `/mnt/data/ods_order_item_create.sql` | `hive/ods/ddl/ods_order_item_create.sql` | F2 `CONFIRMED_CREATED / NOT EXECUTED`；逐表 Pilot 路线已停止，不继续执行，不得列入 VERIFIED 或自动复用于 V2 正式 ODS |

## 历史验收资产

以下文件保存限定范围历史证据，不表示当前服务仍在线：

- `docs/acceptance/env-05-cdc-acceptance.md`
- `docs/acceptance/r1_snapshot_acceptance_frozen.md`
- `docs/acceptance/r1-realtime-acceptance.md`
- `docs/acceptance/realtime_r1_r2_verified.md`
- `docs/acceptance/biz_order_ods_acceptance.md`
- `docs/verification/hist-v1-001.md`

## 当前工程资产

| 范围 | 路径 | 文件事实 | Runtime 边界 |
| --- | --- | --- | --- |
| DataX 候选入口 | `datax/config/`、`datax/scripts/`、`datax/templates/` | `CONFIRMED_CREATED` | 不是 `hist-v1-001` 当次实际执行文件；本轮 `not_run` |
| Hive ODS DDL | `hive/ods/ddl/ods_order.sql` | `CONFIRMED_CREATED` | 本轮 `not_run` |
| ODS 发布重建稿 | `scripts/offline/publish_order_ods_partitions.sh` | `CONFIRMED_CREATED` | `implemented / not_run`；不含实际 ECS 路径 |
| ODS 质量入口 | `quality/checks/check_ods_order_quality.sh` | `CONFIRMED_CREATED` | `implemented / not_run` |
| 订单 DWD Job | `flink/jobs/r1/r1-order-dwd-job/` | 当前 worktree 存在 | 历史 Chat 证明服务器同路径 Job 已构建和运行；当前文件与当次执行内容的逐字一致性未单独证明 |
| 订单明细 DWD Job | `flink/jobs/r3/r3-order-item-dwd-job/` | 当前 worktree 缺失 | 服务器同路径 Job 已构建、运行并完成 Initial Load / Incremental Upsert；未附原文件内容，不能安全同步 |
| Doris 订单 DWD DDL | `doris/ddl/dwd_order_create.sql` | `CONFIRMED_CREATED` | 历史 Doris 表有验收事实；当前文件未重新执行 |
| 实时只读对账 | `scripts/realtime/check_order_dwd_consistency.sh`、`tests/realtime/check_dwd_order_consistency.sh` | `CONFIRMED_CREATED` | `implemented / not_run` |
| 旧 Pilot Generator | `archive/pilot-v1/ecommerce_generator_v1/` | 已归档并恢复原 package layout | `PILOT / ACCEPTANCE / HISTORY`；不作为新的 V2 Python → CSV Generator 实现基础或正式入口 |
| V2 Business / Behavior Generator | `mock/generator/business_generator/`、`mock/generator/behavior_generator/` | `CONFIRMED_CREATED` | `candidate / implemented / not_run`；正式 Contract、`LOAD DATA`、Source Gate 与目标环境 Runtime 未完成 |

## V2 Source Data Build 文件边界

- V2 Business / Behavior Generator 已创建，状态为 `candidate / implemented / not_run`；不能从文件存在性或本地 Unit Test 推导 Source Gate 或目标环境 Runtime 已通过。
- 21 张 CSV 的字段、依赖、生成顺序、数据规模、时间范围、状态分布和跨表比例尚待冻结。
- `LOAD DATA` 初始化脚本、Source Gate 与 V2 正式 ODS 批量配置均尚未创建或验证。
- Formal CDC 配置、正式 Kafka Topic、`event_version`、Domain Flink Applications、Incremental Business Generator、正式 Checkpoint Root 与 V2 Doris 初始化脚本均尚未创建或验证。
- 旧 Pilot 文件继续保存历史证据；后续若需要复用通用算法，必须逐项确认来源与 V2 Contract，不得整体继承旧生成器或逐条 INSERT 路径。

## Evidence Assets

- ODS order：100 rows、100 unique orders、88 partitions、8,372,600 payable cents。
- DWD pilot：`application_1790148204235_0009`，`dt=2026-09-17`，1 row、1 unique order、83,400 payable cents、0 mismatch、`PASS`。
- DWD full history：`application_1790148204235_0013`，100 rows、100 unique orders、88 partitions、69 `PAID`、31 `CANCELED`、8,402,600 gross cents、30,000 discount cents、8,372,600 payable cents、0 mismatch、`PASS`。
- YARN concurrency：调整后 `AMResourceLimit memory=5120 MB`、`usedAMResource memory=2048 MB`、2 active applications、0 pending applications；随后 Spark 任务成功完成。
- order_item historical source：319 items、319 unique items、100 orders、626 quantity，三项金额与订单历史基线一致。
- 当前仓库已有 `docs/acceptance/biz_order_ods_acceptance.md`，但它只记录此前 `biz_order` ODS 历史切片，不自动覆盖本次新增 DWD 与 YARN 验收事实。
- Realtime R3：OrderItem DWD Initial Load 为 MySQL / Doris 各 320 行、320 个不同明细、101 个订单、627 件；应付 8,386,500 分、原价 8,416,500 分、优惠 30,000 分、退款 201,621 分、退款数量 16，孤儿明细与非法金额记录均为 0。
- Realtime R3 Incremental：`order_item_id=2456670014000320` 的 `updated_at` 更新产生 Kafka `op=u`、offset 1185，Doris `kafka_offset` 从 1181 更新为 1185，行数与不同明细数保持 320。
- Realtime Recovery：CDC `chk-396`、Order DWD `chk-179` 是已验证恢复点，恢复后均产生新 Completed Checkpoint；它们不是当前最新 Checkpoint。
- Realtime Application ID 只作为本阶段历史证据；当前 Application、Flink Job、Checkpoint 与 Doris BE 是否在线均为 `UNKNOWN`。
- Application ID、Scheduler 指标和查询结果本轮只来自 Handoff；因未指定新的 Evidence Asset 路径，未创建验收日志或新 acceptance 文档。

## 已迁移的当前文档路径

- `docs/architecture.md` → `docs/architecture/architecture.md`
- `docs/final-architecture-v1.0.md` → `docs/architecture/final-architecture-v1.0.md`
- `docs/business-source-design.md` → `docs/design/business-source-design.md`
- `docs/realtime-pipeline-design.md` → `docs/design/realtime-pipeline-design.md`
- `docs/metrics.md` → `docs/business/metrics.md`
- `mock/generator/ecommerce_generator_v1/` → `archive/pilot-v1/ecommerce_generator_v1/`（Pilot History；原 package layout 已恢复）

## HISTORY / SUPERSEDED

- Hive/Beeline 触发的 MapReduce 聚合：已被 Spark SQL on YARN 替代为当前正式离线计算方式。
- 初版 `offline_m3_03_stage_orders.sh`：存在 SSH 消耗 stdin 问题，已被修正版替代。
- 初版 `build_dwd_order.sh`：Beeline 表格输出解析错误，已被 TSV2 字段解析版本替代。
- `application_1790148204235_0004`：`KILLED / KILLED` 且 0 resource allocation，未执行 SQL 或写入 DWD，仅为故障历史。
- `hist-v1-001`、100 单 Generator、ODS order、DWD order：作为 `PILOT / ACCEPTANCE / HISTORY` 保留，不再作为 V2 正式数据开发入口。
- Realtime R1～R3、`ecommerce_oltp_m2_acceptance`、`ods_cdc_m2_clean_v1`、`all-to-zero`、Pilot `kafka_offset` Sequence 与旧 Checkpoint Root：作为 `PILOT / ACCEPTANCE / HISTORY` 保留，不再作为 Realtime V2 正式入口。
- `OrderDwdJob`、`OrderItemDwdJob`：保留为 `VERIFIED PROTOTYPE / FRAMEWORK REFERENCE`；不删除，也不按逐表方式复制扩展。
- `R4 Payment DWD` 下一步：已被 Shared V2 Source Data Build 与 SOURCE GATE 后的 Formal CDC / Domain DWD-DIM 路线替代。
- 逐表 Pilot 开发方式与 `ods_order_item_create.sql` 后续执行计划：已被按层批量推进的 V2 方案替代。
- R3 Java 17 class major version 61 的编译产物：因 YARN Flink Java 11 Runtime 出现 `UnsupportedClassVersionError`，已由 `javac --release 11`、major version 55 的产物替代。
- 早期 `r1-order-dwd-job.zip`：已被当前正式工程版本替代。
- `archive/legacy-m2-19-table/`：旧 19 表代码归档，不是当前 V2 实现。
- `docs/archive/milestone-2-business-design.md`：旧 19 表设计归档已恢复；仅作历史材料，不作为当前 V2 实现依据。
- `mysql/ddl/`、`mysql/sql/`：上一轮候选路径已从当前工作区移除；不得把历史验收自动映射到新骨架。
- 根目录 `scripts/start.sh`、`scripts/stop.sh`：当前工作区已删除；未获得继续保留或替代入口的 Handoff 事实。

## CONFLICT / UNKNOWN

1. Handoff 中 10 个 `VERIFIED_EXECUTED` 正式 ODS/DWD 文件均未出现在当前 worktree；未附原文件内容，不能安全同步。
2. `hive/ods/ddl/ods_order.sql` 与 ECS 已执行的 `hive/ods/sql/offline_m3_01_ods_order.sql` 名称和路径不同；未做内容等价性判断。
3. `scripts/offline/publish_order_ods_partitions.sh` 与已执行的 `/home/yee/publish_m3_ods.sh` 不是同一已确认版本；不得互相替代。
4. `offline_m3_source_preflight.sh`、`offline_m3_02_make_order_job.py`、`offline_m3_03_stage_orders.sh` 修正版和 `m3_cleanup_nonbaseline_orders.sql` 的实际路径仍为 `UNKNOWN`。
5. `ods_order_item_create.sql` 当前只有 Chat 创建路径，未确认进入 ECS repository 或本 worktree；现已决定停止执行并保持 F2 历史状态。
6. `offline-m4-01-dwd-order.md` 与 `capacity-scheduler.xml.bak-20260923-am` 是否真实创建仍为 `UNKNOWN`。
7. 当前 worktree 有大量既存未提交迁移与新增文件；本轮仅处理已批准的仓库整理范围。
8. Realtime Handoff 已验证的 R3 Job 与 `inspect-source-contract.sh` 当前 worktree 缺失；未附原文件内容，不能根据文件名或 Chat 片段重建。
9. R3 Doris DDL、R2/R3 验收 SQL/Python 当前只有 Chat-only 执行事实；是否在服务器固化为脚本文件仍为 `UNKNOWN`。
10. `capacity-scheduler.xml` 的旧记录路径与本次 Realtime Handoff 路径不同；是否为软链接或同一文件仍为 `UNKNOWN`。
11. CDC、Order DWD、OrderItem DWD 的当前 Application / Job、最新 Checkpoint 和 Doris BE 在线状态均为 `UNKNOWN`。
12. Formal Topic Namespace、Partition 数、Key Strategy、`event_version`、正式 Checkpoint Root 与 Doris Pilot 数据重置方案尚未冻结；不得根据附件中的示例名称自行创建。

## Deferred Issues

- 从 ECS 读取并核对上述 10 个已验证工程文件的真实内容后，再按原路径同步到 worktree。
- 确认四个 M3 路径未知文件的真实位置与最终版本。
- 取得 `/home/yee/publish_m3_ods.sh` 后，仅做 Handoff 指定的维护性参数化与 fail-fast 整理。
- `ods_order_item_create.sql` 保持 F2，不安排部署或状态提升；如未来 V2 ODS 需要同名能力，应依据正式 21 表 Contract 重新评审，不能沿用该状态。
- 核对 `ecommerce_oltp` 的正式 21 表 DDL，并在创建新 Generator 文件前冻结 V2 数据规格。
- SOURCE GATE 通过后再审计 Kafka Topic / Checkpoint，并冻结 Formal CDC Contract；当前不继续 Payment DWD Pilot。
- MySQL 权威 DDL、旧归档文档与 start/stop 脚本仍按原有 Deferred Issue 保留，本轮不处理。
- 从服务器取得 R3 Job 与 `inspect-source-contract.sh` 的真实最终文件后，再按 Handoff 路径同步并核对内容；不提交已构建 JAR。
- 确认 R3 Doris DDL、R2/R3 验收 SQL/Python 是否已固化，以及 `capacity-scheduler.xml` 两个路径的真实关系。
