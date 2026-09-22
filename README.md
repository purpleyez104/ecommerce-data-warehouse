# ecommerce-data-warehouse

“电商离实时一体化数据仓库”是一个从零搭建、面向数据开发岗位求职的工程项目。项目以真实运行、可验证、可复现和可解释为基本要求，先完成稳定的离线数仓闭环，再建设实时链路、服务层和 Project 2 交接能力。

## 当前状态

| 项目 | 当前值 |
| --- | --- |
| 当前阶段 | Milestone 0：`completed`；Milestone 1、2：`in progress` |
| 规格版本 | `0.4-draft` |
| 实现状态 | M1 Step 2～12 已根据用户确认的目标 ECS 验收记录完成功能与兼容性验证，剩余门禁为 DolphinScheduler 3.4.2；M2 的 V2 业务与 21 表候选 DDL 已形成，新 Generator 和验收辅助文件已入库。用户提供的 2026-09-19～20 历史摘要记录了隔离验收库的 21 表 CDC 与 10/100 单测试；不证明正式源库、固定 Seed、完整批处理契约或离线接续通过 |
| 当前允许活动 | M1 继续 DolphinScheduler 3.4.2 门禁；M2 核对现存 MySQL DDL、补齐固定 Seed、Generator 契约及抽取接续；M3 暂不进入 |
| 运行验证 | 已证明 MySQL → DataX → HDFS → Hive → Spark、MySQL Binlog → Flink CDC → Kafka → Flink → Kafka，以及 Kafka → Flink → Checkpoint/Recovery → Doris Connector → Doris 的临时技术验收链路；这些结果不等于 M3/M9 正式业务链路已完成 |
| 精确组件版本 | Hadoop 3.4.1、MySQL 8.0.46、Hive 3.1.3、Spark 3.5.9、DataX 202309、Kafka 3.9.1 KRaft、Flink 1.20.5、Flink CDC 3.6.0、Doris 4.0.8 和 Flink Doris Connector 26.1.1 已在目标 ECS 验证；DolphinScheduler 3.4.2 待验证 |
| 运行平台 | 阿里云 ECS（三节点） |
| 实时数仓 | 仅确定目标架构，详细设计待后续评审 |

仓库中的目录和占位文件只表示模块边界，不表示组件已经安装、任务已经实现或链路已经验证。只有在记录的环境和版本中完成安装、启动、连通、执行和结果对账后，内容才能标记为 `verified`。

## 项目目标

- 建立用户身份、商品、购物车、订单、支付、退款、优惠券和独立行为事件的业务模型。
- 打通 MySQL 经 DataX 直写 Hive ODS，再到 DIM/DWD、DWS、ADS 和 Doris 的离线链路。
- 建设 V2 交易资金、流量转化、商品、用户、退款售后和营销指标体系，并在实现前冻结稳定发布 ID。
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
  → Hive ODS（ORC + Snappy）
  → Spark SQL：DIM/DWD
  → Spark SQL：DWS
  → Spark SQL：ADS
  → 数据质量与逐层对账
  → Spark Doris Connector
  → Doris 离线服务表
