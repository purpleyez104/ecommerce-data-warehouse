# ecommerce-data-warehouse

“电商离实时一体化数据仓库”是一个从零搭建、面向数据开发岗位求职的工程项目。项目以真实运行、可验证、可复现和可解释为基本要求，先完成稳定的离线数仓闭环，再建设实时链路、服务层和 Project 2 交接能力。

## 当前状态

| 项目 | 当前值 |
| --- | --- |
| 当前阶段 | Milestone 0：项目定义与文档基线 |
| 规格版本 | `0.2-draft` |
| 实现状态 | 尚未创建正式业务模型、数据表或运行链路 |
| 运行验证 | 未进行 |
| 精确组件版本 | 未锁定 |
| 运行平台 | 阿里云 ECS（三节点） |
| 实时数仓 | 仅确定目标架构，详细设计待后续评审 |

仓库中的目录和占位文件只表示模块边界，不表示组件已经安装、任务已经实现或链路已经验证。只有在记录的环境和版本中完成安装、启动、连通、执行和结果对账后，内容才能标记为 `verified`。

## 项目目标

- 建立用户、流量、商品、交易和营销五个主题的业务模型。
- 打通 MySQL 到 HDFS landing、Hive ODS、DIM/DWD、DWS、ADS 和 Doris 的离线链路。
- 建设 30 项 V1 正式离线指标，并为 10 项扩展指标保留稳定编号。
- 提供固定 seed 数据、逐层预期结果、数据质量、幂等重跑和连续回补能力。
- 使用 Spark SQL/PySpark 完成分层加工，并真实开展数据倾斜、Join 和分区裁剪实验。
- 在离线链路稳定后，单独评审并实现 Kafka、Flink CDC、Flink 和 Doris 实时链路。
- 使用 DolphinScheduler 管理业务日期、依赖、重试、补数、质量阻断和对账。
- 为 Project 2 提供元数据、血缘、指标、质量、对账和任务状态六个只读契约。

## 项目边界

Project 1 是业务语义、SQL、指标和运行结果的唯一事实来源。Project 2 必须等待 Project 1 完成并稳定后再开始，且只能消费已发布的只读接口，不得回写或重新定义指标。

建议面试讲述权重：

```text
Project 1：65%
Project 2：35%
```

V1 不建设库存域，不建设生产级 Hadoop HA，不引入阿里云专有中间件、Kafka ZooKeeper 模式、Spark/Flink Standalone、Kubernetes、HBase、Redis、Elasticsearch、ClickHouse、Iceberg、Hudi 或 Paimon。

## 目标数据链路

### 离线主线

```text
MySQL ecommerce_oltp
  → DataX
  → HDFS landing/staging（Text/CSV）
  → Hive ODS（ORC + Snappy）
  → Spark SQL：DIM/DWD
  → Spark SQL：DWS
  → Spark SQL：ADS
  → 数据质量与逐层对账
  → Spark Doris Connector
  → Doris 离线服务表
```

`landing/staging` 是物理缓冲区，不属于正式 ODS。DataX 只负责可靠抽取和落地；正式类型转换、金额精度、状态标准化和 ORC 建模由 Spark/Hive 负责。

### 实时目标链路

```text
MySQL Binlog
  → Flink CDC
  → Kafka Raw CDC Topic
  → Flink 实时清洗与计算
  → Kafka 标准事件 / HDFS-Hive 归档 / Doris 实时服务表
```

实时链路当前状态为 `planned`。Topic、Partition、Schema、窗口、Watermark、迟到、去重、状态 TTL、实时维度、Checkpoint 和 Doris 实时表模型必须在 Milestone 8 单独评审，不在当前阶段自行补全。

## 技术栈

