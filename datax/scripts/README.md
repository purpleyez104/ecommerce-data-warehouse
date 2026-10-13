# DataX 执行脚本

Milestone 3 的 DataX 参数化执行入口放在本目录。`generate_job.py` 已实现 21 表配置驱动的 Bootstrap / Incremental Job 生成、逐行业务日期和参数失败路径，状态为 `implemented / not_run`。`run_datax.sh` 与 `validate_datax_output.sh` 仍是早期候选入口，不等于正式 Stage Runner、Spark Validation、Publish 或 ODS Gate。

历史固定 100 单的限定运行事实、金额与分区基线见 [`biz_order` ODS 历史切片验收记录](../../docs/acceptance/biz_order_ods_acceptance.md)。一次性 HDFS 分区发布重建稿与固定基线检查现归档于 `archive/pilot-v1/offline/reference/`。归档脚本均为 `implemented / not_run`，不得据此声称其已在 ECS 验证或属于当前正式入口。

Job Generator 必须显式接收业务日期、批次和抽取时间；`mutable_incremental` 与 `append_only` 的 Incremental 必须额外接收严格本地时间起止窗口，`full_snapshot` 禁止传窗口。Generator 固定写入 `<target_table>/batch_id=<batch_id>` staging；业务 `dt` 来自每行 `business_date`，不使用调度日覆盖全部记录。

私有 Job 含运行时数据库密码，只允许独占创建在 `${PROJECT_HOME}/runtime/datax/jobs` 或其子目录，不能覆盖同名批次；HDFS 输出路径不能由命令行任意覆盖。正式 Stage Runner 后续还必须负责执行失败非零、Job 清理、staging 校验、Spark Publish 和下游阻断。

仓库根目录运行 `bash tests/run_unit.sh` 可执行 Generator、DataX Job Generator 和 MySQL Source Load/Gate 的 Targeted Tests。测试只验证本地生成契约、静态协议和失败路径，不证明 DataX、HDFS 或 Hive Runtime 已通过。
