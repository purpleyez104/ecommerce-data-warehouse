# Technical Design

## Boundary

公共库只提供纯 Evidence/Safety Helper，不知道 MySQL、Hive、Kafka、Spark 或 DataX 的命令和对象。

## Public Shell API

- 初始化：验证 `run-id`、输出根、目录唯一性和权限。
- 执行记录：步骤编号、开始/结束时间、命令描述、退出码和日志路径。
- 断言：固定字符串、正则、数字和值集合检查。
- 证据：SHA-256、去敏白名单和 `summary.env`。
- Cleanup：注册临时对象并在严格 Guard 后调用组件提供的删除函数。

## Evidence Layout

```text
<output-root>/<run-id>/
  summary.env
  commands.log
  assertions.log
  versions/
  configuration/
  runtime/
  functional/
  recovery/
  cleanup/
```

## Status Contract

- `PASS`：适用的功能、失败路径、恢复和 Cleanup 全部完成。
- `PARTIAL`：非中断部分通过，但授权型恢复未运行或存在明确非致命缺证。
- `FAIL`：必需断言、安全检查或 Cleanup 失败，返回非零。

## Safety

- 拒绝 `/`、`/data`、输出根本身、含 `..` 或不含当前 run-id 的 Cleanup 目标。
- 去敏词覆盖 Password、Secret、Token、Private Key 和 JDBC Password。
- 不使用 `eval`，不把 Secret 拼入命令描述。

## Rollback

删除本 Task 新增的公共库；在任何组件尚未开始前不存在调用方迁移。

## Evidence Inbox Contract

- 路径：`.local-notes/m1-evidence/inbox/m1-cas-01-common-contract/`。
- Work 会话负责创建且不得清空已有内容。
- 只保存公共库的本地语法、Contract 和 Mutation Test 输出，并标记 `local_static`。
- 该目录不包含 VM 组件 Runtime 证据，也不提交 Git。
