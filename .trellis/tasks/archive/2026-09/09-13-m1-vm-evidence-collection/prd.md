# M1 虚拟机与组件现场采集

## Goal

提供一个在 `hadoop201` 由 `yee` 执行的无中断、去敏证据采集入口，获得三节点 ECS 的真实虚拟机环境，以及 MySQL、Hive、Kafka KRaft、Spark on YARN、DataX 已安装现场中的版本、路径、进程、端口和关键配置，为后续逐组件功能验收提供事实输入。

## Background

- Milestone 1 当前为 `in progress`；Hadoop 3.4.1 已有真实功能和受控重启证据，其他组件仍需按现场证据分别判断。
- 用户说明 MySQL、Hive、Kafka KRaft、Spark on YARN、DataX 已可进行部分验收，并要求先验收虚拟机环境，后续再提供搭建过程中的重要修复和决策。
- 当前仓库已有 Hadoop 验收脚本和 `/data/logs/ecommerce-data-warehouse/m1/` 证据目录约定。

## Requirements

### R1 执行与范围

- 新脚本必须在 `hadoop201` 由 `yee` 执行，并通过现有免密 SSH 只读采集 `hadoop201`、`hadoop202`、`hadoop203`。
- 必须接收安全格式的 `--run-id` 和新的绝对 `--output-dir`；不得复用非空输出目录。
- 只实施现场采集，不执行组件功能链路、服务重启、软件安装、配置修改、数据库对象创建、Kafka Topic 创建或 NameNode 格式化。

### R2 三节点虚拟机证据

- 每个节点采集 hostname、当前用户、时间与时区、OS、Kernel、CPU、Memory、Swap、Load。
- 每个节点采集 block device、filesystem、mount、磁盘容量、`/data` 的属主、权限和写权限状态。
- 每个节点采集 `ulimit`、Java 11/17 的实际路径与版本、关键进程及监听端口。
- 从 `hadoop201` 验证三节点 SSH、主机名解析和私网连通；检查时间偏差并在超过允许阈值时标记失败。

### R3 组件安装现场

- 探测 MySQL、Hive、Kafka、Spark、DataX 的命令路径、安装目录、稳定软链接、精确版本、运行进程、监听端口、数据目录和日志目录。
- 只读取白名单配置项。至少覆盖：
  - MySQL：监听地址/端口、数据目录、日志、Binlog、字符集、时区相关配置。
  - Hive：Metastore、HiveServer2、Warehouse、Hadoop 配置目录和 Metastore JDBC URL（仅保留去敏后的 host/port/database）。
  - Kafka KRaft：`process.roles`、`node.id`、listeners、controller quorum、log directories 和 cluster id；不得输出凭据。
  - Spark：`SPARK_HOME`、Hadoop/Hive 配置目录、YARN、event log/history、warehouse 和默认提交相关配置。
  - DataX：`DATAX_HOME`、Python/Java 入口、版本或构建标识、MySQL Reader/HDFS Writer plugin 路径和核心日志路径。
- 组件未安装、命令不可用或配置未知时必须记录 `NOT_FOUND` 或 `UNKNOWN`，不得导致其他节点证据丢失。

### R4 安全与证据边界

- 不采集密码、Token、Secret、私钥、完整 JDBC Credential、MySQL 用户列表或业务数据。
- 配置解析必须使用明确白名单；不得复制完整配置文件。
- 输出目录使用 `umask 077`，原始结果只留在 ECS，不加入 Git。
- 用户按 `DR-007` 将完整运行目录原样下载到 `.local-notes/m1-evidence/inbox/<run-id>`，供后续读取和验收。
- 汇总只使用 `COLLECTED`、`PARTIAL`、`FAIL`，不得把本次盘点结果表述为组件 `verified`。

### R5 文档与测试

