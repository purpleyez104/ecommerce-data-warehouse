# File Baseline

更新时间：2026-10-19
扫描范围：Offline Current Baseline、Realtime R3 Handoff、正式回放设计点名路径、Generator/DDL 及当前 worktree
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
| `docs/design/historical-incremental-replay-design.md` | 当前工作区存在；Business Replay 输入已本地实现 | 60 天初始化、30 天双链路回放、时间审计与 SCD2 设计 |

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
| `OrderDwdJob.java` | Engineering | `/data/projects/ecommerce-data-warehouse/flink/jobs/r1/r1-order-dwd-job/src/com/ecommerce/r1/OrderDwdJob.java` | Order DWD | 归档于 `archive/pilot-v1/realtime/flink/order-dwd-job/`；与服务器已执行版本的逐字一致性未单独证明 |
| R1 `build.sh` | Engineering | `/data/projects/ecommerce-data-warehouse/flink/jobs/r1/r1-order-dwd-job/build.sh` | Java 11 target 编译 Order DWD | 归档于 `archive/pilot-v1/realtime/flink/order-dwd-job/`；与服务器已执行版本的逐字一致性未单独证明 |
| R1 `run.sh` | Engineering | `/data/projects/ecommerce-data-warehouse/flink/jobs/r1/r1-order-dwd-job/run.sh` | YARN Application Mode 提交 Order DWD | 归档于 `archive/pilot-v1/realtime/flink/order-dwd-job/`；与服务器已执行版本的逐字一致性未单独证明 |
| `r1-order-dwd.jar` | Build Artifact | `/data/projects/ecommerce-data-warehouse/flink/jobs/r1/r1-order-dwd-job/build/r1-order-dwd.jar` | 已运行的 Order DWD 构建产物 | 不因 Runtime 验证自动纳入 Git |
| `OrderItemDwdJob.java` | Engineering | `/data/projects/ecommerce-data-warehouse/flink/jobs/r3/r3-order-item-dwd-job/src/com/ecommerce/r3/OrderItemDwdJob.java` | OrderItem DWD | 缺失；Handoff 未附正文，不自行重建 |
| R3 `build.sh` | Engineering | `/data/projects/ecommerce-data-warehouse/flink/jobs/r3/r3-order-item-dwd-job/build.sh` | Java 11 target 编译 OrderItem DWD | 缺失；Handoff 未附正文，不自行重建 |
| R3 `run.sh` | Engineering | `/data/projects/ecommerce-data-warehouse/flink/jobs/r3/r3-order-item-dwd-job/run.sh` | YARN Application Mode 提交 OrderItem DWD | 缺失；Handoff 未附正文，不自行重建 |
| `r3-order-item-dwd.jar` | Build Artifact | `/data/projects/ecommerce-data-warehouse/flink/jobs/r3/r3-order-item-dwd-job/build/r3-order-item-dwd.jar` | 已运行的 OrderItem DWD 构建产物 | 不因 Runtime 验证自动纳入 Git |

## VERIFIED_EXECUTED：路径待确认或非正式仓库资产

### 60/30 Replay Day 60 独立运行目录

2026-10-15 已在 `hadoop201` 只读核对 `/home/yee/replay-r3-bootstrap-20261015/`。该目录不是服务器旧 Git 副本的一部分，以下文件只证明隔离 Source Day 60 Bootstrap 与 Source Gate：

| 路径或文件 | 状态 | 证据边界 |
| --- | --- | --- |
| `bootstrap/biz_*.csv`（21 个） | `VERIFIED_EXECUTED` | Day 60 固定输入；不代表 Day 61～90 已应用 |
| `bootstrap/expected_result.json` | `VERIFIED_EXECUTED` | 21 表精确计数基线；只读复核全部匹配 |
| `bootstrap/ods_batch_contract.json` | `CONFIRMED_CREATED` | Day 60 ODS Contract；不证明 ODS Runtime |
| `load.sql`、`source_gate.sql` | `VERIFIED_EXECUTED` | 当次 Bootstrap 装载与 Gate 输入；不作为当前仓库代码版本替代品 |
| `day60-load-r3.out` | `VERIFIED_EXECUTED` | 事务内 45-rule Gate 全部 0，`EXIT_STATUS=0` |
| `day60-postcommit-gate-r3.out` | `VERIFIED_EXECUTED` | 提交后独立 45-rule Gate 全部 0，`EXIT_STATUS=0` |

服务器 Git 副本位于 `/data/projects/ecommerce-data-warehouse`，只读核对时停留在 `codex/m1-infrastructure-compatibility` 的 2026-09-05 HEAD，并包含大量历史删除与未跟踪文件。它不是当前 Replay/ODS 实现来源；不得直接 `git pull`、切分支或清理来部署 Executor。后续部署使用独立运行目录和精确文件/Hash 清单。

