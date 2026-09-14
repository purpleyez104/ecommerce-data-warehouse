# M1-CAS-07 集成测试与交付

## Task Identity

- Task ID：`M1-CAS-07`
- Title：跨脚本 Contract 测试、Operator README 与交付检查

## Goal

证明五个脚本遵守统一安全和证据 Contract，并向用户交付可复制的 VM 执行、回传和恢复说明。

## Scope

- 跨脚本静态 Contract 测试与关键 Mutation Check。
- README 前置条件、参数、执行影响、退出码、证据目录、清理、回滚和回传步骤。
- 最小本地回归、编码、Diff 和文件范围检查。

## Out of Scope

- 不连接或控制 VM。
- 不把静态通过描述为 Runtime 通过。
- 不更新 Milestone、组件状态、CHANGELOG 或 Decision Register。

## Inputs / Dependencies

- `M1-CAS-01～06` 全部实现完成。
- 五脚本最终 CLI、Evidence Schema 和安全 Guard。

## Files / Modules

- `tests/m1/test_component_acceptance_scripts.ps1`
- `scripts/m1/README.md`
- 只读检查 `M1-CAS-01～06` 的实现文件。
- Evidence Inbox：`.local-notes/m1-evidence/inbox/m1-cas-07-integration-handoff/`

## Acceptance Criteria

- [ ] Contract 测试覆盖文件、CLI、状态、证据、安全、确认 Token 和组件特定断言。
- [ ] Mutation Check 能捕获关键 Guard 缺失或危险文本。
- [ ] README 命令与脚本 `--help` 一致。
- [ ] 用户获得 VM 串行执行和证据回传步骤。
- [ ] 本地未运行项明确为 `not_run`，不提高证据等级。
- [ ] Work 会话首先创建专属 Evidence Inbox，只保存标记为 `local_static` 的集成检查输出。
- [ ] 五组件 VM Runtime 证据仍分别保存在 `M1-CAS-02～06` 的 Inbox，不集中复制或改名。

## Verification

- `pwsh -File tests/m1/test_component_acceptance_scripts.ps1`
- `pwsh -File tests/m1/test_collect_vm_environment_evidence.ps1`
- 六个 Shell 文件逐一 `bash -n`
- `git diff --check`

## Risk

- 纯文本 Contract 可能假阳性；Windows 可能缺少 Bash。

## 是否适合并行

- 测试 Skeleton 可在公共 Contract 冻结后准备；最终集成必须等待 `M1-CAS-02～06`，串行收尾。

## 是否需要 Worktree

- 当前不需要；并行开发时必须由单一集成 Owner 维护 README 和跨脚本测试。

## User Decision

- 无新增业务决策；交付后用户决定何时执行 VM 及是否授权中断测试。

## Retirement Result

- Disposition：`superseded`。
- Implementation Result：`not_implemented_not_required`；未实施原五脚本集成交付，不得将行政归档解释为 Contract Suite 完成。
- Reason：M1-CAS-03～06 已被 `DR-026`、`DR-027` 取消为 M1 必需交付，因此原集成前提不再成立。
- Remaining Follow-up：保留现有 M1 安全 Guard；未来只有在新增可维护验收脚本时才增加对应 targeted test。
