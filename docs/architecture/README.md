# 架构说明

版本：`0.3-draft`
状态：离线 100 单与实时 R1～R3 Pilot 已完成限定验收并转为 History；Milestone 1 已完成，M6 Doris Serving 与 Aggregate Backfill 五 Task 成功终态已验证，M8/M9 实时链路仍在实施

总体技术路线见[工程架构基线](baseline.md)，节点和 Java 角色见[部署拓扑](../operations/topology.md)。本文件保留阶段与技术验收边界；业务源、实时设计和完整交付顺序分别见[业务源设计](../design/business-source-design.md)、[实时链路规范](../design/realtime-pipeline-design.md)与[Project 1 完整交付整改方案](../design/project1-completion-remediation-plan.md)。

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

完整状态、来源和配置见 [集群事实基线](../operations/cluster-baseline.md)。

## 离线主线

```text
MySQL → DataX → Hive ODS（HDFS ORC + Snappy）→ DIM / DWD → DWS → ADS → 数据质量与逐层对账 → Doris
```

- 正式源库为 `ecommerce_oltp`；`ecommerce_oltp_m2_acceptance` 只保留为 Pilot、CDC、R1～R3/M3 历史验收环境。
- V2 Source Data Build 固定采用 Python Generator → CSV → MySQL `LOAD DATA`。Generator 只负责业务关系、状态、时间、主外键、金额与边界场景，不负责逐条写入数据库。
- 正式数仓 database 沿用 `ecommerce_ods`、`ecommerce_dwd`、`ecommerce_dim`、`ecommerce_dws`、`ecommerce_ads`，不新增 `_v2`；V2 初始化前须通过单独方案隔离或重置现有 Pilot 数据。
- `datax/`：通过通用 Job Generator 和多表配置写入 HDFS Stage / Hive ODS 分区；每表配置描述 source/target、primary key、partition、extract 与 quality rule，字段顺序统一引用 Business Generator 的 `TABLE_COLUMNS`，字段类型以正式 MySQL DDL 为准，避免重复维护第二套 columns 清单。
- `hive/`：管理 Metastore、Table、Partition 与离线分层；100 单 Pilot 的 ODS/DWD 只作为 History 保留。
- `spark/`：离线计算统一运行于 YARN；通用执行框架承担提交、日志、锁、失败保护、参数和 precheck，DWD/DIM 业务转换 SQL 按表维护。
- `quality/`：可阻断流程的数据质量检查，后续阶段按固定输入实施。
- `scripts/`：参数化、可重跑并返回明确退出状态的阶段验证入口；M1 五组件入口共享一个最小 Evidence Library。

V2 工程实施按层批量推进：

```text
21 表 Source + Source Gate
→ 批量 ODS + ODS Gate
→ DWD / DIM + Model Gate
→ DWS
→ ADS
→ Doris
→ 最终整链路验收
```

取消的是重复逐表端到端验收，不是测试本身。Source Gate 验证 21 表装载、核心主外键、金额和状态；ODS Gate 验证源/ODS 行数、主键、字段、分区和跨表关系；Model Gate 验证订单、明细、支付、退款、商品关系、金额和核心指标。

M1 组件验收采用“五个独立入口 + 一个共享 Evidence Library”的结构。公共库只负责 `run-id` 与输出目录安全、Evidence Layout、步骤日志、断言、SHA-256、Secret 去敏、`summary.env` 状态和受控 Cleanup，不包含 MySQL、Hive、Kafka、Spark 或 DataX 的组件命令。公共 API 冻结后，各组件脚本只能作为调用方；本地 Contract Test 只证明接口与安全行为，不替代目标 ECS 的组件 Runtime 验收。

本项目不建设独立持久化的 landing/staging 数据层。HDFS Stage 是发布前临时工作区，不是长期数仓层；ODS 装载负责 ORC + Snappy 输出、Spark validation、Hive 分区注册、审计字段、幂等发布和失败隔离。Pilot 已证明该模式可行；当前 21 表 DataX Job Generator 与抽取 Contract 已完成本地测试，但 Stage Runner、Spark Validation / Publish、正式 Runtime 与 ODS Gate 尚未实现或验收，不能标记为 `verified`。

## M1 后续组件分布

| 组件 | `hadoop201` | `hadoop202` | `hadoop203` | 当前状态 |
| --- | --- | --- | --- | --- |
| MySQL 8.0.46 | Server | 私网客户端 | 私网客户端 | verified |
| Hive 3.1.3 | Metastore、HiveServer2 | Client | Client | verified；4.1.0 已因 Spark Metastore 不兼容退出 |
| Kafka 3.9.1 KRaft | Broker/Controller 1 | Broker/Controller 2 | Broker/Controller 3 | verified |
| Spark 3.5.9 | Client | YARN Container | YARN Container | verified |
| DataX 202309 运行包 | - | 运行节点 | 运行节点 | verified；当前运行路径为 `/data/module/datax-current` |
| Doris 4.0.8 | FE，HTTP `18030` | BE 1 | BE 2 | verified |
| DolphinScheduler 3.4.2 | MySQL JDBC Registry、Master、API、Alert | Worker | Worker | verified；正式 M6 DAG 自动重试与失败阻断、Aggregate Backfill Instance `17` 五 Task 成功终态，以及质量失败 Instance `18` 的下游阻断均已通过 |
| Flink 1.20.5 | Client | YARN Container | YARN Container | verified；Application Mode 与 YARN Session 的适用边界见 `DR-026` |

