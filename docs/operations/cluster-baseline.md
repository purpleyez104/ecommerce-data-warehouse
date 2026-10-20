# Milestone 1 集群事实基线

版本：`0.3`
状态：`in progress`
更新时间：2026-09-14

## 1. 来源与适用范围

本文件是 Project 1 在 Milestone 1 使用的集群事实入口。事实来源为：

- 来源：用户确认的本地 ECS/Hadoop 集群重建记录；原始文件保留在仓库外，不提交本机路径或 Codex 项目标识。
- 来源快照日期：2026-09-04
- SHA-256：`0556E06CBF754D01E4CCD451356E0EB15F6BE6A3E7B49E91632FA85313F25264`
- 采用依据：用户确认该文件是本项目当前集群的实际搭建记录，其中 `CONFIRMED` 可以作为确认事实。
- VM 现场证据：2026-09-13 运行目录 `.local-notes/m1-evidence/inbox/m1-vm-20260913-01/`，由 `yee@hadoop201` 编排三节点只读采集；原始目录不提交 Git。
- 搭建修复与决策摘要：`.local-notes/m1-evidence/inbox/m1-vm-files-20260913/`，由用户确认为本次整理输入；摘要不替代组件级原始运行日志。

本仓库只提取 Milestone 1 所需的拓扑、配置、状态和验证边界，不整份复制外部文件。未迁入阿里云账号级资源 ID、磁盘 UUID、公网 IP、密钥、真实密码、Project 2 实现规划和通用复建教程。

## 2. 状态映射

| 来源状态 | 本仓库处理 |
| --- | --- |
| `CONFIRMED` | 作为当前集群的确认事实，不降级为候选，也不要求重新证明事实是否存在 |
| `CONFIGURED` | 作为当前已采用配置；不自动补足来源文件明确缺失的功能测试证据 |
| `PLANNED` | 保持计划或候选状态，不描述为已经安装、启动或验证 |
| `UNKNOWN` | 必须从控制台或节点现场获取，不写入猜测值 |

Hadoop 的版本、进程和节点拓扑来自确认事实；仓库要求的 HDFS 固定文件校验、完整 MapReduce 结果、聚合日志和受控重启证据已于 2026-09-05 补齐，因此 Hadoop 整体状态为 `verified`。

## 3. 云、网络与访问

| 项目 | 当前事实 | 状态 |
| --- | --- | --- |
| 云平台与地域 | Alibaba Cloud ECS，杭州地域 | `CONFIRMED` |
| 操作系统 | Ubuntu 24.04 LTS，x86_64 | `CONFIRMED` |
| VPC | `10.20.0.0/16` | `CONFIRMED` |
| vSwitch | `10.20.1.0/24` | `CONFIRMED` |
| 时区 | `Asia/Shanghai` | `CONFIRMED` |
| Swap | 关闭，预检为 `0 B` | `CONFIRMED` |
| 公网管理入口 | 仅 `hadoop201` 的 SSH 22 | `CONFIRMED` |
| worker 管理 | 通过 `hadoop201` 跳板访问私网地址 | `CONFIRMED` |
| 集群端口授权源 | `10.20.1.0/24` | `CONFIGURED` |
| 公网 SSH 授权源 | 管理员当前公网出口 IP `/32` | `CONFIGURED`，实际地址不入库 |

集群内部连接只使用私网主机名。`/etc/hosts` 的统一映射见 `infra/hosts.example`。不得把公网 IP 写入组件配置。

## 4. 节点与角色

| 节点 | 私网 IPv4 | 资源 | 当前 Hadoop 角色 | 后续计划角色 |
| --- | --- | --- | --- | --- |
| `hadoop201` | `10.20.1.201` | 4 vCPU / 16 GiB；系统盘 50 GiB；数据盘 80 GiB | NameNode、SecondaryNameNode、ResourceManager、JobHistoryServer | MySQL、Hive Metastore、HiveServer2、Kafka Broker/Controller 1、Doris FE、DolphinScheduler Master/API/Alert、Spark/Flink 客户端 |
| `hadoop202` | `10.20.1.202` | 8 vCPU / 16 GiB；系统盘 50 GiB；数据盘 120 GiB | DataNode、NodeManager | Kafka Broker/Controller 2、Doris BE 1、DolphinScheduler Worker、DataX、Spark/Flink YARN 容器 |
| `hadoop203` | `10.20.1.203` | 8 vCPU / 16 GiB；系统盘 50 GiB；数据盘 120 GiB | DataNode、NodeManager | Kafka Broker/Controller 3、Doris BE 2、DolphinScheduler Worker、DataX、Spark/Flink YARN 容器 |

