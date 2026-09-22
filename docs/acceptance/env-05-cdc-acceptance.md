# ENV-05｜MySQL → Flink CDC → Kafka 验收记录

> 状态：**CONFIRMED（本次隔离链路、指定故障恢复场景）**。记录日期：2026-09-18。验收证据来自本项目对话中用户粘贴的实际终端输出。本文是脱敏摘要：**不包含密码、完整 YAML、未经脱敏的 YARN 日志或完整启动程序参数。**
> 注意：该状态不等价于端到端 Exactly-Once 的普遍证明，也不等价于正式 21 张 `biz_*` 表及真实 90 日规模通过验收。

## 1. 验收目标与作用范围

验证 MySQL 的真实快照和 ROW Binlog 更新，由 Flink CDC 读取并以 Debezium JSON 输出到 Kafka；确认 HDFS Checkpoint 持续完成、TaskManager 强制终止后能从 Checkpoint 恢复、恢复后继续同步新交易事件。

```text
MySQL 8.0.46 / cdc_acceptance.probe_order
  → Binlog (ROW, FULL)
  → Flink CDC 3.6.0-1.20 + Flink 1.20.5 on YARN Application
  → Kafka 3.9.1 / cdc_acceptance_probe
```

| 项目 | 已验收环境/标识 |
|---|---|
| 实验数据库/表 | `cdc_acceptance.probe_order`（不是正式电商 21 表） |
| MySQL | 8.0.46；`server_id=201`、`log_bin=ON`、`binlog_format=ROW`、`binlog_row_image=FULL` 曾核验 |
| Flink 与 CDC | Flink 1.20.5；Flink CDC 3.6.0-1.20 |
| CDC 专用 Runtime | `/data/module/flink-1.20.5-cdc`，与普通 `/data/module/flink-1.20.5` 分开 |
| CDC Home | `/data/module/flink-cdc-3.6.0-1.20` |
| Kafka | 3.9.1 KRaft；测试 Topic `cdc_acceptance_probe`，单分区；实验时 `min.insync.replicas=1` |
| YARN Application ID | `application_1789696088424_0003` |
| Flink Job ID | `8cbe2b60c54bd3d04b55289e9c15808b` |
| Job 展示名 | `CDC Acceptance MySQL to Kafka` |
| REST 入口（当时） | `http://hadoop202:8081`；仅为内网当时地址，不保证永久可用 |
| Checkpoint 位置 | `hdfs://hadoop201:8020/user/hive/warehouse/ecommerce/flink/checkpoints/cdc_acceptance_probe/8cbe2b60c54bd3d04b55289e9c15808b/` |
| Kafka 消息格式 | Debezium JSON；实际观察 `before`、`after`、`op`、`source.db/table` |

## 2. 历史故障与修复决策

### 2.1 失败现象与因果边界

此前测试 Application `_0001`/`_0002` 的提交命令曾返回成功，但 YARN 最终失败；其中有确定的错误：`Cannot find factory with identifier "kafka" in the classpath.` **提交成功不代表最终运行成功**，以 YARN State、Flink REST 运行及 Kafka 实际输出综合判断。

已验证的 Step 9 使用 CDC Pipeline Kafka Connector 于 Flink Runtime `lib`；随后 Step 10 清理普通 Flink `lib` 中的 CDC Kafka Connector，普通环境保留 `flink-sql-connector-kafka-3.3.0-1.20.jar`。CDC Kafka 工厂与普通 Flink SQL Kafka 工厂不是同一概念。本次解决措施：将原 Flink 安装完整复制为专用 Runtime，给其 `lib` 补齐 CDC MySQL/Kafka Pipeline Connector 和 JDBC Driver；不改变普通 Flink 软链接与原安装。

### 2.2 隔离 Runtime 的现场验证

