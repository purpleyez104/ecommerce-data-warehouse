# DataX

`jobs/` 用于存放经验证的 DataX 任务配置，`scripts/` 用于参数化执行入口。当前 `scripts/`、`templates/` 和 `config/datax.env.example` 已有候选实现，但 2026-09-22 `hist-v1-001` 的实际 DataX Job 与当次运行文件未进入仓库；现有候选文件不能冒充历史执行入口。运行前需在本地复制为 `config/datax.env` 并填入私有值，该文件已被 Git 忽略。

用户提供的 2026-09-22 Chat 记录已证明 `biz_order` 固定 100 单切片完成 MySQL → DataX → HDFS ORC → Hive ODS 发布和 Spark 汇总核验。限定结论、固定基线与未验证边界见 [`biz_order` ODS 历史切片验收记录](../docs/acceptance/biz_order_ods_acceptance.md)。M3 仍为 `in_progress`，不代表 21 表、增量、重跑/回补或后续离线分层通过。

新增任务前需确认 DataX 版本、MySQLReader、目标存储写入器、DECIMAL 类型、分区策略、失败重试和幂等重跑行为；验证结论应同步记录到项目文档。
