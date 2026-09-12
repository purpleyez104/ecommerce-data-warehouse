# T5 执行计划：固定 Seed 与预期结果

## 实施边界

- 仅修改 `mysql/seed/`、`mock/` 与 `tests/m2/` 下 T5 所需文件。
- 不修改 Candidate DDL、Generator、ECS/M1 配置、T6/T7 Task 或正式项目 docs；实现完成后另行判断 docs 是否需要同步。
- 不安装依赖、不连接 MySQL；真实执行、同库直接重跑和失败行为验证由 T7 在 M1 MySQL 门禁通过后进行。

## 步骤

1. 依据 `001_ecommerce_oltp_candidate.sql` 和 `DR-021` 设计 19 表的确定性合法记录，使用显式内部主键、唯一业务键和 `Asia/Shanghai` 毫秒业务时间。
2. 新建正常固定 Seed SQL，严格按 T2 创建拓扑的父表到子表顺序写入，并覆盖 4 个确认业务日期与 12 个场景。
3. 新建异常 SQL，分别定义 5 个数据库约束失败的独立事务和 `ROLLBACK`；不得在正常 Seed 中插入非法行。
4. 新建 JSON 预期清单，记录逐表行数、稳定业务键与内容摘要、业务日期、场景映射、14 个失败用例及预期退出行为。
5. 新建 `tests/m2/invoke_fixed_seed_idempotency.ps1`，使其接收隔离测试库连接参数，并在实际执行前比较清单中的行数与内容摘要：相同则不写入，漂移则非零失败；该入口只在 T7 连接 MySQL 运行。
6. 新建 PowerShell 静态 Contract 和 mutation regression：校验 Seed 表/行数/引用顺序、预期清单完整性、异常事务隔离，以及直接重跑入口的“相同则不写入、漂移非零”契约。
7. 运行静态 Contract、mutation regression 与 `git diff --check`；不运行 MySQL。
8. 完成后只读检查项目 docs 是否需反映“Seed 已实现但未在 MySQL 验证”，获得用户确认后才写入正式 docs。

## 预期验证命令

```powershell
pwsh -NoProfile -File tests/m2/validate_fixed_seed_contract.ps1
pwsh -NoProfile -File tests/m2/test_validate_fixed_seed_contract.ps1
git diff --check
```

## 预期结果与回滚

- 两个 PowerShell 命令仅在固定文件和清单满足静态 Contract 时返回 `0`；受控变异必须返回非零。
- 这些命令不连接 MySQL，不能证明 SQL 可执行、约束行为、同库直接重跑或异常回滚已经通过。
- 如需回滚 T5 产物，仅移除本 Task 新增的 Seed、预期结果和测试文件；不得删除 Candidate DDL、现有 Contract 测试或任何 MySQL 数据。
