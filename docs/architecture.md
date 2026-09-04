# 架构说明

版本：`0.3-draft`
状态：Milestone 1 实施中；Hadoop 运行拓扑已确认，后续组件待验证

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
- 当前 Hadoop 版本、进程和节点拓扑是确认事实；固定 HDFS 文件、完整 MapReduce 结果和重启证据仍待补齐。

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
- `scripts/`：参数化、可重跑并返回明确退出状态的阶段验证入口。

本项目不建设独立持久化的 landing/staging 数据层。ODS 装载负责 ORC + Snappy 输出、Hive 分区注册、审计字段、幂等发布和失败隔离；在 Milestone 3 真实验证完成前不得把该路径标记为 `verified`。

## M1 后续组件分布

| 组件 | `hadoop201` | `hadoop202` | `hadoop203` | 当前状态 |
| --- | --- | --- | --- | --- |
| MySQL 8.0.46 | Server | 私网客户端 | 私网客户端 | candidate |
| Hive 4.1.0 | Metastore、HiveServer2 | 客户端配置 | 客户端配置 | candidate |
| Kafka 3.9.1 KRaft | Broker/Controller 1 | Broker/Controller 2 | Broker/Controller 3 | candidate |
| Spark 3.5.9 | 客户端 | YARN 容器 | YARN 容器 | candidate |
| DataX 202309 | - | 运行节点 | 运行节点 | candidate |
| Doris 4.0.8 | FE，HTTP `18030` | BE 1 | BE 2 | candidate |
| DolphinScheduler 3.4.2 | ZooKeeper、Master、API、Alert | Worker | Worker | candidate |
| Flink 1.20.5 | 客户端 | YARN 容器 | YARN 容器 | candidate |

单节点 ZooKeeper 只服务 DolphinScheduler；Kafka 坚持 KRaft。组件的精确证据状态见 [兼容性矩阵](compatibility-matrix.md)。

## 实时边界

```text
MySQL Binlog → Flink CDC → Kafka → Flink → Doris
```

M1 只允许使用临时对象验证组件兼容性。正式 Topic、Partition、窗口、Watermark、迟到、去重、状态 TTL、维度策略和 Doris 实时表模型必须等待 Milestone 8 评审。

## 配置边界

环境变量示例位于 `env/.env.example`。仓库不保存真实密码、密钥、公网 IP、磁盘 UUID、生产地址或渲染后的秘密配置。组件端口只允许 VPC 私网访问，Web UI 通过 SSH 隧道查看。
