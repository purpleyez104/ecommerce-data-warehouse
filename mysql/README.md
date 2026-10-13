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

该命令覆盖 Generator 回归、bundle 篡改、dry-run 零 MySQL 调用、Schema/非空保护、单 session SQL 顺序、MySQL/Gate 失败、严格 TSV 协议及密码不进入 argv。本地测试本身不证明 Runtime；本次目标 MySQL 的真实装载与 Gate 结论单独记录在 acceptance 文档中。目标 21 表现已非空，直接重跑会按设计 fail-fast，任何重置或重新装载都需要新的 Database Operation 授权。
