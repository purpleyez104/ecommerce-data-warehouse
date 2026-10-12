# MySQL 模块边界

本目录保留 V2 正式源库的模块入口。`ddl/001_ecommerce_oltp.sql` 是 2026-10-11 根据目标 MySQL 只读结构核对、业务基线、指标口径和候选物理模型整理的 21 表候选 DDL；它尚未执行、部署或通过 Source Gate，不是 Runtime `verified` 事实。

当前正式库 `ecommerce_oltp` 只存在 3 张技术测试表，没有 21 张 `biz_*`。历史验收库的 21 表主体可复用，但候选 DDL 已移除订单/优惠券循环 FK：保留 `biz_order.coupon_id` 的单向外键，券表反向订单字段只建索引并交由 Source Gate 校验。DDL 不含 `DROP`、`TRUNCATE`、`DELETE`、`INSERT` 或 `IF NOT EXISTS`，对象冲突必须显式失败。

DDL、CSV Contract、Targeted Test、本地正式规模生成和 Behavior 对 Business Entity Manifest 的复用已经完成。V2 `LOAD DATA` 与 Shared Source Gate 已实现并完成本地静态、fake-client 和失败路径测试；尚未连接 MySQL、部署 DDL、装载数据或执行 Gate，因此状态为 `implemented / not_run`。正式库部署和装载仍需单独 Database Operation 授权。历史 19 表与 Pilot 资产分别保留在 `archive/legacy-m2-19-table/` 和 `archive/pilot-v1/`。

## V2 CSV bundle preflight

固定输入是 Business Generator 输出目录，其中必须包含 21 张 `biz_*.csv`、`dataset_manifest.json` 和 `entity_manifest.json`，且不能包含额外 CSV。纯本地 dry-run 不读取数据库凭据，也不会调用 `mysql`：

```bash
bash mysql/scripts/load_v2_csv.sh --dry-run --bundle /absolute/path/to/generated-bundle
```

预期输出为 `status: valid` 的 JSON 装载计划、21 表 FK-safe 顺序和逐表 Manifest 信息；预期退出状态为 `0`。缺失或多余 CSV、表头、行数、大小、SHA-256、Manifest identity、Entity binding、主键或引用不一致时返回非零，并指出对象和原因。输出目录和 Generator 原始 bundle 不会被修改。

## 真实装载（需要单独授权）

真实模式从环境变量读取 `MYSQL_HOST`、`MYSQL_PORT`、`MYSQL_DATABASE`、`MYSQL_USER`、`MYSQL_PASSWORD`。`MYSQL_DATABASE` 只接受安全标识符；密码只写入 mode `0600` 的临时 `defaults-extra-file`，不进入 argv、SQL 或日志。示例变量名见 `env/.env.example`。

```bash
bash mysql/scripts/load_v2_csv.sh --bundle /absolute/path/to/generated-bundle
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

该命令覆盖 Generator 回归、bundle 篡改、dry-run 零 MySQL 调用、Schema/非空保护、单 session SQL 顺序、MySQL/Gate 失败、严格 TSV 协议及密码不进入 argv。本地测试不证明候选 DDL 可部署、MySQL `LOAD DATA` 已成功、Source Gate 已在目标库通过或下游可以开始；这些 Runtime 结论必须在获得 Database Operation 授权后单独记录。
