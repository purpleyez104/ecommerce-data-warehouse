# Parent Coordination Plan

## Authorization Boundary

本 Parent 只协调七个真实 Child Task / Story。创建和规划 Child Task 不代表可以运行 `task.py start`、修改脚本或执行 VM 验收。必须由用户批准最新 Parent/Child 规划后才能开始实现。

## Child Task Sequence

```text
M1-CAS-01 Shared Evidence Contract
→ M1-CAS-02 MySQL
→ M1-CAS-03 Hive
→ M1-CAS-04 Kafka KRaft
→ M1-CAS-05 Spark on YARN
→ M1-CAS-06 DataX
→ M1-CAS-07 Contract Tests and Handoff
```

## Dependency Rules

- `M1-CAS-01` 必须最先完成并冻结公共 Shell API、Evidence Schema、安全和 Cleanup Contract。
- `M1-CAS-02～06` 只依赖 `M1-CAS-01`，技术上可并行，但当前未授权并行 Agent，推荐按 ID 串行实现。
- `M1-CAS-07` 依赖 `M1-CAS-01～06` 的最终接口，必须最后完成。
- VM Runtime 不采用实现并行关系，必须按组件门禁串行执行。

## Evidence Inbox Initialization

每个 Child Task 的 Work 会话必须把创建专属 Evidence Inbox 作为第一步。该步骤只保证接收位置存在，不代表已有任何验收证据：

```text
M1-CAS-01 → .local-notes/m1-evidence/inbox/m1-cas-01-common-contract/
M1-CAS-02 → .local-notes/m1-evidence/inbox/m1-cas-02-mysql/
M1-CAS-03 → .local-notes/m1-evidence/inbox/m1-cas-03-hive/
M1-CAS-04 → .local-notes/m1-evidence/inbox/m1-cas-04-kafka-kraft/
M1-CAS-05 → .local-notes/m1-evidence/inbox/m1-cas-05-spark-yarn/
M1-CAS-06 → .local-notes/m1-evidence/inbox/m1-cas-06-datax/
M1-CAS-07 → .local-notes/m1-evidence/inbox/m1-cas-07-integration-handoff/
```

目录创建后不得清空已有内容。VM Runtime 文件由用户放入，本协调会话只读验收。

## Shared Change Gates

- 公共接口：仅 `M1-CAS-01` 修改，冻结后其他 Child Task 只消费。
- Operator README 与跨脚本测试：仅 `M1-CAS-07` 最终修改。
- Database Schema/Migration：无永久修改，只有严格前缀运行期临时对象。
- 组件永久配置与 Dependency：无修改。
- 运行服务：只有 VM 阶段在用户显式授权后短暂重启 MySQL/Hive 或停止单个 Kafka Broker。

## User Decision Gates

1. 批准最新 Parent/Child 规划后才能开始 `M1-CAS-01`。
2. MySQL 受控重启需要单独确认。
3. Hive 受控重启需要单独确认；Runtime Java 决策等待实际证据。
4. Kafka 单 Broker 验收需要选择 Failure Node 并单独确认。
5. VM 证据审查后，再确认是否提升状态及更新正式文档。

## Worktree Decision

- 当前单 Agent 按 Child Task 串行实现，不需要新增 Worktree。
- 若未来授权多个写入型 Implementer 并行实现 `M1-CAS-02～06`，每个 Implementer 必须使用独立 Worktree，且不得修改共享接口。

## Recommended Repository Execution Order

1. 启动并完成 `M1-CAS-01`。
2. 依次启动并完成 `M1-CAS-02`、`03`、`04`、`05`、`06`。
3. 启动 `M1-CAS-07`，完成集成测试、README 和本地交付检查。
4. 检查七个 Child Task Acceptance Criteria 后再判断 Parent 是否完成。

## Recommended VM Execution Order

```text
MySQL 非中断检查
→ MySQL 受控重启（单独授权）
→ Hive 非中断检查
→ Hive 受控重启（单独授权）
→ Kafka KRaft 非中断检查
→ Kafka 单 Broker 停止与恢复（选择节点并单独授权）
→ Spark on YARN 成功与预期失败作业
→ DataX 双 Worker 成功与预期失败 Job
→ 回传五个完整证据目录
→ Codex 只读验收
```

任一组件为 `FAIL` 时停止后续验收。`PARTIAL` 可以保存证据，但不得标记为 `verified`，是否继续下一门禁由证据审查决定。

## Parent Completion Gate

- 七个 Child Task 均满足各自 Acceptance Criteria。
- 本地静态检查均通过或明确标记 `not_run`。
- 用户获得可执行 VM 命令和证据回传说明。
- Parent 完成只代表验收脚本交付，不代表五组件 Runtime 已 `verified`。

## Rollback

- 使用 `task.py remove-subtask` 解除指定 Child 关联。
- 只删除本轮新建且路径经过验证的 `09-13-m1-cas-01～07` 目录。
- 使用反向 `apply_patch` 恢复 Parent 的 `task.json/prd.md/design.md/implement.md`。
- 不使用 `git reset --hard` 或覆盖用户其他修改。
