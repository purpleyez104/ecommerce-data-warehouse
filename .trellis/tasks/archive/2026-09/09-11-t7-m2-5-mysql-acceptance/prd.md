# T7 M2.5 MySQL 集成验收与 M2 收尾

## Goal

在真实 MySQL 上联合验收 DDL、Seed、Generator 和业务约束，并据证据判断 M2 是否可以收尾。

## Scope

- 在已通过门禁的 MySQL 环境执行 Candidate DDL、Seed 和 Generator 输出。
- 验证首次运行、同日重跑、连续业务日期和重复输入。
- 验证约束、状态、金额、`update_time`、软删除与硬删除语义。
- 保存命令、输入、退出状态、日志和结果证据。
- 根据完整证据评估 M2 完成状态。

## Out of Scope

- 不进入 M3、Hive、DataX 或指标实现。
- 不把局部成功或静态检查描述为 M2 全部完成。

## Acceptance Criteria

- [ ] T2、T5、T6 均已满足各自 Acceptance Criteria，且外部 M1 MySQL 门禁已通过。
- [ ] 19 张表按既定顺序创建成功。
- [ ] 正常、重复、非法、跨日、状态和守恒场景结果均符合预期。
- [ ] 失败场景返回非 0 状态，且不污染验收基线。
- [ ] 安装、连接、执行、结果核对和清理证据完整。
- [ ] 仅在上述条件全部满足后，才允许提议将 M2 标记为 `completed`。

## Verification

- 按 `docs` 中的验收 Checklist 执行并保存证据。
- 将实际 Schema 与静态 Contract 逐项对比。
- 执行 Seed、Generator、失败用例和重跑测试。
- 核对 Binlog、`update_time`、金额与数量守恒，以及清理结果。

## Parallelism

不适合并行；这是共享环境上的最终集成 Gate。

## Worktree

不需要；由协调会话在共享验收环境串行执行。

## Conflicting Files / Modules

- `mysql/`
- `generator/`
- `mock/`
- `tests/`
- MySQL 验收环境
- 所有 M1/M2 状态文档

## Dependencies

- T2 M2.2 候选 DDL 与静态检查。
- T5 M2.3 固定 Seed 与预期结果。
- T6 M2.4 参数化 Generator 与 Python 规则。
- 外部门禁：M1 MySQL 启动与连接验证已通过；这不是本轮创建的 Trellis Task。
