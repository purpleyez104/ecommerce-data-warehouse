# Technical Design

## Design Summary

采用“五个独立入口 + 一个最小公共库 + 一个静态 Contract 测试”的结构。每个入口只负责一个组件，默认执行非中断检查；MySQL、Hive、Kafka 的重启或单节点停止测试必须显式解锁。脚本不修改永久配置，只创建带 `run-id` 的临时对象和证据。

Parent Task 只维护总体 Contract、依赖和验收顺序。具体实现由七个真实 Child Task / Story 管理：

```text
M1-CAS-01 Common Contract
├── M1-CAS-02 MySQL
├── M1-CAS-03 Hive
├── M1-CAS-04 Kafka KRaft
├── M1-CAS-05 Spark on YARN
└── M1-CAS-06 DataX
     └── M1-CAS-07 Integration and Handoff（依赖 01～06）
```

## File Layout

```text
scripts/m1/
  lib/evidence-common.sh
  verify-mysql.sh
  verify-hive.sh
  verify-kafka-kraft.sh
  verify-spark-yarn.sh
  verify-datax.sh
  README.md
tests/m1/
  test_component_acceptance_scripts.ps1
```

公共库仅提供：参数与 `run-id` 校验、证据目录创建、`umask`、时间戳日志、命令结果记录、SHA-256、去敏输出、临时对象前缀校验、`summary.env` 写入和 Trap 清理。组件命令、断言和恢复逻辑保留在各入口脚本中。

## Frozen Public Evidence API

`M1-CAS-01` 冻结以下函数名、参数顺序和返回语义；`M1-CAS-02～06` 只能调用，不得自行修改公共库。

| API | Parameters | Return contract |
| --- | --- | --- |
| `evidence_init` | `component run_id [output_root]` | `0` 初始化成功；`2` 为输入或重复目录拒绝；目录系统错误原样失败。 |
| `evidence_redact_stream` | stdin → stdout | 成功为 `0`；`sed` 失败返回非零。脱敏 `-p<value>`、`--password=<value>`、`MYSQL_PWD=<value>`，不得修改非密码参数。 |
| `evidence_redact_file` | `source_file destination_file` | `0` 成功；未初始化或源不可读为 `2`；其余 I/O 错误非零。 |
| `evidence_log` | `level message...` | 已初始化时写入去敏 `commands.log`；未初始化为 `2`。 |
| `evidence_run` | `description relative_log command argv...` | 返回被执行 argv 的退出码；不安全路径或空 argv 为 `2`；去敏失败返回去敏程序的非零码。禁止 Command String 与 `eval`。 |
| `evidence_assert` | `assertion_name result detail` | 写入断言并累计状态；有效结果返回 `0`，无效状态或未初始化为 `2`。 |
| `evidence_assert_equals` / `evidence_assert_matches` | `assertion_name expected actual` / `assertion_name expression actual` | 匹配为 `0`，不匹配为 `1`，并写入 `PASS` 或 `FAIL` 断言。 |
| `evidence_sha256` | `file` | stdout 输出 SHA-256；未初始化或非普通文件为 `2`，外部读取失败非零。 |
| `evidence_summary_set` / `evidence_mark_partial` | `key value` / `reason` | 成功为 `0`；未初始化或不安全摘要键为 `2`。 |
| `evidence_register_cleanup` | `handler target [owner]` | `0` 注册；函数、Owner、前缀或目标 Guard 不通过为 `2`。 |
| `evidence_cleanup` | none | 所有已注册 Cleanup 成功为 `0`；任一 Cleanup 失败为 `1`；未初始化为 `2`。 |
| `evidence_finalize` / `evidence_install_exit_trap` | `[exit_code]` / none | `evidence_finalize` 写入摘要，最终非 `FAIL` 为 `0`、`FAIL` 为 `1`；Trap 将退出码交给 finalize。 |

内部 Guard `evidence_require_initialized`、`evidence_is_safe_run_id`、`evidence_is_safe_component`、`evidence_is_safe_output_root` 与 `evidence_cleanup_registration_is_safe` 仅供公共库内部实现；其名称不作为组件调用接口。

## Command Contract

所有脚本的公共入口：

```bash
bash verify-<component>.sh --run-id <component-specific-run-id> [component options]
```

公共参数：

- `--run-id`：必填，只允许小写字母、数字和单个连字符组合，组件前缀必须匹配。
- `--output-root`：可选，默认 `/data/logs/ecommerce-data-warehouse/m1`；必须是绝对路径。

