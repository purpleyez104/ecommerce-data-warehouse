# T2 M2.2 候选 DDL 与静态检查

## Goal

把已确认的业务模型转换为 19 张 MySQL 源表的 Candidate DDL，并建立可重复的静态 Contract 检查。

## Scope

- 在 `mysql/ddl/` 中生成 19 张源表的 Candidate DDL。
- 提供明确的执行顺序与反向回滚说明。
- 建立不依赖真实 MySQL 的静态 Contract 检查。
- 提供对应的测试入口、固定检查项和退出状态约定。

## Out of Scope

- 不在真实 MySQL 上执行 DDL。
- 不创建 Seed 或 Generator。
- 不创建 Hive、ODS、DataX 或指标 SQL。
- 不引入 Trigger 或 Stored Procedure。

## Acceptance Criteria

- [x] Candidate DDL 恰好覆盖 19 张表和 230 个字段。
- [x] 全部表使用已确认的 InnoDB、utf8mb4、时间与金额规范。
- [x] 已确认的约束、状态检查和生成列唯一索引均被表达。
- [x] 不通过关闭 FK 检查掩盖建表顺序或数据完整性问题。
- [x] 证据状态最高只能标记为 `implemented`，不得描述为 MySQL `verified`。

## Verification

- 静态核对表数、字段数、名称和 FK 目标。
- 静态核对约束、生成列表达式、索引及建表顺序。
- 静态检查器成功时退出码为 0，发现违约时退出码非 0。
- 运行 `git diff --check`。
- MySQL 行为验证明确延后至 T7。

## Parallelism

有限并行；仅与不修改 DDL、Schema Contract 或相关测试入口的独立工作并行。

## Worktree

条件需要；若由独立 Implementer 执行，使用 Worktree。协调会话串行实施时可不使用。

## Conflicting Files / Modules

- `mysql/ddl/`
- `tests/` 中的 DDL 静态 Contract 检查
- 中央业务模型设计
- 跨域 FK 与建表顺序

## Dependencies

- T1 M2.2 物理规范收口。
