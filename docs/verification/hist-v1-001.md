# `hist-v1-001` 固定样本摘要

## 生成参数

| 参数 | 值 |
| --- | --- |
| `run_id` | `hist-v1-001` |
| seed | `20260920` |
| mode | `history` |
| count | 100 |
| history days | 90 |
| anchor | `2026-09-20T14:00:00`（`Asia/Shanghai`） |

## 固定规模与状态

| 项目 | 期望值 |
| --- | ---: |
| `biz_order` | 100 |
| `biz_order_item` | 319 |
| `biz_payment_attempt` | 82 |
| `PAID` 订单 | 69 |
| `CANCELED` 订单 | 31 |
| `business_date` / `dt` 分区 | 88 |
| `gross_amount_cents` 合计 | 8,402,600 |
| `discount_amount_cents` 合计 | 30,000 |
| `payable_amount_cents` 合计 | 8,372,600 |

金额单位为人民币分；固定金额满足 `8,402,600 - 30,000 = 8,372,600`。

## 证据边界

以上规模、状态、分区和金额基线来自用户提供的 2026-09-22 Chat 运行结果，并与当前确定性生成器的固定参数静态复算一致。本文件不是原始 ECS 日志，也不证明新入库脚本已在 ECS 执行。

限定范围的 ODS Runtime 结论见 [`biz_order` ODS 历史切片验收记录](../acceptance/biz_order_ods_acceptance.md)。M3 仍为 `in_progress`；21 表全量、增量、重跑/回补、失败恢复和后续离线分层仍未完成。
