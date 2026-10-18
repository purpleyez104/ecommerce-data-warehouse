# MySQL 模块边界

本目录保留当前正式源库的模块入口。`ddl/001_ecommerce_oltp.sql` 是根据目标 MySQL 结构、业务基线、指标口径和物理模型整理的 21 表正式 DDL；2026-10-12 已在 MySQL 8.0.46 的 `ecommerce_oltp` 部署并完成 Runtime 验收，证据边界见 [`source-load-gate-acceptance.md`](../docs/acceptance/source-load-gate-acceptance.md)。

当前正式库 `ecommerce_oltp` 保留原有 3 张技术测试表，并新增已验收的 21 张 `biz_*` 表。正式 DDL 移除了订单/优惠券循环 FK：保留 `biz_order.coupon_id` 的单向外键，券表反向订单字段只建索引并交由 Source Gate 校验。DDL 不含 `DROP`、`TRUNCATE`、`DELETE`、`INSERT` 或 `IF NOT EXISTS`，对象冲突必须显式失败。

DDL、CSV Contract、Targeted Test、正式规模生成和 Behavior 对 Business Entity Manifest 的复用已经完成。2026-10-12 已通过 `LOAD DATA LOCAL INFILE` 装载 21 表共 1,328,502 行，事务内及提交后独立 Shared Source Gate 均通过 45 条规则；`local_infile` 已恢复为 `OFF`。该结论不证明 DataX/Hive ODS、正式 CDC 或下游模型已完成。历史 19 表与 Pilot 资产分别保留在 `archive/legacy-m2-19-table/` 和 `archive/pilot-v1/`。

## CSV bundle preflight

固定输入是 Business Generator 输出目录，其中必须包含 21 张 `biz_*.csv`、`dataset_manifest.json` 和 `entity_manifest.json`，且不能包含额外 CSV。纯本地 dry-run 不读取数据库凭据，也不会调用 `mysql`：

```bash
bash mysql/scripts/load_csv_bundle.sh --dry-run --bundle /absolute/path/to/generated-bundle
```

预期输出为 `status: valid` 的 JSON 装载计划、21 表 FK-safe 顺序和逐表 Manifest 信息；预期退出状态为 `0`。缺失或多余 CSV、表头、行数、大小、SHA-256、Manifest identity、Entity binding、主键或引用不一致时返回非零，并指出对象和原因。输出目录和 Generator 原始 bundle 不会被修改。

## Daily Package Replay dry-run

MySQL Replay Planner 只处理当前 Replay Contract 中包含 `operation_time` 的 Daily Package。它校验 Replay Manifest、Business Hash、Package Manifest、ODS Batch Contract、文件 SHA-256、时间窗口、表名、字段、主键和 `operation_time + LOAD_TABLE_ORDER` 顺序，然后生成不含 Secret 的本地执行计划和事务 SQL：

```bash
python mysql/scripts/replay_daily_package.py \
  --replay-bundle /absolute/path/to/replay-bundle \
  --day 61 \
  --output runtime/mysql-replay-day-61 \
  --dry-run
```

预期成功退出状态为 `0`，结果位于指定输出目录的 `plan.json` 和 `replay.sql`。计划固定记录 `dry_run=true`、`execution_authorized=false`、`database_contacted=false`；SQL 只作为后续单独授权前的审计产物，不能据此声称 MySQL 回放已经执行。缺少 `--dry-run`、输出目录已存在，或 Manifest、Hash、字段、主键、时间窗口、操作顺序不一致时返回 `2`，且不创建完成态输出。旧 Bundle 若缺少当前 Contract 要求的 `operation_time` 会被拒绝，不提供隐式兼容。

该入口不读取数据库环境变量，不调用 MySQL Client，也不允许直接对第 90 日终态正式库回放。Runtime 必须使用另行授权的隔离 Source 并按日顺序执行。当前本地回滚只需移除本次输出目录；不会修改 Replay Bundle 或数据库。

## Daily Package Replay Executor

Executor 使用 Planner 的同一套 Manifest、Hash、Schema、主键、窗口与操作顺序校验，并通过 MySQL Client 在同一事务中执行 Daily 操作和 45-rule Source Gate。默认拒绝数据库访问；只有同时提供 `--execute` 与匹配的 `--confirm-day` 才会调用 Client：

```bash
python mysql/scripts/execute_replay_daily_package.py \
  --replay-bundle /absolute/path/to/replay-bundle \
  --day 61 \
  --confirm-day 61 \
  --output /absolute/path/to/mysql-replay-day-61-result \
  --execute
```

真实模式只从环境变量读取 `MYSQL_HOST`、`MYSQL_PORT`、`MYSQL_DATABASE`、`MYSQL_USER`、`MYSQL_PASSWORD`。密码写入 mode `0600` 的临时 defaults file，不进入 argv、日志或 `result.json`。MySQL Client 或 Source Gate 失败时返回非零，不生成成功结果；只有事务提交后才写出 `status=executed`、Package/SQL/Gate Hash 和操作数。输出目录已存在时 fail-fast，避免覆盖既有验收证据。

Executor 以 `replay_batch_ledger` 作为数据库提交事实：`batch_id` 与 `day_number` 唯一，Daily 操作、Ledger 写入和 45-rule Source Gate 位于同一事务。相同 Day 与相同 Hash 重跑返回 `already_applied`；同 Day 但 Hash/操作数冲突时 fail-fast。该机制避免进程中断后从 Day 61 盲目重放。

