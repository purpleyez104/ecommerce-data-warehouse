# M1 五组件功能验收脚本

## Task Identity

- Task ID：`m1-component-acceptance-scripts`
- Title：M1 五组件功能验收脚本
- Priority：`P1`

## Goal

为已经部署在 `hadoop201`、`hadoop202`、`hadoop203` 上的 MySQL、Hive、Kafka KRaft、Spark on YARN 和 DataX 提供五个可独立执行的验收脚本。脚本必须采集版本、关键配置路径、进程与端口、固定功能结果、失败行为和受控恢复证据，并将结果写入可回传的证据目录，供 Codex 进行后续只读验收。

## Background

- Hadoop 3.4.1 已有真实运行证据，本 Task 不重复格式化、初始化或扩大 Hadoop 验收范围。
- 当前现场盘点只能证明五个组件已部署或有部分运行事实，尚不足以把它们整体提升为 `verified`。
- 组件版本、安装路径、服务拓扑和搭建期间的重要修复以当前仓库文档和用户回传证据为基线；脚本执行结果才是本轮运行验收的主要证据。
- 五组件按 `MySQL → Hive → Kafka KRaft → Spark on YARN → DataX` 顺序验收，但每个脚本可单独重跑。

## In Scope

- 新增五个 Linux Shell 验收脚本：
  - `scripts/m1/verify-mysql.sh`
  - `scripts/m1/verify-hive.sh`
  - `scripts/m1/verify-kafka-kraft.sh`
  - `scripts/m1/verify-spark-yarn.sh`
  - `scripts/m1/verify-datax.sh`
- 新增一个只包含公共安全校验、日志和摘要函数的最小共享库 `scripts/m1/lib/evidence-common.sh`。
- 新增一个 PowerShell 静态 Contract 测试 `tests/m1/test_component_acceptance_scripts.ps1`。
- 更新 `scripts/m1/README.md`，说明前置条件、执行顺序、参数、影响、退出码、证据目录、清理和回传方法。
- 脚本从 `hadoop201` 发起，通过既有 SSH 免密连接检查必要的远端节点。

## Out of Scope

- 安装、升级、重新初始化或永久修改 MySQL、Hive、Kafka、Spark、DataX、Hadoop 或 JDK 配置。
- 创建或修改 `infra/versions.env`；只有全部 M1 版本完成真实验收后才另行决定。
- 运行或修改 M2 的 `ecommerce_oltp` Candidate DDL、fixed seed、Generator 或 M2.5 验收。
- 创建正式 Hive ODS 表、正式 Kafka Topic、正式 Spark/DataX 作业，或提前完成 M3、M8、M9。
- 验收 Doris、DolphinScheduler、Flink，或证明生产级 HA、Exactly-Once、性能收益。
- 将凭据、原始 Secret、完整配置文件或无关运行日志写入仓库或证据包。

## Inputs / Dependencies

- 当前 `README.md`、`docs/spec.md`、`docs/plan.md` 的 M1 门禁与证据规则。
- `docs/compatibility-matrix.md`、`docs/installation-troubleshooting.md` 和 `docs/decision-register.md` 中的已确认版本、DR-022、DR-023、DR-024 与待决事项。
- 已有 `scripts/m1` 的安全 `run-id`、证据目录、受控重启、临时对象和日志 Pattern。
- 用户回传的 VM 盘点与搭建修复记录；这些材料只作为脚本设计输入，不替代新脚本产生的运行证据。
- 运行时依赖：三节点 SSH、既有组件服务、HDFS/YARN、受保护 MySQL Secret 文件及用户对中断测试的逐项授权。

## Files / Modules

- Task 规划：`.trellis/tasks/09-13-m1-component-acceptance-scripts/`
- Child Task / Story：`.trellis/tasks/09-13-m1-cas-01/` 至 `.trellis/tasks/09-13-m1-cas-07/`
- Shell 实现：`scripts/m1/`、`scripts/m1/lib/`
- Operator 文档：`scripts/m1/README.md`
- 静态验证：`tests/m1/test_component_acceptance_scripts.ps1`
- 后续 VM 证据：`.local-notes/m1-evidence/inbox/<run-id>/`，不提交 Git。

### Evidence Inbox Mapping

| Task ID | Evidence Inbox |
| --- | --- |
| `M1-CAS-01` | `.local-notes/m1-evidence/inbox/m1-cas-01-common-contract/` |
| `M1-CAS-02` | `.local-notes/m1-evidence/inbox/m1-cas-02-mysql/` |
| `M1-CAS-03` | `.local-notes/m1-evidence/inbox/m1-cas-03-hive/` |
| `M1-CAS-04` | `.local-notes/m1-evidence/inbox/m1-cas-04-kafka-kraft/` |
| `M1-CAS-05` | `.local-notes/m1-evidence/inbox/m1-cas-05-spark-yarn/` |
| `M1-CAS-06` | `.local-notes/m1-evidence/inbox/m1-cas-06-datax/` |
| `M1-CAS-07` | `.local-notes/m1-evidence/inbox/m1-cas-07-integration-handoff/` |

