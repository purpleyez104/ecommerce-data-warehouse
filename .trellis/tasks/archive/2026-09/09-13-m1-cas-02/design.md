# Technical Design

## Flow

1. Preflight：SSH、客户端、服务、端口、版本和配置路径。
2. Configuration：SQL 查询 `server_id`、`log_bin`、`binlog_format`、`binlog_row_image`。
3. Functional：建立 `m1_accept_<run-id>` Database/Table，记录起点并执行固定 I/U/D。
4. Binlog：核对 Position 和三类 Row Event。
5. Recovery：精确确认后重启、有限轮询、核对哨兵。
6. Cleanup：只删除本次临时 Database。

## Secret Contract

- 只接受 VM 本地绝对路径 Secret 文件。
- 检查 Owner 和权限不高于 `0600`。
- 不复制、不打印，不在证据中记录 Credential。

## Status

- 非中断检查通过、未授权重启：`PARTIAL`。
- 包含重启且全部通过：`PASS`。
- 任一必需断言或安全检查失败：`FAIL`。

## Rollback

恢复 MySQL 服务；清理严格前缀临时 Database；保留证据目录。

## Evidence Inbox Contract

- 路径：`.local-notes/m1-evidence/inbox/m1-cas-02-mysql/`。
- Work 会话只创建目录并可写入标记为 `local_static` 的脚本测试输出。
- 用户将 MySQL VM 完整 run 目录原样放入；不得只提供截图或摘录。
- 协调会话只读核对版本、Binlog、I/U/D、重启、Hash、时间和退出码。