| 职责 | 技术 | 进入阶段 |
| --- | --- | --- |
| 业务数据源 | MySQL | Milestone 1-2 |
| 分布式存储与资源管理 | Hadoop HDFS、YARN | Milestone 1 |
| 数仓元数据与 SQL | Hive | Milestone 1、3-5 |
| 离线抽取 | DataX | Milestone 1、3 |
| 离线计算 | Spark SQL、PySpark，运行于 YARN | Milestone 1、4-7 |
| 分析服务 | Doris | Milestone 1、6 |
| 工作流调度 | DolphinScheduler | Milestone 1、6 |
| 消息传输 | Kafka KRaft | Milestone 1、8-9 |
| CDC 与实时计算 | Flink CDC、Flink SQL、Java DataStream | Milestone 1、8-9 |
| 数据生成与质量工具 | Python、SQL | Milestone 2、5 |

这是数据开发岗位中辨识度较高的经典开源技术组合。“主流”表示技术方向和岗位能力具有代表性，不表示精确版本已经兼容或链路已经运行。所有精确版本必须经过官方依据、安装、启动、连通和最小链路验证后才能锁定。

## 模块划分

### 当前仓库模块

| 路径 | 模块职责 | 首次投入阶段 | 当前状态 |
| --- | --- | --- | --- |
| `docs/` | 规格、计划、架构、指标口径和验证结论 | Milestone 0 | draft |
| `env/` | 不含秘密值的环境变量示例 | Milestone 0-1 | placeholder |
| `mock/` | 固定 seed 验收数据、边界场景和预期结果说明 | Milestone 2 | placeholder |
| `mysql/ddl/` | OLTP DDL、约束、索引和状态字段 | Milestone 2 | placeholder |
| `mysql/seed/` | 固定验收数据与初始化入口 | Milestone 2 | placeholder |
| `datax/jobs/` | MySQL 到 HDFS landing 的全量和增量抽取任务 | Milestone 3 | placeholder |
| `hive/ods/` | ODS 表及 landing 到 ODS 的装载逻辑 | Milestone 3 | placeholder |
| `hive/dwd/` | 原子事实、去重、状态和字段标准化 | Milestone 4 | placeholder |
| `hive/dws/` | 可复用主题汇总、比率分子和分母 | Milestone 4-5 | placeholder |
| `hive/ads/` | 30 项正式指标和面向查询的结果表 | Milestone 5 | placeholder |
| `spark/sql/` | ODS、DIM/DWD、DWS、ADS 转换和性能实验入口 | Milestone 4-7 | placeholder |
| `quality/checks/` | 唯一性、完整性、状态、分区和守恒检查 | Milestone 3-6 | placeholder |
| `doris/ddl/` | 离线服务表；实时表在 Milestone 8 后确定 | Milestone 6 | placeholder |
| `scheduler/dolphinscheduler/` | T+1 DAG、参数、重试、补数、阻断和对账 | Milestone 6 | placeholder |
| `flink/jobs/` | CDC、实时清洗、聚合和恢复作业 | Milestone 9 | placeholder |
| `scripts/` | 参数化执行、健康检查和阶段验证入口 | 按阶段 | unconfigured |

`placeholder` 表示只存在目录或说明文件；`unconfigured` 表示入口明确返回未配置状态；二者都不代表实现可用。

### 按需创建的后续模块

以下目录当前不存在，只有在对应阶段产生可维护内容时才创建：

| 计划路径 | 模块职责 | 创建条件 |
| --- | --- | --- |
| `infra/` | 主机、组件配置、版本锁定和兼容性记录 | Milestone 1 开始且版本验证方案通过 |
| `generator/` | 历史数据和持续业务事件生成器 | Milestone 2 的业务模型确认 |
| `hive/dim/` | 一致维度和待确认的历史变化策略 | Milestone 4 的维度设计确认 |
| `reconciliation/` | 跨层及离实时对账任务 | Milestone 5 形成稳定结果结构 |
| `tests/` | 固定输入、预期输出、契约和回归测试 | 首个可执行任务进入仓库 |
| `kafka/` | Topic、Schema 和生命周期配置 | Milestone 8 实时设计通过 |

## 指标范围

- `P1_METRIC_001` 至 `P1_METRIC_030`：V1 正式离线指标。
- `P1_METRIC_031` 至 `P1_METRIC_040`：扩展候选指标。
- `P1_METRIC_014`、`015`、`016`、`025`、`026`：未来实时阶段候选指标。