## Functional Requirements

### Common

- 每次执行必须显式接收安全格式的 `--run-id`，且只在 `/data/logs/ecommerce-data-warehouse/m1/<run-id>/` 下创建本次证据。
- 拒绝已存在或非空的目标证据目录，使用 `umask 077`，并记录开始时间、结束时间、主机、组件、命令退出状态。
- 每个脚本输出原始步骤日志和机器可读的 `summary.env`；最终状态只能是 `PASS`、`PARTIAL` 或 `FAIL`。
- 任何必需断言失败都必须返回非零退出码；未执行受控重启或故障注入时，相关组件最多为 `PARTIAL`。
- 临时对象必须使用 `m1_accept_<run-id>` 派生的严格前缀，只能删除脚本自己创建且已验证前缀的对象。
- 采集关键配置的文件路径、权限、SHA-256 和去敏白名单键值，不复制包含密码、Token、Private Key 或完整 JDBC Credential 的文件。
- 不使用执行机器当前日期推断业务日期；本 Task 的固定测试数据使用脚本内明确常量，不代表正式业务数据。

### MySQL

- 验证 MySQL 8.0.46 版本、`systemd` 状态、监听地址/端口和三节点私网可达性。
- 采集实际配置文件加载路径以及 `server_id`、`log_bin`、`binlog_format=ROW`、`binlog_row_image=FULL` 等关键结果。
- 在独立临时数据库中执行固定 `INSERT`、`UPDATE`、`DELETE`，证明 Binlog 位置推进并出现对应 Row Event；不得接触 `ecommerce_oltp` 或 Hive Metastore 数据库。
- 只有提供精确确认参数时才执行受控 MySQL 重启，并验证重启前哨兵数据在恢复后仍存在。

### Hive

- 验证 Hive 3.1.3、Metastore、HiveServer2、Beeline 连通、9083/10000/10002 监听和实际服务 Java executable。
- 采集 Hive 配置路径及去敏关键项，并明确记录服务端和 YARN Container 实际使用的 Java；不得预设 Hive Runtime Java 8/11 的最终决策。
- 创建独立临时 Database/Table，以 ORC + Snappy 写入固定数据，强制执行一个 YARN MapReduce 路径，核对查询结果、文件格式和压缩。
- 只有提供精确确认参数时才调用现有组件级启停脚本重启 Hive，并验证哨兵数据与 Beeline 查询恢复。

### Kafka KRaft

- 验证 Kafka 3.9.1、Scala 2.12、三节点 combined broker/controller 进程、9092/9093、Cluster ID、Controller Quorum、Broker 列表及关键去敏配置。
- 创建唯一临时 Topic，显式使用复制因子 3、`min.insync.replicas=2`，完成固定消息生产、消费和指定 Offset 重放。
- 只有提供精确确认参数时才停止并恢复一个指定 Broker，验证降级期间可继续生产消费、ISR 变化和恢复后 ISR 回到三副本。
- 任何路径都禁止执行 `kafka-storage.sh format`，禁止删除或改写 `/data/kafka/kraft-combined-logs`。

### Spark on YARN

- 验证 Spark 3.5.9、Hadoop Profile、提交入口、关键配置路径以及 YARN 可用性。
- 以固定输入提交 Spark SQL on YARN 作业，读写 Hive ORC + Snappy 临时对象，核对固定结果并保存 YARN Application ID、Final-State 和聚合日志。
- 再提交一个预期失败的固定作业，证明客户端非零退出且 YARN 最终状态可解释；Spark 不执行服务重启。

### DataX

- 验证 DataX 202309 Runtime、`/data/module/datax/bin/datax.py`、Python/JDK、`mysqlreader` 和 `hdfswriter` Plugin；`/data/module/datax-current` 只作为历史残留检测项。
- 在 `hadoop202` 和 `hadoop203` 分别运行隔离的固定 MySQL → HDFS ORC + Snappy 测试，随后通过 Hive/Spark 核对内容、格式和压缩。
- 凭据只能来自脚本外部的受保护 Secret 文件；临时 DataX Job JSON 使用 `0600` 权限并在受控路径内清理，日志必须去敏。
- 运行一个预期失败的固定 Job，证明 DataX 返回非零状态且错误可定位。
- 测试用 ODS `STRING` 映射只证明当前 Smoke Workaround，不代表 M3 正式 Schema 决策。

## Acceptance Criteria

