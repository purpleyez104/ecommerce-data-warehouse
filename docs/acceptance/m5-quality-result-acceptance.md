# M5 持久化质量结果验收

> 后继 Contract：Cohort P0 指标加入后，当前质量结果已扩展为 40 条且 `FAIL=0`，见 `m5-cohort-metrics-acceptance.md`。本文保留扩展前 33 条规则的首次持久化与幂等验收事实。

日期：2026-10-19  
状态：`VERIFIED`

## 验收范围

- 结果表：`ecommerce_quality.data_quality_result`。
- 固定运行标识：`run_id=m5-quality-20261019-r1`。
- 输入批次：`batch_id=m5-metrics-20261019-r1`。
- 规则来源：现有 Aggregate Gate 的 33 条有效规则；最终 `AGGREGATE_GATE_PASS` 哨兵不作为业务规则保存。
- 写入语义：按 `run_id` 动态分区覆盖；结果写入后断言规则数为 33 且 `FAIL=0`，失败时返回非零并阻断下游。

## Runtime 结果

| 操作 | YARN Application | 结果 |
| --- | --- | --- |
| 创建 `ecommerce_quality.data_quality_result` | `application_1792373377526_0002` | `FINISHED / SUCCEEDED` |
| 首次写入并执行 Quality Gate | `application_1792373377526_0003` | `FINISHED / SUCCEEDED`；输出 `QUALITY_RESULT_GATE_PASS` |
| 同一 `run_id` 幂等重跑 | `application_1792373377526_0006` | 输出 `QUALITY_RESULT_GATE_PASS` |

首次写入和同一 `run_id` 重跑后的独立查询结果均为：

```text
row_count=33
distinct_rules=33
failed_rules=0
true_results=33
```

## 运行环境与已知现象

- 服务器重启后先通过 `/home/yee/bin/bigdata-start.sh offline` 恢复离线组件；最终两个 NodeManager 均为 `RUNNING`，启动脚本输出 `BIGDATA START FINISHED`。
- Spark 写入两次均遇到一次 Hive Metastore `listPartitionsWithAuthInfo` 自动重连告警；任务随后完成，Gate 与独立查询均未发现结果缺失。
- 本次只创建新的质量结果表和对应 `run_id` 分区，没有修改现有 DWS/ADS 数据。

## 证据边界

本验收证明当前六域 Aggregate 的 33 条质量规则可以持久化、同一 `run_id` 幂等覆盖并在失败时形成阻断入口。它不证明跨层 `reconciliation_result`、离实时对账、Doris Serving 或 DolphinScheduler 已完成。
