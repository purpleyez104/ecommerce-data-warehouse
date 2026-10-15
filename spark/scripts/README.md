# Spark 提交脚本

`render_ods_batch_sql.py` 根据 21 表 ODS Contract 与版本化 Batch Contract 生成 Validation SQL、Publish SQL 和受影响分区计划。Validation 覆盖必需字段 Projection、PK 非空/唯一、总行数、逐业务日期行数、业务日期集合和审计字段；Bootstrap 直接覆盖完整分区，Incremental 先把目标分区未命中本批 PK 的行与本批行物化到临时 Cache，再覆盖该分区并立即 `UNCACHE`。SQL 只生成、不在本地执行；字段类型和额外字段仍须由真实 Spark Executor 读取 ORC Schema 后验证。

当前状态为 `implemented / not_run`。该入口只属于 Milestone 3 ODS 发布准备，不表示 Spark Runtime、Hive 分区发布、ODS Gate 或 Milestone 4-7 转换与性能实验已经完成。