| 检查 | 实际结果 |
|---|---|
| 原 Flink 软链接 | `/data/module/flink` → `/data/module/flink-1.20.5`，保持不变 |
| CDC Runtime | `/data/module/flink-1.20.5-cdc`；版本 `1.20.5` |
| CDC Pipeline Connector | `flink-cdc-pipeline-connector-mysql-3.6.0-1.20.jar` 与 `flink-cdc-pipeline-connector-kafka-3.6.0-1.20.jar` 存在 |
| JDBC | `mysql-connector-j-8.0.33.jar` 存在 |
| 同目录的普通 Kafka SQL Connector | 也存在，但**本次未观测到 Factory 冲突**；不应无证据宣称它造成问题 |
| 原/副本配置 | `config.yaml` 与 `log4j.properties` diff 无差异，GlobalConfiguration 日志级别为 WARN |

提交方式沿用已验证路线：`yarn-application`，`FLINK_HOME` 和 `--flink-home` 都指向专用 Runtime；`pipeline.jars` **只指定单个** Flink CDC Dist JAR（不使用曾失败的多 JAR 参数）。真实密码不在本文复现。

> 安全事件：早期日志曾泄露 CDC 凭据；用户报告已完成密码轮换，CDC 用户是否为其他作业共用曾不确定。调低指定 INFO logger 只抑制该类配置日志，**不能保证**作业参数/YARN 元数据的所有暴露途径已解决。正式部署需再次检查脱敏、权限和凭据分发，不把完整日志/配置提交 Git。

## 3. 逐阶段实际验收证据

| 阶段 | 证据（均来自实测终端输出） | 结论 |
|---|---|---|
| ENV-05A 环境/前置 | MySQL 查询正常；CDC 用户可查询 probe_order；Kafka Topic 可创建且 `min.insync.replicas=1`；单分区 | PASS |
| ENV-05B 初始快照 | `_0003` 提交后 YARN RUNNING；从 Kafka beginning 收到 1001/1002/1003 共 3 条；各 `before=null,op=c`，source 指向测试表 | PASS |
| ENV-05C Checkpoint | 首次 REST：11 completed、0 failed；后续 53 completed、0 failed、最新 `chk-53 COMPLETED`；2/2 task RUNNING | PASS |
| ENV-05D 增量 | 从变更前 end offset=3 起读出 INSERT 1004、UPDATE 1002、DELETE 1003 三条；offset 至 6 | PASS |
| ENV-05E-1 故障与状态恢复 | 精确匹配 TaskManager PID 8433 与 container `...000002`，执行 `kill -9`；YARN 仍 RUNNING，新 TM `...000003`；Job RUNNING 2/2，restored=1，从 chk-84 恢复，随后 chk-85 完成 | PASS |
| ENV-05E-2 恢复后增量 | 故障后 end offset 仍 6；1005 起初不存在；MySQL 新增 1005/500 元；Kafka offset=6 位置收到唯一一条 op=c、order_id=1005/amount=500；end offset 至 7 | PASS |

### 3.1 Snapshot 实际值

| Kafka offset（单分区） | order_id | status | amount | op |
|---:|---:|---|---:|---|
| 0 | 1001 | CREATED | 100.00 | c |
| 1 | 1002 | CREATED | 200.00 | c |
| 2 | 1003 | PAID | 300.00 | c |

这次 snapshot 实际观察到 `op=c`，应尊重现场输出，不根据对 Debezium 其他实现的预期替换成 `op=r`。科学计数法 JSON 数字 `1E+2`、`2E+2`、`3E+2` 分别表示 100/200/300。

### 3.2 单事务 INSERT / UPDATE / DELETE 实际值

变更前 Kafka end offset = `cdc_acceptance_probe:0:3`；在同一 MySQL 事务执行、成功 COMMIT：

| offset | 操作 | order_id | before | after | 验收 |
|---:|---|---:|---|---|---|
| 3 | INSERT / `op=c` | 1004 | null | CREATED、400.00 | PASS |
| 4 | UPDATE / `op=u` | 1002 | CREATED、200.00 | PAID、250.00 | PASS |
| 5 | DELETE / `op=d` | 1003 | PAID、300.00 | null | PASS |

