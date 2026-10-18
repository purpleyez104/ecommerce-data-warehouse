# DataX

当前正式批量 ODS 实现包括：21 表抽取策略配置、正式 Snapshot Contract Generator、通用 DataX Job Generator、Stage Runner、Spark Validation / Publish SQL Renderer，以及 Bootstrap / Incremental 参数校验。2026-10-17 已完成正式 `ecommerce_oltp` 1,328,502 行 → `ecommerce_ods` 21 表 Bootstrap 与 1,476 项独立 ODS Gate；2026-10-18 又在隔离环境完成 Day 60 Bootstrap、Day 61～90 连续增量、29/29 自动 Checkpoint 和 1,498 项最终 ODS Gate。Milestone 3 已完成，详见 [Day 60～90 ODS Stage Gate 验收](../docs/acceptance/formal-ods-smoke-acceptance.md)。

`config/ods_tables.json` 为 21 表 source/target、抽取策略、主键、增量水位、业务时间、分区和质量规则 Contract；源字段顺序复用 Business Generator 的 `TABLE_COLUMNS`，DataX 类型从正式 MySQL DDL 推导。策略分为：

- `mutable_incremental`：Bootstrap 全量，Incremental 按 `updated_at` 半开窗口抽取。
- `append_only`：Bootstrap 全量，Incremental 按 `recorded_at` 或等价记录水位抽取。
- `full_snapshot`：用于没有可靠更新水位的 `biz_identity_mapping`；Bootstrap 和日批均全量抽取。

`scripts/generate_bootstrap_contract.py` 会验证正式 Bundle 的 Manifest、文件大小、SHA-256、字段顺序和行数，并按每表业务时间生成 Snapshot Bootstrap 分区期望。`jobs/formal-bootstrap-20260228-r1/` 保存本次正式批次的 21 个占位符 job 与 SHA-256 Manifest；Secret 只在私有 Runtime 子进程中临时注入。

Generator 必须显式接收 `business_date`、`batch_id`、`extract_time`；水位增量策略还必须接收严格的本地时间半开区间 `[window_start, window_end)`。`business_date` 对事实和事件按行从业务时间计算，对全量快照取显式快照日。输出只进入批次隔离路径：

```text
${ODS_STAGE_ROOT}/<target_table>/batch_id=<batch_id>
```

每行保留全部源字段，并追加 `business_date`、`extract_time`、`batch_id`、`source_table` 四个审计字段。一个 batch staging 可以包含多个 `business_date`；Spark Renderer 会生成必需字段 Projection、PK、总行数、逐业务日期行数、业务日期集合和审计字段 Validation SQL，以及受影响 `dt` 的 Publish / 分区注册计划。增量发布先把“目标分区内未命中本批 PK 的旧行 + 本批最新行”写入批次隔离的 `_merge` ORC，再从独立物理边界覆盖目标分区，避免迟到更新删除同分区其他记录和 Spark 同表读写限制。文件格式固定为 ORC + Snappy，`writeMode=nonConflict`。

Dry-run 状态机推进到 `planned → staged → validated → publish_ready` 且 `publish_allowed=false`；真实执行器成功时进入 `published`。Day 61 实测表明 Spark 不能在同一 statement 中读取并 overwrite 同一 Hive 表，因此增量发布先写批次隔离 `_merge` ORC，再从独立物理边界覆盖目标分区。Hive 覆盖的原子边界是单个表分区；批次中途失败必须阻断下游，并通过同一 Contract 重跑全部受影响分区，不能声称 21 表跨分区事务原子性。

已完成 staging 的失败批次可以使用 `--execute --resume-from <prior-output>` 恢复。Runner 会绑定先前的 batch、dataset、窗口、目标库和完整 partition plan，跳过 DataX，但仍重新执行 Spark Validation 与 Publish；该路径不需要 `--env-file`。未完成 staging 或 Contract 不一致的目录会被拒绝。

单表 Runtime Job 仍使用被 Git 忽略的私有 `config/datax.env`。新 `run_ods_batch.py --dry-run` 只生成带 `${MYSQL_PASSWORD}` 占位符的私有审计 Job，不读取或落盘 Secret；真实执行器必须在运行时注入凭据。相同输出目录会 fail-fast，Validation、Manifest 或执行器失败会把状态写为 `failed` 并保持 `publish_allowed=false`。

```powershell
python datax/scripts/run_ods_batch.py --dry-run `
  --batch-contract output/replay-smoke/daily/day_61/ods_batch_contract.json `
  --output-dir runtime/ods/day_61 `
  --project-home . `
  --stage-root /warehouse/ecommerce/ods-stage
```

预期成功退出状态为 `0`，失败返回非零并在运行目录保留 `state.json`。运行 Daily Contract 前，必须先把对应 `operations.jsonl` 按序应用到隔离 Source 并通过 Source Gate。Day 60～90 已按日期顺序完成；恢复路径使用已提交 Ledger/Checkpoint 定位下一日，不得从 Day 61 盲目重放，也不得对 Day 90 终态库补做历史日抽取。本地回滚只移除本次隔离的 Replay/Runner Output，不修改正式 Source Bundle。真实环境回滚必须隔离失败 Staging、禁止 Publish，并在另行授权下按 Batch/Partition 边界处理，不能覆盖或清理已验收数据。

用户提供的 2026-09-22 Chat 记录已证明 `biz_order` 固定 100 单切片完成 MySQL → DataX → HDFS ORC → Hive ODS 发布和 Spark 汇总核验。限定结论、固定基线与未验证边界见 [`biz_order` ODS 历史切片验收记录](../docs/acceptance/biz_order_ods_acceptance.md)。该历史切片不是 M3 完成依据；M3 的 21 表、增量、恢复和连续回补结论以当前 Stage Gate 记录为准，且仍不代表后续离线分层通过。

2026-10-14 的本地 Targeted Tests 进一步覆盖 21 表 Dry-run、状态机、受影响分区稳定性、Manifest Hash、重复批次、Stage/Validation 失败传播和 Publish 阻断；这些结果仍不证明 DataX/HDFS/Hive Runtime。历史 `hist-v1-001` 事实也不得外推到正式 21 表。
