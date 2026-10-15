# DataX

当前正式批量 ODS 的本地实现包括：21 表抽取策略配置、通用 DataX Job Generator、Stage Runner、Spark Validation / Publish SQL Renderer，以及 Bootstrap / Incremental 参数校验。状态为 `implemented / not_run`，不表示 DataX、HDFS 或 Hive 已运行通过。

`config/ods_tables.json` 为 21 表 source/target、抽取策略、主键、增量水位、业务时间、分区和质量规则 Contract；源字段顺序复用 Business Generator 的 `TABLE_COLUMNS`，DataX 类型从正式 MySQL DDL 推导。策略分为：

- `mutable_incremental`：Bootstrap 全量，Incremental 按 `updated_at` 半开窗口抽取。
- `append_only`：Bootstrap 全量，Incremental 按 `recorded_at` 或等价记录水位抽取。
- `full_snapshot`：用于没有可靠更新水位的 `biz_identity_mapping`；Bootstrap 和日批均全量抽取。

Generator 必须显式接收 `business_date`、`batch_id`、`extract_time`；水位增量策略还必须接收严格的本地时间半开区间 `[window_start, window_end)`。`business_date` 对事实和事件按行从业务时间计算，对全量快照取显式快照日。输出只进入批次隔离路径：

```text
${ODS_STAGE_ROOT}/<target_table>/batch_id=<batch_id>
```

每行保留全部源字段，并追加 `business_date`、`extract_time`、`batch_id`、`source_table` 四个审计字段。一个 batch staging 可以包含多个 `business_date`；Spark Renderer 会生成必需字段 Projection、PK、总行数、逐业务日期行数、业务日期集合和审计字段 Validation SQL，以及受影响 `dt` 的 Publish / 分区注册计划。增量发布先把“目标分区内未命中本批 PK 的旧行 + 本批最新行”物化为临时 Cache，再覆盖目标分区，避免迟到更新删除同分区其他记录，也避免同一语句直接读写目标路径。文件格式固定为 ORC + Snappy，`writeMode=nonConflict`。

本地 Runner 状态机推进到 `planned → staged → validated → publish_ready`，但默认 Dry-run 的 `publish_allowed=false`，只表示计划生成完毕；只有后续注入真实执行器并成功完成 Stage/Validation/Publish Preparation 才能授权发布。真实 DataX/Spark/HDFS/Hive 执行和 `published` 状态仍为 `not_run`。Hive 覆盖的原子边界是单个表分区；批次中途失败必须阻断下游，并通过同一 Contract 重跑全部受影响分区，不能声称 21 表跨分区事务原子性。

单表 Runtime Job 仍使用被 Git 忽略的私有 `config/datax.env`。新 `run_ods_batch.py --dry-run` 只生成带 `${MYSQL_PASSWORD}` 占位符的私有审计 Job，不读取或落盘 Secret；真实执行器必须在运行时注入凭据。相同输出目录会 fail-fast，Validation、Manifest 或执行器失败会把状态写为 `failed` 并保持 `publish_allowed=false`。

```powershell
python datax/scripts/run_ods_batch.py --dry-run `
  --batch-contract output/replay-smoke/daily/day_61/ods_batch_contract.json `
  --output-dir runtime/ods/day_61 `
  --project-home . `
  --stage-root /warehouse/ecommerce/ods-stage
```

预期成功退出状态为 `0`，结果位于 `runtime/ods/day_61/`；失败返回非零并在该目录保留 `state.json`。运行 Daily Contract 前，必须先把对应 `operations.jsonl` 按序应用到隔离 Source；当前 P0 只生成操作包，尚未实现或运行 MySQL Replay Executor，不能直接对第 90 日终态库执行第 61～90 日抽取。本地回滚只移除本次隔离的 Replay/Runner Output，不修改正式 Source Bundle。真实环境回滚必须隔离失败 Staging、禁止 Publish，并在另行授权下按 Batch/Partition 边界处理，不能覆盖或清理已验收数据。

用户提供的 2026-09-22 Chat 记录已证明 `biz_order` 固定 100 单切片完成 MySQL → DataX → HDFS ORC → Hive ODS 发布和 Spark 汇总核验。限定结论、固定基线与未验证边界见 [`biz_order` ODS 历史切片验收记录](../docs/acceptance/biz_order_ods_acceptance.md)。M3 仍为 `in_progress`，不代表 21 表、增量、重跑/回补或后续离线分层通过。

2026-10-14 的本地 Targeted Tests 进一步覆盖 21 表 Dry-run、状态机、受影响分区稳定性、Manifest Hash、重复批次、Stage/Validation 失败传播和 Publish 阻断；这些结果仍不证明 DataX/HDFS/Hive Runtime。历史 `hist-v1-001` 事实也不得外推到正式 21 表。
