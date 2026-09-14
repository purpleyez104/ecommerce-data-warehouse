# Technical Design

## Flow

1. Preflight：两 Worker 的 Canonical Path、版本、Python/JDK 和 Plugin。
2. Input：建立严格前缀 MySQL 临时 Database/Table，写固定三行。
3. Success：在两 Worker 生成各自 `0600` Job JSON，写入不同全新 HDFS 路径。
4. Verify：通过 Hive/Spark 核对行、值、ORC 和 Snappy。
5. Failure：运行不存在源表的固定 Job，断言非零并去敏日志。
6. Cleanup：删除本次 Job JSON、MySQL/Hive/HDFS 临时对象。

## Secret Boundary

- 从 VM 本地受保护文件读取，不进入仓库、证据或命令描述。
- Job JSON 仅存在于当前私有临时目录，Trap 前再次验证路径和前缀。

## Compatibility Boundary

`/data/module/datax` 是 Canonical Path；`datax-current` 只记录是否存在。测试 `STRING` 映射只标记为 Smoke Workaround。

## Rollback

停止当前 run-id Job；删除严格前缀临时对象和私有 JSON；保留去敏证据。

## Evidence Inbox Contract

- 路径：`.local-notes/m1-evidence/inbox/m1-cas-06-datax/`。
- Work 会话只创建目录并可写入标记为 `local_static` 的脚本测试输出。
- 用户将 DataX VM 完整 run 目录原样放入。
- 协调会话只读核对双 Worker、Plugin、成功/失败 Job、Hive/Spark 结果、ORC+Snappy、Hash 和退出码。
