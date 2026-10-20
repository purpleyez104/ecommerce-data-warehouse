# M5 Stage Gate Assessment

日期：2026-10-19  
状态：`VERIFIED`

## Acceptance → Evidence

| Acceptance | 当前证据 | 结论 |
| --- | --- | --- |
| 六个指标域具有代表性 DWS/ADS | `m5-six-domain-aggregate-acceptance.md` 与 `m5-cohort-metrics-acceptance.md`：6 DWS + 1 ADS、最终 41/41 Gate、幂等重跑 | `VERIFIED` |
| 已实现指标具有稳定 ID、版本和定义绑定 | Metric Registry Validator：36 项有效；`TF-05`、`TR-13`、`TR-14` 均绑定正式输出 | `VERIFIED` |
| 质量结果持久化并可阻断失败 | `m5-cohort-metrics-acceptance.md`：40 条唯一规则、`FAIL=0` | `VERIFIED` |
| 六域代表性指标完成逐日跨层对账 | `m5-cohort-metrics-acceptance.md`：10 项 × 90 日、900 行、`FAIL=0` | `VERIFIED` |
| 全部 P0 指标进入正式实现与发布 | `TR-13/TR-14` 使用显式 `as_of_time` 和订单支付截止窗口，Cohort DWS、现有 ADS 与 Registry 均已发布 | `VERIFIED` |
| 未冻结指标不提前发布 | 排行和 `TBD` 指标未错误进入 Registry | `VERIFIED` |

## Gate 结论

M5 Stage Gate 通过。最终范围为 6 张 DWS + 1 张 ADS、36 项 Metric Registry、40 条持久化质量规则和 10 项 × 90 日跨层对账；全部已执行规则均为零失败。该验收形成时的下一入口为 M6 Doris Serving；当前 Doris 独立任务、DolphinScheduler 组件门禁及 Aggregate Backfill Instance `17` 五 Task 成功终态与调度后对账均已由后续 M6/M1 验收完成。