```

DataX 使用 HDFS Writer 直接写入 Hive ODS 对应的 HDFS 业务日期分区，输出格式为 ORC + Snappy，不建设独立持久化的中间数据层。Hive ODS 同时表示 Hive 逻辑表和其 HDFS 物理存储；分区注册、审计字段、幂等发布和失败隔离属于 ODS 装载责任。该路径的兼容性和运行行为必须在 Milestone 1、3 真实验证。

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
| CDC 与实时计算 | Flink CDC；正式作业为 Java DataStream Jar + YARN Application Mode；SQL Client + YARN Session 用于技术验证 | Milestone 1、8-9 |
| 数据生成与质量工具 | Python、SQL | Milestone 2、5 |

这是数据开发岗位中辨识度较高的经典开源技术组合。“主流”表示技术方向和岗位能力具有代表性，不表示精确版本已经兼容或链路已经运行。所有精确版本必须经过官方依据、安装、启动、连通和最小链路验证后才能锁定。

## 模块划分

### 当前仓库模块

| 路径 | 模块职责 | 首次投入阶段 | 当前状态 |
| --- | --- | --- | --- |
| `docs/` | 规格、计划、架构、集群基线、兼容矩阵、指标口径和验证结论 | Milestone 0 | in progress |
| `infra/` | 主机、端口、组件配置、版本锁定和兼容性记录 | Milestone 1 | implemented |
| `env/` | 不含秘密值的环境变量示例 | Milestone 0-1 | implemented |
| `mock/` | V2 Generator、生成参数和固定验收样本边界 | Milestone 2 | Generator 文件级 `implemented`；固定样本仍为 `planned`，旧固定结果已移入代码归档 |
| `mysql/ddl/`、`mysql/ddl/reference/` | 候选 OLTP DDL；隔离库版本仅作结构参考 | Milestone 2 | 候选文件已入库；`M2-03` 未执行是设计快照，不代表后来隔离库的历史状态或当前正式库结构 |
| `mysql/sql/` | 当前 V2 Seed、初始化和业务验证 SQL 入口 | Milestone 2 | 验收 SQL 已入库；固定 Seed 仍为 `planned` |
| `mock/generator/ecommerce_generator_v1/` | 新 21 表业务生成器 | Milestone 2 | `implemented`（文件已入库）；显式日期、同日重跑和精确依赖版本仍待确认，不作为正式批任务 |
| `tests/`、`scripts/cdc/`、`scripts/generator/`、`scripts/kafka/` | V2 生成器测试、隔离验收辅助与 VM 脚本 | Milestone 2 | 文件已入库；本次导入的 `.sh` 仅保存，未在本机执行或评价运行状态 |
| `archive/legacy-m2-19-table/` | 旧 19 表 Seed、Generator、脚本、测试和固定结果 | 历史归档 | 不作为当前 V2 实现或验收依据 |
| `datax/jobs/`、`datax/scripts/` | MySQL 到 Hive ODS 对应 HDFS 分区的抽取任务和执行入口 | Milestone 3 | placeholder |
| `hive/ods/` | ODS 表、分区注册、审计字段和发布规则 | Milestone 3 | placeholder |
| `hive/dwd/` | 原子事实、去重、状态和字段标准化 | Milestone 4 | placeholder |
| `hive/dws/` | 可复用主题汇总、比率分子和分母 | Milestone 4-5 | placeholder |
| `hive/ads/` | V2 正式指标和面向查询的结果表 | Milestone 5 | placeholder |
| `spark/sql/`、`spark/scripts/` | ODS、DIM/DWD、DWS、ADS 转换、提交脚本和性能实验入口 | Milestone 4-7 | placeholder |
| `quality/checks/` | 唯一性、完整性、状态、分区和守恒检查 | Milestone 3-6 | placeholder |
| `doris/ddl/`、`doris/sql/` | 离线服务表与验证 SQL；实时表在 Milestone 8 后确定 | Milestone 6 | placeholder |
| `scheduler/dolphinscheduler/` | T+1 DAG、参数、重试、补数、阻断和对账 | Milestone 6 | placeholder |
| `flink/cdc/`、`flink/sql/`、`flink/jobs/`、`flink/scripts/` | CDC、技术验证 SQL、正式 Java 作业和提交/恢复入口 | Milestone 8-9 | placeholder；目录存在不表示正式实时设计或作业已实现 |
| `scripts/` | 参数化执行、健康检查和阶段验证入口 | 按阶段 | implemented；Hadoop 和 MySQL 仓库脚本已有 Runtime 结果；其他组件的当前运行事实来自用户确认的 Step 2～12 验收记录，不虚构尚未进仓的自动化脚本 |

`placeholder` 表示只存在目录或说明文件；`unconfigured` 表示入口明确返回未配置状态；二者都不代表实现可用。

### 后续模块占位与创建门禁

部分目录已按用户批准建立为占位，但只有在对应阶段通过门禁后才能加入正式实现：

| 计划路径 | 模块职责 | 创建条件 |
| --- | --- | --- |
| `hive/dim/` | 一致维度和待确认的历史变化策略 | 已建立占位；Milestone 4 的维度设计确认后实施 |
| `reconciliation/` | 跨层及离实时对账任务 | Milestone 5 形成稳定结果结构 |
| `kafka/` | Topic、Schema 和生命周期配置 | 已建立占位；Milestone 8 实时设计通过后实施 |

## 指标范围

V2 指标按六个域组织：交易与资金 `TR-01`～`TR-14`、流量与转化 `TF-01`～`TF-08`、商品 `PR-01`～`PR-05`、用户 `US-01`～`US-06`、退款与售后 `RF-01`～`RF-07`、营销 `MK-01`～`MK-07`。这些是文档检索编号，不自动等同于稳定发布 ID。

完整口径见 [V2 指标体系](docs/metrics.md)。复购率、部分退款比例、券核销率、细分漏斗分母和 30 日退款率精确分母截止点等仍为 `待细化`。

## 阶段总览

| Milestone | 名称 | 核心交付 | 当前状态 |
| --- | --- | --- | --- |
| 0 | 项目定义与文档基线 | README、规格、阶段计划、协作边界 | completed |
| 1 | 基础设施与兼容性 | 三节点、版本矩阵、启动和最小连通验证 | in progress |
| 2 | 业务模型与数据生成 | V2 业务基线、21 表 OLTP、行为事件、固定 seed、预期结果 | in progress |
| 3 | DataX 直写 Hive ODS | 全量/增量抽取、ODS ORC 分区、注册与对账 | pending |
| 4 | 离线数仓 MVP | DIM/DWD、DWS、ADS 最小垂直链路 | pending |
| 5 | 正式指标与数据质量 | V2 正式指标、质量结果、幂等和回补 | pending |
| 6 | Doris 服务与调度 | 离线服务表、T+1 DAG、失败阻断和对账 | pending |
| 7 | Spark 性能实验 | 倾斜、Join、分区裁剪实验 | pending |
| 8 | 实时数仓设计评审 | Topic、窗口、状态、维度、Doris 模型 | pending |
| 9 | 实时链路与可靠性 | CDC、Kafka、Flink、恢复、五项对账 | pending |
| 10 | Project 1 面试发布 | 可复现部署、证据、六个只读交接契约 | pending |

详细进入条件、模块、交付物和验收标准见 [阶段开发计划](docs/plan.md)。

## 开发环境

三个节点均运行于阿里云 ECS；以下网络、资源、磁盘和 Hadoop 角色来自本项目当前集群记录，按 `DR-005` 作为确认事实：

| ECS 节点 | 私网 IPv4 | 集群角色 | 计算资源 | 系统盘 | 数据盘 |
| --- | --- | --- | --- | --- | --- |
| `hadoop201` | `10.20.1.201` | `master` | 4 vCPU / 16 GB | 50 GiB | 80 GiB |
| `hadoop202` | `10.20.1.202` | `worker01` | 8 vCPU / 16 GB | 50 GiB | 120 GiB |
| `hadoop203` | `10.20.1.203` | `worker02` | 8 vCPU / 16 GB | 50 GiB | 120 GiB |

这是成本受限的 ECS 开发环境，不代表生产拓扑。三台数据盘均为 `/dev/vdb`、ext4、挂载到 `/data`；组件由 `yee` 运行，默认 Java 为 17，Hadoop 3.4.1 单独使用 Java 11。HDFS 的 NameNode/SecondaryNameNode 位于 `hadoop201`，两个 worker 运行 DataNode；YARN 的 ResourceManager 和 JobHistoryServer 位于 `hadoop201`，两个 worker 运行 NodeManager。是否扩容必须依据磁盘空间不足、OOM、持续 Swap、频繁 Full GC、进程被杀或核心服务无法稳定共存等真实证据。Doris FE HTTP 已决定使用 `18030`，保留 YARN ResourceManager Scheduler 的 `8030`。

## 文档入口

- [项目规格](docs/spec.md)：项目范围、架构、指标、接口和验收标准。
- [阶段开发计划](docs/plan.md)：Milestone 顺序、模块、交付物、进入条件和阻断规则。
- [架构说明](docs/architecture.md)：当前架构边界说明；后续需随实施阶段更新。
- [建模说明](docs/modeling.md)：业务、逻辑、物理和指标建模文档导航。
- [部署说明](docs/deployment.md)：部署拓扑、环境基线、兼容性和排障文档导航。
- [最终工程架构 V1.0](docs/final-architecture-v1.0.md)：总体技术路线、Flink 正式部署选择与历史技术验收边界。
- [部署拓扑](docs/deployment-topology.md)：三节点角色、资源、Java 与安全边界。
- [业务源设计](docs/business-source-design.md)：V2 21 表和独立行为源的交付及验收边界。
- [实时链路规范](docs/realtime-pipeline-design.md)：DataStream Application 方案与 Milestone 8 待评审契约。
- [集群事实基线](docs/cluster-baseline.md)：当前 ECS、网络、磁盘、用户、Java 和 Hadoop 的确认事实及验证结论。
- [组件兼容性矩阵](docs/compatibility-matrix.md)：精确版本候选、官方依据、项目状态和验证门禁。
- [安装与排障记录](docs/installation-troubleshooting.md)：目标 ECS 上真实发生的问题、修复、复测和回滚。
- [V2 指标体系](docs/metrics.md)：六个指标域的完整口径、依赖、待细化项和最小验收案例。
- [V2 业务基线](docs/business/business-baseline-v2.md)：当前自营商城业务规则和验收不变量。
- [V2 逻辑模型](docs/source/logical-model-v2.md)：当前实体、关系、状态和指标字段覆盖。
- [21 表候选物理设计](docs/source/physical-model-v1.md)：字段级候选方案；不等于现存 MySQL 结构。
- [M2-03 设计快照](docs/source/M2-03-物理设计与静态审查.md)：当时静态检查通过、DDL 未执行；后续隔离验收另按历史事实记录。
- [ENV-05 CDC 验收](docs/acceptance/env-05-cdc-acceptance.md)：单隔离测试表的限定范围 CDC 与故障恢复证据。
- [历史 Milestone 2 业务设计](docs/archive/milestone-2-business-design.md)：旧方案完整归档，不作为当前 21 表实现输入。
- [修改日志](CHANGELOG.md)：按“新增、变更、修复、移除”记录面向使用者和维护者的可交付变更。
- [项目决策记录](docs/decision-register.md)：记录影响项目范围、业务口径、架构、版本、模型、接口、安全或验收方式的正式决策及其状态。
- [协作规则](AGENTS.md)：Codex 和贡献者修改仓库时必须遵循的规则。

## 工作规则

1. 修改前依次阅读 `README.md`、`docs/spec.md` 和 `docs/plan.md`。
2. 每次只完成当前 Milestone 的可验收内容，不一次生成整个项目。
3. 先确认业务语义，再设计物理表、任务和指标 SQL。
4. 新实现必须给出执行命令、固定输入、预期结果和失败行为。
5. 旧仓库只作为外部参考；迁入内容必须记录来源、理由、改造、验证和回滚方式。
6. 不提交密码、密钥、Token、`.env`、真实生产地址、个人数据或原始运行日志。
7. 静态检查只能证明文件和契约一致，不能替代真实组件和数据链路验证。
8. Agent 每次最终答复都总结核心操作和核心决策，并询问用户是否将其写入 `CHANGELOG.md`、`docs/decision-register.md` 或两者；未获确认时不自动落盘，当前请求已明确授权的记录除外。
9. Trellis 只管理 Task 状态、计划和执行证据；项目事实优先级为 `AGENTS.md`、项目 docs、Trellis Task。当前使用 Data Engineering spec、Codex inline，自动 Commit 与 Hook 注册均关闭。

Milestone 0 已于 2026-09-04 通过用户评审。根据 `DR-026`，M1 Step 2～12 已完成兼容性与功能验收，当前只剩 DolphinScheduler 3.4.2，M1 整体仍为 `in progress`。M2 以 V2 业务、指标和 21 表候选源模型为准，状态为 `in progress`。`M2-03` 保留未执行时的设计快照；用户提供的 2026-09-19～20 摘要记录了后来隔离验收库的有限 CDC/造数结果，不等于当前正式库结构、固定 Seed、90 天数据、完整抽取接续或 M2 完成。旧方案文档和代码分别位于 `docs/archive/` 与 `archive/legacy-m2-19-table/`。M3 仍被 M2 交付门禁阻断。

根据 `DR-029`，正式实时作业选用 Java DataStream Jar + YARN Application Mode；该选型不解除 Milestone 8 设计评审和 Milestone 9 运行验收门禁。BI/Dashboard/Agent 仅为后续数据应用规划，尚未实施；Doris 4.0.8 受控重启恢复已通过，但正式业务服务表仍待对应阶段验收。