### Replay Executor 数据盘部署目录

`/data/ecommerce-replay-runtime-20261015/` 是后续使用的 mode `0700` 数据盘独立部署目录，不属于服务器旧 Git 副本。它由 `/home/yee/ecommerce-replay-runtime-20261015/` 逐文件复制而来；源/目标均为 31 个文件、47M，`diff -qr` 无差异，Day 62 两份关键证据 SHA-256 保持一致。目录包含 Planner/Executor、Source Gate、最小 Python Contract、r3 Replay Manifest 与 Day 61～62 Package。`results/day61/result.json` 与 `results/day62/result.json` 分别记录 19,456 和 22,995 个操作已提交且事务内 Gate 通过；对应提交后独立 45-rule Gate 全部为 0。Day 63～90 Package 尚未部署到该目录。原 `/home/yee/ecommerce-replay-runtime-20261015/` 暂作为已验收备份保留，尚未删除。

`/data/ecommerce-replay-runtime-20261016-r6/` 是已完成的 Batch Ledger/Range Executor 运行目录，目标库为 `ecommerce_oltp_replay_20260105_r6`。目录包含完整 Day 61～90 Bundle、30 份逐日 Acceptance/Checkpoint、最终独立 Gate 与审计日志；Range State 为 `verified`，30 条 Ledger 覆盖 Day 61～90，最终独立 Source Gate 为 45/45、0 违规，`local_infile=OFF`。Replay 身份对 r6 的临时权限已回收；r5/r4/r2 目录、数据库与权限未在本次操作中修改。

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
- `archive/pilot-v1/offline/reference/hist-001.md`

## 当前工程资产