完整范围批量入口为：

```bash
python mysql/scripts/execute_replay_range.py \
  --replay-bundle /absolute/path/to/replay-bundle \
  --start-day 61 \
  --end-day 90 \
  --output /absolute/path/to/range-result \
  --execute
```

入口先对完整日期范围执行无数据库写入的 Preflight，再按日执行并保存自动 Checkpoint。中断后使用相同参数增加 `--resume`；Resume 会核对现有 Acceptance、目标数据库 Ledger 与最新 Source Gate，只跳过证据一致的已提交日期。默认 MySQL Client Timeout 为 300 秒，可通过 `MYSQL_COMMAND_TIMEOUT_SECONDS` 调整，最大 3600 秒。

当前本地实现和测试已完成。服务器运行目录 `/data/ecommerce-replay-runtime-20261016-r6/` 和隔离库 `ecommerce_oltp_replay_20260105_r6` 已完成 Day 60～90 Replay：Range State 为 `verified`，30 条 Ledger 覆盖 Day 61～90，30/30 Acceptance 完整，最终独立 Source Gate 为 45/45、0 违规，`local_infile=OFF`。Day 75 曾在事务提交后、Acceptance 落盘前被 signal 中断；修复后的 Resume 先核对下一日 Ledger，再通过 `already_applied` 补齐 Gate/Acceptance，没有重复业务写入。Replay 身份对 r6 的临时权限已精确回收；旧 r5/r4/r2 环境和权限未在本次操作中修改。真实回滚、重置或重放继续遵守新的 Database Operation 授权边界。

同一 Replay Baseline 的 Day 60～90 DataX/Hive ODS Stage Gate 也已完成，具体运行证据与边界见 [`formal-ods-smoke-acceptance.md`](../docs/acceptance/formal-ods-smoke-acceptance.md)；本节 Source Replay 结论仍不替代 ODS 或下游分层的独立验收。

## Replay Bootstrap Source Load dry-run

Bootstrap Planner 校验 Replay/Source/ODS Manifest Hash、21 张 CSV、字段、主键、FK、`LOAD_TABLE_ORDER`、Expected Result 和 Day 60 Cutover 未来状态边界，并生成不含凭据的单 Session 事务计划：

```bash
python mysql/scripts/plan_replay_bootstrap.py \
  --replay-bundle /absolute/path/to/replay-bundle \
  --output runtime/mysql-replay-bootstrap \
  --dry-run
```

成功时输出 `plan.json` 与 `load.sql`，计划固定记录 `execution_authorized=false`、`database_contacted=false`、目标必须为空、获取 advisory lock 且提交前执行 Source Gate。该入口不会调用 MySQL Client；缺少 `--dry-run`、Manifest/Hash 不一致、PK/FK 孤儿或已发生状态时间不早于 Cutover 时返回非零。

## 真实装载（重跑仍需单独授权）

真实模式从环境变量读取 `MYSQL_HOST`、`MYSQL_PORT`、`MYSQL_DATABASE`、`MYSQL_USER`、`MYSQL_PASSWORD`。`MYSQL_DATABASE` 只接受安全标识符；密码只写入 mode `0600` 的临时 `defaults-extra-file`，不进入 argv、SQL 或日志。示例变量名见 `env/.env.example`。

```bash
bash mysql/scripts/load_csv_bundle.sh --bundle /absolute/path/to/generated-bundle
```

入口先执行完整 bundle preflight，再以一个 MySQL session 获取 advisory lock、核对 21 表非生成列 Contract 和目标总行数为零，在事务中按 `LOAD_TABLE_ORDER` 执行 21 次 `LOAD DATA LOCAL INFILE`，并在 `COMMIT` 前运行 `mysql/sql/source_gate.sql`。任一步失败均返回非零，连接结束时由 MySQL 回滚未提交事务；脚本不会 `DROP`、`TRUNCATE`、`DELETE` 或自动清理目标库。若需要回滚，保留失败现场并由获得授权的操作者根据验收记录处理，不能直接重跑到非空库。

独立提交后复核入口：

```bash
bash mysql/scripts/run_source_gate.sh --bundle /absolute/path/to/generated-bundle
```

Gate 固定输出 `rule_id<TAB>violation_count`。Runner 对规则全集执行严格解析：规则缺失、重复、未知、非整数、非零，或 MySQL client 失败都会返回非零。规则覆盖 21 表计数、业务键、引用和多态商品目标、购物车合并、订单金额、支付唯一成功/金额/15 分钟、退款申请/资金/明细聚合、券与订单双向一致、事件最终状态/时间，以及 Manifest 冻结的订单状态分布。

## 本地验证与边界

```bash
E:/Software/Git/bin/bash.exe -c 'export PATH=/usr/bin:/mingw64/bin:$PATH; bash tests/run_unit.sh'
```

该命令覆盖 Generator 回归、Replay Bootstrap/Daily Package dry-run、bundle 篡改、Cutover 未来状态、PK/FK 孤儿、dry-run 零 MySQL 调用、Schema/非空保护、单 session SQL 顺序、MySQL/Gate 失败、严格 TSV 协议及密码不进入 argv。本地测试本身不证明 Runtime；本次目标 MySQL 的真实装载与 Gate 结论单独记录在 acceptance 文档中。目标 21 表现已非空，直接重跑会按设计 fail-fast，任何回放、重置或重新装载都需要新的 Database Operation 授权。
