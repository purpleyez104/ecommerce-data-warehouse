# M1-CAS-04 Kafka KRaft 验收脚本

## Task Identity

- Task ID：`M1-CAS-04`
- Title：Kafka KRaft 三节点功能与单 Broker 恢复验收脚本

## Goal

验证 Kafka 3.9.1 Scala 2.12 三节点 combined broker/controller、Quorum、RF/ISR、消息重放和单 Broker 恢复。

## Scope

- 三节点版本、进程、9092/9093、Cluster ID、Broker、Quorum 和配置白名单。
- 严格前缀临时 Topic，RF=3、minISR=2。
- 固定有序消息生产、消费和指定 Offset 重放。
- 显式授权后的单 Broker 停止、降级读写、恢复和 ISR 回归。

## Out of Scope

- 禁止 `kafka-storage.sh format`。
- 不删除或改写 `/data/kafka/kraft-combined-logs`。
- 不操作正式 Topic，不决定 M8 Topic/Partition/Schema。

## Inputs / Dependencies

- `M1-CAS-01` 完成并冻结。
- 三节点 Kafka 已运行、SSH 和 Kafka 自带管理/生命周期命令。

## Files / Modules

- `scripts/m1/verify-kafka-kraft.sh`
- Evidence Inbox：`.local-notes/m1-evidence/inbox/m1-cas-04-kafka-kraft/`

## Acceptance Criteria

- [ ] 三节点 Cluster ID 一致、Quorum 与 Broker 列表完整。
- [ ] 临时 Topic 为 RF=3、minISR=2，固定消息完整且可按 Offset 重放。
- [ ] 默认不停止 Broker 并输出 `PARTIAL`。
- [ ] 授权后降级期间继续读写，恢复后 ISR 回到三副本才可 `PASS`。
- [ ] 只删除本次临时 Topic，任何必需失败返回非零。
- [ ] Work 会话首先创建专属 Evidence Inbox；VM 原始 run 目录由用户原样放入。
- [ ] 在用户回传并经协调会话审查前，Kafka Runtime 保持 `not_run`/未 `verified`。

## Verification

- `bash -n scripts/m1/verify-kafka-kraft.sh`
- `M1-CAS-07` 检查危险命令禁令。
- VM Topic、Producer、Consumer、Offset、ISR 和 Recovery 证据。

## Risk

- 单 Broker 停止会降低短时容错；误操作 KRaft Storage 将不可接受。

## 是否适合并行

- 实现可在 `M1-CAS-01` 后并行；VM 验收必须在 Hive 后执行。

## 是否需要 Worktree

- 当前单 Agent 不需要；若独立 Implementer 并行写入则需要。

## User Decision

- 用户需选择 Failure Node，并显式传入 `KAFKA_KRAFT_SINGLE_BROKER`。

## Retirement Result

- Disposition：`superseded`。
- Implementation Result：`not_implemented_not_required`；未创建 `verify-kafka-kraft.sh`，不得将行政归档解释为脚本实现完成。
- Reason：`DR-026` 已确认 Kafka KRaft 核心能力通过，`DR-027` 将重复的详细取证附件降为 Optional Evidence；继续实现本 Task 不再是 M1 门禁。
- Remaining Follow-up：Milestone 8 的正式 Topic、Schema 和重放策略仍需独立设计评审。
