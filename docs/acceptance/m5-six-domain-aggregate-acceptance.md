# M5 首批六域 Aggregate Runtime 验收

> 后继 Contract：Cohort P0 指标加入后，当前模型为 6 DWS + 1 ADS，最终 Aggregate Gate 为 41/41，见 `m5-cohort-metrics-acceptance.md`。本文保留扩展前 5 DWS + 1 ADS、34/34 Gate 的历史验收事实。

日期：2026-10-19  
状态：`VERIFIED`

## 验收范围

- Contract：`m5-metrics-v1`。
- 新增正式表：`ecommerce_dws.dws_product_day_sku`、`ecommerce_dws.dws_user_day`、`ecommerce_dws.dws_coupon_day`。
- 复用正式表：`dws_trade_day`、`dws_behavior_day`、`ads_daily_business_overview`。
- 固定输入：Seed `20260105` 对应的正式 DIM/DWD，业务日期覆盖 2025-12-01～2026-02-28。
- Runtime：hadoop201 `/data/m5-metrics-20261019-r1/`；原始日志不提交 Git。

## Runtime 结果

| 步骤 | YARN Application | 结果 |
| --- | --- | --- |
| 6 张 Aggregate 表 DDL | `application_1792344728440_0001` | `FINISHED / SUCCEEDED` |
| 首次 5 DWS + 1 ADS Build | `application_1792344728440_0002` | `FINISHED / SUCCEEDED` |
| 首次 34 条 Aggregate Gate | `application_1792344728440_0003` | `FINISHED / SUCCEEDED`，34/34 无违规 |
| 首次结果摘要 | `application_1792344728440_0004` | `FINISHED / SUCCEEDED` |
| 同批幂等重跑 | `application_1792344728440_0005` | `FINISHED / SUCCEEDED` |
| 重跑后 34 条 Aggregate Gate | `application_1792344728440_0006` | `FINISHED / SUCCEEDED`，34/34 无违规 |
| 重跑后结果摘要 | `application_1792344728440_0007` | `FINISHED / SUCCEEDED` |

## 固定结果与幂等性

| 汇总项 | 首次构建 | 同批重跑后 |
| --- | ---: | ---: |
| 商品 DWS 行数 | 94,272 | 94,272 |
| 支付商品数量 | 399,306 | 399,306 |
| 商品退款数量 | 6,482 | 6,482 |
| 商品支付金额（分） | 10,374,159,421 | 10,374,159,421 |
| 用户 DWS 行数 | 90 | 90 |
| 注册用户数 | 40,000 | 40,000 |
| 首购用户数 | 33,056 | 33,056 |
| 活跃身份日累计 | 1,808,012 | 1,808,012 |
| 营销 DWS 行数 | 90 | 90 |
| 发券数 | 60,000 | 60,000 |
| 锁券数 | 30,000 | 30,000 |
| 核销数 | 21,085 | 21,085 |
| 解锁数 | 8,617 | 8,617 |
| 用券优惠金额（分） | 24,535,139 | 24,535,139 |
| 用券支付订单数 | 21,085 | 21,085 |
| ADS 行数 | 90 | 90 |

16 项摘要逐行比较结果为 `IDEMPOTENCE_METRICS_IDENTICAL`。Gate 覆盖业务键、审计字段、分区、非负值、交易/支付/退款、商品、用户、营销事件与 ADS 对账。

## 运行环境与已知边界

- 启动脚本在 SSH TTY 结束时向 ResourceManager 传递 `SIGHUP`；本次根据日志根因，仅以脱离终端方式恢复 ResourceManager，未修改 Hadoop 配置。收尾复核确认 ResourceManager 仍在线、两个 NodeManager 均为 `RUNNING`。
- HDFS 有 2 个 Live DataNode、0 Corrupt Replica、0 Missing Block；767 个 Under-replicated Block 继续作为基础设施已知状态，不外推为本次数据错误。
- Spark 写入期间出现一次 Hive Metastore `listPartitionsWithAuthInfo` 重连告警；所有对应 Application 最终均为 `SUCCEEDED`，两轮 Gate 和幂等摘要未发现违规。
- 本次 Aggregate 验收时 `TF-05` 尚未发布；后续已按正式决策收敛为加购行为量，发布与跨层对账证据见当前 Metric Registry 和 `m5-cross-layer-reconciliation-acceptance.md`。
- 本验收不证明 cohort 指标、比率、排行、Doris Serving、DolphinScheduler 或正式实时链路已经完成。
