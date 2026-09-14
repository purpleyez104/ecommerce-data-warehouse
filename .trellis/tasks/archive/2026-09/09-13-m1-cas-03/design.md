# Technical Design

## Flow

1. Preflight：服务、端口、Beeline、版本、配置和 PID。
2. Java Evidence：解析服务进程 executable，并从 YARN 日志采集 Container Java。
3. Functional：创建严格前缀 Database/Table，写入固定三行并触发 YARN MapReduce。
4. Storage：核对查询值、HDFS 文件、ORC Footer 与 Snappy。
5. Recovery：确认后调用受限的现有 `<stop-command> hive` 和 `<start-command> hive`。
6. Cleanup：删除本次临时 Database/HDFS Path。

## Lifecycle Command Boundary

- 默认通过 `command -v` 发现现有脚本。
- 可接受无额外参数的绝对路径；固定追加 `hive`。
- 找不到时恢复阶段失败，不生成替代启动逻辑。

## Status

未授权重启最多 `PARTIAL`；功能和恢复全部通过才为 `PASS`。

## Rollback

使用同一现有生命周期脚本恢复 Hive；只清理本次临时对象。

## Evidence Inbox Contract

- 路径：`.local-notes/m1-evidence/inbox/m1-cas-03-hive/`。
- Work 会话只创建目录并可写入标记为 `local_static` 的脚本测试输出。
- 用户将 Hive VM 完整 run 目录原样放入。
- 协调会话只读核对 Metastore/HS2、ORC+Snappy、YARN、实际 Java、恢复、Hash 和退出码。
