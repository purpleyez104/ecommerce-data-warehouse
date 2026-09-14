# M1-CAS-05 Spark on YARN 验收脚本

## Task Identity

- Task ID：`M1-CAS-05`
- Title：Spark 3.5.9 on YARN 成功与失败路径验收脚本

## Goal

验证 Spark 3.5.9 on YARN、Hive Catalog、ORC+Snappy 读写、固定结果和预期失败终态。

## Scope

- Spark 版本、提交入口、关键配置路径、Hadoop Profile 和 YARN 可用性。
- 固定 Spark SQL on YARN 成功 Application。
- Hive 临时对象、ORC+Snappy 结果、Application ID、Final-State 和聚合日志。
- 固定预期失败 Application 与非零退出。

## Out of Scope

- 不运行 Spark Standalone。
- 不做性能实验、不宣称性能收益、不重启服务。

## Inputs / Dependencies

- `M1-CAS-01` 完成并冻结。
- HDFS、YARN、Hive 可用，Spark 3.5.9 已部署。

## Files / Modules

- `scripts/m1/verify-spark-yarn.sh`
- Evidence Inbox：`.local-notes/m1-evidence/inbox/m1-cas-05-spark-yarn/`

## Acceptance Criteria

- [ ] 成功作业在 YARN 完成，固定聚合结果正确。
- [ ] 输出确认为 ORC+Snappy，Hive Catalog 可读取。
- [ ] Application ID、Final-State、Diagnostics 和聚合日志可追溯。
- [ ] 预期失败作业客户端非零且 YARN 终态可解释。
- [ ] 只清理本次临时 Hive/HDFS 对象。
- [ ] Work 会话首先创建专属 Evidence Inbox；VM 原始 run 目录由用户原样放入。
- [ ] 在用户回传并经协调会话审查前，Spark Runtime 保持 `not_run`/未 `verified`。

## Verification

- `bash -n scripts/m1/verify-spark-yarn.sh`
- `M1-CAS-07` 静态 Contract。
- VM 成功/失败 Application 与聚合日志。

## Risk

- YARN 日志聚合可能延迟；必须有限重试和明确超时，不能无限等待。

## 是否适合并行

- 实现可在 `M1-CAS-01` 后并行；VM 验收必须在 Kafka 后执行。

## 是否需要 Worktree

- 当前单 Agent 不需要；若独立 Implementer 并行写入则需要。

## User Decision

- 无实现前或服务中断决策。

## Retirement Result

- Disposition：`superseded`。
- Implementation Result：`not_implemented_not_required`；未创建 `verify-spark-yarn.sh`，不得将行政归档解释为脚本实现完成。
- Reason：`DR-026` 已确认 Spark 3.5.9 on YARN 核心能力通过，`DR-027` 将重复的详细取证附件降为 Optional Evidence；继续实现本 Task 不再是 M1 门禁。
- Remaining Follow-up：正式数仓 Spark 作业及逐层结果仍按 Milestone 4～7 分别验收。
