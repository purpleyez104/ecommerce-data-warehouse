# Design：M1 虚拟机与组件现场采集

## 1. 边界

实现单一 Bash 入口 `scripts/m1/collect-vm-environment-evidence.sh`。脚本从 `hadoop201` 编排三节点只读采集，不把现场发现自动写回仓库，也不执行任何服务生命周期或业务功能操作。

## 2. 输入与输出契约

输入：

- `--run-id <safe-id>`：匹配 `[A-Za-z0-9][A-Za-z0-9._-]{0,79}`。
- `--output-dir <absolute-path>`：必须是绝对路径，不得为 `/` 或 `/data`，且现有目录必须为空。

输出目录建议：

```text
/data/logs/ecommerce-data-warehouse/m1/<run-id>/
  collect-vm-environment-evidence.log
  summary.env
  hadoop201/
  hadoop202/
  hadoop203/
```

每节点目录保存：

- `identity-system.txt`
- `network-time.txt`
- `storage.txt`
- `limits-runtime.txt`
- `process-ports.txt`
- `component-inventory.txt`
- `component-config-whitelist.txt`

`summary.env` 记录运行编号、整体采集状态、三节点结果、时间偏差和组件发现状态。`COLLECTED` 表示全部预期采集动作完成，不表示组件功能已验收。

用户通过 MobaXterm 将完整目录下载到 `.local-notes/m1-evidence/inbox/<run-id>`。后续审查从该本地隔离目录读取，不要求 ECS 直接提交证据。

## 3. 采集流程

1. 在产生输出前验证参数、用户、主机、依赖命令和 SSH。
2. 创建 `umask 077` 的全新输出目录并启动主日志。
3. 对三个节点分别执行受控的内嵌只读采集函数。
4. 将组件探测设计为容错项：一个组件缺失不终止其他证据采集。
5. 聚合节点状态、时间戳、目录与组件发现状态；基础身份/SSH/输出安全失败返回非零，组件缺失产生 `PARTIAL`。

## 4. 配置去敏设计

- 只扫描已知安装位置和命令解析出的配置目录。
- 配置项采用 property/key 白名单输出，先屏蔽包含 `password`、`passwd`、`secret`、`token`、`credential`、`private.key` 的键。
- JDBC URL 仅输出 scheme、host、port、database；删除 user-info 和 query string。
- 不读取 `.env`、SSH 目录、MySQL grant table、Kafka credential store 或业务数据库。
- 无法安全解析的配置标记 `UNKNOWN`，不回退为整文件复制。

## 5. 兼容性

- 目标平台是 Ubuntu 24.04 Bash；优先使用系统基础命令。
- `ss`、`timedatectl`、`systemctl`、`python3` 等非所有节点必有的命令必须使用能力探测和降级输出。
- 组件路径不得只依赖当前交互 Shell 环境变量；同时检查 `command -v`、`/data/module/<component>` 稳定链接和受限候选目录。
- Hadoop 已 verified，本脚本只采集其共存现场，不重复 Hadoop 功能/重启测试。

## 6. 失败与回滚

- 采集失败保留已经生成的只读证据和 `summary.env`，便于诊断。
- 脚本不改变服务或配置，因此运行回滚仅是人工删除本次明确 `run-id` 输出目录；脚本自身不提供递归删除功能。
- 仓库回滚仅涉及新增脚本、测试、Task planning artifacts 和 `scripts/m1/README.md` 的本次段落。

## 7. 后续扩展

现场盘点评审后，再分别设计 MySQL、Hive、Kafka、Spark、DataX 的功能验收脚本。每个组件脚本独立控制临时对象前缀、功能输入、失败退出和清理，不把这些破坏面混入本次虚拟机盘点。

## 8. 回传证据归档设计

- VM 采集目录是直接现场证据，允许形成 VM、路径、进程、端口和白名单配置事实。
- Step 1-12 Markdown 是用户确认的搭建总结，用于提取排障和决策；缺少对应原始日志时不单独提升组件状态。
- 当前 Task 只修正 inventory collector 和正式文档，不加入会创建数据库、Hive 表、Kafka Topic、YARN 输出或执行服务重启的组件验收行为。
