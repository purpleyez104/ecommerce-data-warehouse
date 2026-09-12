# T5 技术设计：固定 Seed 与预期结果

## 边界

当前缺口是仓库没有可重复的 19 表合法固定 Seed、场景/逐表预期结果及可静态检查的异常用例清单。T5 只交付本地产物和静态 Contract；不连接 MySQL、不创建业务表、不实现参数化 Generator，也不把静态检查提升为 MySQL 运行验收。

## 产物与职责

| 路径 | 职责 |
| --- | --- |
| `mysql/seed/001_ecommerce_oltp_fixed_seed.sql` | 按 Candidate DDL 的父子依赖顺序写入合法、确定性固定数据；显式业务键、内部主键和业务时间均来自已确认固定集。 |
| `mysql/seed/002_ecommerce_oltp_constraint_failure_cases.sql` | 5 个数据库约束失败用例的独立事务定义；每个失败后必须 `ROLLBACK`，不混入正常 Seed。 |
| `mock/m2_fixed_seed_expected_results.json` | 19 表行数、4 个业务日期、`M2-SC-001` 至 `012` 映射、正常行的稳定业务键清单和 14 个失败用例分类。 |
| `tests/m2/invoke_fixed_seed_idempotency.ps1` | 接收隔离 MySQL 测试库连接参数；首次写入、第二次直接重跑前比较清单中的行数与内容摘要，完全匹配时不写入，漂移时非零失败。T7 才实际连接并运行它。 |
| `tests/m2/validate_fixed_seed_contract.ps1` | 不连接数据库的静态 Contract：核对 SQL 引用顺序、合法 Seed 的表/业务键/行数、预期结果清单、异常隔离和所需重跑入口。 |
| `tests/m2/test_validate_fixed_seed_contract.ps1` | 对正常输入及受控变异（行数、引用顺序、业务键、异常事务、预期清单）执行回归检查。 |

## 直接重跑契约

正常 Seed 的首次写入与第二次直接重跑均针对同一隔离测试库。运行入口在执行写入前读取 `mock/m2_fixed_seed_expected_results.json` 的 19 表行数与稳定业务键/内容摘要：

1. 目标表为空时，按 `001` 的依赖顺序写入正常 Seed。
2. 目标表已存在时，先逐表比较行数与稳定内容摘要；完全相同则不写入并以 `0` 退出。
3. 任一同业务键内容不一致、缺失、额外行或摘要不一致时，以非零退出；不得 `UPDATE`、`REPLACE`、`INSERT IGNORE` 或删除已有数据。

该运行入口的真实数据库实现和行为验证属于 T7；T5 的静态 Contract 只验证它的输入、预期结果与失败边界被完整定义。

## 数据和异常边界

- 正常 Seed 只写入符合 Candidate DDL 与已确认跨行规则的记录，并覆盖 `DR-021` 给定的 19 表行数与 `2025-01-29` 至 `2025-02-01` 业务日期。
- 5 个 MySQL 约束失败用例分别覆盖唯一键、`NOT NULL`、`CHECK`、外键和生成列唯一约束；每例独立事务、预期失败并回滚。
- 9 个 Python 写入层失败用例仅在预期结果清单中定义输入/预期非零/不污染要求；不在 T5 实现 Python 写入层。
- `M2-SC-001` 至 `012` 必须有至少一个正常或隔离异常用例映射；19 表必须有正常 Seed 覆盖方式。

## 风险与回滚

Candidate DDL 尚未在 MySQL 8.0.46 执行，SQL 语法、`CHECK`、生成列唯一约束及直接重跑运行行为均未验证。若 T7 证明固定输入与 DDL 或已确认业务规则不兼容，新增替代决策并同步调整 Seed、预期结果与测试；不得通过关闭外键、修改 Candidate DDL、删除正常数据或忽略漂移绕过失败。