提交后 MySQL：1001 CREATED/100；1002 PAID/250；1004 CREATED/400；Kafka End Offset 6。后续检查 `completed=53, failed=0, latest chk-53 COMPLETED`，证明增量操作后 Checkpoint 仍持续完成。

### 3.3 TaskManager 故障恢复

```text
故障前：PID 8433 ⇔ container_1789696088424_0003_01_000002（精确匹配）
故障注入：只对匹配的 YarnTaskExecutorRunner 执行 kill -9
故障后：Application _0003 RUNNING；出现 container_1789696088424_0003_01_000003
Flink Job：8cbe2b60c54bd3d04b55289e9c15808b，RUNNING，2/2 tasks
Checkpoint：completed=85，failed=0，restored=1；latest restored chk-84，随后 chk-85 完成
```

本次验证的是**一次目标明确的 TaskManager 进程故障**。未验证 JobManager/AM 故障、Kafka 多 Broker 丢失、长时间断链或 Binlog 被清理后的恢复。容器级终止应仅在安全隔离实验中执行，不视为日常运维操作。

### 3.4 故障后新的业务变更

- 故障后操作前：Topic 单分区 end offset = **6**；MySQL 中订单 1005 不存在。
- 新增 `order_id=1005, CREATED, amount=500.00` 后，MySQL 最终有 1001/1002/1004/1005 四笔。
- 从 offset 6 消费得到 1 条 `before=null, op=c, after.order_id=1005, amount=5E+2`；`Processed a total of 1 messages`；end offset = **7**。
- 结合完整已观察 offset `0..6`，本次没有观察到丢失或异常重复；**仅凭这个实验不得声称所有路径都满足端到端 Exactly-Once**。

## 4. 最终验收结论与限制

**结论：ENV-05 = CONFIRMED**，范围为：隔离测试表的 snapshot + Binlog c/u/d、HDFS Checkpoint、指定 TaskManager 故障恢复及恢复后持续采集/对账。

未包含：21 张正式业务源表的 DDL/CDC 采集与多表事务顺序、数据生成器正式造数、三组行为 Topic、DataX 与 CDC 90 天初始化接续、端到端 Exactly-Once 多故障证明、性能/延迟目标。另 Step 10 仅确认 Kafka Source/Sink 基础链路并存在重复输出备注；Step 11 Doris 重启验收尚无完成证据；Step 12 Doris 链路通过指定恢复场景但不应据此扩展本项范围。

## 5. 交接与清理约束

1. 当前实验作业在最后一次状态检查时为 RUNNING；记录的是**当时状态**，不是本文件生成时实时查询。不要在未核验当前状态前重复提交。
2. 保留本次验收元数据与脱敏摘要；敏感 YAML 和日志留在受控私有目录，禁止进入仓库或报告。
3. 如果要停止，使用受控正常取消流程，先确认 Application/JID、独立作业归属与状态保留策略；不要直接清理测试 Topic、MySQL 测试表或 HDFS Checkpoint。
4. 后续正式业务表 CDC 上线前，另行验收业务白名单、Snapshot/Binlog 交界、历史/当前事件重复处理、离实时最终对账和恢复能力。

## 6. 技术决策索引

- Flink 1.20.5 on YARN Application 是主部署方向；不搭建 Standalone。
- CDC 专用 Flink Runtime 解决 `kafka` factory 不可发现；普通 Flink 目录和软链接保持不变。
- `pipeline.jars` 单 Dist JAR，Connector/J 与 CDC Pipeline Connector 在隔离 Runtime `lib`。
- Kafka Raw CDC 用 Debezium JSON；不以业务生成器直接投递代替 CDC。
- Java 版本区分角色：开发/Flink Client Java 17；Hadoop/YARN Runtime Java 11；提交的自编译 User Jar 按 Step 12 target Java 11。不能把此约定误写成该 CDC 任务全链路统一 Java 17。
- Step 12 DataStream Jar + YARN Application 已验证 Doris 集成；Step 10 Kafka SQL YARN Session 成功，但 Step 12 的 SQL Client + Doris DML 曾失败，根因未充分证明，不能写成“所有 SQL Client 均不可用”。
