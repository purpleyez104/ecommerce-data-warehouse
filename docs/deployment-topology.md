# 三节点部署拓扑与资源边界

状态：当前 ECS 与已验收组件拓扑记录；未实施的服务仍为规划。更新时间：2026-09-20。

本文件展开 [最终工程架构](architecture/final-architecture-v1.0.md)的部署视图。运行事实以[集群事实基线](cluster-baseline.md)、[兼容性矩阵](compatibility-matrix.md)和 `DR-026` 为证据来源；不因出现在拓扑图中就把后续业务作业标记为已部署。

## 节点与角色

| 节点 | 资源与磁盘 | 已确认或已验证的主要角色 | 尚待阶段验收的角色 |
| --- | --- | --- | --- |
| `hadoop201`（`10.20.1.201`） | 4 vCPU / 16 GiB；系统盘 50 GiB、`/data` 80 GiB | NameNode、SecondaryNameNode、ResourceManager、JobHistoryServer；MySQL 8.0.46、Hive Metastore/HiveServer2、Kafka Broker/Controller 1、Doris FE `18030`、Spark/Flink Client | DolphinScheduler 3.4.2 Master/API/Alert 与单节点 ZooKeeper 3.8.4；正式业务作业 |
| `hadoop202`（`10.20.1.202`） | 8 vCPU / 16 GiB；系统盘 50 GiB、`/data` 120 GiB | DataNode、NodeManager、Kafka Broker/Controller 2、Doris BE 1、DataX 运行节点、YARN 容器 | DolphinScheduler Worker；正式业务作业 |
| `hadoop203`（`10.20.1.203`） | 8 vCPU / 16 GiB；系统盘 50 GiB、`/data` 120 GiB | DataNode、NodeManager、Kafka Broker/Controller 3、Doris BE 2、DataX 运行节点、YARN 容器 | DolphinScheduler Worker；正式业务作业 |

三节点均为 Ubuntu 24.04，数据盘 `/dev/vdb` 使用 ext4 并挂载 `/data`；组件由 `yee` 运行。HDFS 为单 NameNode、双 DataNode、副本数 2；Kafka 为三节点 KRaft 混合角色。该布局是成本受限的开发环境，不是生产级 HA。

## 网络、端口与 Java

- VPC 为 `10.20.0.0/16`，vSwitch 为 `10.20.1.0/24`。公网仅为 `hadoop201` 的 SSH 管理入口；其余组件端口限制在私网，Web UI 优先经 SSH 端口转发。不得把公网 IP、凭据或磁盘 UUID 写入仓库。
- YARN ResourceManager Scheduler 保留 `8030`；Doris FE HTTP 使用 `18030`。其他端口以已验证配置和[兼容性矩阵](compatibility-matrix.md)为准，不在本文猜测。
- 默认 OpenJDK 为 17.0.20；Hadoop/YARN 守护进程使用独立 OpenJDK 11.0.32。Hive 3.1.3 已在当前 Java 17 环境通过验收；Flink Client 使用 Java 17，当前 Flink YARN Container 和 User Jar 以 Java 11 兼容边界运行。Java 策略不授权修改全局 JDK。

## 运行链路与证据边界

```text
MySQL (hadoop201) ──DataX (workers)──> HDFS/Hive ODS ──Spark on YARN──> Doris FE/BE
       └─Binlog──> Flink CDC on YARN ──> Kafka KRaft ──> Flink Application ──> Doris
```

已通过的 MySQL→DataX→HDFS→Hive→Spark、MySQL Binlog→Flink CDC→Kafka→Flink→Kafka、Kafka→Flink→Doris 均为限定范围的技术验收。Doris 4.0.8 FE/BE、SQL 和受控重启恢复已通过。正式 21 表数据、Hive ODS、实时 Topic、Flink 业务 Jar、Doris 服务表和离实时对账仍须按 Milestone 2～9 分别验收。

Flink 正式业务作业的目标部署方式为 Java DataStream Jar + YARN Application Mode；SQL Client + YARN Session 仅保留作 Kafka SQL 技术验证。Application 提交命令退出 0 只代表提交成功，调度和验收必须核对 YARN final state。详见[实时链路规范](design/realtime-pipeline-design.md)。

## 资源与变更门禁

- `hadoop201` 承载多项控制服务，只有发生磁盘不足、OOM、持续 Swap、频繁 Full GC、进程被杀或核心服务无法共存等实测问题，才提出扩容。
- 两个 worker 的 YARN 资源按现有配置保持 `10240 MiB / 6 vCore`；正式 Flink/Spark 与 Doris 共存前需重新核对内存、磁盘、进程和 GC。
- 不格式化既有 NameNode，不重置 KRaft storage，不用停掉关键服务的方式伪装资源充足。DolphinScheduler 验收完成前，Milestone 1 保持 `in progress`，不创建 `infra/versions.env`。
