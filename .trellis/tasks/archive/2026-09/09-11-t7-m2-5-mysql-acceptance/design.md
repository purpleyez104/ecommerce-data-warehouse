# T7 M2.5 MySQL 集成验收设计

## Boundary

T7 只在已通过 M1 门禁的 MySQL 8.0.46 上验证现有 M2.2 Candidate DDL、M2.3 fixed Seed 和 M2.4 Generator 输出，并据真实结果判断 M2 是否具备收尾条件。它不进入 M3，不修改业务模型、指标口径、ECS 服务或 M1 配置，也不把局部成功提升为完整链路验证。

## Acceptance Topology

一次验收使用唯一 `run-id`，并创建两个专用 Database：

- `ecommerce_oltp_t7_fixed_<run-id>`：DDL、fixed Seed、同内容重跑、漂移拒绝和 5 个 MySQL 约束失败场景。
- `ecommerce_oltp_t7_generated_<run-id>`：DDL、固定参数 Generator SQL、重复生成 checksum、首次装载和结果核对。

`run-id` 必须先规范化并校验为小写字母、数字和下划线，Database 名必须匹配 T7 前缀并由操作者显式传入确认开关。不得复用 `ecommerce_oltp` 或任何已有业务 Database，不得关闭 `FOREIGN_KEY_CHECKS`。密码只通过进程环境变量传入，不写入命令行、日志、Task 或 Git。

## Data Flow and Contracts

1. 先运行现有静态 Contract，确认 DDL、Seed、预期 JSON 和 Generator 未漂移。
2. 在两个空的隔离 Database 中分别按 `DR-020` 顺序执行同一份 Candidate DDL。
3. fixed 通道首次写入 19 表 Seed，并按 `mock/m2_fixed_seed_expected_results.json` 核对表数、逐表行数、业务键和内容 digest。
4. fixed 通道再次运行 idempotency runner：内容一致时不写入并返回 0；构造受控漂移时返回非 0 且不写入。
5. 5 个 MySQL constraint failure case 分别在独立事务中执行，预期失败后回滚，并核对基线未变化。
6. Generator 使用 `--seed 42 --start-date 2025-01-29 --days 4 --scale 1` 生成两次 SQL；两个文件 checksum 必须一致，再将其中一份装载到 generated 通道。
7. generated 通道核对 19 表存在、引用完整性、状态合法性、金额/数量守恒、生成列行为和 `update_time` 查询边界。
8. 最后按 DDL 头部精确反向顺序清理两个 T7 Database；清理失败必须报告为未完成，不得隐去残留。

Python 写入层的 9 个跨行失败规则不伪装成 MySQL constraint。它们继续由 `tests/m2/test_generator_rules.py` 和 `tests/m2/test_generate_ecommerce_oltp.py` 验证；T7 只补充 Generator SQL 在真实 MySQL 上的执行与结果核对。

## Minimal Evidence

采用风险分级后的最小充分证据，不要求重复截图或逐语句附件：

- Hard Gate：MySQL 精确版本、隔离 Database 名、各阶段退出状态、DDL 19 表、fixed/generated 结果摘要、预期失败与基线不变、清理结果。
- Process Check：输入文件 SHA-256、Generator 参数与输出 SHA-256、开始/结束时间、实际 MySQL client 版本。
- Optional：只有发生异常或需要人工判断时才保留额外查询结果或截图。

原始去敏证据保存在 `.local-notes/m2/t7/<run-id>/`，不提交 Git。正式文档只在验收完成后按单独批准范围写入结论和可复现命令。

## Failure and Rollback

- 任一 Hard Gate 失败，立即停止后续状态提升，T7 保持 `in_progress` 或 `blocked`，M2 保持 `in progress`。
- Schema 清理只允许作用于本轮两个、且名称通过前缀与 `run-id` 双重校验的 Database。
- 表级回滚遵循 `refund_attempt` 到 `user_account` 的精确反向顺序；不得对既有 Database 执行 `DROP TABLE` 或 `DROP DATABASE`。
- 如果 MySQL 8.0.46 行为与已确认语义冲突，记录 `DECISION_REQUIRED`，不静默修改 DDL、Seed 或 Generator。

## Parallelism and Worktree

真实 MySQL 验收串行执行，不适合并行，也不需要 Worktree。只读 Reviewer 可在结果产生后独立复核摘要，但不得与执行者同时操作验收 Database。
