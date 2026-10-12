# `biz_order` ODS 历史切片验收记录

## 1. 结论

用户提供的 2026-09-22 Chat 终端记录证明，固定批次 `hist-v1-001` 的 `biz_order` 已在目标 ECS 完成以下限定链路：

```text
MySQL ecommerce_oltp_m2_acceptance.biz_order
  → DataX
  → HDFS ORC 历史输出
  → Hive ecommerce_ods.ods_order 分区发布
  → Spark SQL 固定基线汇总
```

该结论只适用于 100 单历史切片。Milestone 3 保持 `in progress`，不代表 21 表、增量抽取、同日重跑、连续回补、异常批次保护或后续 DIM/DWD/DWS/ADS/Doris 离线链路已完成。

## 2. 固定输入与结果

| 项目 | 固定值 |
| --- | ---: |
| `run_id` | `hist-v1-001` |
| seed | `20260920` |
| anchor | `2026-09-20T14:00:00`（`Asia/Shanghai`） |
| history days | 90 |
| 订单 | 100 |
| 订单明细 | 319 |
| 支付尝试 | 82 |
| `PAID` | 69 |
| `CANCELED` | 31 |
| ODS 业务日期分区 | 88 |
| pilot 分区 / `batch_id` | `2026-09-17` / `m3pilot_20260921_01` |
| 其余 87 分区 / `batch_id` | `m3hist_20260921_01` |
| `source_table` | `ecommerce_oltp_m2_acceptance.biz_order` |
| `gross_amount_cents` 合计 | 8,402,600 |
| `discount_amount_cents` 合计 | 30,000 |
| `payable_amount_cents` 合计 | 8,372,600 |

金额单位为人民币分。订单状态合计为 100，且 `gross_amount_cents - discount_amount_cents = payable_amount_cents`。

## 3. 证据来源与等级

- Runtime 事实来源是用户提供的 2026-09-22 Chat 终端输出；本仓库没有冒充保存原始 ECS 日志、实际 DataX Job、当次分区清单或当次 Spark SQL 文件。
- 当前仓库中的 `datax/scripts/`、`datax/templates/` 与 `archive/pilot-v1/offline/reference/ods_order.sql` 用于解释历史实现边界，但不冒充当次实际执行文件。
- `archive/pilot-v1/offline/reference/publish_order_ods_partitions.sh` 是对当时剩余 87 个 HDFS 分区移动步骤的发布重建稿。它要求外部提供经审计的 87 行日期清单；最终 88 个 ODS 分区是历史 Runtime 结果，不能由重建稿的文件存在反推。
- `archive/pilot-v1/offline/reference/check_ods_order_quality.sh` 固化九列 Spark 汇总基线及审计/日期规则；当前仅为仓库文件级 `implemented`，未在 ECS 执行。

## 4. 可复用入口

发布重建稿必须先准备一个恰好包含 87 个唯一合法日期的清单，再显式传入 HDFS 源根目录和目标根目录：

```bash
bash archive/pilot-v1/offline/reference/publish_order_ods_partitions.sh \
  <source_root> \
  <target_root> \
  <audited_87_date_manifest>
```

脚本在任何 `hdfs dfs -mv` 前完成清单、日期、重复值、pilot 分区排除、源目录和目标不存在检查；任一检查失败返回非零。它不执行 Hive 分区注册，也不包含实际 ECS 路径。

在目标 ECS 确认 Hive 表仍对应固定切片后，可执行只读质量入口：

```bash
bash archive/pilot-v1/offline/reference/check_ods_order_quality.sh
```

预期退出码为 `0`，并输出 `ODS_ORDER_QUALITY: PASS`。Spark 执行失败、结果不是唯一九列数值行或任一固定值不符时返回非零且不输出 PASS。执行输出由操作者保存在私有证据目录，去敏摘要评审后再进入仓库。

## 5. 未验证边界与回滚

- 新增的发布重建稿和质量脚本均未在 ECS 执行；本机只允许静态或模拟验证，不提升 Runtime 证据等级。
- 没有补造 Chat 中缺失的五个实际执行文件，也没有重跑历史 100 单或历史发布操作。
- 未验证硬删除、增量窗口、同日重跑、连续回补、空分区、迟到输入和发布中途失败后的自动恢复。
- 发布脚本只在开始前保证全量预检；若 HDFS 在移动过程中发生故障，脚本返回非零并保留已完成移动，不自动反向移动。恢复前必须人工核对源/目标目录。
- 回滚本次仓库变更只需删除两个新增脚本和本记录，并恢复同步修改的导航/状态文档；不得对 ECS 数据执行删除、覆盖或重放。
