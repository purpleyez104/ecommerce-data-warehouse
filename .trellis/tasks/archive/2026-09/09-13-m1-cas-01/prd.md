# M1-CAS-01 共享 Evidence Contract 与公共库

## Task Identity

- Task ID：`M1-CAS-01`
- Title：共享 Evidence Contract 与公共库

## Goal

冻结五组件验收脚本共同使用的 CLI、安全、日志、状态、证据目录和 Cleanup Contract，避免各脚本产生不兼容或不安全的实现。

## Scope

- 安全 `run-id`、绝对输出根、全新证据目录和 `umask 077`。
- 统一步骤日志、断言、SHA-256、去敏、退出码及 `summary.env`。
- 仅允许清理当前脚本以严格前缀创建的临时对象。

## Out of Scope

- 不实现组件命令、服务启停或 VM Runtime 验收。
- 不接受 `eval`、任意 Shell Command String 或永久配置修改。

## Inputs / Dependencies

- Parent Task 的 PRD/Design。
- `DR-022`、`DR-023`、`DR-024`。
- `scripts/m1/collect-hadoop-evidence.sh`、`restart-hadoop-and-verify.sh` 和 `collect-vm-environment-evidence.sh` 的安全 Pattern。
- 无前置 Child Task。

## Files / Modules

- `scripts/m1/lib/evidence-common.sh`
- Evidence Inbox：`.local-notes/m1-evidence/inbox/m1-cas-01-common-contract/`

## Acceptance Criteria

- [ ] 非法 `run-id`、相对输出路径、已存在或非空目录均被拒绝。
- [ ] Evidence Schema 支持 `PASS/PARTIAL/FAIL` 和步骤级状态。
- [ ] Secret 不进入 argv 日志、证据文件或标准输出。
- [ ] Cleanup 同时检查 Owner、前缀、当前 run-id 和禁止目标。
- [ ] 公共库不包含任何组件业务逻辑。
- [ ] Work 会话首先创建专属 Evidence Inbox，并在 Handoff 中报告路径。
- [ ] Inbox 只接收明确标记为 `local_static` 的本地 Contract/语法证据，不伪造 VM Runtime 证据。

## Verification

- `bash -n scripts/m1/lib/evidence-common.sh`
- 由 `M1-CAS-07` 的 Contract 测试覆盖危险路径、重复目录、去敏和非零失败。

## Risk

- 公共库缺陷会影响全部五个组件，必须最先完成并冻结接口。

## 是否适合并行

- 否。必须串行先完成；后续组件只能消费已冻结接口。

## 是否需要 Worktree

- 当前单 Agent 不需要。
- 若后续授权并行 Implementer，本文件仍只能由一个 Owner 修改。

## User Decision

- 无新增业务决策；开始实现前仍需用户批准完整 Child Task 规划。
