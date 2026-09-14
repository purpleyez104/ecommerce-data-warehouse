# T6 M2.4 参数化 Generator 与 Python 规则

## Goal

实现确定性、可配置的数据 Generator，并落实由 Python 写入层负责的跨行业务规则。

## Scope

- 创建 `generator/` 下的参数化数据生成实现。
- 显式接收随机种子、业务日期与数据规模参数。
- 实现跨行状态、退款、优惠券、金额分摊等 Python 业务规则。
- 提供参数验证、失败退出和针对性测试。

## Confirmed Decisions

- T6 可将当前未提交的 T5 固定 Seed、预期 JSON 与静态 Contract 测试作为只读交叉核对输入；不得修改、移动或重写这些产物。
- Generator 提供 Python CLI，输出确定性 SQL 文件，并在写文件前以纯 Python 执行跨行规则校验；不得连接 MySQL。
- T6 不承担 MySQL Runtime Acceptance；数据库执行、约束行为与结果验收保留给 M2.5。
- 若 T5 后续契约变化，T6 在集成阶段进行兼容性核对，不在本 Task 提前修改 T5 产物。

## Out of Scope

- 不修改或生成 DDL。
- 不重复实现 T5 的固定 Seed。
- 不建设通用数据生成 Framework。

## Acceptance Criteria

- [ ] 相同参数产生相同输出。
- [ ] 数据范围使用显式业务日期，不依赖执行机器当前日期。
- [ ] 参数非法或规则违约时返回非 0 退出状态。
- [ ] 使用 `DECIMAL`、`HALF_UP` 及确定性分摊和退款规则。
- [ ] Generator 不绕过 MySQL 约束或掩盖 Contract 错误。

## Verification

- 对相同参数输出生成并比较 Checksum。
- 测试参数非法、累计金额、重复输入和跨日生成。
- 用小规模输出与 T5 的预期规则交叉核对。
- 未接入真实 MySQL 时，不宣称数据库约束行为已验证。

## Parallelism

完成 T2 和 T4 后，适合与 T5 并行。

## Worktree

需要；如由独立 Implementer 执行，使用专属 Worktree 和明确文件所有权。

## Conflicting Files / Modules

- `generator/`
- `tests/m2/`
- 与 T5 共享的业务规则
- T2 提供的 DDL 字段 Contract

## Dependencies

- T2 M2.2 候选 DDL 与静态检查。
- T4 M2-DEC-015 验收数据规模决策。
