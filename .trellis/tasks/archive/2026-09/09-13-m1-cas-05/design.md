# Technical Design

## Flow

1. Preflight：版本、配置、Hadoop Profile、YARN 和 Hive Catalog。
2. Success Path：提交固定 Spark SQL Application，读临时源、聚合并写 ORC+Snappy。
3. Evidence：提取 Application ID，轮询 Final-State，保存 Diagnostics 和聚合日志。
4. Failure Path：提交引用确定不存在输入的 Application，断言客户端非零和失败终态。
5. Cleanup：删除本次临时 Hive/HDFS 对象。

## Runtime Boundary

- 使用 `--master yarn`，不允许 Standalone。
- 不重启 Spark；Spark 作为批任务由 YARN 管理。
- 成功和失败 Application 使用不同名称并含当前 run-id。

## Rollback

终止仍在运行且名称匹配当前 run-id 的 Application；清理严格前缀临时对象。

## Evidence Inbox Contract

- 路径：`.local-notes/m1-evidence/inbox/m1-cas-05-spark-yarn/`。
- Work 会话只创建目录并可写入标记为 `local_static` 的脚本测试输出。
- 用户将 Spark VM 完整 run 目录原样放入。
- 协调会话只读核对 Application ID、Final-State、日志、ORC+Snappy、固定结果、失败路径、Hash 和退出码。