DolphinScheduler 按 `DR-049` 复用 MySQL JDBC Registry，项目不再维护 ZooKeeper；Kafka 坚持 KRaft。组件的精确证据状态见 [兼容性矩阵](../operations/compatibility-matrix.md)。

2026-09-13 的盘点曾发现 worker Hive 软链接漂移，后续验收已锁定 Hive 3.1.3，并确认其在当前 JDK 17 环境下实际运行。Hadoop/YARN 守护进程继续使用独立 Java 11，不因 Hive/Flink 客户端验收切换。

当前已证明的是临时技术验收链路：

```text
MySQL → DataX → HDFS → Hive → Spark
MySQL Binlog → Flink CDC → Kafka → Flink → Kafka
Kafka → Flink → Checkpoint / Recovery → Doris Connector → Doris
```

这些 M1 结果只锁定组件兼容性，不自动创建正式 ODS、Topic、Flink 业务作业或 Doris 实时表模型。其后 R1 小切片另形成了业务链路的限定范围 Runtime 证据，不能反向扩大 M1 技术验收结论。

## 实时边界

```text
MySQL Binlog → Flink CDC → Kafka → Flink → Doris
```

M1 只允许使用临时对象验证组件兼容性。后续 R1～R3 小切片已经形成以下限定范围历史事实：指定 21 表隔离库完成初始 Snapshot；`biz_product_change_event` 的隔离 INSERT、DELETE 以 `op=c/d` 到达 Kafka；`OrderDwdJob` 与 `OrderItemDwdJob` 完成 Java 11 target 构建和 YARN Application Mode Initial Load；订单 `CREATED → CANCELED` 及订单明细 `updated_at` 变更均完成 Kafka `op=u` 到 Doris 同键 Upsert。Doris 历史结果为 101 单（`PAID=69`、`CANCELED=32`）及 320 条订单明细；CDC 与 Order DWD 已从指定 Checkpoint 恢复并继续形成 Completed Checkpoint。当前在线状态、各作业最新 Checkpoint、全字段/跨分区/乱序、物理 DELETE 和更新故障恢复仍未验证。

正式 Flink 业务作业采用 Java DataStream Jar + YARN Application Mode；SQL Client + YARN Session 仅为技术验证。YARN Flink Runtime 使用 Java 11，自行编译的业务 Job 必须保持 `javac --release 11`（class major version 55），除非运行时基线经正式升级。当前 Order / OrderItem DWD 的 `all-to-zero` 与 `kafka_offset` Sequence 只属于 Pilot，不外推为正式多分区方案。

Realtime V2 与离线共享 `ecommerce_oltp`、21 表业务模型、Source Gate 和 Metrics Contract。历史初始化为 Python → CSV → `LOAD DATA`；增量业务生成器通过 MySQL Transaction 产生 Binlog，不能直接写 Kafka。正式 CDC 覆盖 21 表，Topic Namespace 在 Inventory 后冻结，Key/Partition 保证 Same Business Key → Same Partition → Ordered Events，正式 `event_version` 另行设计。Flink 工程按业务域组织 Domain Applications，运行框架通用化、业务转换分业务维护；不再一表一 Application。Shared Source Gate 已通过；当前入口是 60/30 输入 Contract、Topic / Checkpoint Inventory 与 Formal CDC Contract，之后依次进入 CDC Gate、Domain DWD/DIM、Recovery Gate 与离实时对账。

## 轻量 Data Governance 边界

Data Governance 是 Project 1 的内部治理与证据组织能力，不是独立平台：

```text
MySQL / Hive / Doris Runtime ──→ Metadata Snapshot
DataX / SQL / Doris Load / Scheduler Artifact ──→ Table-level Lineage
Released Metric Definition + Quality / Reconciliation / Task Result ──→ Metric Registry
```

- 只实现真实 Metadata Snapshot、基于真实 Artifact 的 Table-level Lineage 和 Project 1-owned Metric Registry。
- 复用既有 Quality、Reconciliation 和 DolphinScheduler 结果，不复制执行引擎。
- 六个 `P1-*` Contract 首先服务于 Project 1 自身验收、治理和简历证据。
- 不建设独立前后端、权限系统、SQL Assistant、Text-to-SQL、LLM/Agent、Column-level Lineage 或 DAG UI。
- 无法采集或解析的内容标记为 `STALE` / `UNKNOWN`，不得按目录、表名或设计意图推断运行事实。

## 配置边界

环境变量示例位于 `env/.env.example`。仓库不保存真实密码、密钥、公网 IP、磁盘 UUID、生产地址或渲染后的秘密配置。组件端口只允许 VPC 私网访问，Web UI 通过 SSH 隧道查看。
