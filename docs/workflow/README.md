# Project Workflow

本项目使用轻量的 **Stage-Step 滚动开发**。同一 Chat 可以直接开发、验证并更新 Repository；Handoff 是跨上下文工具，不是日常必经阶段。

## 1. 默认开发

Confirmed Spec 范围内执行：

```text
理解当前目标与相关范围
→ 检查代码、配置、相关文档章节和 Git Diff
→ 连续实现当前 Step
→ Targeted Verification
→ Step Gate
→ 简短汇报
```

同一任务链允许保留 Dirty Worktree，但必须保护已有修改。普通 Step 不自动进入 BMad、生成 Handoff、运行多层 Review 或创建 Commit。

## 2. Stage 与 Step

Stage 开始时确定 Goal、Scope / Non-goals、核心 Contract/Schema/Architecture 边界、Acceptance Criteria、验证方式、主要风险和粗粒度 Step Map。

只详细设计当前 Step。Step 完成后按证据选择：

1. **Local Fix**：Stage Contract 不变，直接修复并复测。
2. **Replan Remaining Steps**：只影响后续实现顺序或细节，调整剩余 Step Map。
3. **Correct Course**：改变 Scope、核心 Contract、Schema、Architecture 或 Acceptance，暂停实现并等待用户确认。

Stage 结束时做一次阶段 Review、必要的 Integration/Full Validation、文档同步提议，并单独申请一次 Git Commit。

## 3. BMad 边界

BMad 仅用于：用户明确要求；新 Milestone；核心 Contract/Schema/Architecture 变化；高返工成本关键歧义；需要跨会话协调多个独立 Story。

```text
BMad：设计/审查 Stage（Master）
普通开发：设计并实施当前 Step（Worker）
```

`bmad-build` 不自动接管普通实现。

## 4. 文档路由

| 文档 | 职责 |
| --- | --- |
| `README.md` | 项目总览、当前能力、运行和验证入口 |
| `docs/spec.md` | 已确认 Scope、Contract、Acceptance |
| `docs/plan.md` | Milestone/Stage 路线与门禁 |
| `docs/status/` | 当前 `VERIFIED / DOING / DESIGNED / HISTORY / UNKNOWN` |
| `docs/architecture/architecture.md` | 长期 Architecture 边界 |
| `docs/business/metrics.md` | 已冻结业务与指标口径 |
| `docs/decision-register.md` | 高影响正式决策 |
| `docs/acceptance/` | 实际验收证据及其边界 |
| `CHANGELOG.md` | 已交付变更 |

Agent 判断是否具有长期参考价值，然后提出“更新哪些文件、写什么、为什么、影响什么”。正式文档须经用户确认后修改：Contract/Architecture/Schema 等变化即时提出；普通状态和验证结果在 Step/Stage Gate 集中提出。没有记录价值时直接说明“不需要记录”。

## 5. 事实与状态

- 当前代码、配置、Git Diff 与实际 Test/Runtime：实现和运行事实。
- Confirmed Spec / 业务 Contract：Scope 与语义。
- Status：当前进度与证据摘要。
- Plan：阶段路线。
- Architecture / Decision Register：长期约束。
- Handoff：跨上下文运输，不是更高层事实来源。

统一状态：`VERIFIED / DOING / DESIGNED / HISTORY / UNKNOWN`，并始终遵守 `FILE EXISTS ≠ VERIFIED`。进度文档落后时提出同步，不为匹配旧 Plan 倒推代码。

## 6. Handoff

只在以下情况使用：换 Chat、换 Agent/执行环境、跨 Worktree、交给另一执行者，或用户明确要求。

最小 Handoff 包含 Objective/Scope、状态、Changed Files/Diff 边界、实际验证、关键 Contract/Decision/Risk、下一入口与禁止误判事项。接收者必须对照当前 Repository 复核；冲突标记为 `CONFLICT`，证据不足保持 `UNKNOWN`。

旧式 `Development Chat → Work Handoff → Repository` Prompt 已移除；历史内容保留在 Git 历史中。新的跨上下文交接统一使用显式 `project-handoff` Skill。

## 7. 安全与提交

Secret、真实认证信息和原始敏感日志不得进入仓库。Commit、Push、Merge、Database Operation、数据迁移和外部服务写入都需要单独授权。每个完整 Stage 通常只申请一次 Commit，不为每个小步骤停下来提交。