`hadoop201` 不加入 Hadoop `workers`，不运行 DataNode 或 NodeManager。SecondaryNameNode 不构成 Hadoop HA，本项目也不宣称生产级高可用。

## 5. 用户、磁盘、目录与 Java

- 大数据组件统一由 `yee` 运行；`yee` 具备无密码 `sudo`，但 Hadoop 不以 `root` 运行。
- `yee@hadoop201` 已通过 `~/.ssh/id_ed25519` 对三节点免密 SSH；私钥不得进入仓库。
- 系统盘为 `/dev/vda`，根分区为 ext4 并挂载到 `/`。
- 数据盘为 `/dev/vdb`，格式化为 ext4 并挂载到 `/data`。
- `/etc/fstab` 使用各节点现场 UUID；UUID 不得从其他节点复制或写入仓库。
- `/data` 属主为 `yee:yee`，权限基线为 `755`。
- 安装包保存到 `/data/software`，组件安装到 `/data/module/<component>-<version>`，通过 `/data/module/<component>` 稳定软链接访问。
- 默认 Java 为 OpenJDK 17；Hadoop 在 `hadoop-env.sh` 中固定使用 `/usr/lib/jvm/java-11-openjdk-amd64`。
- `nofile` 和 `nproc` 的 soft/hard 基线均为 `65536`。

主要数据目录：

```text
/data/hadoop
/data/kafka
/data/flink
/data/doris
/data/dolphinscheduler
/data/datax
/data/logs
/data/tmp
```

## 6. Hadoop 当前事实

| 项目 | 当前值 | 状态 |
| --- | --- | --- |
| Hadoop | `3.4.1`，revision `4d7825309348956336b8f06a08322b78422849b1` | `CONFIRMED` |
| HDFS | 1 NameNode、1 SecondaryNameNode、2 DataNode | `CONFIRMED` |
| Live DataNode | `hadoop202`、`hadoop203` | `CONFIRMED` |
| HDFS 副本数 | `2` | `CONFIGURED` |
| HDFS 可配置容量 | 合计约 `235.12 GiB` | `CONFIRMED` |
| YARN | `hadoop201` ResourceManager，两个 worker 各 1 个 NodeManager | `CONFIRMED` |
| YARN 节点 | 2 个，均为 `RUNNING` | `CONFIRMED` |
| MapReduce | YARN 模式；JobHistoryServer 位于 `hadoop201` | 来源 `CONFIRMED`；项目 `verified` |
| Hadoop Java | OpenJDK 11 | 来源 `CONFIRMED`；项目 `verified` |

关键配置：

- `fs.defaultFS=hdfs://hadoop201:8020`
- NameNode 数据目录：`/data/hadoop/dfs/name`
- DataNode 数据目录：`/data/hadoop/dfs/data`
- NodeManager 本地目录：`/data/hadoop/yarn/local`
- NodeManager 日志目录：`/data/hadoop/yarn/logs`
- 每个 worker 的 YARN 资源：`10240 MiB`、`6 vCore`
- 单容器最大资源：`4096 MiB`、`4 vCore`
- YARN 聚合日志 HDFS 目录：`/tmp/logs`，保留 7 天

NameNode 已存在。任何 M1 脚本都不得执行 `hdfs namenode -format` 或删除 `/data/hadoop/dfs/name`。

## 7. Hadoop 验证结论与当时门禁

2026-09-05 已完成以下真实 ECS 验证：

