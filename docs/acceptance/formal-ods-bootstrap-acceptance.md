# 正式 ODS Bootstrap 验收

状态：`VERIFIED`（正式终态 Snapshot Bootstrap 范围）  
验收日期：2026-10-17

## 范围与固定输入

- Source：正式 MySQL `ecommerce_oltp`，Dataset `v2.3-bootstrap`，Seed `20260928`，21 表合计 1,328,502 行。
- Target：正式 Hive `ecommerce_ods`，21 张 EXTERNAL 表，ORC + Snappy，显式根路径 `/warehouse/ecommerce/ods/<table>`。
- Batch：`formal-bootstrap-20260228-r1`；DataX HDFS Writer → batch staging → Spark Validation → Publish → 独立 ODS Gate。
- Runtime：hadoop202 `/data/formal-ods-runtime-20261017-r1-hadoop202/`；原始日志和 Secret 不提交 Git。

## 结果

- 旧 `ecommerce_ods` Pilot 三表已重命名为 `pilot_20260921_*`；原 EXTERNAL HDFS 数据、88 个 `ods_order` 历史分区和原 LOCATION 保持不变，未删除或覆盖。
- 正式 21 表运行状态为 `planned → staged → validated → published`，`publish_allowed=true`，`error=null`。
- 发布后的独立 Gate 生成并执行 1,476 条断言 SQL；成功结果 1,476/1,476，失败关键字 0。覆盖总行数、逐业务日期分区、主键、审计字段、Hive 类型和 DDL 外键引用。
- Gate 前再次只读核对正式 MySQL 21 表实时行数，逐表均与 Dataset Manifest 一致，总计 1,328,502 行。
- 临时 `GRANT SELECT ON ecommerce_oltp.*` 已精确回收；hadoop202 的 `datax.env` 已删除，运行目录不存在残留 `ods-datax-*.json` Secret job。
- 仓库导出 21 个不含 Secret 的 DataX job 与 SHA-256 Manifest，路径为 `datax/jobs/formal-bootstrap-20260228-r1/`。

## 回滚与证据边界

- Pilot 元数据回滚入口为 `hive/ods/rollback_archive_pilot_20260921.sql`；只有正式 `ods_order` 已按单独授权移除时才能执行，当前未执行回滚。
- 正式 ODS 表为 EXTERNAL；任何删除表、删除 `/warehouse/ecommerce/ods/`、重置分区或重跑正式 Bootstrap 都需要新的 Database/HDFS Operation 授权。
- 本验收本身只证明 Seed `20260928` 终态 Snapshot 的正式 Source → ODS Bootstrap。Seed `20260105` 的 Day 60～90 时间推进式增量、跨日恢复、连续回补和完整 Milestone 3 Stage Gate 已在 [`formal-ods-smoke-acceptance.md`](formal-ods-smoke-acceptance.md) 单独验收；DIM/DWD/DWS/ADS、Doris 离线服务和调度仍未由两份 ODS 验收证明。
