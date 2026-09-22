# MySQL 初始化与验证 SQL

本目录用于当前 V2 的固定 Seed、初始化辅助和业务验证 SQL。`acceptance.sql` 是带 `<RUN_ID>` 占位符的只读批次验收模板，由 `tests/scripts/check_batch_mysql.sh` 调用。

当前固定 Seed 仍为 `planned`。不得在本目录加入自动 `DROP`、`TRUNCATE` 或绕过外键的清理脚本；任何写入型 SQL 都必须说明固定输入、预期结果、失败行为和回滚方式。
