# 架构说明

版本：`0.3-draft`
状态：Milestone 1 实施中；M1 Step 2～12 已验证，当前剩余门禁为 DolphinScheduler 3.4.2

## 当前基础设施

```text
管理员电脑
  └─ SSH → hadoop201 / 10.20.1.201
               ├─ NameNode + SecondaryNameNode
               ├─ ResourceManager + JobHistoryServer
               ├─ 私网 SSH → hadoop202 / 10.20.1.202
               │                └─ DataNode + NodeManager
               └─ 私网 SSH → hadoop203 / 10.20.1.203
                                └─ DataNode + NodeManager
```

- 三节点位于杭州地域、VPC `10.20.0.0/16`、vSwitch `10.20.1.0/24`。
- 数据盘均挂载到 `/data`，组件由 `yee` 运行。
- 默认 Java 为 OpenJDK 17；Hadoop 3.4.1 单独使用 OpenJDK 11。
- HDFS 为单 NameNode、双 DataNode，副本数 2；YARN 为单 ResourceManager、双 NodeManager。
- Hadoop 3.4.1 已完成固定 HDFS 文件、MapReduce WordCount、YARN application、聚合日志和受控重启验证；当前状态为 `verified`。

完整状态、来源和配置见 [集群事实基线](cluster-baseline.md)。

## 离线主线

```text
MySQL → DataX → Hive ODS（HDFS ORC + Snappy）→ DIM / DWD → DWS → ADS → 数据质量与逐层对账 → Doris
```

- `mysql/`：源表 DDL 与固定种子数据；M1 只安装 MySQL 和验证 Binlog，不创建正式业务表。
- `datax/`：通过 HDFS Writer 直接写入 Hive ODS 对应 HDFS 业务日期分区；M1 只验证临时数据的 MySQL Reader、HDFS Writer 和 ORC + Snappy。
- `hive/`：离线分层 SQL；M1 只验证 Metastore、HiveServer2 和临时外部表。
- `spark/`：离线计算统一运行于 YARN；M1 只验证最小 YARN 作业和 Hive/ORC 访问。
- `quality/`：可阻断流程的数据质量检查，后续阶段按固定输入实施。
- `scripts/`：参数化、可重跑并返回明确退出状态的阶段验证入口；M1 五组件入口共享一个最小 Evidence Library。

M1 组件验收采用“五个独立入口 + 一个共享 Evidence Library”的结构。公共库只负责 `run-id` 与输出目录安全、Evidence Layout、步骤日志、断言、SHA-256、Secret 去敏、`summary.env` 状态和受控 Cleanup，不包含 MySQL、Hive、Kafka、Spark 或 DataX 的组件命令。公共 API 冻结后，各组件脚本只能作为调用方；本地 Contract Test 只证明接口与安全行为，不替代目标 ECS 的组件 Runtime 验收。

本项目不建设独立持久化的 landing/staging 数据层。ODS 装载负责 ORC + Snappy 输出、Hive 分区注册、审计字段、幂等发布和失败隔离；在 Milestone 3 真实验证完成前不得把该路径标记为 `verified`。

## M1 后续组件分布

| 组件 | `hadoop201` | `hadoop202` | `hadoop203` | 当前状态 |
| --- | --- | --- | --- | --- |
| MySQL 8.0.46 | Server | 私网客户端 | 私网客户端 | verified |
| Hive 3.1.3 | Metastore、HiveServer2 | Client | Client | verified；4.1.0 已因 Spark Metastore 不兼容退出 |
| Kafka 3.9.1 KRaft | Broker/Controller 1 | Broker/Controller 2 | Broker/Controller 3 | verified |
| Spark 3.5.9 | Client | YARN Container | YARN Container | verified |
| DataX 202309 运行包 | - | 运行节点 | 运行节点 | verified；当前运行路径为 `/data/module/datax-current` |
| Doris 4.0.8 | FE，HTTP `18030` | BE 1 | BE 2 | verified |
| DolphinScheduler 3.4.2 | ZooKeeper、Master、API、Alert | Worker | Worker | candidate |
| Flink 1.20.5 | Client | YARN Container | YARN Container | verified；Application Mode 与 YARN Session 的适用边界见 `DR-026` |

单节点 ZooKeeper 只服务 DolphinScheduler；Kafka 坚持 KRaft。组件的精确证据状态见 [兼容性矩阵](compatibility-matrix.md)。

2026-09-13 的盘点曾发现 worker Hive 软链接漂移，后续验收已锁定 Hive 3.1.3，并确认其在当前 JDK 17 环境下实际运行。Hadoop/YARN 守护进程继续使用独立 Java 11，不因 Hive/Flink 客户端验收切换。

当前已证明的是临时技术验收链路：

```text
MySQL → DataX → HDFS → Hive → Spark
MySQL Binlog → Flink CDC → Kafka → Flink → Kafka
Kafka → Flink → Checkpoint / Recovery → Doris Connector → Doris
```

这些结果锁定组件兼容性，不创建正式 ODS、Topic、Flink 业务作业或 Doris 实时表模型。

## 实时边界

```text
MySQL Binlog → Flink CDC → Kafka → Flink → Doris
```

M1 只允许使用临时对象验证组件兼容性。正式 Topic、Partition、窗口、Watermark、迟到、去重、状态 TTL、维度策略和 Doris 实时表模型必须等待 Milestone 8 评审。

## 配置边界

环境变量示例位于 `env/.env.example`。仓库不保存真实密码、密钥、公网 IP、磁盘 UUID、生产地址或渲染后的秘密配置。组件端口只允许 VPC 私网访问，Web UI 通过 SSH 隧道查看。