中断型参数：

- MySQL：`--confirm-restart EXISTING_MYSQL_INSTANCE`
- Hive：`--confirm-restart EXISTING_HIVE_SERVICES`
- Kafka：`--failure-node hadoop202 --confirm-single-broker-stop KAFKA_KRAFT_SINGLE_BROKER`

Hive 可选接收 `--start-command`、`--stop-command` 的现有绝对路径；未提供时用 `command -v start-cluster.sh` 和 `command -v stop-cluster.sh`。只允许常规文件、不可包含额外参数，实际调用固定为 `<command> hive`。MySQL 和 Kafka 优先使用明确的 `systemctl` / Kafka 自带生命周期命令，不接受任意 Shell 字符串。

## Evidence Model

每次运行目录结构：

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

`summary.env` 固定写入以下字段（由公共库保证存在）：

```text
schema_version=1
component=mysql|hive|kafka_kraft|spark_yarn|datax
run_id=...
status=PASS|PARTIAL|FAIL
started_at_utc=...
finished_at_utc=...
initiator_host=...
functional_check=PASS|FAIL|NOT_RUN
recovery_check=PASS|FAIL|NOT_RUN
failure_path_check=PASS|FAIL|NOT_RUN
cleanup=PASS|FAIL|NOT_RUN
exit_code=...
```

`functional_check`、`recovery_check`、`failure_path_check` 也可为 `PARTIAL` 或 `NOT_APPLICABLE`；组件通过 `evidence_summary_set` 写入的非敏感扩展字段（例如 `tested_nodes`）是可选字段，不能替代上述固定字段。

原始日志使用步骤编号，记录调用的程序及退出码。可能含 Secret 的命令只记录经过固定模板生成的描述，不记录 argv、环境变量或配置原文。

## Safety and Secret Handling

- 证据目录新建前执行绝对路径、根目录和非空检查；拒绝 `/`、`/data`、输出根本身和含 `..` 的目标。
- Cleanup 必须同时满足：对象由本脚本创建、名称匹配 `m1_accept_`、含当前规范化 run-id、目标不等于系统或正式业务路径。
- 禁止 NameNode format、Kafka storage format、递归删除 Kafka Data Directory、删除非临时 Topic，以及修改 `ecommerce_oltp`、`hive_metastore` 或正式 Hive Database。
- MySQL/DataX 凭据由 VM 上用户预先创建的绝对路径 Secret 文件提供；脚本检查 owner、权限不高于 `0600`，不将该文件复制进证据目录。
- DataX 的临时 Job JSON 位于本次私有临时目录，权限 `0600`；Trap 仅删除经路径和前缀双重验证的该文件。
- 所有关键配置只输出白名单字段；Password、Secret、Token、Private Key、JDBC Password 统一写为 `[REDACTED]`。

## Component Flows

### MySQL

1. Preflight：主机、SSH、二进制、服务、3306、版本与配置加载路径。
2. Configuration：通过 SQL 读取关键变量，三节点分别完成 TCP 与认证查询。
3. Functional：创建临时 Database/Table，记录 Binlog 起点，执行固定 I/U/D，核对 `Write_rows`、`Update_rows`、`Delete_rows` 与位置推进。
4. Recovery：仅在精确确认后重启 MySQL，轮询恢复，核对哨兵数据和 Binlog 状态；否则状态为 `PARTIAL`。
5. Cleanup：删除本次临时 Database，保留证据。

### Hive

1. Preflight：Metastore/HS2/Beeline、监听端口、配置路径、服务 PID 对应 Java executable。
2. Functional：创建临时 Database 与 ORC+Snappy Table，写入固定三行，执行 YARN MapReduce，核对聚合结果、HDFS 文件和 ORC 压缩元数据。
3. Runtime Java：从服务进程和 YARN 聚合日志分别采集实际 Java 路径与版本。
4. Recovery：仅在精确确认后执行 `<stop-command> hive`、`<start-command> hive`，等待端口与 Beeline 恢复并核对哨兵。
5. Cleanup：删除临时 Database 与严格受控 HDFS 路径。

### Kafka KRaft

1. Preflight：三节点版本、进程、端口、`meta.properties` Cluster ID、Quorum 与配置白名单。
2. Functional：创建临时 Topic（RF=3、minISR=2），发送固定有序消息，消费并按 Offset 重放，核对副本和 ISR。
3. Recovery：仅在精确确认后在指定节点停止 Kafka，等待 ISR 降级，继续固定生产消费，恢复该节点并等待 ISR 回到三副本。
4. Cleanup：删除且仅删除本次临时 Topic；不操作 KRaft Storage。

