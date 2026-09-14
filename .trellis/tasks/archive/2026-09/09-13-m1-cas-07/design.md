# Technical Design

## Test Strategy

- Common Contract：文件集合、共享库、CLI、状态 Schema、输出根、`umask`、Secret 和非零失败。
- Safety Contract：精确确认 Token、临时对象前缀、危险路径和格式化禁令。
- Component Contract：MySQL Row Binlog、Hive ORC/YARN/Java、Kafka RF/ISR/Replay、Spark YARN Success/Failure、DataX 双 Worker/Plugin/Failure。
- Mutation Check：临时改变测试输入中的关键 Guard 文本，证明测试确实失败，不修改真实脚本。

## Documentation Structure

1. 前置条件与 Secret 文件准备。
2. 非中断执行命令。
3. 中断测试的影响、授权 Token 和恢复。
4. `PASS/PARTIAL/FAIL` 与退出码。
5. 证据目录和回传方法。
6. 已知限制与 Runtime 证据边界。

## Rollback

撤销本 Task 对测试和 README 的对应变更；不触碰五组件脚本或其他文档。

## Evidence Inbox Contract

- 路径：`.local-notes/m1-evidence/inbox/m1-cas-07-integration-handoff/`。
- Work 会话保存标记为 `local_static` 的 Contract、Mutation、回归、Shell 语法和 Diff 检查输出。
- 不把五组件 VM 原始证据复制进本目录；协调会话仍从各组件 Inbox 审查。
- 目录不提交 Git，项目运行不得依赖它。