| 范围 | 路径 | 文件事实 | Runtime 边界 |
| --- | --- | --- | --- |
| DataX 21 表 Pipeline | `datax/config/ods_tables.json`、`datax/scripts/generate_job.py`、`datax/scripts/run_ods_batch.py`、`datax/templates/mysql_to_hdfs_ods.json.tpl`、`spark/scripts/render_ods_batch_sql.py` | `VERIFIED_EXECUTED` | Job Generator、Stage Runner 与 Validation/Publish Renderer 已完成正式 Snapshot、Day 60～90、跨日恢复和最终 1,498 项 ODS Gate；当前统一 DataX/ODS 测试为 32/32 |
| Hive ODS DDL | `archive/pilot-v1/offline/reference/ods_order.sql` | `CONFIRMED_CREATED` | 本轮 `not_run`；仅作 Pilot History |
| ODS 发布重建稿 | `archive/pilot-v1/offline/reference/publish_order_ods_partitions.sh` | `CONFIRMED_CREATED` | `implemented / not_run`；不含实际 ECS 路径 |
| ODS 质量入口 | `archive/pilot-v1/offline/reference/check_ods_order_quality.sh` | `CONFIRMED_CREATED` | `implemented / not_run` |
| 订单 DWD Job | `archive/pilot-v1/realtime/flink/order-dwd-job/` | 当前 worktree 存在 | 历史 Chat 证明服务器原路径 Job 已构建和运行；当前文件与当次执行内容的逐字一致性未单独证明 |
| 订单明细 DWD Job | `flink/jobs/r3/r3-order-item-dwd-job/` | 当前 worktree 缺失 | 服务器同路径 Job 已构建、运行并完成 Initial Load / Incremental Upsert；未附原文件内容，不能安全同步 |
| Doris 订单 DWD DDL | `archive/pilot-v1/realtime/doris/dwd_order_create.sql` | `CONFIRMED_CREATED` | 历史 Doris 表有验收事实；当前文件未重新执行 |
| 实时只读对账 | `archive/pilot-v1/realtime/acceptance/check_order_dwd_consistency.sh`、`archive/pilot-v1/realtime/acceptance/check_dwd_order_consistency.sh` | `CONFIRMED_CREATED` | `implemented / not_run` |
| 旧 Pilot Generator | `archive/pilot-v1/ecommerce_generator_v1/` | 已归档并恢复原 package layout | `PILOT / ACCEPTANCE / HISTORY`；不作为新的 V2 Python → CSV Generator 实现基础或正式入口 |
| 21 表正式 DDL 与 Source Gate | `mysql/ddl/001_ecommerce_oltp.sql`、`mysql/scripts/`、`mysql/sql/` | `VERIFIED_EXECUTED` | MySQL 8.0.46 已部署 21 表并装载 1,328,502 行；事务内与提交后独立 45-rule Source Gate 均通过，`local_infile` 已恢复为 `OFF` |
| Business / Behavior Generator | `mock/generator/business_generator/`、`mock/generator/behavior_generator/` | `VERIFIED_EXECUTED` | Business 21 表 1,328,502 行已在目标服务器生成并装载；Behavior 3,000,000 事件已完成本地正式规模验证；Entity Manifest 绑定及全量引用/Session/事件唯一性检查通过 |
| 60/30 Business Replay | `mock/generator/business_generator/src/business_generator/replay.py`、`mock/generator/business_generator/config/replay_formal_20260105.json`、`mysql/ddl/002_replay_batch_ledger.sql`、`mysql/scripts/plan_replay_bootstrap.py`、`mysql/scripts/replay_daily_package.py`、`mysql/scripts/execute_replay_daily_package.py`、`mysql/scripts/execute_replay_range.py` | 当前 worktree 存在；Ledger/Range Executor 已部署到 r6 数据盘独立目录 | 当前正式 Baseline 已由本地重生成复现；r6 Day 60～90、30/30 Acceptance、最终独立 Source Gate、批量 ODS Stage Gate与权限回收均已验证。Formal CDC、SCD2 Runtime 与离实时接管仍为 `not_run` |
| 60/30 Behavior Replay | `mock/generator/behavior_generator/src/behavior_generator/replay.py`、`mock/generator/behavior_generator/config/replay_formal_20260105.json` | 当前 worktree 存在 | Dataset `v2.3-behavior-replay-formal-20260105-r1` 已绑定 Business r2 Entity Manifest 并生成 3,000,000 条事件：Bootstrap 895,324 条、30 个 Daily Package 2,104,676 条；Manifest/Hash/窗口/实体有效期/全局 Event ID 审计通过。Hive `ods_behavior_event` 已完成 3,000,000 行、90 分区 Runtime Gate；Kafka/Flink Runtime 仍为 `not_run` |
| DIM/DWD Model | `hive/model/`、`hive/model/migrate_m5_refund_contract.sql`、`hive/model/rollback_m5_refund_contract.sql`、`spark/scripts/render_*model*.py`、`spark/scripts/render_dim_snapshot_sql.py`、`spark/scripts/render_product_scd2_sql.py`、`spark/scripts/render_dwd_sql.py` | 14 表 `VERIFIED_EXECUTED` | 当前申请粒度 `dwd_refund` 已完成受控迁移并通过 60/60 Model Gate；旧成功资金粒度表与 HDFS 备份保留，回滚入口已入库 |
| 六域 DWS/ADS Aggregate | `hive/model/aggregate_contract.json`、`hive/model/aggregate_physical_contract.json`、`hive/model/generate_aggregate_ddl.py`、`spark/scripts/render_aggregate_sql.py`、`spark/scripts/render_aggregate_gate_sql.py` | `VERIFIED_EXECUTED` | 6 张 DWS + 1 张 ADS 已完成正式 Runtime；最终 41/41 Gate 首次及重跑后均通过 |
| Metric Registry | `governance/metric_registry/metric_registry.json`、`governance/metric_registry/validate_metric_registry.py`、`tests/governance/` | `VERIFIED_EXECUTED` | 36 个已实现指标绑定定义 SHA-256、Aggregate 输出与 M5 验收；6/6 Registry Tests 通过 |
| Quality Result | `quality/quality_result_contract.json`、`quality/generate_quality_result_ddl.py`、`spark/scripts/render_quality_result_sql.py`、`tests/quality/` | `VERIFIED_EXECUTED` | `data_quality_result` 当前为 40 条唯一规则、`FAIL=0`；写入后 Gate 可阻断失败运行 |
| Reconciliation Result | `reconciliation/reconciliation_result_contract.json`、`reconciliation/generate_reconciliation_result_ddl.py`、`spark/scripts/render_cross_layer_reconciliation_sql.py`、`tests/reconciliation/` | `VERIFIED_EXECUTED` | 通用左右值 Contract 已落地；当前 10 项 × 90 日共 900 行，`FAIL=0` |

## 正式 Source Data Build 文件边界

