# T2 实施计划

1. 从 M2.2 字段字典、关系定义和 DR-020 台账逐表提取已确认字段、类型、约束和对象名；核对合计为 19 表、230 字段。
2. 在 `mysql/ddl/001_ecommerce_oltp_candidate.sql` 中按已确认顺序编写 Candidate DDL，并将逆序回滚作为注释说明；不执行该 SQL。
3. 新建 `tests/contracts/validate_mysql_ddl_contract.ps1`，只对 DDL 文本运行固定静态断言；新建最小 `mysql/ddl/README.md` 说明入口和证据边界。
4. 按需要同步已受影响的项目文档，使其仅陈述 Candidate DDL 已实现、MySQL 运行验证仍由 T7 阻断；不自行更新 `CHANGELOG.md` 或新增决策记录。
5. 运行静态 Contract 检查和 `git diff --check`；如任一检查失败，先修复再重跑。

## 验收门槛

- 静态检查成功退出 `0`；被篡改或违反 Contract 的输入必须退出非零（通过检查器的断言路径保证）。
- 不出现 `FOREIGN_KEY_CHECKS`、`TRIGGER` 或 `PROCEDURE`。
- 汇报仅使用 `implemented` 与静态检查证据，不宣称 MySQL 已执行或已验证。