- [ ] 五个脚本、公共库、Contract 测试和 README 均已实现，文本为 UTF-8、LF、末尾换行，Shell 使用 2 空格缩进。
- [ ] 静态 Contract 测试实际通过，并检查 run-id、证据目录、权限、状态、非零失败、Secret 去敏和危险命令禁令。
- [ ] `bash -n` 对五个脚本及公共库实际通过；如本机无 Bash，明确记录为 `not_run`，不能声称通过。
- [ ] 所有运行影响和中断操作均有精确确认参数；默认执行不会停止服务、格式化存储或触碰正式业务对象。
- [ ] 每个脚本均记录固定输入、预期结果、预期退出码、实际结果、日志位置、已知限制和清理结果。
- [ ] 用户能按 README 在虚拟机执行，并把完整 run 目录放入 `.local-notes/m1-evidence/inbox/<run-id>/`。
- [ ] 每个 Child Task 的 Work 会话首先创建自己的专属 Evidence Inbox，并在 Handoff 中报告绝对路径。
- [ ] Work 会话只可写入本地静态证据；VM Runtime 原始证据由用户放入对应组件 Inbox，本协调会话只读审查。
- [ ] 脚本进入仓库最多证明 `implemented`；只有后续现场证据逐项满足门禁后，对应组件才可评为 `verified`。

## Verification

- Task 规划：`python .trellis/scripts/task.py validate .trellis/tasks/09-13-m1-component-acceptance-scripts`
- Shell 语法：对公共库和五个脚本逐一运行 `bash -n`。
- 静态 Contract：运行 `pwsh -File tests/m1/test_component_acceptance_scripts.ps1`，并完成关键安全 Guard 的最小 Mutation Check。
- 回归：运行已有 `pwsh -File tests/m1/test_collect_vm_environment_evidence.ps1`。
- 文本与 Diff：检查 UTF-8、LF、末尾换行和 `git diff --check`。
- Runtime：由用户在 VM 按 README 串行执行；Codex 后续只读审查回传证据。未运行不得标记为通过。

## Risks

- 中断测试可能短暂影响已有服务，必须使用精确确认参数并先验证下层依赖健康。
- Hive Runtime Java 尚未最终确认，只能采集实际值，不能在脚本中自动修改。
- DataX 运行时需要短暂读取 Credential，必须依赖受保护文件、私有临时目录和去敏日志。
- 当前工作区已有其他用户改动；实现必须使用严格文件范围，不能覆盖或混入无关内容。
- 五个组件可以分别实现，但共享 Evidence Contract 若未先冻结会造成接口漂移。

## Parallelism

- Parent Task 本身不整体并行启动；先串行完成共享 Contract 和公共库。
- `M1-CAS-01` 完成并冻结公共接口后，`M1-CAS-02～06` 在文件所有权隔离时可以并行实现。
- 当前用户未授权并行 Agent，因此推荐按 Child Task ID 串行实施。
- Contract 测试与 README 的最终定稿必须等待五个组件脚本完成。
- VM Runtime 验收必须按 M1 门禁顺序串行执行。

## Worktree Decision

- 当前采用单 Agent、顺序写入且文件范围可隔离，不需要新增 Worktree。
- 如果用户后续明确授权多个写入型 Sub-agent 并行实现五个组件脚本，则每个 Implementer 需要独立 Worktree；`evidence-common.sh`、README 和测试仍由单一 Owner 维护。

## Child Tasks / Stories

| Task ID | Title | Dependency | Implementation | VM Runtime |
| --- | --- | --- | --- | --- |
| `M1-CAS-01` | 共享 Evidence Contract 与公共库 | 无 | 必须最先串行 | 不适用 |
| `M1-CAS-02` | MySQL 验收脚本 | `01` | 可并行，当前推荐串行 | 第 1 |
| `M1-CAS-03` | Hive 验收脚本 | `01` | 可并行，当前推荐串行 | 第 2 |
| `M1-CAS-04` | Kafka KRaft 验收脚本 | `01` | 可并行，当前推荐串行 | 第 3 |
| `M1-CAS-05` | Spark on YARN 验收脚本 | `01` | 可并行，当前推荐串行 | 第 4 |
| `M1-CAS-06` | DataX 验收脚本 | `01` | 可并行，当前推荐串行 | 第 5 |
| `M1-CAS-07` | 集成测试与交付 | `01～06` | 必须最后串行 | 不适用 |

## Open Decisions

- 无需用户在实现前新增业务或架构决策。
- Hive Runtime Java 的最终选择继续保持 `DECISION_REQUIRED`；本 Task 只采集实际运行证据。
- 若现场 `start-cluster.sh` / `stop-cluster.sh` 不在 `PATH`，脚本应明确失败并提示用户提供现有脚本的绝对路径，不能猜测或生成替代启停逻辑。

## Closure Result

- Disposition：`partially_delivered_then_superseded`。
- Delivered：M1-CAS-01 共享 Evidence Contract 与 M1-CAS-02 MySQL 验收脚本已完成并归档。
- Not Implemented / Not Required：M1-CAS-03～07 的 Hive、Kafka、Spark、DataX 和五脚本集成交付因 `DR-026`、`DR-027` 已不再属于 M1 必需门禁，按 superseded 行政关闭。
- Remaining M1 Gate：DolphinScheduler 3.4.2 由独立精简 Task 管理；不属于本 Parent 的原五组件范围。
