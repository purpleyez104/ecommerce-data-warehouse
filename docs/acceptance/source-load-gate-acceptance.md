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

## 6. 60/30 Replay 隔离 Source 的 Day 60 验收

- 验收日期：2026-10-15。
- 环境：`hadoop201`，MySQL 8.0.46，隔离目标库 `ecommerce_oltp_replay_20260105_r2`；未触碰正式 `ecommerce_oltp`。
- 固定输入：`replay_formal_20260105.json`、Seed `20260105`、`generated_at=2026-10-15T10:00:00+08:00`；修复后的 Replay Bundle 输出目录标识为 `r3`，Dataset Version 仍为 `v2.3-replay-formal-20260105-r2`，Business Hash 为 `4abcd890a0e2372b652fe7dbee0208bbf5a0649089f60d7dfc6042acc5d3e327`。
- Bootstrap 21 表共提交 438,869 行。事务内与提交后独立 Shared Source Gate 均执行 45 条规则，全部 `violation_count=0`；`local_infile` 验收后恢复为 `OFF`。
- 远端去敏结果保留于 `/home/yee/replay-r3-bootstrap-20261015/`。该隔离库已非空，不得直接重跑、删除或重置；任何回滚、重置或 Day 61 写入均需单独 Database Operation 授权。

本节只证明 Seed `20260105` 的隔离 Source Day 60 切换点已完成真实 MySQL 装载与 Source Gate 验收；不证明 Day 61～90 回放、DataX/Hive ODS、正式 CDC、Kafka、Flink、Doris 或后续数仓分层已完成。

### 6.1 服务器只读复核

2026-10-15 在 `hadoop201` 对上述隔离库和去敏证据目录执行只读复核：21 张 `biz_*` 表的精确 `COUNT(*)` 全部匹配 Bootstrap `expected_result.json`，`MISMATCH_COUNT=0`；MySQL `local_infile=OFF`。`day60-load-r3.out` 与 `day60-postcommit-gate-r3.out` 分别保存事务内和提交后 45 条规则结果，全部 `violation_count=0` 且 `EXIT_STATUS=0`。服务器未发现 Day 61 Replay 成功结果，当前表计数仍精确等于 Day 60 基线。

本次只读复核没有执行 DDL、DML、Replay、清理或文件修改，不证明服务持续在线，也不授权 Day 61 或后续操作。公网地址、凭据和原始 Secret 不进入仓库。

## 7. 60/30 Replay 隔离 Source 的 Day 61 验收

- 验收日期：2026-10-15。
- 目标：`ecommerce_oltp_replay_20260105_r2`，未触碰正式 `ecommerce_oltp`。
- 输入：Dataset `v2.3-replay-formal-20260105-r2` 的 `day_61`，Business Hash `4abcd890a0e2372b652fe7dbee0208bbf5a0649089f60d7dfc6042acc5d3e327`，Package Manifest SHA-256 `482e02d46afd221bb842d9e4c46633cd1217fc9a5413d24746acbe61cdf56f16`。
- Executor 提交 19,456 个操作，`result.json` 记录 `database_contacted=true`、`committed_after_source_gate=true`。
- 事务内 Source Gate 通过；提交后独立 Source Gate 为 45/45 规则、`violation_count` 合计 0。
- 21 表精确计数全部匹配 Day 61 Expected Result，合计 453,809 行；订单状态为 21,783 `PAID`、8,970 `CANCELED`、315 `CREATED`。
- `local_infile=OFF`。去敏结果 SHA-256：`result.json` 为 `b4f0f513480a047f20539b4b6ae51275b3b19f033f9af4f9c4ef52e6dae02bbb`，提交后 Gate 输出为 `83562f6d146ae4509698a3e55b17a041da5b0f1d8c1a83492148d897306ed6db`。

该历史分节只证明 Day 61 Source Replay，不能单独证明 Day 62～90、DataX/Hive ODS、CDC、Kafka、Flink 或下游模型完成。后续 Day 61～90 Source Replay 已在本文第 9 节验收，ODS 证据见 [`formal-ods-smoke-acceptance.md`](formal-ods-smoke-acceptance.md)；相关隔离库临时权限已精确回收。

## 8. 60/30 Replay 隔离 Source 的 Day 62 验收

