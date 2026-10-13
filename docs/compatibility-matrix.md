# Milestone 1 组件兼容性矩阵

版本：`0.4`
状态：`in progress`
更新时间：2026-09-20

## 使用规则

- `CONFIRMED` 和 `CONFIGURED` 来源于本项目当前集群记录，含义见 [集群事实基线](cluster-baseline.md)。
- 项目证据状态只使用 `draft`、`candidate`、`planned`、`implemented` 和 `verified`。
- 官方文档只能提供候选兼容依据；目标 ECS 上的安装、启动、核心功能与必要恢复验证，以及用户确认的 Runtime 验收记录，才可支持 `verified`。
- 精确版本调整必须先保存失败证据并取得用户确认，不得静默升级、降级或使用容器兜底。
- 全部 M1 组件验证完成前不创建 `infra/versions.env`。
- `DR-026` 已采用用户确认的 Step 2～12 Runtime 验收记录作为当前能力基线；文件完整性用于可复现与审计，不再以非核心附件缺失否定已实际展示的组件能力。
- [最终工程架构](architecture/final-architecture.md)确定正式 Flink 业务作业采用 Java DataStream Jar + YARN Application Mode；这是一项部署选型，不会将 M1 临时作业提升为 M9 正式业务链路验收。

## 当前矩阵

| 对象 | 精确版本或配置 | 来源状态 | 项目状态 | 还需完成 |
| --- | --- | --- | --- | --- |
| Ubuntu | 24.04 LTS，x86_64 | `CONFIRMED` | `verified` | 记录补丁与内核版本只用于环境快照 |
| 默认 JDK | OpenJDK 17.0.20 | `CONFIRMED` | `verified` | 三节点 `java -version` 已采集；后续组件仍需分别验证所用 Java |
| Hadoop JDK | OpenJDK 11.0.32 | `CONFIRMED` | `verified` | 三节点守护进程已确认使用 JDK 11；补丁版本由 2026-09-13 环境快照补齐 |
| Hadoop | 3.4.1 | `CONFIRMED` | `verified` | HDFS SHA-256、MapReduce、聚合日志、清理和受控重启均已通过 |
| MySQL | 8.0.46 | `CONFIRMED` | `verified` | 私网连接、固定 CRUD、ROW/FULL Binlog、认证失败、受控重启与恢复均通过 |
| Connector/J | 8.0.33 | Hive Metastore 实际使用 | `verified` | 已支持 Hive Metastore 连接；后续升级需重新验证 |
| Hive | 3.1.3；Metastore schema 3.1.0 | `CONFIRMED_WITH_VERSION_CHANGE` | `verified` | JDK 17、MySQL Metastore、HiveServer2/Beeline 与 ORC 链路已通过；4.1.0 已退出候选 |
| Kafka | 3.9.1，Scala 2.12，KRaft | `CONFIRMED` | `verified` | 三节点仲裁、RF=3、minISR=2、生产消费、单 Broker 故障与恢复通过 |
| Spark | 3.5.9-bin-hadoop3，Scala 2.12.18 | `CONFIRMED` | `verified` | YARN 提交、Hive ORC 读取与计算通过 |
| DataX | datax_v202309；运行入口 `/data/module/datax-current` | `CONFIRMED` | `verified` | MySQL Reader、HDFS Writer、ORC + Snappy、3 行链路与失败非零通过 |
| Doris | 4.0.8 | `CONFIRMED` | `verified` | FE/BE、SQL、端口与受控重启恢复均已通过；正式服务表仍待 M6/M9 |
| Spark Doris Connector | 26.0.0，Spark 3.5 构件 | `PLANNED` | `candidate` | Spark、Scala、Java、Doris 类型和写入验证 |
| ZooKeeper | 3.8.4，单节点 | 已接受设计 | `planned` | 仅为 DolphinScheduler 验证安装和重启 |
| DolphinScheduler | 3.4.2 | `PLANNED` | `candidate` | 当前唯一剩余 M1 门禁：MySQL、ZooKeeper、Worker、成功/失败任务和重启 |
| Flink | 1.20.5，Scala 2.12 | `CONFIRMED_WITH_NOTE` | `verified` | YARN Application Mode 已通过；正式业务部署选 Java DataStream Jar，尚无正式业务 Jar；提交退出 0 不代表最终成功，调度必须查询 YARN final state |
| Flink CDC | 3.6.0 for Flink 1.20 | `CONFIRMED` | `verified` | MySQL Snapshot、Binlog CRUD 与 Kafka 输出通过；正式 Topic 设计仍等待 M8 |
| Flink Doris Connector | 26.1.1 for Flink 1.20 | `CONFIRMED` | `verified` | insert/upsert、类型、schema、Checkpoint、TaskManager 故障恢复通过；不确认正式实时表模型或 Exactly-Once |

