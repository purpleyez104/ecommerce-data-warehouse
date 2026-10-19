# M4 DWS/ADS Aggregate Gate 验收

日期：2026-10-18  
状态：`VERIFIED / HISTORY`（证明修改前 Aggregate Contract；当前修正版 Runtime 见 M5 验收）

> 后续 Contract 变更：M5-02 把退款申请数、成功申请数、成功金额和退款件数分开计算，并将 ADS 改为交易/行为日期并集。本文件继续作为旧 Contract HISTORY；当前实现已在 `m5-refund-contract-migration-acceptance.md` 通过新的 18/18 Gate 与幂等重跑。

## 验收范围

- 固定输入：Seed `20260105` 对应的正式 8 张 DWD，覆盖 2025-12-01～2026-02-28 共 90 个业务日。
- 正式目标：`ecommerce_dws.dws_trade_day`、`ecommerce_dws.dws_behavior_day`、`ecommerce_ads.ads_daily_business_overview`。
- 存储：Hive EXTERNAL TABLE、ORC + Snappy、显式 HDFS 根路径 `/warehouse/ecommerce/model/`、按 `dt` 分区。
- 语义边界：只发布已确认的可加总日粒度计数和金额，不提前分配稳定 Metric ID，也不实现尚未冻结的比率、精度与零分母口径。
- Aggregate Gate：主键、唯一性、审计字段、非负约束、现金净额公式、DWD → DWS 订单/支付/退款/行为对账，以及 DWS → ADS 日期与度量对账。

## 运行结果

DDL 执行返回 `exit=0`，三张目标表均为 EXTERNAL ORC + Snappy 表。首次聚合构建 Application `application_1792311537042_0001` 完成三步计算，客户端 `exit=0`；HDFS 结果为：

| 模型 | 分区数 | HDFS 文件字节数 |
| --- | ---: | ---: |
| `dws_trade_day` | 90 | 149,715 |
| `dws_behavior_day` | 90 | 104,138 |
| `ads_daily_business_overview` | 90 | 157,297 |

首次 Aggregate Gate Application `application_1792325482148_0001` 为 `FINISHED / SUCCEEDED`，18/18 项断言没有返回违规行，客户端 `exit=0`。

## 幂等重跑

使用相同 SQL 和固定输入执行一次完整重跑：

- Aggregate Application `application_1792325482148_0003`：`FINISHED / SUCCEEDED`，三个聚合步骤均执行完成。
- 重跑后 Gate Application `application_1792325482148_0004`：`FINISHED / SUCCEEDED`，18/18 项断言返回 `NULL`，客户端 `exit=0`。
- 重跑后只读汇总 Application `application_1792325482148_0005`：客户端 `exit=0`。
- 重跑前后抽取的 8 个核心结果行执行 `diff -u`，结果为 `identical`。

| 汇总项 | 重跑前 | 重跑后 |
| --- | ---: | ---: |
| `ads_daily_business_overview.rows` | 90 | 90 |
| `dws_behavior_day.events` | 3,000,000 | 3,000,000 |
| `dws_behavior_day.rows` | 90 | 90 |
| `dws_trade_day.created_orders` | 100,000 | 100,000 |
| `dws_trade_day.effective_gmv_cents` | 10,521,427,122 | 10,521,427,122 |
| `dws_trade_day.paid_amount_cents` | 10,374,159,421 | 10,374,159,421 |
| `dws_trade_day.refund_amount_cents` | 311,199,194 | 311,199,194 |
| `dws_trade_day.rows` | 90 | 90 |

幂等重跑的远端 `aggregate-rerun.exit` 被本地 PowerShell 外层展开为布尔文本，不能作为有效客户端退出码证据；因此本次重跑只采用 YARN 成功终态、三步 SQL 完成日志、重跑后 Gate `exit=0` 和前后汇总完全一致作为验收证据，未为修正该证据文件重复提交作业。

## 本地验证

`tests/run_unit.sh`：100/100 通过，其中 Business 6、Behavior 6、DataX/ODS 32、Model 19、MySQL 37。Aggregate 新增范围包含 5 项 DDL、转换和 Gate Renderer 测试。

## 证据位置与回滚边界

- 远端运行目录：`/data/m4-aggregate-runtime-20261018-r1/`。
- 首次构建、Gate、重跑、重跑后 Gate、前后汇总及 diff 均保留为该目录下的独立日志或结果文件。
- 三张目标表均为 EXTERNAL TABLE。回滚元数据时不得直接删除 HDFS 数据；应先保留或重命名表，再按精确 Location 评估后续操作。
- 本验收完成 Milestone 4 最小离线闭环，不证明 Milestone 5 稳定 Metric ID、正式指标字典、质量结果表、Doris、DolphinScheduler、Formal CDC 或实时链路已完成。
