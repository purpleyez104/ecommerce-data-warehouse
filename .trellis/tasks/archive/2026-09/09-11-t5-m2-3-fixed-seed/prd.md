# T5 M2.3 固定 Seed 与预期结果

## Goal

建立可重复的合法固定 Seed、隔离的失败用例和逐表预期结果。

## Scope

- 在 `mysql/seed/` 中创建合法固定 Seed。
- 在 `mock/` 中定义场景与逐表预期结果。
- 为数据库约束失败用例提供隔离事务和回滚方式。
- 覆盖首次运行、同日重跑、连续业务日期和上游重复输入。

## Confirmed Decisions

- 正常固定 Seed 必须在同一隔离测试库中直接执行两次；第二次执行后，全部 19 张表的行数与内容保持不变。
- 发现相同业务键对应的内容漂移时，Seed 必须以非零状态失败；禁止使用静默覆盖或忽略错误的方式继续执行。

## Out of Scope

- 不实现参数化 Generator。
- 不把非法数据混入合法 Seed。
- 不执行或宣称完成最终 M2.5 MySQL 验收。

## Acceptance Criteria

- [ ] 固定输入使用确定性业务键并产生确定性预期结果。
- [ ] 覆盖 5 个业务域和 `M2-SC-001` 至 `M2-SC-012`。
- [ ] 失败用例相互隔离，并在失败后完成回滚，不污染合法基线。
- [ ] 预期结果覆盖唯一性、引用完整性、状态、金额和数量守恒。
- [ ] 同一测试库的直接重跑保持 19 张表行数与内容不变；同业务键内容漂移返回非零。

## Verification

- 对固定 Seed 与预期结果生成 Checksum。
- 静态检查引用顺序、业务键和逐表行数。
- 真实数据库行为延后至 T7。
- 在未完成真实 MySQL 验收前，状态最高为 `implemented`。

## Parallelism

完成 T2 和 T4 后，适合与 T6 并行。

## Worktree

需要；如由独立 Implementer 执行，使用专属 Worktree 和明确文件所有权。

## Conflicting Files / Modules

- `mysql/seed/`
- `mock/`
- `tests/m2/`
- 与 T6 共享的业务规则
- T2 提供的 DDL Contract

## Dependencies

- T2 M2.2 候选 DDL 与静态检查。
- T4 M2-DEC-015 验收数据规模决策。
