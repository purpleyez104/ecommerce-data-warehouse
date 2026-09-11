# Data Engineering 项目规范

## Goal

维护 Trellis 的项目规范入口，使其服务于当前电商离实时一体化数据仓库，而不是导入默认 Fullstack 约定。

## 事实优先级

`AGENTS.md > README.md、docs/spec.md、docs/plan.md 等项目文档 > Trellis Task`。

Trellis Task 只记录当前工作边界、计划、执行和验证证据；不得复制、覆盖或替代项目 docs 的业务事实、Milestone 门禁或运行结论。

## Scope

- 基于已确认的 `AGENTS.md` 和项目 docs 维护 `.trellis/spec/data-engineering/` 入口。
- 在新增长期可复用的工程约束时，记录其来源与适用范围。
- 检查 Trellis Task 的 context 指向实际存在且适用的项目文件。

## Out of Scope

- 不引入 frontend/backend、React、ORM、API 或 TypeScript 规范，除非项目事实将来明确引入相应实现。
- 不复制业务模型、DDL、ECS 配置、指标口径或 `docs/plan.md`。
- 不启用 hooks、channel workflow 或自动 Sub-agent dispatch。

## Acceptance Criteria

- [ ] 规范入口只引用当前项目已确认的 Data Engineering 工程事实。
- [ ] 不存在无项目依据的默认 Fullstack 模板内容。
- [ ] 新增规范不提高 `draft`、`candidate`、`implemented` 或 `verified` 的证据等级。
- [ ] 相关 Trellis Task context 均可验证且不替代 docs。

## Verification

- `trellis platforms`
- `E:\Software\Python\3.12.10\python.exe ./.trellis/scripts/get_context.py --mode packages`
- `rg -n -i 'frontend|react|component|hook|state management|orm' .trellis/spec`