## 官方依据入口

| 组合 | 官方入口 | 当前结论边界 |
| --- | --- | --- |
| Hadoop 3.4.1 | <https://hadoop.apache.org/docs/r3.4.1/> | 版本文档存在；本项目运行事实来自当前集群记录和 2026-09-05 的功能及重启验证 |
| Hive 3.1.3 / Hadoop 3.4.1 / Spark 3.5.9 | <https://hive.apache.org/general/downloads/> | 4.1.0 在当前 Spark Metastore client Smoke Test 中失败；Hive 3.1.3 使用 JDK 17 的当前组合已通过 Runtime 验收 |
| Spark 3.5 / Java 17 / YARN | <https://spark.apache.org/docs/3.5.9/> | 支持范围不替代本项目的 Hadoop、Hive 和 YARN 实测 |
| Kafka 3.9 KRaft | <https://kafka.apache.org/39/documentation.html#kraft> | 只采用 KRaft，不因 DolphinScheduler 引入的 ZooKeeper 改变 Kafka 模式 |
| DataX HDFS Writer | <https://github.com/alibaba/DataX/blob/master/hdfswriter/doc/hdfswriter.md> | ORC、压缩和依赖必须用 202309 包真实验证 |
| Spark Doris Connector | <https://doris.apache.org/docs/3.x/ecosystem/spark-doris-connector/> | 版本矩阵是候选依据，Java 17 和 Doris 4.0.8 仍需实测 |
| Flink CDC 3.6 | <https://nightlies.apache.org/flink/flink-cdc-docs-release-3.6/> | 只验证兼容性，不提前设计正式实时语义 |
| Flink Doris Connector | <https://doris.apache.org/docs/3.x/ecosystem/flink-doris-connector/> | 只验证临时数据写入，不替代 Milestone 8-9 设计与可靠性验收 |
| DolphinScheduler | <https://dolphinscheduler.apache.org/en-us/docs/3.2.2/guide/installation/pseudo-cluster> | 版本与 JDK 17、MySQL、ZooKeeper 组合需单独实测 |

## 强制顺序

```text
已有事实迁入（已完成）
→ Hadoop 缺失证据补齐（已完成）
→ MySQL（已完成）
→ Hive（已完成）
→ Spark on YARN（已完成）
→ DataX（已完成）
→ Kafka KRaft（已完成）
→ Flink / Flink CDC / Kafka source-sink（已完成，保留执行模式边界）
→ Doris / Flink Doris Connector（已完成）
→ DolphinScheduler + 单节点 ZooKeeper（当前唯一剩余门禁）
```

任一门禁失败时停止后续组件接入。失败记录至少包含节点、版本、命令、退出状态、关键日志、影响范围和回滚结果。

## Java 与执行模式边界

| 对象 | 当前已验证用法 | 不可外推的结论 |
| --- | --- | --- |
| Hadoop/YARN 守护进程 | OpenJDK 11.0.32 | 不表示 Hive 也已切换到 Java 11 |
| Hive 3.1.3 | 当前 Java 17 环境下的 Metastore、HiveServer2/Beeline 与 ORC 链路 | 未验证 Hive Java 11 切换 |
| Flink Client | Java 17；YARN Application Mode 验证 | 提交成功不等于作业最终成功 |
| Flink YARN Container / Doris User Jar | Java 11 兼容边界、限定范围的连接器验收 | 不表示正式 21 表业务 Jar 或端到端 Exactly-Once 已通过 |
| Flink SQL Client + YARN Session | Kafka Source/Sink 技术验证 | 不作为正式业务部署模式；不替代 Java DataStream Jar 验收 |

节点分布与资源边界见[部署拓扑](deployment-topology.md)，正式实时链路的待决策契约见[实时链路规范](design/realtime-pipeline-design.md)。

## 端口与资源约束

- YARN ResourceManager Scheduler 已确认使用 `hadoop201:8030`。
- Doris FE HTTP 使用 `hadoop201:18030`，不得改动 YARN `8030` 来掩盖冲突。
- Kafka 不使用 ZooKeeper；单节点 ZooKeeper 只服务 DolphinScheduler。
- 两个 worker 的 YARN 资源保持 `10240 MiB / 6 vCore`，组件共存后必须重新采集内存、进程、磁盘和 GC 证据。
- `hadoop201` 是否扩容只依据 OOM、持续 Swap、频繁 Full GC、磁盘不足、进程被杀或关键服务不能共存等实测证据。
