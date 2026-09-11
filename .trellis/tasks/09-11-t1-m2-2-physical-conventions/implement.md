# T1 M2.2 物理规范收口执行计划

## 执行顺序

- [x] 修正 T1 PRD 中的冲突文件路径。
- [x] 将 183 项命名台账、两个 `VIRTUAL` 生成列、19 表创建顺序和精确反向回滚顺序写入 T1 设计依据。
- [x] 扩展 `DR-020`，使其覆盖完整 T1 决策，并保留 `DR-017`、`DR-018` 的历史原文。
- [x] 同步 `docs/spec.md` 和 `docs/milestone-2-business-design.md` 中仍将已确认物理项描述为待决策的内容。
- [x] 确认 README 与计划已指向 T2 Candidate DDL，不额外修改已一致内容。
- [x] 激活 T1 为 `in_progress`；Codex `dispatch_mode: inline`，`implement.jsonl` 和 `check.jsonl` 保持为空并使用 `--allow-empty-context`。

## Verification

- [x] 台账包含 19 个逻辑 PK、30 个 UQ、42 个 CHECK、32 个 FK、60 个二级索引，总计 183 项。
- [x] 除 MySQL 固定的实际 `PRIMARY` 外，台账名称在 19 张表范围内唯一。
- [x] 两个生成列均明确为 `VIRTUAL GENERATED ALWAYS`，并分别配对唯一索引。
- [x] 31 个跨表 FK 的父表均先于子表创建；`category` 仅有同表自引用。
- [x] 回滚顺序与 19 表创建顺序精确相反。
- [x] 不再把已确认的名称、生成列物理形式和建表顺序列为 `DECISION_REQUIRED`。
- [x] `git diff --check` 通过，差异仅落在批准范围内。

## Review Gate

完成上述检查后，由协调会话重新验收 T1 Acceptance Criteria。只有验收通过且后续 Commit/归档范围另行确认后，才可将 Trellis Task 更新为 `done`。

## Rollback

- 对共享 docs 仅反向恢复本 Task 的精确段落，不使用会覆盖其他未提交修改的 `git restore` 或 `git reset`。
- 删除本 Task 新建的 `design.md`、`implement.md`，并将 `task.json` 的 `status` 和 `branch` 恢复到启动前状态。
