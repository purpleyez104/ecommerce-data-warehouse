# C0 Trellis 项目基线确认

## Goal

确保 Trellis 使用当前 Data Engineering 项目事实，而不是默认 Fullstack 模板。

## Scope

- 审查 `.trellis/config.yaml`、`.trellis/spec/`、`.agents/`、`.codex/`。
- 决定自动生成的 `00-bootstrap-guidelines` 是改造成项目规范任务，还是标记为不适用。
- 明确 `AGENTS.md > docs > Trellis Task` 的事实优先级。

## Out of Scope

- 不启用 hooks 或 channel workflow。
- 不修改业务模型、DDL、ECS 配置。
- 不创建 M1/M2 实现。

## Acceptance Criteria

- [x] 默认 frontend/backend 指南不再被误当作本项目规范。
- [x] `00-bootstrap-guidelines` 已在用户确认后转换为 Data Engineering 项目规范任务。
- [x] Trellis 只承担 Task 状态，不复制或替代 `docs/plan.md`。
- [x] 初始化文件已完成 diff 审查，并形成可恢复的 Git Commit 基线；用户已确认保留基线 Commit `145a64c`，阻断修复已提交为 `b00be53`。

## Verification

- 运行 `trellis platforms`。
- 运行 `git status --short`。
- 运行 `git diff -- .gitattributes`。
- 检查 `.trellis/spec/` 是否仍包含无项目依据的模板内容。

## Parallelism

不适合并行；应在其他 Trellis Task 开始实施前完成。

## Worktree

不需要；这是共享工作流基线。

## Conflicting Files / Modules

- `.trellis/`
- `.agents/`
- `.codex/`
- `.gitattributes`
- `AGENTS.md`

## Dependencies

无。

## Completion Note

Trellis 已建立面向当前 Data Engineering 项目的规范入口；`00-bootstrap-guidelines` 已按用户确认转换。自动 Git Commit 已显式关闭，Hook 注册已清空，C0 Acceptance Criteria 全部通过。

## Verification Note

- `trellis platforms`：通过，仅配置 Codex。
- `get_context.py --mode packages`：通过，Single-repo，Spec layer 为 `data-engineering`。
- `task.py validate 09-11-c0-trellis-project-baseline`：通过。
- `.codex/hooks.json`：JSON 解析通过，注册 Hook 数量为 0。
- Trellis 有效配置：`session_auto_commit=False`。
- `git diff --check` 与 targeted Git diff：通过。
- Git evidence：基线 Commit `145a64c`；阻断修复 Commit `b00be53`。

## Remaining Follow-up

Trellis 生成脚本中的本机 Python 路径仍会产生 `invalid escape sequence '\S'` Warning。该问题不影响当前命令退出状态或 C0 验收，作为后续 Trellis 升级或可移植性治理事项保留。
