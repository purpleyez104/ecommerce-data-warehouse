# Milestone 1 组件兼容性矩阵

版本：`0.1-draft`
状态：`in progress`
更新时间：2026-09-05

## 使用规则

- `CONFIRMED` 和 `CONFIGURED` 来源于本项目当前集群记录，含义见 [集群事实基线](cluster-baseline.md)。
- 项目证据状态只使用 `draft`、`candidate`、`planned`、`implemented` 和 `verified`。
- 官方文档只能提供候选兼容依据；只有目标 ECS 上的安装、启动、功能、上下游连通和重启证据才能标记 `verified`。
- 精确版本调整必须先保存失败证据并取得用户确认，不得静默升级、降级或使用容器兜底。
- 全部 M1 组件验证完成前不创建 `infra/versions.env`。

## 当前矩阵

| 对象 | 精确版本或配置 | 来源状态 | 项目状态 | 还需完成 |
| --- | --- | --- | --- | --- |
| Ubuntu | 24.04 LTS，x86_64 | `CONFIRMED` | `verified` | 记录补丁与内核版本只用于环境快照 |
| 默认 JDK | OpenJDK 17.0.20 | `CONFIRMED` | `verified` | 三节点 `java -version` 已采集；后续组件仍需分别验证所用 Java |
| Hadoop JDK | OpenJDK 11，补丁未知 | `CONFIRMED` | `verified` | 三节点守护进程均已确认使用 JDK 11；补丁版本仍需后续环境快照 |
| Hadoop | 3.4.1 | `CONFIRMED` | `verified` | HDFS SHA-256、MapReduce、聚合日志、清理和受控重启均已通过 |
| MySQL | 8.0.46 | `PLANNED` | `candidate` | 安装、Binlog、私网连接、增删改和重启 |
| Connector/J | 8.0.33 | `PLANNED` | `candidate` | Hive Metastore JDBC 连接 |
| Hive | 4.1.0 | `PLANNED` | `candidate` | Metastore、HiveServer2、Beeline、外部表和重启 |
| Kafka | 3.9.1，Scala 2.12，KRaft | `PLANNED` | `candidate` | 三节点仲裁、生产消费、重放和单节点重启 |
| Spark | 3.5.9-bin-hadoop3 | `PLANNED` | `candidate` | YARN 作业、Hive 连接、ORC + Snappy 读写 |
| DataX | 202309 | `PLANNED` | `candidate` | JDK、MySQL Reader、HDFS Writer、ORC + Snappy |
| Doris | 4.0.8 | `PLANNED` | `candidate` | CPU 指令集、FE/BE、临时表和重启 |
| Spark Doris Connector | 26.0.0，Spark 3.5 构件 | `PLANNED` | `candidate` | Spark、Scala、Java、Doris 类型和写入验证 |
| ZooKeeper | 3.8.4，单节点 | 已接受设计 | `planned` | 仅为 DolphinScheduler 验证安装和重启 |
| DolphinScheduler | 3.4.2 | `PLANNED` | `candidate` | MySQL、ZooKeeper、Worker、成功/失败任务和重启 |
| Flink | 1.20.5，Scala 2.12 | `PLANNED` | `candidate` | YARN 作业和重启 |
| Flink CDC | 3.6.0 | `PLANNED` | `candidate` | MySQL Snapshot、Binlog 增删改和 Kafka 输出 |
| Flink Doris Connector | 26.1.1 for Flink 1.20 | `PLANNED` | `candidate` | 临时表写入和重复写入行为 |

## 官方依据入口

| 组合 | 官方入口 | 当前结论边界 |
| --- | --- | --- |
| Hadoop 3.4.1 | <https://hadoop.apache.org/docs/r3.4.1/> | 版本文档存在；本项目运行事实来自当前集群记录和 2026-09-05 的功能及重启验证 |
| Hive 4.1.0 / Hadoop 3.4.1 | <https://hive.apache.org/general/downloads/> | 官方发布说明可作为组合候选依据，仍需目标集群验证 |
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
→ MySQL（当前门禁）
→ Hive
→ Kafka KRaft
→ Spark on YARN
→ DataX
→ Doris
→ DolphinScheduler + 单节点 ZooKeeper
→ Flink / Flink CDC
```

任一门禁失败时停止后续组件接入。失败记录至少包含节点、版本、命令、退出状态、关键日志、影响范围和回滚结果。

## 端口与资源约束

- YARN ResourceManager Scheduler 已确认使用 `hadoop201:8030`。
- Doris FE HTTP 使用 `hadoop201:18030`，不得改动 YARN `8030` 来掩盖冲突。
- Kafka 不使用 ZooKeeper；单节点 ZooKeeper 只服务 DolphinScheduler。
- 两个 worker 的 YARN 资源保持 `10240 MiB / 6 vCore`，组件共存后必须重新采集内存、进程、磁盘和 GC 证据。
- `hadoop201` 是否扩容只依据 OOM、持续 Swap、频繁 Full GC、磁盘不足、进程被杀或关键服务不能共存等实测证据。
