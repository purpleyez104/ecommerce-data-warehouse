# DataX

当前正式批量 ODS 的第一批本地实现包括：21 表抽取策略配置、通用 DataX Job Generator、动态源字段与 HDFS Writer 类型映射，以及 Bootstrap / Incremental 参数校验。状态为 `implemented / not_run`，不表示 DataX、HDFS 或 Hive 已运行通过。

`config/ods_tables.json` 为 21 表 source/target、抽取策略、主键、增量水位、业务时间、分区和质量规则 Contract；源字段顺序复用 Business Generator 的 `TABLE_COLUMNS`，DataX 类型从正式 MySQL DDL 推导。策略分为：

- `mutable_incremental`：Bootstrap 全量，Incremental 按 `updated_at` 半开窗口抽取。
- `append_only`：Bootstrap 全量，Incremental 按 `recorded_at` 或等价记录水位抽取。
- `full_snapshot`：用于没有可靠更新水位的 `biz_identity_mapping`；Bootstrap 和日批均全量抽取。

Generator 必须显式接收 `business_date`、`batch_id`、`extract_time`；水位增量策略还必须接收严格的本地时间半开区间 `[window_start, window_end)`。`business_date` 对事实和事件按行从业务时间计算，对全量快照取显式快照日。输出只进入批次隔离路径：

```text
${ODS_STAGE_ROOT}/<target_table>/batch_id=<batch_id>
```

每行保留全部源字段，并追加 `business_date`、`extract_time`、`batch_id`、`source_table` 四个审计字段。一个 batch staging 可以包含多个 `business_date`；后续 Spark Publish 负责识别并原子重建对应 `dt`，当前尚未实现。文件格式固定为 ORC + Snappy，`writeMode=nonConflict`。Stage Runner、Spark Validation、Publish、Hive DDL/分区注册和 ODS Gate 尚未实现或运行。

运行前需将 `config/datax.env.example` 复制为已被 Git 忽略的 `config/datax.env`，再填入私有值。生成的 Job 含运行时数据库密码，只能独占创建在 `${PROJECT_HOME}/runtime/datax/jobs` 或其子目录；同名文件、路径逃逸和符号链接逃逸会被拒绝。POSIX 环境下权限固定为 `0600`，Job 不得提交或复制到证据文件。HDFS 输出路径由 Contract 和 `ODS_STAGE_ROOT` 生成，不提供任意 `--output-path`。

用户提供的 2026-09-22 Chat 记录已证明 `biz_order` 固定 100 单切片完成 MySQL → DataX → HDFS ORC → Hive ODS 发布和 Spark 汇总核验。限定结论、固定基线与未验证边界见 [`biz_order` ODS 历史切片验收记录](../docs/acceptance/biz_order_ods_acceptance.md)。M3 仍为 `in_progress`，不代表 21 表、增量、重跑/回补或后续离线分层通过。

2026-10-13 的本地 Targeted Tests 覆盖 21 表 Contract、三类抽取策略、逐行业务日期、Incremental 半开窗口、审计字段、ORC + Snappy、batch staging、严格时间、重复配置键、路径逃逸、私有权限和重复批次拒绝；这些静态结果不证明 DataX/HDFS/Hive Runtime。历史 `hist-v1-001` 事实也不得外推到正式 21 表。
