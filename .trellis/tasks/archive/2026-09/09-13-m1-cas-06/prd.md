# M1-CAS-06 DataX 验收脚本

## Task Identity

- Task ID：`M1-CAS-06`
- Title：DataX 双 Worker、MySQL→HDFS 与失败路径验收脚本

## Goal

验证 DataX 202309 Runtime、Plugin、双 Worker 执行、MySQL→HDFS ORC+Snappy 输出和可诊断失败。

## Scope

- `hadoop202/203` Canonical Path、历史残留路径、版本、Python/JDK 和 Plugin。
- 严格前缀临时 MySQL 输入。
- 两 Worker 各自的私有临时 Job JSON 和隔离 HDFS 输出。
- Hive/Spark 结果、格式、压缩核对和固定失败 Job。

## Out of Scope

- 不使用正式 M2 表。
- 不设计 M3 全量/增量、幂等发布或正式 ODS Schema。
- 测试 `STRING` Workaround 不升级为项目决策。

## Inputs / Dependencies

- `M1-CAS-01` 完成并冻结。
- VM Runtime 执行前 MySQL、HDFS、Hive、Spark 已通过前序门禁。
- 双 Worker SSH 和权限不高于 `0600` 的 Secret 文件。

## Files / Modules

- `scripts/m1/verify-datax.sh`
- Evidence Inbox：`.local-notes/m1-evidence/inbox/m1-cas-06-datax/`

## Acceptance Criteria

- [ ] 两 Worker 的 Runtime、Python/JDK、`mysqlreader`、`hdfswriter` 均有证据。
- [ ] 两个隔离 Job 均输出固定三行且结果一致。
- [ ] Hive/Spark 确认 ORC+Snappy 和固定值。
- [ ] 预期失败 Job 返回非零并保存去敏错误摘要。
- [ ] 临时 Job JSON 为 `0600` 且仅在受控路径清理。
- [ ] Work 会话首先创建专属 Evidence Inbox；VM 原始 run 目录由用户原样放入。
- [ ] 在用户回传并经协调会话审查前，DataX Runtime 保持 `not_run`/未 `verified`。

## Verification

- `bash -n scripts/m1/verify-datax.sh`
- `M1-CAS-07` Secret/路径/双 Worker Contract。
- VM 两个成功 Job、一个失败 Job和 Hive/Spark 核对。

## Risk

- Credential 短暂物化；Writer Path 错误可能覆盖数据；必须使用全新目录和严格 Cleanup。

## 是否适合并行

- 实现可在 `M1-CAS-01` 后并行；VM 验收必须最后执行。

## 是否需要 Worktree

- 当前单 Agent 不需要；若独立 Implementer 并行写入则需要。

## User Decision

- 执行前用户准备 Secret 文件，但不得把内容发送给 Codex；无新增业务决策。

## Retirement Result

- Disposition：`superseded`。
- Implementation Result：`not_implemented_not_required`；未创建 `verify-datax.sh`，不得将行政归档解释为脚本实现完成。
- Reason：`DR-026` 已确认 DataX 202309 核心能力通过，`DR-027` 将重复的详细取证附件降为 Optional Evidence；继续实现本 Task 不再是 M1 门禁。
- Remaining Follow-up：正式 ODS Schema、幂等发布和失败隔离仍由 Milestone 3 验收。
