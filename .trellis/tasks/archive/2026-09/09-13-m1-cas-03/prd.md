# M1-CAS-03 Hive 验收脚本

## Task Identity

- Task ID：`M1-CAS-03`
- Title：Hive 3.1.3、ORC/Snappy、YARN 与恢复验收脚本

## Goal

验证 Hive Metastore、HiveServer2、Beeline、ORC+Snappy、YARN MapReduce、实际 Java 和受控恢复。

## Scope

- 版本、9083/10000/10002、进程、配置路径、服务 Java executable。
- 临时 Hive Database/Table、固定三行、YARN MapReduce、查询与 ORC 压缩证据。
- YARN Container Java。
- 显式授权后的 Hive 组件级重启与哨兵恢复。

## Out of Scope

- 不选择或切换 Hive Runtime Java。
- 不创建正式 ODS 表，不修改 Hive/Hadoop 配置。

## Inputs / Dependencies

- `M1-CAS-01` 完成并冻结。
- HDFS/YARN/MySQL/Hive 已运行。
- 现有 `start-cluster.sh`、`stop-cluster.sh` 或其绝对路径。

## Files / Modules

- `scripts/m1/verify-hive.sh`
- Evidence Inbox：`.local-notes/m1-evidence/inbox/m1-cas-03-hive/`

## Acceptance Criteria

- [ ] Metastore、HS2、Beeline 和端口均有运行证据。
- [ ] 固定数据结果正确，文件确认为 ORC+Snappy。
- [ ] YARN Application、聚合日志与 Container Java 可追溯。
- [ ] 记录服务端实际 Java，不擅自修复。
- [ ] 只有 `EXISTING_HIVE_SERVICES` 才允许重启；恢复后哨兵仍存在。
- [ ] 仅清理本次临时 Hive/HDFS 对象。
- [ ] Work 会话首先创建专属 Evidence Inbox；VM 原始 run 目录由用户原样放入。
- [ ] 在用户回传并经协调会话审查前，Hive Runtime 保持 `not_run`/未 `verified`。

## Verification

- `bash -n scripts/m1/verify-hive.sh`
- `M1-CAS-07` 静态 Guard。
- VM Beeline、ORC、YARN、Java 和受控恢复证据。

## Risk

- 生命周期脚本路径未固化；实际 Java 可能与预期不同；重启会短暂中断 Hive 查询。

## 是否适合并行

- 实现可在 `M1-CAS-01` 后并行；VM 验收必须在 MySQL 后执行。

## 是否需要 Worktree

- 当前单 Agent 不需要；若独立 Implementer 并行写入则需要。

## User Decision

- VM 重启需显式授权；Runtime Java 最终选择待证据返回后决定，不阻塞脚本实现。

## Retirement Result

- Disposition：`superseded`。
- Implementation Result：`not_implemented_not_required`；未创建 `verify-hive.sh`，不得将行政归档解释为脚本实现完成。
- Reason：`DR-026` 已确认 Hive 3.1.3 核心能力通过，`DR-027` 将重复的详细取证附件降为 Optional Evidence；继续实现本 Task 不再是 M1 门禁。
- Remaining Follow-up：Hive 正式 ODS 行为仍由 Milestone 3 验收，不由本 Task 替代。
