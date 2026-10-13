# 正式业务源装载与 Shared Source Gate 验收

## 1. 验收结论

- 验收日期：2026-10-12。
- 环境：`hadoop201`，MySQL 8.0.46，目标库 `ecommerce_oltp`。
- 结论：`VERIFIED`。21 张 `biz_*` 表已部署，正式 Business bundle 已通过单 MySQL session 的 `LOAD DATA LOCAL INFILE` 装载并提交。
- 事务内 Shared Source Gate 与提交后独立 Source Gate 均通过 45 条规则，所有 `violation_count=0`。
- 提交后逐表精确 `COUNT(*)` 合计 1,328,502 行，与 Dataset Manifest 完全一致。
- MySQL 全局变量 `local_infile` 仅在装载期间临时启用，验收后已恢复为 `OFF`。
- 在非空目标库重新调用装载入口实测返回 `1`，命中 `__source_load_target_not_empty__` guard；随后总行数仍为 1,328,502，证明第一条 `LOAD DATA` 前已阻断。

本验收不证明 DataX/Hive ODS、正式 21 表 CDC、Kafka Raw、Flink Domain Application、Doris 服务表或后续数仓分层已经完成。

## 2. 固定输入

| 项目 | 值 |
| --- | --- |
| 配置 | `mock/generator/business_generator/config/formal.json` |
| Seed | `20260928` |
| `generated_at` | `2026-09-28T10:00:00+08:00` |
| 业务时间范围 | 2025-12-01 00:00:00 ～ 2026-02-28 23:59:59.999，`Asia/Shanghai` |
| Dataset Manifest SHA-256 | `9f40c67fe089824232f17c10531f872b44676aa60ce999de7b3102c789444639` |
| Entity Manifest SHA-256 | `bbe92740d74dd6dd4c71b7d72e43bde1d37c8d67f59486bceea522492a6fec7a` |
| 服务器生成耗时 | 213 秒；仅为本次输入和环境事实，不作为性能基线 |

正式生成前发现配置中的 `biz_refund_event` 和 `biz_coupon_event` 声明数量与状态机派生数量不一致。修复后 Generator 对所有配置表数量实行 fail-fast，不再静默覆盖；重新生成的 21 张 CSV 与首次生成逐文件 SHA-256 一致。

## 3. 精确行数

| 表 | 行数 | 表 | 行数 |
| --- | ---: | --- | ---: |
| `biz_user` | 40,000 | `biz_visitor` | 80,000 |
| `biz_identity_mapping` | 24,000 | `biz_category` | 60 |
| `biz_spu` | 1,200 | `biz_sku` | 4,000 |
| `biz_product_change_event` | 2,000 | `biz_cart` | 50,000 |
| `biz_cart_item` | 110,000 | `biz_cart_merge_record` | 8,000 |
| `biz_coupon_template` | 30 | `biz_coupon` | 60,000 |
| `biz_order` | 100,000 | `biz_order_item` | 285,000 |
| `biz_order_status_event` | 199,000 | `biz_payment_attempt` | 95,300 |
| `biz_payment_event` | 95,300 | `biz_refund_request` | 9,000 |
| `biz_refund_transaction` | 9,540 | `biz_refund_event` | 26,370 |
| `biz_coupon_event` | 129,702 | **合计** | **1,328,502** |

## 4. 验收范围

Shared Source Gate 覆盖：21 表 Manifest 行数、主键与业务键唯一性、物理和软引用完整性、购物车合并、订单头明细金额、支付唯一成功与金额、15 分钟支付窗口、退款申请/资金/明细守恒、优惠券与订单双向关系、状态事件链连续性、最终状态与时间顺序，以及订单状态分布。

本地回归入口：

```bash
E:/Software/Git/bin/bash.exe -c 'export PATH=/usr/bin:/mingw64/bin:$PATH; bash tests/run_unit.sh'
```

本次修复后共执行 24 项测试，全部通过。服务器侧关键入口为：

```bash
bash mysql/scripts/load_csv_bundle.sh --bundle /absolute/path/to/formal-current
bash mysql/scripts/run_source_gate.sh --bundle /absolute/path/to/formal-current
```

密码只从服务器已有的权限为 `0600` 的 Secret 文件读取，并写入脚本创建的 `0600` 临时 MySQL defaults 文件；未进入 argv、仓库、SQL、Manifest 或验收输出。

## 5. 结果位置与重跑边界

- 服务器 runtime：`/home/yee/ecommerce-source-runtime-20261012/`。
- 去敏执行证据：该目录下 `evidence/`；原始输出不提交 Git。
- 目标 21 表现已非空，装载入口的 fail-fast 重跑保护已在真实目标库验证；不能直接重跑。
- 回滚或重置需要新的 Database Operation 授权，并必须先明确备份、精确对象和恢复方法。
- 下一步可进入批量 ODS 实现和 Formal CDC Contract/初始化设计；两条路径仍需各自验收，不能由本验收自动提升状态。
