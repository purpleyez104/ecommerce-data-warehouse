# T7 M2.5 MySQL 集成验收实施计划

## Planned Runtime Scope

Phase 2 预计只在确有必要时新增一个安全的 T7 PowerShell 验收入口及对应本地 safety/parse test；现有 DDL、Seed、Generator 和预期结果默认作为只读输入：

- `tests/m2/invoke_mysql_acceptance.ps1`：串行执行 preflight、双 Database 验收、摘要生成和受控清理。
- `tests/m2/test_invoke_mysql_acceptance.ps1`：不连接 MySQL，验证 Database 前缀、显式确认、失败传播、去敏和 cleanup guard。
- `.local-notes/m2/t7/<run-id>/`：运行时去敏日志与摘要；不提交 Git。

若现有入口经 Phase 2 复核已能完整覆盖，则不为形式新增脚本；实际修改文件范围必须在开始实现前单独确认。

## Execution Order

1. Preflight：复核 Git 状态、MySQL 8.0.46、client 可用性、最小权限账号、进程环境变量、规范化后的 `run-id` 和两个目标 Database 均为本轮新建。
2. Static gate：运行 DDL contract、fixed Seed contract、Generator 12 个 Python tests 和 `git diff --check`。
3. Safety gate：对拟用验收入口运行本地 test，确认缺少显式隔离确认、错误前缀或缺失密码时均在任何 Database 写入前非 0 退出。
4. Fixed lane：创建隔离 Database、执行 Candidate DDL、加载 fixed Seed并核对 19 表预期结果。
5. Rerun lane：运行 `invoke_fixed_seed_idempotency.ps1`，确认同内容 no-write；用受控副本模拟 drift，确认 nonzero 且基线不变。
6. MySQL failure lane：逐个执行 5 个 SQL 约束失败场景，记录预期错误类别、非 0 和 rollback 后基线摘要。
7. Generator lane：以固定参数生成两份 SQL并比较 SHA-256，在第二个隔离 Database 执行 DDL 与一份 Generator SQL，再核对跨表结果。
8. Incremental semantics：对受控记录执行允许的变化，核对 `update_time` 变化与 `(update_time, *_pk)` 查询边界；恢复或丢弃该隔离 Database。
9. Cleanup：按精确反向顺序清理本轮对象，确认两个 T7 Database 不再存在；保留去敏 summary。
10. Coordinator acceptance：逐条核对 T7 Acceptance Criteria。只有全部 Hard Gate 通过，才另行提出 M2 `completed`、docs 同步和 Trellis 归档方案。

## Verification Commands

规划阶段静态验证：

```powershell
E:\Software\Python\3.12.10\python.exe -W ignore .trellis\scripts\task.py validate .trellis\tasks\09-11-t7-m2-5-mysql-acceptance
git diff --check
git status --short
```

Phase 2 开始前复跑现有基线：

```powershell
pwsh -NoProfile -File tests\contracts\validate_mysql_ddl_contract.ps1
pwsh -NoProfile -File tests\contracts\test_validate_mysql_ddl_contract.ps1
pwsh -NoProfile -File tests\m2\test_validate_fixed_seed_contract.ps1
E:\Software\Python\3.12.10\python.exe -m unittest discover -s tests\m2 -p "test_*.py"
```

计划中的 Runtime 入口形式如下；该命令必须在脚本实现、范围确认和操作者确认两个隔离 Database 后才能执行：

```powershell
pwsh -NoProfile -File tests\m2\invoke_mysql_acceptance.ps1 -Server <private-host> -Port 3306 -User <least-privileged-user> -RunId <run-id> -ConfirmIsolatedDatabases
```

密码由进程环境变量 `M2_TEST_MYSQL_PASSWORD` 提供，不得出现在命令或日志中。

## Review Gates

- Scope：不修改 M1、M3、指标、Hive、DataX 或 ECS 配置。
- Safety：不接触既有 `ecommerce_oltp`；所有写入和清理都受 T7 prefix、`run-id` 与显式开关保护。
- Evidence：以 Hard Gate 摘要为主，不为证明同一事实重复采集证据。
- State：静态通过不提升为 `verified`；MySQL 局部失败不允许 M2 收尾。
- Git：`.gitignore` 和其他活动 Task 不进入 T7 提交。

## Stop Conditions

- 目标不是全新的隔离 Database，或账号权限超出验收所需范围。
- MySQL 版本、DDL/Seed digest 或 Generator baseline 与已接受输入不一致。
- 任何 cleanup guard、Secret 去敏或失败传播检查不成立。
- 发现需要改变已确认业务语义、DDL 物理结构或固定数据口径。
