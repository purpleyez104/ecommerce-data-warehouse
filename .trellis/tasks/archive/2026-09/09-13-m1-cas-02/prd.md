# M1-CAS-02 MySQL 验收脚本

## Task Identity

- Task ID：`M1-CAS-02`
- Title：MySQL 8.0.46 功能与恢复验收脚本

## Goal

生成能够证明 MySQL 版本、三节点私网访问、ROW/FULL Binlog I/U/D 和受控重启恢复的可审计证据。

## Scope

- 版本、`systemd`、3306、实际配置加载路径和关键变量。
- 三节点 TCP 与认证查询。
- 严格前缀临时 Database/Table 中的固定 `INSERT/UPDATE/DELETE`。
- Binlog Position 与 `Write_rows/Update_rows/Delete_rows`。
- 显式授权后的重启和哨兵恢复。

## Out of Scope

- 不操作 `ecommerce_oltp`、`hive_metastore`、M2 DDL、Seed 或账号权限。
- 不修改 MySQL 永久配置。

## Inputs / Dependencies

- `M1-CAS-01` 完成并冻结。
- MySQL 8.0.46 已运行、三节点 SSH、VM 上权限不高于 `0600` 的 Secret 文件。

## Files / Modules

- `scripts/m1/verify-mysql.sh`
- Evidence Inbox：`.local-notes/m1-evidence/inbox/m1-cas-02-mysql/`

## Acceptance Criteria

- [x] 版本、服务、监听、配置路径与 Binlog 关键变量均有证据。
- [x] 三节点私网连接与认证查询成功。
- [x] 固定 I/U/D 对应 Row Event 且 Binlog Position 推进。
- [x] 默认不重启并输出 `PARTIAL`。
- [x] 只有 `EXISTING_MYSQL_INSTANCE` 才允许重启；恢复后哨兵存在才可 `PASS`。
- [x] 仅删除本次临时 Database，失败返回非零。
- [x] Work 会话首先创建专属 Evidence Inbox；VM 原始 run 目录由用户原样放入。
- [x] 在用户回传并经协调会话审查前，MySQL Runtime 保持 `not_run`/未 `verified`。

## Verification

- `bash -n scripts/m1/verify-mysql.sh`
- `M1-CAS-07` 静态 Guard。
- VM 固定功能、Binlog、受控重启和 Cleanup 证据。

## Risk

- MySQL 重启会影响 Hive Metastore；错误 Cleanup 可能伤及正式数据库。

## 是否适合并行

- 实现可在 `M1-CAS-01` 后与 `M1-CAS-03～06` 并行；VM 验收必须第一个执行。

## 是否需要 Worktree

- 当前单 Agent 不需要；若独立 Implementer 并行写入则需要。

## User Decision

- 实现无新增决策；VM 重启需用户显式授权。

## Acceptance Result

- Status：`completed`。
- Completion Note：MySQL 8.0.46 的版本、三节点私网认证、ROW/FULL Binlog I/U/D、默认非中断路径、受控重启恢复、哨兵检查和严格临时 Database Cleanup 已通过协调验收。
- Verification Note：按 `DR-027` 的风险分级口径，脚本 SHA-256、已审查的 `set -euo pipefail` 控制流、`summary.env` 中的 `functional_check=PASS`、`recovery_check=PASS`、`cleanup=PASS` 和最终 `exit_code=0` 共同构成最小充分证据；独立 recovery 分文件不再作为技术阻断。
- Remaining Follow-up：远程 Secret 严格键值解析作为 non-blocking hardening，后续仅在相关脚本再次修改或安全加固 Task 中处理，不阻断本 Task 完成。