### Spark on YARN

1. Preflight：Spark 版本、配置路径、Hadoop Profile、YARN 连通和 Hive Catalog 可用性。
2. Success Path：提交固定 Spark SQL Application，读取 Hive 临时源并写 ORC+Snappy 结果，核对聚合值，采集 Application ID、Final-State、诊断和聚合日志。
3. Failure Path：提交引用明确不存在输入的固定 Application，断言客户端非零且 YARN 为 `FAILED` 或有可解释失败终态。
4. Cleanup：清理本次临时 Hive/HDFS 对象，不重启 Spark 服务。

### DataX

1. Preflight：两 Worker 的 Canonical Path、历史残留路径、版本、Python/JDK 与 Plugin。
2. Input：使用独立临时 MySQL Database/Table 写入固定三行，不使用 M2 正式对象。
3. Success Path：两 Worker 各自生成私有临时 Job JSON，写入不同 HDFS 临时路径；通过 Hive/Spark 核对行、值、ORC 和 Snappy。
4. Failure Path：使用不存在的临时源表执行固定失败 Job，断言非零退出并保存去敏错误摘要。
5. Cleanup：删除本次临时 Job JSON、MySQL/Hive/HDFS 对象；保留运行日志和摘要。

## Status Rules

- `PASS`：脚本要求的功能、失败路径、恢复路径和清理均完成；不适用项可以为 `NOT_APPLICABLE`，不能以 `NOT_RUN` 代替。
- `PARTIAL`：所有非中断检查通过，但用户未提供中断确认参数，或某项非致命证据因明确环境限制未采集。
- `FAIL`：必需断言失败、Secret 安全检查失败、清理无法保证安全，或执行出现不可解释状态；返回非零。
- 单个脚本 `PASS` 不自动提升整个 M1，也不替代 Codex 对证据目录的后续审查。

## Alternatives Considered

- 单一总控脚本：执行方便，但失败隔离差、恢复风险集中，且不便按门禁逐项重跑，因此不采用。
- 完全复制公共逻辑：初期简单，但五份安全校验容易漂移；采用最小共享库，避免抽象组件业务逻辑。
- 自动发现并杀进程：对现有集群风险过高；只使用可确认的生命周期入口和精确确认参数。

## Known Risks

- 现场生命周期脚本的绝对路径未固化；实现必须发现并打印实际路径，找不到时停止恢复阶段。
- Hive Runtime Java 仍待实测；脚本只能报告事实，不能自动更改 Java。
- DataX Job 需要短暂物化 Credential；通过 VM 外部 Secret 文件、私有目录、`0600`、去敏日志和受控清理降低风险。
- Kafka 单节点停止会短暂降低容错能力；必须指定节点、确认另外两节点健康并在恢复后核对 ISR。

## Ownership and Shared Change Surface

- `M1-CAS-01` 独占 `scripts/m1/lib/evidence-common.sh` 和公共 Evidence Schema。
- `M1-CAS-02～06` 各自独占一个组件脚本，不得自行修改公共库接口。
- `M1-CAS-07` 独占跨脚本 Contract 测试和 `scripts/m1/README.md` 的本 Task 章节。
- 无 Child Task 修改正式 Database Schema、Migration、Dependency 或组件永久配置。
- 如未来启用并行写入，组件 Owner 使用独立 Worktree；共享库与集成文件仍保持单一 Owner。

## Evidence Inbox Coordination

- 每个 Child Task 使用独立的 `.local-notes/m1-evidence/inbox/m1-cas-XX-<component>/`，不得把不同组件证据混放。
- 对应 Work 会话第一步创建 Inbox；目录已存在时保留原内容，不覆盖或清空。
- Work 会话可以放入明确标记为 `local_static` 的静态测试输出，但不得生成或伪造 VM Runtime 证据。
- 用户将 VM 脚本产生的完整 run 目录原样放入组件 Inbox，不扁平化、不改名、不只保留截图或摘录。
- M1 协调会话只读检查 `summary.env`、原始日志、Hash、时间和退出码，判断 `PASS/PARTIAL/FAIL`。
- Evidence Inbox 位于 `.local-notes/`，不作为 Git 交付物，项目运行不得依赖它。
