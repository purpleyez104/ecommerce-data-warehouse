# Data Engineering 项目规范入口

本目录只提供 Trellis 工作时的项目规范导航，不是业务、架构或运行事实的副本。

## 事实优先级

1. `AGENTS.md`：仓库协作规则、授权边界、状态与证据标准。
2. `README.md`、`docs/spec.md`、`docs/plan.md` 及相关项目 docs：范围、Milestone 门禁、已采用设计与验证事实。
3. `.trellis/tasks/<task>/`：当前 Task 的范围、计划、context 和验证记录。

较低层不得覆盖较高层。发现冲突、缺失或证据不足时，标记 `DECISION_REQUIRED`，停止在当前 Milestone；不得使用经验默认值补全。

## Pre-Development Checklist

- 依次完整阅读 `README.md`、`docs/spec.md`、`docs/plan.md` 和当前 Task 的 `prd.md`。
- 读取与目标模块直接相关的项目 docs、代码、配置和现有验证证据。
- 确认工作属于当前允许的 Milestone；M1/M2 并行不解除直接运行依赖。
- 将静态检查与真实运行验证分开报告；不得把 `candidate`、`implemented` 写成 `verified`。
- 仅在用户明确要求 Sub-agent、parallel agents 或指定角色时派发；默认 Codex inline。

## 可执行实现契约

- [M2.4 Generator Contract](generator-contract.md)：参数化 SQL Generator 的 CLI、确定性输出、失败行为、静态验证和 MySQL 运行边界。

## Quality Check

- Task 不复制或替代 `docs/plan.md`、业务模型、DDL、ECS 配置或指标口径。
- 所有新增批处理均使用显式业务日期或起止时间；Generator 实现还必须遵守 [M2.4 Generator Contract](generator-contract.md)。
- 变更仅限用户批准范围，并报告 `Changed`、`Verified`、`Notes`、`Next`。
- 未明确要求时，不启用 hooks、channel workflow、安装、初始化、Push、Merge 或重写 Git 历史。