- 更新 `scripts/m1/README.md`，写明命令、前置条件、输出、退出状态、限制和失败处理。
- 新增 PowerShell 静态 Contract Test，检查危险命令缺失、参数/节点/输出目录保护、去敏边界、必要采集项和 README 使用示例。
- 初始采集实现不修改项目状态文档；真实 ECS 输出回传并经用户确认后，允许按证据等级同步 `README.md`、M1 事实/兼容性/排障文档、`CHANGELOG.md` 和 `docs/decision-register.md`。

### R6 回传证据评审与收口

- 读取完整 VM 运行目录和用户提供的 Step 1-12 搭建总结，区分直接现场证据、总结性证据、正式决策与 `DECISION_REQUIRED`。
- 只将三节点 VM 基线和既有 Hadoop 证据保持为 `verified`；MySQL、Hive、Kafka、Spark、DataX 在组件级原始日志和剩余门禁闭合前保持 `candidate`。
- 修正采集器对 DataX 历史稳定入口的漏检，并显式采集 Java 8、Java 进程可执行文件、Hive 并存版本和三节点 Hive 软链接一致性。
- 不创建 `infra/versions.env`，不把兼容性 Smoke Test 描述为 Milestone 3 或 Milestone 9 已完成。

## Acceptance Criteria

- [x] `collect-vm-environment-evidence.sh --help` 的接口与 README 一致。
- [x] 非 `yee`、非 `hadoop201`、非法 `run-id`、非绝对或过宽输出目录、非空输出目录均在采集前返回非零或已由静态 Contract 覆盖；ECS 身份路径仍随真实执行核对。
- [ ] 三节点各自生成可定位的 system、storage、network、runtime 和 component inventory 证据。
- [ ] 汇总明确列出每节点采集状态、时间偏差、关键目录检查以及五个组件的 `FOUND / NOT_FOUND / UNKNOWN` 状态。
- [x] 输出契约使用敏感键白名单排除和 JDBC URL 去敏；真实输出仍需在回传后复核。
- [x] README 要求回传完整运行目录而非仅回传 `summary.env`，并使用 `.local-notes/m1-evidence/inbox/<run-id>` 隔离原始证据。
- [x] 脚本不包含服务 start/stop/restart、安装、远程配置写入、数据库/Topic 创建、HDFS 删除或 NameNode format 行为。
- [x] 静态 Contract Test 实际执行并通过。
- [x] Bash 语法检查已使用现有 Git Bash 实际执行并通过。
- [x] 三节点 VM 回传证据已评审，VM 基线通过；五个组件的功能验收缺口已分别记录。
- [x] 重要修复、候选版本、端口、环境示例和正式决策已按职责同步，未提高无原始证据组件的状态。
- [x] DataX/Hive/Java 补充采集 Contract 已加入并通过静态测试。

## Out of Scope

- MySQL DDL/Seed/M2.5 验收。
- Hive 外部表、Beeline、Metastore/HS2 重启验收。
- Kafka 生产、消费、重放和 Broker 重启验收。
- Spark on YARN 的 Hive ORC + Snappy 读写验收。
- DataX MySQL Reader 到 HDFS Writer 的最小链路验收。
- 任何组件安装、修复、版本调整、服务重启、云安全组修改或正式状态提升。

## Technical Notes

- 后续组件验收应以本 Task 输出和用户提供的真实修复/决策为输入，逐组件形成固定输入、预期结果、退出状态、日志位置和回滚方式。
- 现有 `.gitignore`、`AGENTS.md`、T6/T7 Trellis 改动属于用户已有工作，必须保持不变。

## Closure Result

- Disposition：`completed_under_recalibrated_acceptance`。
- Completion Note：现场采集器、静态 Contract、VM 基线回传和项目事实同步已完成；`DR-026` 已接纳 Step 2～12 作为 M1 Runtime 基线。
- Verification Note：按 `DR-027`，尚未逐项补齐的节点级附件属于 Optional Evidence，不再阻断本 Task 收尾。
- Remaining Follow-up：DolphinScheduler 3.4.2 是当前唯一 M1 Runtime 门禁，由独立精简 Task 跟踪。
