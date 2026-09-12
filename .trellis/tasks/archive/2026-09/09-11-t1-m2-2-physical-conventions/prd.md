# T1 M2.2 物理规范收口

## Goal

在生成 SQL 前统一 19 张 MySQL 源表的 Schema 级物理规则。

## Scope

- 统一 PK、UQ、FK、CHECK 与 Index 的命名规则。
- 明确生成列的物理形式及其适用理由。
- 确定建表顺序和反向回滚顺序。
- 完整核对跨域 FK 拓扑与引用方向。
- 保持已确认的 19 张表、230 个字段，以及 `DR-013` 至 `DR-018` 的约束边界。

## Out of Scope

- 不生成最终 Candidate DDL。
- 不创建 Seed 或 Generator。
- 不编写指标 SQL。
- 不连接或执行 MySQL。

## Acceptance Criteria

- [x] 所有约束和索引名称在 19 张表范围内唯一且可追踪。
- [x] 每个生成列都有明确的物理形式与采用理由。
- [x] 建表顺序覆盖全部 FK，且不存在未解决的循环依赖。
- [x] 如需改变已确认字段、关系或约束语义，必须标记为 `DECISION_REQUIRED`，不得自行补全。

## Verification

- 对照业务模型设计第 8 节与 `DR-013` 至 `DR-018`。
- 检查约束和索引名称唯一性。
- 检查 FK 引用目标与引用完整性。
- 检查建表及回滚拓扑是否完整、方向是否一致。

## Parallelism

仅适合与不触碰 Schema 物理规范的独立工作并行；不与 T2 并行。

## Worktree

不需要；由协调会话串行收口共享设计。

## Conflicting Files / Modules

- `docs/spec.md`
- `docs/plan.md`
- `docs/milestone-2-business-design.md`
- `docs/decision-register.md`
- 后续 `mysql/ddl/` 的命名与依赖约定

## Dependencies

- C0 Trellis 项目基线确认。
