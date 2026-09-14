# Implementation Plan

## Evidence Inbox Initialization — First Step

Work 会话开始后首先执行：

```powershell
New-Item -ItemType Directory -Force -Path ".local-notes\m1-evidence\inbox\m1-cas-07-integration-handoff" | Out-Null
```

不得清空已有内容。该目录只保存明确标记的本地集成证据，不复制组件 VM Runtime 原始证据。

1. 核对五脚本最终 CLI 和公共 Evidence Schema。
2. 实现公共、安全及组件特定 Contract 断言。
3. 增加不修改真实实现的最小 Mutation Check。
4. 更新 Operator README，逐项核对 `--help`。
5. 运行新测试、已有 M1 回归、`bash -n` 和 `git diff --check`。
6. 汇报 Changed/Verified/Notes/Next，不声称 VM Runtime 通过。

## Completion Gate

- 所有可用本地检查通过或明确记录 `not_run`。
- 用户可按 README 执行并回传完整证据目录。
- Handoff 报告本 Task Evidence Inbox 和五个组件 Inbox 的绝对路径。

## Recommended Next Step

用户按 `MySQL → Hive → Kafka KRaft → Spark on YARN → DataX` 在 VM 串行执行；Codex 随后只读验收证据。
