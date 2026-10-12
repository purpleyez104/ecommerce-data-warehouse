# DataX 执行脚本

Milestone 3 的 DataX 参数化执行入口放在本目录。当前包含 Job 生成、DataX 调用和 HDFS 输出检查的候选脚本，但它们不是 `hist-v1-001` 在 2026-09-22 的实际执行文件，也尚未完成本切片的 ECS Runtime 验收。

历史固定 100 单的限定运行事实、金额与分区基线见 [`biz_order` ODS 历史切片验收记录](../../docs/acceptance/biz_order_ods_acceptance.md)。一次性 HDFS 分区发布重建稿与固定基线检查现归档于 `archive/pilot-v1/offline/reference/`。两者均为 `implemented / not_run`，不得据此声称归档脚本已在 ECS 验证或属于 V2 正式入口。

后续正式入口仍必须显式接收业务日期或起止时间，并验证失败时返回非零状态。

仓库根目录运行 `bash tests/run_unit.sh` 可执行 V2 Generator 与 DataX Job Generator 的 Targeted Test。该测试只验证本地生成契约和失败路径，不证明 DataX、HDFS 或 Hive Runtime 已通过。