- 非中断运行编号：`m1-hadoop-20260905-02`，脚本退出状态为 0，`summary.env` 为 `PASS`。
- 固定 UTF-8 文件的本地与 HDFS SHA-256 均为 `5c3700d16b676bc03bdf7a66a28cf3e53bd4c1d307fff0781c511e3b7293dbd2`。
- MapReduce WordCount 的 application 为 `application_1788593194299_0001`，最终状态和日志聚合状态均为 `SUCCEEDED`；固定结果为 `alpha=2`、`beta=2`、`gamma=1`。
- 三节点守护进程实际使用 `/usr/lib/jvm/java-11-openjdk-amd64/bin/java`；默认命令行 Java 为 OpenJDK 17。
- 受控重启运行编号：`m1-hadoop-restart-20260905-02`，脚本退出状态为 0，`summary.env` 为 `PASS`。
- 重启哨兵预期与实际 SHA-256 一致；重启前后均为 2 个 Live DataNode、2 个 RUNNING NodeManager，`hadoop201` 的四个控制进程恢复。
- 重启后低副本块、损坏副本和缺失块均为 0；两个脚本创建的临时 HDFS 路径均已清理。

原始日志保存在 ECS `/data/logs/ecommerce-data-warehouse/m1/` 和本地 Git 忽略目录，不提交仓库。上述段落记录 Hadoop 3.4.1 的独立验收；当前 M1 状态与后续组件结论以第 9 节和 `DR-026` 为准。

## 8. 2026-09-13 VM 与组件安装现场

运行 `m1-vm-20260913-01` 的 `summary.env` 为 `PARTIAL`、退出状态为 0，表示三节点盘点成功但至少一个组件入口未被采集器识别；它不是组件功能验收。现场确认：

- 三节点均为 Ubuntu 24.04.4 LTS、Kernel 6.8.0-137，节点、用户、私网解析与连通正常，采集时间偏差均为 0 秒。
- `hadoop201`、`hadoop202`、`hadoop203` 分别为 4、8、8 vCPU，现场可见内存均约 14 GiB；Swap 为 0。
- 三块 `/dev/vdb` 均以 ext4 挂载到 `/data`，容量分别为 80、120、120 GiB，`yee` 可写；`nofile` 与 `nproc` 为 65536。
- OpenJDK 11.0.32 与 17.0.20 均已安装，默认命令行 Java 为 17.0.20；Hadoop 已验证守护进程继续使用 Java 11。
- `hadoop201` 发现 MySQL 8.0.46、Hive 3.1.3、Kafka 3.9.1 和 Spark 3.5.9；MySQL、Hive Metastore、HiveServer2 及 Doris FE 在采集时存在进程或监听端口。
- 三节点均发现 Kafka 3.9.1 KRaft 配置，`node.id` 分别为 1、2、3，`controller.quorum.voters` 一致，存储元数据使用相同 Cluster ID。采集时 Kafka 进程和 9092/9093 未监听，因此本快照只确认安装与配置，不证明当时服务运行。
- Spark 3.5.9-bin-hadoop3、Scala 2.12.18 在三节点可发现，版本命令使用 Java 17.0.20；本盘点不执行 Spark YARN 作业。
- 两个 worker 存在 DataX 的 `mysqlreader`、`hdfswriter` 和日志目录，但原采集器未找到可执行 `bin/datax.py`，因此 `summary.env` 记录为 `NOT_FOUND`。需要用修正后的采集器复测正式入口。

当前配置漂移：

- `hadoop201` 的 `/data/module/hive` 解析为 `apache-hive-3.1.3-bin`，两个 worker 的同名入口仍解析为 `apache-hive-4.1.0-bin`。当前架构候选为 Hive 3.1.3；worker 客户端是否保留及软链接统一方式需在修复后复测。
- 搭建摘要对 Hive 3.1.3 Runtime 给出 Java 8 与 Java 11 两种结论。正式文档不选择其中任一值，必须从 Hive 服务进程的 `/proc/<pid>/exe` 和 Hive-on-MR YARN Container 日志取证。
- DataX 摘要同时使用 `/data/module/datax` 与 `/data/module/datax-current`。正式约定采用版本目录加 `/data/module/datax` 稳定软链接；完成现场统一前保持待复核。

用户提供的 Step 3 至 Step 7 摘要记录了 MySQL Binlog、Hive ORC、Spark on YARN、DataX MySQL→HDFS ORC 和 Kafka KRaft Smoke Test。由于本次目录不含对应完整命令输出、退出状态文件、YARN application 日志和受控重启目录，这些结论作为后续组件验收输入，不在本节直接把组件状态提升为 `verified`。