- Business / Behavior Generator 已完成固定输入的正式规模生成与 Targeted Test；Business 21 表已完成历史目标 MySQL Runtime，Seed `20260105` 的 Business 60/30 已完成 r6 Day 60～90 MySQL 与 ODS Runtime，Behavior 60/30 也已完成 Hive ODS Runtime Gate。
- 正式数据规模、90 天时间范围、21 张 CSV 字段、装载顺序、状态分布、跨表关系及 Behavior 对 Business Entity Manifest 的复用已确认；Source Gate 验收边界见 `docs/acceptance/source-load-gate-acceptance.md`。
- `LOAD DATA` 初始化脚本与 Shared Source Gate 已实现并通过本地失败路径与目标 MySQL Runtime 验收；正式 ODS 21 表抽取 Contract、Job Generator、Stage Runner 与 Spark Validation/Publish Renderer 已完成本地测试及 DataX/HDFS/Hive/Spark Runtime，最终 ODS Gate 已验证。
- Formal CDC 配置、正式 Kafka Topic、`event_version`、Domain Flink Applications、Incremental Business Generator、正式 Checkpoint Root 与 V2 Doris 初始化脚本均尚未创建或验证。
- Seed `20260105` 的 60 天 Business Bootstrap、30 个 Daily Package、Expected Result、Bootstrap 与 Daily Dry-run Plan 已生成并审计；Behavior 60 天 Bootstrap、30 个 Daily Package、Manifest 与 Hash 审计也已完成。隔离 Source/ODS、Behavior ODS 与首批 DIM/DWD 均已通过 Runtime Gate；Kafka/Flink 写入和离实时逐日接管仍为 `DESIGNED / not_run`。Seed `20260928` 的既有最终 90 天 Source Gate 数据不替代这些 Runtime 资产。
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
- M5 首批六域 Runtime 的 Application ID、34/34 Gate 与幂等摘要记录于 `docs/acceptance/m5-six-domain-aggregate-acceptance.md`；后继 Cohort 扩展、最终 41/41 Gate、40 条质量规则和 10 项对账记录于 `docs/acceptance/m5-cohort-metrics-acceptance.md`。服务器原始日志不进入 Git。

## 已迁移的当前文档路径

- `docs/architecture.md` → `docs/architecture/architecture.md`
- `docs/final-architecture.md` → `docs/architecture/final-architecture.md`
- `docs/business-source-design.md` → `docs/design/business-source-design.md`
- `docs/realtime-pipeline-design.md` → `docs/design/realtime-pipeline-design.md`
- `docs/metrics.md` → `docs/business/metrics.md`
- `mock/generator/ecommerce_generator_v1/` → `archive/pilot-v1/ecommerce_generator_v1/`（Pilot History；原 package layout 已恢复）
- `hive/ods/ddl/ods_order.sql`、`scripts/offline/publish_order_ods_partitions.sh`、`quality/checks/check_ods_order_quality.sh` → `archive/pilot-v1/offline/reference/`
- `flink/jobs/r1/r1-order-dwd-job/`、Pilot CDC/Kafka/Doris/对账文件 → `archive/pilot-v1/realtime/`

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
- `mysql/ddl/`、`mysql/sql/` 的早期不完整候选骨架已移除；当前同路径内容是后来建立并已完成正式部署／Source Gate 验收的权威实现，不得与早期骨架混为一谈。
- 根目录 `scripts/start.sh`、`scripts/stop.sh`：当前工作区已删除；未获得继续保留或替代入口的 Handoff 事实。

## CONFLICT / UNKNOWN

1. Handoff 中 10 个 `VERIFIED_EXECUTED` 正式 ODS/DWD 文件均未出现在当前 worktree；未附原文件内容，不能安全同步。
2. `archive/pilot-v1/offline/reference/ods_order.sql` 与 ECS 已执行的 `hive/ods/sql/offline_m3_01_ods_order.sql` 名称和路径不同；未做内容等价性判断。
3. `archive/pilot-v1/offline/reference/publish_order_ods_partitions.sh` 与已执行的 `/home/yee/publish_m3_ods.sh` 不是同一已确认版本；不得互相替代。
4. `offline_m3_source_preflight.sh`、`offline_m3_02_make_order_job.py`、`offline_m3_03_stage_orders.sh` 修正版和 `m3_cleanup_nonbaseline_orders.sql` 的实际路径仍为 `UNKNOWN`。
5. `ods_order_item_create.sql` 当前只有 Chat 创建路径，未确认进入 ECS repository 或本 worktree；现已决定停止执行并保持 F2 历史状态。
6. `offline-m4-01-dwd-order.md` 与 `capacity-scheduler.xml.bak-20260923-am` 是否真实创建仍为 `UNKNOWN`。
7. 当前 worktree 仍有大量既存未提交迁移、DataX 实现与文档同步修改；文件存在和未提交 diff 不等于已形成 Git 提交或 Runtime 证据。
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
- 已完成 `ecommerce_oltp` 正式 21 表 DDL、Generator、装载与 Source Gate 核对；后续结构变化必须重新执行 Schema Contract 与 Source Gate。
- 当前审计 Kafka Topic / Checkpoint，并冻结 Formal CDC Contract；继续停止 Payment DWD Pilot。
- 旧归档文档与 start/stop 脚本仍按原有 Deferred Issue 保留；MySQL 权威 DDL 已由正式部署和 Source Gate 闭合，不再列为 Deferred Issue。
- 从服务器取得 R3 Job 与 `inspect-source-contract.sh` 的真实最终文件后，再按 Handoff 路径同步并核对内容；不提交已构建 JAR。
- 确认 R3 Doris DDL、R2/R3 验收 SQL/Python 是否已固化，以及 `capacity-scheduler.xml` 两个路径的真实关系。
