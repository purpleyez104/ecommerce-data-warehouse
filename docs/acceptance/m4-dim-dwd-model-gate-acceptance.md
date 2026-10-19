# M4 DIM/DWD Model Gate 验收

日期：2026-10-18  
状态：`VERIFIED / HISTORY`（证明 2026-10-18 的旧成功退款粒度 Contract；当前申请粒度 Runtime 见 M5 验收）

> 后续 Contract 变更：M5-02 将 `dwd_refund` 改为每个退款申请一行，并把 Model Gate 扩展为 60 条。本文件的 59/59 结果继续作为历史证据；当前实现已在 `m5-refund-contract-migration-acceptance.md` 通过 60/60 Runtime Gate。

## 验收范围

- 固定输入：Seed `20260105` 对应的 21 张 Business ODS 与 1 张 Behavior ODS。
- 正式目标：`ecommerce_dim` 6 张 DIM、`ecommerce_dwd` 8 张 DWD。
- 存储：Hive EXTERNAL TABLE、ORC + Snappy、显式 HDFS 根路径 `/warehouse/ecommerce/model/`、按 `dt` 分区。
- 历史策略：4 张 Type 1 DIM、`dim_identity_mapping` 源有效区间、`dim_product_zip` SCD2。
- Model Gate：业务键、审计字段、SCD2 当前版本/区间、事实引用、金额守恒、Behavior 事件类型/分区/时态维度匹配。

## 运行结果

DDL 通过 Beeline 执行并返回 `exit=0`。抽查 `dim_product_zip` 与 `dwd_order` 均为 EXTERNAL ORC 表，`orc.compress=SNAPPY`，Location 分别位于：

- `/warehouse/ecommerce/model/ecommerce_dim/dim_product_zip`
- `/warehouse/ecommerce/model/ecommerce_dwd/dwd_order`

Spark on YARN 运行结果：

| 范围 | Application | 结果 |
| --- | --- | --- |
| 5 张 Type 1 / 源区间 DIM | `application_1792309323393_0002` | `FINISHED / SUCCEEDED` |
| `dim_product_zip` SCD2 | `application_1792309323393_0004` | `FINISHED / SUCCEEDED` |
| 8 张 DWD 初次批处理 | `application_1792309323393_0005` | 前 7 张成功，Behavior 因 ODS 审计列映射错误失败 |
| `dwd_behavior_event` 表级恢复 | `application_1792309323393_0006` | `FINISHED / SUCCEEDED`，客户端 `exit=0` |
| 59 条 Model Gate | `application_1792309323393_0007` | `FINISHED / SUCCEEDED`，59/59，客户端 `exit=0` |
| 14 表只读行数汇总 | `application_1792309323393_0008` | `FINISHED / SUCCEEDED`，客户端 `exit=0` |

Behavior DWD 首次失败的根因是其 ODS 审计列使用 `load_time`，而 DataX ODS 使用 `extract_time`。修复后 renderer 支持 `--model dwd_behavior_event` 表级恢复，未重跑已成功的 7 张 DWD。

## 精确行数

| 模型 | 行数 | 模型 | 行数 |
| --- | ---: | --- | ---: |
| `dim_category` | 60 | `dim_coupon_template` | 30 |
| `dim_identity_mapping` | 24,000 | `dim_product_zip` | 6,000 |
| `dim_user` | 40,000 | `dim_visitor` | 80,000 |
| `dwd_cart_item` | 110,000 | `dwd_cart_merge` | 8,000 |
| `dwd_order` | 100,000 | `dwd_order_item` | 285,000 |
| `dwd_payment` | 70,000 | `dwd_refund` | 7,200 |
| `dwd_coupon_event` | 129,702 | `dwd_behavior_event` | 3,000,000 |

## 本地验证

`tests/run_unit.sh`：95/95 通过，其中 Business 6、Behavior 6、DataX/ODS 32、Model 14、MySQL 37。`git diff --check` 通过。

## 历史资产与回滚边界

- 原 Pilot `ecommerce_dwd.dwd_order` 已在执行正式 DDL 前重命名为 `ecommerce_dwd.pilot_20260921_dwd_order`；88 个分区及原 HDFS Location 保持不变，未删除或移动数据。
- 正式 14 表均为 EXTERNAL TABLE。回滚本次模型元数据时不得直接删除 HDFS 数据；应先保留或重命名正式表，再按精确 Location 评估后续操作。
- 本验收不证明 DWS、ADS、Doris、DolphinScheduler、Formal CDC 或实时链路已完成。