## 9. 2026-09-14 Step 2～12 Runtime 验收基线

用户已确认 Step 2～12 的运行记录可作为当前 M1 能力基线。它证明目标集群已具备后续阶段所需的组件安装、核心功能、必要链路和恢复能力；非核心附件完整性继续服务于复现和审计，但不单独否定已展示的能力。

| Step | 组件 | 当前结论 | 已确认能力与边界 |
| --- | --- | --- | --- |
| 2 | Hadoop 3.4.1 / HDFS / YARN | `CONFIRMED` | HDFS、MapReduce、聚合日志、Cleanup 和受控重启通过 |
| 3 | MySQL 8.0.46 | `CONFIRMED` | 私网连接、固定 CRUD、ROW/FULL Binlog、失败路径和受控重启恢复通过 |
| 4 | Hive 3.1.3 | `CONFIRMED_WITH_VERSION_CHANGE` | JDK 17、MySQL Metastore schema 3.1.0、HiveServer2/Beeline 与 ORC 能力通过；Hive 4.1.0 退出候选 |
| 5 | Spark 3.5.9 on YARN | `CONFIRMED` | YARN 提交及 Hive ORC 读取、计算通过 |
| 6 | DataX datax_v202309 | `CONFIRMED` | 实际入口 `/data/module/datax-current`；MySQL→HDFS ORC + Snappy、失败非零通过 |
| 7 | Kafka 3.9.1 KRaft | `CONFIRMED` | 三节点 RF=3、minISR=2、生产消费和单 Broker 故障恢复通过 |
| 8～10 | Flink 1.20.5 / Flink CDC 3.6 / Kafka Connector | `CONFIRMED_WITH_NOTE` | Application Mode、MySQL CDC→Kafka 及 SQL Client + YARN Session source/sink 通过；提交后必须查询 YARN final state |
| 11 | Doris 4.0.8 | `CONFIRMED` | FE/BE、SQL 与受控重启恢复通过 |
| 12 | Flink Doris Connector 26.1.1 | `CONFIRMED` | insert/upsert、类型、schema、Checkpoint、TaskManager 故障与恢复通过 |

已验证的临时技术链路包括 `MySQL→DataX→HDFS→Hive→Spark`、`MySQL Binlog→Flink CDC→Kafka→Flink→Kafka` 和 `Kafka→Flink→Checkpoint/Recovery→Doris Connector→Doris`。这些结果验证组件组合兼容性，不创建正式业务 Topic、Schema 或实时表模型，也不替代 Milestone 3 的 ODS 业务验收、Milestone 8 的实时设计评审或 Milestone 9 的端到端 Exactly-Once 验收。Flink 客户端可使用 Java 17；当前 YARN Container 和 Flink Doris User Jar 以 Java 11 兼容边界运行。

根据 `DR-049`，DolphinScheduler 3.4.2 使用 MySQL JDBC Registry，不再引入 ZooKeeper。Master/API/Alert、双 Worker、成功/失败任务和受控重启后复跑已通过，Milestone 1 组件门禁已经闭合；`infra/versions.env` 仍须在版本清单完成去敏复核后单独生成。

## 10. 已知未知项

- `hadoop201` 公网 IP/EIP、三台实例 ID、可用区和实例规格族。
- VPC、vSwitch 和安全组资源 ID。
- 三块数据盘 ID 与各自 ext4 UUID。
- 阿里云密钥对名称、绑定关系、初始镜像管理用户名。
- 管理员当前公网出口 IP `/32`。
- JDK 11 当前采集为 11.0.32、JDK 17 为 17.0.20；后续升级漂移仍需按运行批次记录。

这些值只在需要验证对应行为时现场采集，并按秘密或环境专属信息边界处理。

## 11. 回滚

若本次事实提取存在错误，回滚只撤销本文件及关联仓库配置，并通过新的决策记录修正。不得因此停止现有 Hadoop、格式化 NameNode、删除 HDFS 数据、修改云盘或覆盖 ECS 配置。