- 验收日期：2026-10-16。
- 目标：`ecommerce_oltp_replay_20260105_r2`，未触碰正式 `ecommerce_oltp`。
- 输入：Dataset `v2.3-replay-formal-20260105-r2` 的 `day_62`，Business Hash `4abcd890a0e2372b652fe7dbee0208bbf5a0649089f60d7dfc6042acc5d3e327`，Package Manifest SHA-256 `6406bde606d9dabd6923d134e7158a6d9a832eb8a1c258274cd87432b2bb8fb5`。
- 四个上传文件的服务器端 SHA-256 与固定清单一致；Planner Dry-run 记录 `status=planned`、`operation_count=22995`、`database_contacted=false`、`execution_authorized=false`。
- Executor 提交 22,995 个操作，`result.json` 记录 `database_contacted=true`、`committed_after_source_gate=true`。
- 事务内 Source Gate 通过；提交后独立 Source Gate 为 45/45 规则、`violation_count` 合计 0。
- 21 表精确计数全部匹配 Day 62 Expected Result，合计 471,317 行；订单状态为 22,686 `PAID`、9,373 `CANCELED`、326 `CREATED`。
- `local_infile=OFF`。去敏结果 SHA-256：`result.json` 为 `92e6aa78f140087fd4ed79c25f8a80e49850f5d80ad91d18bbd501cc0e4980dc`，提交后 Gate 输出为 `6d0628bd466be4ce39943b09e11331be3a62684ad422f1d0c07cbf5fcb573f42`。
- 运行目录已复制并验证到 `/data/ecommerce-replay-runtime-20261015/`；后续从数据盘路径继续。原 `/home/yee/ecommerce-replay-runtime-20261015/` 暂时保留。

该历史分节只证明 Day 62 Source Replay，不能单独证明 Day 63～90、DataX/Hive ODS、CDC、Kafka、Flink 或下游模型完成。后续 Day 63～90 Source Replay 已在本文第 9 节验收，ODS 证据见 [`formal-ods-smoke-acceptance.md`](formal-ods-smoke-acceptance.md)；相关隔离库临时权限已精确回收。

## 9. Batch Ledger、Range Executor 与 r6 完整验收

- 验收日期：2026-10-16。
- 新增 `replay_batch_ledger`：Daily 业务操作、Ledger 写入和 45-rule Source Gate 位于同一事务，`batch_id` 与 `day_number` 分别唯一；同一输入重跑返回 `already_applied`，冲突输入 fail-fast。
- Range Executor 在数据库写入前完成完整 Day 61～90 Preflight，逐日保存 Acceptance/Checkpoint；`--resume` 必须同时核对本地 Acceptance、目标 Ledger 和最新 Source Gate，不固定从 Day 61 重放。
- 隔离 Integration Test 目标为 `m1_accept_replay_ledger_20261016`：Day 72 首次执行写入 25,628 个操作和 Ledger；同日重跑未重复执行业务 SQL；强制 Day 73 Expected Result 错误后 MySQL 返回非零，Day 73 Ledger 为 0，业务表计数不变。
- r6 运行目录为 `/data/ecommerce-replay-runtime-20261016-r6/`，目标库为 `ecommerce_oltp_replay_20260105_r6`。Day 60 Bootstrap 共 438,869 行，事务内与提交后独立 Source Gate 均为 45/45、0 违规，`local_infile=OFF`。
- 2026-10-17 恢复连接后确认旧进程已被 signal 终止；Range State 当时已完成 Day 61～74。首次 `--resume` 发现数据库 Ledger 已提交 Day 75、但 Day 75 Acceptance 尚未落盘，旧恢复顺序因使用 Day 74 Expected Result 检查已推进到 Day 75 的数据库而 fail-fast，未产生新的业务写入。
- 修复后的 Resume 在“下一日目录存在但 Acceptance 缺失”时先只读核对下一日 Ledger；Day 75 返回 `already_applied`，随后执行 Day 75 提交后 Gate 并补齐 Acceptance，没有重复业务 SQL。新增 Targeted Test 覆盖该恢复路径，完整 Unit Test 共 66 项通过。
- Range Executor 最终完成 Day 61～90，`range-state.json` 为 `status=verified`、`next_day=null`；30 条 Ledger 覆盖 Day 61～90，操作总数 1,210,882；30/30 Acceptance 均为 `verified`、`violation_count=0`。
- Day 90 完成后使用新连接执行最终独立 Source Gate，45/45 规则、0 违规；`local_infile=OFF`。`ecommerce_user@localhost` 对 `ecommerce_oltp_replay_20260105_r6` 的 `SELECT / INSERT / UPDATE / CREATE TEMPORARY TABLES` 临时权限已精确回收，正式库以及旧 r5/r4/r2 权限未修改。
- r6 Runtime Bundle 使用 Dataset `v2.3-replay-formal-20260105-r2`、Business Hash `ecea32d620bfbf44671ff2c1e1ff765fe4638f330f621229b9dd8f543578deb5`、Replay Manifest SHA-256 `5e09633896125c487a9a2d55632507621eb058679f4e30bc83c313c42e46533c`。2026-10-17 当前 worktree 使用相同 Config、Seed 和 `generated_at` 重生成 146 个文件、1,210,882 个操作，并复现相同 Business Hash、Replay Manifest SHA-256 和 30 个 Package Manifest。

本节证明当前正式 Business Replay Baseline 的 Day 60～90 隔离 MySQL Runtime、批量断点恢复、Ledger、逐日 Acceptance、最终 Source Gate、确定性重生成和权限回收。它不证明 DataX/Hive ODS、CDC、Kafka、Flink、Doris、Behavior Runtime 或下游模型完成；任何数据库重置、删除或重新回放仍需新的 Database Operation 授权。
