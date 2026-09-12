# T2 技术设计：Candidate DDL 与静态 Contract

## 边界

本任务把 `DR-014` 至 `DR-020` 已确认的 19 张 OLTP 源表转写为一个可审阅的 MySQL Candidate DDL 文件，并用 PowerShell 做文本级静态 Contract 检查。该检查不连接 MySQL，不替代 T7 的运行验收。

## 输入与权威来源

- `docs/milestone-2-business-design.md`：字段字典、关系、状态、单行约束与物理对象台账。
- `docs/decision-register.md` 的 `DR-014` 至 `DR-020`：类型、约束命名、生成列和建表顺序的确认结论。
- `docs/spec.md` 与 `docs/plan.md`：M2.2/T7 的证据与门禁边界。

若以上文档互相冲突，停止实现并标记 `DECISION_REQUIRED`；不从经验补全未确认语义。

## 产物设计

- `mysql/ddl/001_ecommerce_oltp_candidate.sql`：按 DR-020 的拓扑顺序包含 19 个 `CREATE TABLE`；文件头说明执行前提、创建顺序、反向 `DROP TABLE` 顺序及禁止关闭 FK 检查。每张表使用 InnoDB、utf8mb4，并将命名的 UQ/CHECK/FK/普通索引、VIRTUAL 生成列完整写出。
- `mysql/ddl/README.md`：给出静态检查命令、固定输入、成功/失败退出码、输出位置、限制和回滚说明；明确 DDL 仅为 Candidate/implemented。
- `tests/contracts/validate_mysql_ddl_contract.ps1`：仅读取上述 SQL，以确定性断言表数、字段数、表名、引擎/字符集、禁止项、FK/索引/生成列和建表顺序。违约时退出非零。

## 可验证性与兼容性

检查器只验证 DDL 文本是否兑现当前规格，不能验证 MySQL 8.0.46 语法、生成列索引、CHECK 或外键运行行为；这些留给 T7，且不得标注为 `verified`。不引入新依赖，使用现有 PowerShell。

## 回滚

本地文件改动可由版本控制恢复。若将 Candidate DDL 用于人工实验，按 SQL 文件中列出的逆拓扑 `DROP TABLE` 顺序手工回滚；本任务不执行数据库操作。