指标名称、来源映射和排除原因以 [项目规格](docs/spec.md) 为准。指标编号已确定，但完整公式、时间归属、去重、取消/退款、精度、舍入和零分母规则仍需在实现前确认。

## 阶段总览

| Milestone | 名称 | 核心交付 | 当前状态 |
| --- | --- | --- | --- |
| 0 | 项目定义与文档基线 | README、规格、阶段计划、协作边界 | in progress |
| 1 | 基础设施与兼容性 | 三节点、版本矩阵、启动和最小连通验证 | pending |
| 2 | 业务模型与数据生成 | OLTP、状态机、固定 seed、预期结果 | pending |
| 3 | DataX landing 与 ODS | 全量/增量抽取、HDFS landing、Hive ODS | pending |
| 4 | 离线数仓 MVP | DIM/DWD、DWS、ADS 最小垂直链路 | pending |
| 5 | 正式指标与数据质量 | 30 项指标、质量结果、幂等和回补 | pending |
| 6 | Doris 服务与调度 | 离线服务表、T+1 DAG、失败阻断和对账 | pending |
| 7 | Spark 性能实验 | 倾斜、Join、分区裁剪实验 | pending |
| 8 | 实时数仓设计评审 | Topic、窗口、状态、维度、Doris 模型 | pending |
| 9 | 实时链路与可靠性 | CDC、Kafka、Flink、恢复、五项对账 | pending |
| 10 | Project 1 面试发布 | 可复现部署、证据、六个只读交接契约 | pending |

详细进入条件、模块、交付物和验收标准见 [阶段开发计划](docs/plan.md)。

## 开发环境

三个节点均运行于阿里云 ECS：

| ECS 节点 | 集群角色 | 计算资源 | 系统盘 | 数据盘 |
| --- | --- | --- | --- | --- |
| `hadoop201` | `master` | 4 vCPU / 16 GB | 50 GiB | 80 GiB |
| `hadoop202` | `worker01` | 8 vCPU / 16 GB | 50 GiB | 120 GiB |
| `hadoop203` | `worker02` | 8 vCPU / 16 GB | 50 GiB | 120 GiB |

这是成本受限的 ECS 开发环境，不代表生产拓扑。系统盘和数据盘的挂载点、文件系统、目录分配及实际可用容量尚未确认，必须在 Milestone 1 通过真实磁盘检查后记录。是否扩容必须依据磁盘空间不足、OOM、持续 Swap、频繁 Full GC、进程被杀或核心服务无法稳定共存等真实证据。Doris 配置前必须解决 YARN ResourceManager 与 Doris FE 默认 `8030` 端口冲突。

## 文档入口

- [项目规格](docs/spec.md)：项目范围、架构、指标、接口和验收标准。
- [阶段开发计划](docs/plan.md)：Milestone 顺序、模块、交付物、进入条件和阻断规则。
- [架构说明](docs/architecture.md)：当前架构边界说明；后续需随实施阶段更新。
- [指标口径](docs/metrics.md)：指标定义和血缘入口；正式口径尚待后续阶段补充。
- [协作规则](AGENTS.md)：Codex 和贡献者修改仓库时必须遵循的规则。

## 工作规则

1. 修改前依次阅读 `README.md`、`docs/spec.md` 和 `docs/plan.md`。
2. 每次只完成当前 Milestone 的可验收内容，不一次生成整个项目。
3. 先确认业务语义，再设计物理表、任务和指标 SQL。
4. 新实现必须给出执行命令、固定输入、预期结果和失败行为。
5. 旧仓库只作为外部参考；迁入内容必须记录来源、理由、改造、验证和回滚方式。
6. 不提交密码、密钥、Token、`.env`、真实生产地址、个人数据或原始运行日志。
7. 静态检查只能证明文件和契约一致，不能替代真实组件和数据链路验证。

当前没有可宣称成功运行的安装、任务或指标结果。下一步由 Milestone 0 的规格评审结果决定是否进入 Milestone 1。
