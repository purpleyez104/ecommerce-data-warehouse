# M5 Cohort P0 指标验收

日期：2026-10-19  
状态：`VERIFIED`

## Contract

- `TR-13`：订单创建日群组截至显式 `as_of_time` 的成功支付金额减成功退款金额。
- `TR-14`：同一创建日群组中，在订单自身 `payment_deadline_at` 前且不晚于 `as_of_time` 支付成功的订单数 / 创建订单数。
- 固定运行参数：`as_of_date=2026-02-28`，对应 `as_of_time=2026-02-28 23:59:59 Asia/Shanghai`。
- 物理落点：新增 `dws_trade_cohort_day`；最终净支付、分子、分母和转化率进入现有 `ads_daily_business_overview`，未新增重复 ADS。

## Runtime 结果

- Schema 迁移：`application_1792373377526_0013`，`SUCCEEDED`。
- 修正列顺序后的首次 Build：`application_1792373377526_0015`，`SUCCEEDED`。
- 首次 41 项 Aggregate Gate：`application_1792373377526_0016`，`SUCCEEDED`。
- 同批幂等重跑 Build / Gate：`application_1792373377526_0018` / `0019`，均 `SUCCEEDED`。
- 持久化质量结果：`application_1792373377526_0020`，40 条唯一规则，`FAIL=0`。
- 跨层对账：`application_1792373377526_0021`，10 项 × 90 日，共 900 行，`FAIL=0`。

以上 7 个有效 Application 已再次通过 YARN 查询确认均为 `FINISHED / SUCCEEDED`。

固定结果：

```text
cohort_rows=90
created_orders=100000
paid_orders=70000
paid_amount_cents=10374159421
refund_amount_cents=311199194
cumulative_net_paid_cents=10062960227
min_as_of_time=2026-02-28 23:59:59
max_as_of_time=2026-02-28 23:59:59
ads_rows=90
missing_rates=0
```

## 修复与边界

首次 ADS 写入因 Hive `ADD COLUMNS` 的真实追加顺序与 Renderer 输出顺序不一致而失败；未放宽业务规则。修复物理 Contract 和 Renderer 列顺序后完整重跑通过，后续幂等重跑结果一致。

本验收证明固定截止点下 `TR-13/TR-14` 的离线 cohort 实现、质量与跨层一致性；不证明其他 cohort、离实时结果、Doris Serving 或调度已完成。
