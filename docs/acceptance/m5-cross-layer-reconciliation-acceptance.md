# M5 六域跨层对账验收

> 后继 Contract：Cohort P0 指标加入后，当前对账已扩展为 10 项 × 90 日、900 行且 `FAIL=0`，见 `m5-cohort-metrics-acceptance.md`。本文保留扩展前 8 项对账的首次与幂等验收事实。

日期：2026-10-19  
状态：`VERIFIED`

## 验收范围

- 结果表：`ecommerce_quality.reconciliation_result`。
- 固定运行标识：`run_id=m5-reconciliation-20261019-r1`。
- 输入批次：`batch_id=m5-metrics-20261019-r1`。
- 比较范围：`comparison_scope=CROSS_LAYER`。
- 对账窗口：2025-12-01～2026-02-28，共 90 个业务日。
- 阈值：当前首批离线跨层对账要求精确相等，`threshold_value=0`。

通用结果 Contract 使用 `left_object/right_object` 和 `left_value/right_value`，同一张表可在未来保存 `OFFLINE_REALTIME` 结果；本次没有生成任何离实时数据。

## Runtime 结果

| 操作 | YARN Application | 结果 |
| --- | --- | --- |
| 创建 `ecommerce_quality.reconciliation_result` | `application_1792373377526_0008` | `FINISHED / SUCCEEDED` |
| 首次写入并执行 Reconciliation Gate | `application_1792373377526_0009` | `FINISHED / SUCCEEDED`；输出 `CROSS_LAYER_RECONCILIATION_PASS` |
| 同一 `run_id` 幂等重跑 | `application_1792373377526_0011` | `FINISHED / SUCCEEDED`；输出 `CROSS_LAYER_RECONCILIATION_PASS` |

首次运行和幂等重跑后的独立查询均为：

```text
row_count=720
comparison_count=8
failed_rows=0
min_business_date=2025-12-01
max_business_date=2026-02-28
```

八项代表性对账均为 90 行且 `FAIL=0`：

| Reconciliation ID | Metric ID | 左侧 → 右侧 |
| --- | --- | --- |
| `cross_layer.tr_07.paid_amount` | `TR-07` | DWD Payment → DWS Trade |
| `cross_layer.tf_05.add_cart_count` | `TF-05` | DWD Behavior → DWS Behavior |
| `cross_layer.pr_04.paid_amount` | `PR-04` | DWD Order Item → DWS Product |
| `cross_layer.us_05.paid_user_count` | `US-05` | DWD Payment/Order → DWS User |
| `cross_layer.rf_03.refund_amount` | `RF-03` | DWD Refund → DWS Trade |
| `cross_layer.mk_01.issued_coupon_count` | `MK-01` | DWD Coupon Event → DWS Coupon |
| `cross_layer.tr_02.effective_gmv` | `TR-02` | DWS Trade → ADS Overview |
| `cross_layer.tf_01.pv_count` | `TF-01` | DWS Behavior → ADS Overview |

## 已知现象与证据边界

- 两次写入均出现一次 Hive Metastore `listPartitionsWithAuthInfo` 自动重连告警；Application 随后成功，Gate 和独立查询结果一致。
- 本验收证明六个指标域的代表性离线跨层值以及两项 DWS→ADS 值在固定 90 日窗口内逐日一致。
- 本验收不证明完整指标集合、离实时对账、Doris Serving、DolphinScheduler 或正式实时链路已经完成。
