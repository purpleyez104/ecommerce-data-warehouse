# DataX 执行脚本

Milestone 3 的 DataX 参数化执行入口放在本目录。`generate_job.py` 负责单表 Job；`run_ods_batch.py` 负责 21 表批次计划、Manifest 绑定、状态机、可注入执行器和 Dry-run。两者状态均为 `implemented / not_run`。`run_datax.sh` 与 `validate_datax_output.sh` 仍是早期候选入口，不属于正式批次 Runner。

历史固定 100 单的限定运行事实、金额与分区基线见 [`biz_order` ODS 历史切片验收记录](../../docs/acceptance/biz_order_ods_acceptance.md)。一次性 HDFS 分区发布重建稿与固定基线检查现归档于 `archive/pilot-v1/offline/reference/`。归档脚本均为 `implemented / not_run`，不得据此声称其已在 ECS 验证或属于当前正式入口。

Job Generator 必须显式接收业务日期、批次和抽取时间；`mutable_incremental` 与 `append_only` 的 Incremental 必须额外接收严格本地时间起止窗口，`full_snapshot` 禁止传窗口。Generator 固定写入 `<target_table>/batch_id=<batch_id>` staging；业务 `dt` 来自每行 `business_date`，不使用调度日覆盖全部记录。

Dry-run Job 只保存 `${MYSQL_PASSWORD}` 占位符，文件和状态计划使用私有权限。Runner 不允许覆盖同名批次，任何 Job、Manifest 或 Validation 失败均返回非零并禁止进入 `publish_ready`；默认 Dry-run 即使到达 `publish_ready` 也保持 `publish_allowed=false`。真实执行器、Job 临时 Secret 注入、Source 操作包应用、staging 清理和 ODS Gate 仍须在目标环境验收。

仓库根目录运行 `bash tests/run_unit.sh` 可执行 Generator、DataX Job Generator 和 MySQL Source Load/Gate 的 Targeted Tests。测试只验证本地生成契约、静态协议和失败路径，不证明 DataX、HDFS 或 Hive Runtime 已通过。
