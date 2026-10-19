# M5 退款事实与聚合 Contract 迁移验收

日期：2026-10-18  
状态：`VERIFIED`

## 验收范围

- 决策：`DR-047`，不新增 `dwd_refund_request`；`dwd_refund` 改为每个 `refund_request_id` 一行的累积事实。
- 受影响正式表：`ecommerce_dwd.dwd_refund`、`ecommerce_dws.dws_trade_day`、`ecommerce_ads.ads_daily_business_overview`。
- 未变表：`ecommerce_dws.dws_behavior_day` Schema 与 Location 保持不变，但完整聚合重跑继续使用其数据构建 ADS。
- 固定输入：Seed `20260105` 对应的正式 ODS、DIM/DWD，业务日期覆盖 2025-12-01～2026-02-28。
- Runtime：hadoop201 `/data/m5-refund-migration-20261018-r1/`；原始日志不提交 Git。

## 迁移与回滚边界

首次尝试使用 `ALTER TABLE ... REPLACE COLUMNS CASCADE`，Hive 因列位置类型不兼容而在第一条语句原子失败；只读复核确认三张正式表均未改变。最终采用以下切换方式：

1. 将三张旧 EXTERNAL 表重命名为 `m5_20261018_history_*`，保留原 Location、分区和数据。
2. 三张新正式表使用干净 Schema 和 `/warehouse/ecommerce/model/m5_20261018/` 下的独立 Location。
3. 迁移前另在 `/warehouse/ecommerce/backups/m5-02-20261018-r1/` 保存三份 HDFS 数据副本，大小与旧正式目录逐项一致。
4. 回滚 SQL 只删除新 EXTERNAL 表元数据并把 HISTORY 表重命名回来，不删除旧数据；新 Location 数据也不会因 `DROP TABLE` 被删除。

集群预检显示 2 个 Live DataNode、0 Corrupt Replica、0 Missing Block；同时存在 767 个 Under-replicated Block。后者没有阻断本次写入，但仍是基础设施层需要继续观察的已知状态。

## Runtime 结果

| 步骤 | YARN Application | 结果 |
| --- | --- | --- |
| 新 `dwd_refund` 构建 | `application_1792325482148_0010` | `FINISHED / SUCCEEDED` |
| 60 条 Model Gate | `application_1792325482148_0011` | `FINISHED / SUCCEEDED`，60/60 无违规 |
| 首次 DWS/ADS 构建 | `application_1792325482148_0012` | `FINISHED / SUCCEEDED` |
| 首次 18 条 Aggregate Gate | `application_1792325482148_0013` | `FINISHED / SUCCEEDED`，18/18 无违规 |
| 同批 DWS/ADS 幂等重跑 | `application_1792325482148_0015` | `FINISHED / SUCCEEDED` |
| 重跑后 18 条 Aggregate Gate | `application_1792325482148_0016` | `FINISHED / SUCCEEDED`，18/18 无违规 |

作业日志均出现一次 Hive Metastore `listPartitionsWithAuthInfo` 重连告警，与历史 M4 运行特征一致；所有对应 YARN Application 最终状态均为 `SUCCEEDED`，Gate 与结果核对没有发现数据违规。

## 结果与幂等性

| 汇总项 | 首次构建 | 同批重跑后 |
| --- | ---: | ---: |
| `dwd_refund` 申请数 | 9,000 | 9,000 |
| `dwd_refund` 成功申请数 | 7,200 | 7,200 |
| 申请金额合计（分） | 390,075,825 | 390,075,825 |
| 成功退款金额合计（分） | 311,199,194 | 311,199,194 |
| `dws_trade_day` 行数 | 90 | 90 |
| DWS 退款件数 | 6,482 | 6,482 |
| `ads_daily_business_overview` 行数 | 90 | 90 |
| ADS PV | 899,471 | 899,471 |

前后比较覆盖 15 项核心行数和度量，`diff` 结果为 `IDEMPOTENCE_METRICS_IDENTICAL`。新 HDFS Location 均已有 ORC 数据；旧 HISTORY 表及迁移前备份均保留，未删除任何旧 HDFS 数据。

## 证据边界

本验收证明 M5-02 退款事实与当前 DWS/ADS 技术切片已经完成真实集群迁移、Gate 和幂等重跑。它不证明全部六域正式指标、Metric Registry、质量结果表、Doris Serving 或 DolphinScheduler 已完成。
