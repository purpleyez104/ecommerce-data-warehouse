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
- [ ] 初始化文件已完成 diff 审查；等待用户确认后创建可恢复的 Git Commit 基线。

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
