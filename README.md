# ecommerce-data-warehouse

“电商离实时一体化数据仓库”是一个从零搭建、面向数据开发岗位求职的工程项目。项目以真实运行、可验证、可复现和可解释为基本要求。MySQL 21 表 ODS、独立 Behavior ODS 和 Milestone 4 最小离线闭环均已有真实 Runtime；M5 已完成申请粒度退款事实以及六域 6 DWS + 1 ADS，最新 41/41 Aggregate Gate 与幂等重跑通过。Formal CDC 保持独立并行支线。

## 当前状态

| 项目 | 当前值 |
| --- | --- |
| 当前阶段 | 离线与实时 Pilot：`completed / HISTORY`；Shared Source Data Build、批量 ODS、M4/M5 离线建模质量与 M6 Doris Serving/调度：`VERIFIED`。Milestone 0、1、3、4、5、6：`completed`；Milestone 2、8、9：`in progress`；Milestone 7：`pending` |
| 规格版本 | `0.5-draft` |
| 实现状态 | M1 已完成，DolphinScheduler 3.4.2 + MySQL JDBC Registry 已通过成功/失败任务与受控重启复跑。Seed `20260105` 的隔离 ODS 已完成 Day 60～90、29/29 Checkpoint、跨日中断恢复和 1,498/1,498 最终 Gate；Behavior ODS 为 3,000,000 行、90 分区、95/95 Gate；M6 Doris Serving 已完成 90 日首次/幂等装载及 Hive/Doris 22 字段逐行对账。Formal CDC、Kafka Raw Layer 与 Domain Flink Applications 仍为 `not_run` 或未完成 |
| 当前允许活动 | M6 Stage Gate 已完成：Aggregate Backfill Instance `17` 五 Task 成功；质量失败验证 Instance `18` 按预期失败且未运行 Doris/Reconciliation，Doris 90 日基线未变化。下一入口是 M7 Spark 性能实验；实时仍只进入 Formal CDC Contract 与初始化设计，不并行执行 Runtime |
| 运行验证 | 除三条临时技术验收链路外，`hist-v1-001` 已在历史限定范围证明 100 单、69 `PAID`、31 `CANCELED`、88 个 ODS 业务日期分区及三项金额基线；正式 M3 已通过 Snapshot 与 Day 60～90 ODS Stage Gate。实时 R1～R3 在历史限定范围证明 21 表 1,178 条 Snapshot、Binlog 增量、CDC/Order DWD 从 Checkpoint 恢复、订单 `CREATED → CANCELED` Upsert，以及 OrderItem DWD 320 行 Initial Load 与一次同键增量更新；当前实时在线状态仍为 `UNKNOWN`，上述 Pilot 结果不等于 M9 完整业务链路、全字段/乱序、恢复一致性或端到端 Exactly-Once 已完成 |
| 精确组件版本 | Hadoop 3.4.1、MySQL 8.0.46、Hive 3.1.3、Spark 3.5.9、DataX 202309、Kafka 3.9.1 KRaft、Flink 1.20.5、Flink CDC 3.6.0、Doris 4.0.8、Flink Doris Connector 26.1.1 和 DolphinScheduler 3.4.2 + MySQL JDBC Registry 已在目标 ECS 验证 |
| 运行平台 | 阿里云 ECS（三节点） |
| 实时数仓 | M8/M9 为 `in progress`；R1～R3 已完成 Pilot / Acceptance 使命并转为 History，`OrderDwdJob` / `OrderItemDwdJob` 保留为 Verified Prototype 与 Framework Reference。`ecommerce_oltp_m2_acceptance`、`ods_cdc_m2_clean_v1`、`all-to-zero`、Pilot Checkpoint 和 `kafka_offset` Sequence 不进入正式链路。Shared Source Gate 已通过，下一步为 Formal CDC Contract、CDC Gate 与按业务域组织的 DWD/DIM |

仓库中的目录和占位文件只表示模块边界，不表示组件已经安装、任务已经实现或链路已经验证。只有在记录的环境和版本中完成安装、启动、连通、执行和结果对账后，内容才能标记为 `verified`。

## 项目目标

### 交付版本路线

- **V1 Pilot**：离线 100 单切片和实时 R1～R3 均已完成限定验收并转为 History。Pilot 用于证明组件组合、CDC/Upsert/Recovery 和工程模式，不再作为正式 V2 数据开发入口。
- **V2（当前共同主线）**：离线与实时共享 21 表正式源模型、Python → CSV → `LOAD DATA` → `ecommerce_oltp`、Source Gate、业务模型和指标合同；Source Gate 后分别进入批量 ODS 与正式 CDC。正式数据规模已确认为 90 天、100,000 笔订单、约 285,000 条订单明细、约 100 万条 OLTP 记录和 3,000,000～5,000,000 条行为事件；性能实验规模为约 900,000 笔订单和 9,000,000 条行为事件。Topic、Partition、事件版本和性能结论仍须在规格冻结和实测后给出。

这里的“交付 V1/V2”是项目建设阶段，与文档中已有的“V2 业务基线/指标体系”版本标识不是同一个维度。

- 建立用户身份、商品、购物车、订单、支付、退款、优惠券和独立行为事件的业务模型。
- 打通 MySQL 经 DataX 直写 Hive ODS，再到 DIM/DWD、DWS、ADS 和 Doris 的离线链路。
- 建设 V2 交易资金、流量转化、商品、用户、退款售后和营销指标体系，并在实现前冻结稳定发布 ID。
- 提供固定 seed 数据、逐层预期结果、数据质量、幂等重跑和连续回补能力。
- 使用 Spark SQL/PySpark 完成分层加工，并真实开展数据倾斜、Join 和分区裁剪实验。
- 以独立可验收 Stage 推进 Kafka、Flink CDC、Flink 和 Doris 实时链路，实时范围扩展仍须通过 Milestone 8 契约评审。
- 使用 DolphinScheduler 管理业务日期、依赖、重试、补数、质量阻断和对账。
- 建设轻量 Data Governance：真实 Metadata Snapshot、基于真实 SQL/配置的 Table-level Lineage 和 Project 1-owned Metric Registry，并关联质量、对账和调度结果。
- 发布元数据、血缘、指标、质量、对账和任务状态六个只读契约，首先服务于 Project 1 自身治理、验收和证据组织。

## 项目边界

Project 1 是业务语义、SQL、指标和运行结果的唯一事实来源。当前目标是完成整个 Project 1，并获得足以支撑完整简历描述的真实证据；Stage/Step 只控制实施顺序，不缩减最终范围。Project 2 已暂缓，不属于本仓库实现范围。

Project 1 不建设完整库存域、生产级 Hadoop HA，也不引入阿里云专有中间件、Kafka ZooKeeper 模式、Spark/Flink Standalone、Kubernetes、HBase、Redis、Elasticsearch、ClickHouse、Iceberg、Hudi 或 Paimon。

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

DataX 使用 HDFS Writer 将 ORC + Snappy 写入 Hive ODS 发布范围内的批次隔离 staging，不建设独立持久化的中间数据层。事实和事件在抽取结果中按行业务时间携带 `business_date`，维度全量快照使用显式快照日；后续 Spark Validation / Publish 再按 `business_date` 原子发布并注册最终 Hive `dt` 分区。2026-10-18 已完成隔离 Day 60～90 时间推进式 ODS、29/29 Checkpoint、跨日中断恢复与 1,498 项最终 Gate；正式 `ecommerce_oltp` 终态 Snapshot 到正式 `ecommerce_ods` 的 21 表 Bootstrap 也已完成。

### 实时目标链路

```text
MySQL Binlog
  → Flink CDC
  → Kafka Raw CDC Topic
  → Flink 实时清洗与计算
  → Kafka 标准事件 / HDFS-Hive 归档 / Doris 实时服务表
```

实时链路当前状态为 `in progress`，依据是用户确认链路正在建设。R1 初始 Snapshot 只证明冻结范围内的行数与订单对账，不是项目阶段或当前实施进度。正式 Behavior 60/30 本地输入已经冻结，但尚未写入 Kafka；Topic、Partition、Schema、窗口、Watermark、迟到、去重、状态 TTL、实时维度、Checkpoint 和 Doris 实时表模型仍须经过 Milestone 8 契约和 Runtime 验收。

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
| `mock/generator/business_generator/`、`mock/generator/behavior_generator/` | Business CSV 与 Behavior JSONL Generator | Milestone 2 | Business 21 表 1,328,502 行已在目标服务器正式生成并装载；Behavior 3,000,000 事件已在本机正式规模生成。Entity Manifest SHA-256 绑定、全量实体引用、Session 与事件唯一性检查通过 |
| `mysql/` | 正式源库 DDL、装载、Replay 计划、执行和验收入口 | Milestone 2-3 | MySQL 8.0.46 已部署 21 表并通过历史 Shared Source Gate；Seed `20260105` 的 r6 隔离 Source 已完成 Day 60～90、30 条 Ledger、30/30 Acceptance、最终独立 Gate与权限回收 |
| `archive/pilot-v1/` | 旧 Pilot Generator、离线参考资产与实时 R1 工程/验收资产 | Milestone 2-3、8-9 历史 | `PILOT / ACCEPTANCE / HISTORY`；不作为 V2 正式入口，归档移动不提升 Runtime 状态 |
| `tests/` | Generator / DataX / Model / Governance / MySQL Targeted Test 与后续阶段测试入口 | Milestone 2-10 | 2026-10-20 本地 140 个 Unit Tests 通过：Business 6、Behavior 6、DataX/ODS 33、Model 19、Governance 6、Quality 5、Reconciliation 4、Doris 6、Scheduler 18、MySQL 37；Pilot 对账脚本已移入 `archive/pilot-v1/` |
| `datax/config/`、`datax/scripts/`、`datax/templates/`、`datax/jobs/` | MySQL 到 Hive ODS 的 Contract、Job 生成、可审计导出和批次编排入口 | Milestone 3 | 正式 21 表 Snapshot Bootstrap、Day 60～90 隔离增量、跨日恢复及 1,498 项最终 Gate 已验证 |
| `hive/ods/` | ODS 外部表、Pilot History 迁移、分区注册、审计字段和发布规则 | Milestone 3-4 | MySQL/DataX 21 表已验证；独立 Behavior Source 使用第 22 张 `ods_behavior_event`，3,000,000 行、90 个业务日分区与 95/95 项 Gate 已验证 |
| `hive/model/` | DIM/DWD/DWS/ADS 粒度、业务键、历史策略、物理 DDL 与 Gate Contract | Milestone 4-5 | 当前 6 DIM、8 DWD、6 DWS 与 1 ADS 已有正式 Runtime；60/60 Model Gate、41/41 Aggregate Gate 和幂等重跑通过 |
| `hive/dwd/` | 原子事实、去重、状态和字段标准化 | Milestone 4-5 | 6 DIM + 8 DWD 当前 Runtime 有效；申请粒度 `dwd_refund` 已通过 60/60 Model Gate |
| `hive/dws/` | 可复用主题汇总、比率分子和分母 | Milestone 4-5 | 当前已区分退款申请数、成功申请数、成功金额和件数；修正版 Runtime `VERIFIED` |
| `hive/ads/` | V2 正式指标和面向查询的结果表 | Milestone 4-5 | 当前每日概览使用交易/行为日期并集；修正版 Runtime `VERIFIED`，稳定 Metric ID 与首版版本规则已由 M5-01 确认 |
| `spark/sql/`、`spark/scripts/` | ODS Publish、DIM/DWD、DWS、ADS 转换、提交脚本和性能实验入口 | Milestone 3-7 | 当前退款事实与六域 Aggregate SQL 已通过 Targeted Test、真实集群 Build、41/41 Gate 和幂等重跑 |
| `governance/metric_registry/` | 已发布指标、定义哈希、物理输出与验收证据绑定 | Milestone 5 | 36 个 `metric_id@1.0.0` 已发布并通过 Registry Validator；`TF-05`、`TR-13`、`TR-14` 已绑定正式输出 |
| `quality/` | 唯一性、完整性、状态、分区、守恒检查及结果 Contract | Milestone 3-6 | 成功运行保存 40 条 Aggregate 规则且 `FAIL=0`；M6 失败验证另以独立 `run_id` 保存 40 条、`FAIL=1` |
| `reconciliation/` | 跨层及未来离实时对账的通用结果 Contract | Milestone 5、8 | 当前 10 项 × 90 日离线跨层对账共 900 行，`FAIL=0` |
| `doris/ddl/`、`doris/sql/` | 离线服务表与验证 SQL；实时表在 Milestone 8 后确定 | Milestone 6 | 离线 `ads_daily_business_overview` 90 日装载、幂等和逐字段对账均为 `VERIFIED`；实时表仍待 M8 |
| `scheduler/dolphinscheduler/` | T+1 DAG、参数、重试、补数、阻断和对账 | Milestone 6 | `VERIFIED`；成功回补与显式质量失败阻断均已完成 Runtime 验证 |
| `flink/cdc/`、`flink/sql/`、`flink/jobs/`、`flink/scripts/` | CDC、技术验证 SQL、正式 Java 作业和提交/恢复入口 | Milestone 8-9 | 当前正式实现区为 placeholder；现存 Order DWD 工程已归档，R3 最终文件仍缺失。Realtime V2 尚未开始 Formal CDC Contract 或 Domain Job 实现 |
| `scripts/` | 参数化执行、健康检查和阶段验证入口 | 按阶段 | implemented；Hadoop 和 MySQL 仓库脚本已有 Runtime 结果；其他组件的当前运行事实来自用户确认的 Step 2～12 验收记录，不虚构尚未进仓的自动化脚本 |

`placeholder` 表示只存在目录或说明文件；`unconfigured` 表示入口明确返回未配置状态；二者都不代表实现可用。

### 后续模块占位与创建门禁

部分目录已按用户批准建立为占位，但只有在对应阶段通过门禁后才能加入正式实现：

| 计划路径 | 模块职责 | 创建条件 |
| --- | --- | --- |
| `hive/dim/` | Type 1、源有效区间和 `dim_product_zip` SCD2 维度 | 6 张正式 DIM 已构建并通过 Model Gate |
| `reconciliation/` | 跨层及离实时对账任务 | Milestone 5 形成稳定结果结构 |
| `kafka/` | Topic、Schema 和生命周期配置 | 已建立占位；Milestone 8 实时设计通过后实施 |

## 指标范围

V2 指标按六个域组织：交易与资金 `TR-01`～`TR-14`、流量与转化 `TF-01`～`TF-08`、商品 `PR-01`～`PR-05`、用户 `US-01`～`US-06`、退款与售后 `RF-01`～`RF-07`、营销 `MK-01`～`MK-07`。根据 `DR-048`，这些编号直接作为稳定 `metric_id`，首版定义使用 `definition_version=1.0.0`。

完整口径见 [V2 指标体系](docs/business/metrics.md)。复购率、部分退款比例、券核销率、细分漏斗分母和 30 日退款率精确分母截止点等仍为 `待细化`。

## 阶段总览

| Milestone | 名称 | 核心交付 | 当前状态 |
| --- | --- | --- | --- |
| 0 | 项目定义与文档基线 | README、规格、阶段计划、协作边界 | completed |
| 1 | 基础设施与兼容性 | 三节点、版本矩阵、启动和最小连通验证 | in progress |
| 2 | 业务模型与数据生成 | V2 业务基线、21 表 OLTP、行为事件、固定 seed、预期结果 | in progress |
| 3 | DataX 直写 Hive ODS | 全量/增量抽取、ODS ORC 分区、注册与对账 | completed（正式 Snapshot 与隔离 Day 60～90、跨日恢复、1,498 项最终 Gate 已通过） |
| 4 | 离线数仓 MVP | DIM/DWD、DWS、ADS 最小垂直链路 | completed（59/59 Model Gate、18/18 Aggregate Gate 与幂等重跑已通过） |
| 5 | 正式指标与数据质量 | V2 正式指标、质量结果、幂等和回补 | completed（6 DWS + 1 ADS、36 项 Metric Registry、40 条质量规则、10 项跨层对账及 Stage Gate 已通过） |
| 6 | Doris 服务与调度 | 离线服务表、T+1 DAG、失败阻断和对账 | completed（成功回补、Doris Load、调度后对账、自动重试及显式质量失败阻断均已通过） |
| 7 | Spark 性能实验 | 倾斜、Join、分区裁剪实验 | pending |
| 8 | 实时数仓设计评审 | Topic、窗口、状态、维度、Doris 模型 | in progress |
| 9 | 实时链路与可靠性 | CDC、Kafka、Flink、恢复、五项对账 | in progress（Order / OrderItem DWD 已完成限定范围 Initial Load 与正常顺序 Upsert；CDC / Order DWD 指定恢复点已验收，可靠性与完整对账未闭合） |
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
- [架构说明](docs/architecture/README.md)：当前架构边界与技术路线入口。
- [建模说明](docs/business/modeling.md)：业务、逻辑、物理和指标建模文档导航。
- [运维与部署](docs/operations/README.md)：部署拓扑、环境基线、兼容性和排障文档导航。
- [工程架构基线](docs/architecture/baseline.md)：总体技术路线、Flink 正式部署选择与历史技术验收边界。
- [部署拓扑](docs/operations/topology.md)：三节点角色、资源、Java 与安全边界。
- [业务源设计](docs/design/business-source-design.md)：V2 21 表和独立行为源的交付及验收边界。
- [历史初始化与双链路回放设计](docs/design/historical-incremental-replay-design.md)：60 天初始化、30 天离实时回放、重跑时间契约和 SCD2 拉链维度。
- [实时链路规范](docs/design/realtime-pipeline-design.md)：DataStream Application 方案与 Milestone 8 待评审契约。
- [Project 1 完整交付整改方案](docs/design/project1-completion-remediation-plan.md)：跨阶段实施顺序、完整简历证据目标与轻量 Data Governance 边界。
- [Project 1 简历证据当前台账](docs/status/resume-evidence-current.md)：已验证简历数据候选、使用边界和后续缺口。
- [集群事实基线](docs/operations/cluster-baseline.md)：当前 ECS、网络、磁盘、用户、Java 和 Hadoop 的确认事实及验证结论。
- [组件兼容性矩阵](docs/operations/compatibility-matrix.md)：精确版本候选、官方依据、项目状态和验证门禁。
- [安装与排障记录](docs/operations/troubleshooting.md)：目标 ECS 上真实发生的问题、修复、复测和回滚。
- [V2 指标体系](docs/business/metrics.md)：六个指标域的完整口径、依赖、待细化项和最小验收案例。
- [数据规格候选稿（历史）](docs/archive/data-spec-candidate-2026-09-28.md)：2026-09-28 设计输入；整体状态为 `candidate`，不覆盖 `docs/spec.md` 的正式门禁。
- [实施计划候选稿（历史）](docs/archive/implementation-plan-candidate-2026-09-28.md)：2026-09-28 阶段设计输入；未执行内容不得写成当前进度。
- [Benchmark 设计规范](docs/benchmark/spec.md)：数据规模与性能证据设计；所有数值须经真实运行验证。
- [业务基线](docs/business/business-baseline.md)：当前自营商城业务规则和验收不变量。
- [逻辑模型](docs/source/logical-model.md)：当前实体、关系、状态和指标字段覆盖。
- [21 表候选物理设计](docs/source/physical-model.md)：字段级候选方案；不等于现存 MySQL 结构。
- [M2-03 设计快照](docs/source/M2-03-物理设计与静态审查.md)：当时静态检查通过、DDL 未执行；后续隔离验收另按历史事实记录。
- [ENV-05 CDC 验收](docs/acceptance/env-05-cdc-acceptance.md)：单隔离测试表的限定范围 CDC 与故障恢复证据。
- [R1 全量快照验收冻结记录](docs/acceptance/r1_snapshot_acceptance_frozen.md)：指定 21 表隔离库到当前开发 Topic 的初始快照和订单对账证据；不包含增量、全字段或 Exactly-Once 结论。
- [R1 实时链路验收记录](docs/acceptance/r1-realtime-acceptance.md)：R1 首次装载基线、R2 补充说明及安全边界。
- [R1/R2 实时链路验收记录](docs/acceptance/realtime_r1_r2_verified.md)：21 表 Snapshot、Binlog 增量、Checkpoint 恢复、订单正常顺序 Upsert 与未验证边界。
- [`biz_order` ODS 历史切片验收记录](docs/acceptance/biz_order_ods_acceptance.md)：`hist-v1-001` 的 100 单、88 分区、金额基线、发布重建稿、质量入口及未验证边界。
- [Formal ODS Day 60～90 隔离 Stage Gate 验收](docs/acceptance/formal-ods-smoke-acceptance.md)：21 表 Bootstrap、连续增量、两阶段 ORC Publish、跨日恢复、1,498 项独立 Gate 与权限回收。
- [正式 ODS Bootstrap 验收](docs/acceptance/formal-ods-bootstrap-acceptance.md)：正式源 1,328,502 行、21 表 EXTERNAL ODS、1,476 项独立 Gate、Pilot History 与权限回收。
- [Behavior ODS Runtime 验收](docs/acceptance/behavior-ods-acceptance.md)：独立 3,000,000 行 Behavior Source、90 个 Hive 分区与 95/95 项 Gate。
- [M4 DIM/DWD Model Gate 历史验收](docs/acceptance/m4-dim-dwd-model-gate-acceptance.md)：修改前 6 张 DIM、8 张 DWD、精确行数与 59/59 条真实集群断言；当前退款粒度修正版不沿用该结论。
- [M4 DWS/ADS Aggregate Gate 历史验收](docs/acceptance/m4-dws-ads-aggregate-gate-acceptance.md)：修改前 2 张 DWS、1 张 ADS、18/18 条真实集群断言与幂等结果。
- [M5 退款 Contract 迁移验收](docs/acceptance/m5-refund-contract-migration-acceptance.md)：申请粒度退款事实、60/60 Model Gate、18/18 Aggregate Gate、幂等重跑与回滚边界。
- [M5 首批六域 Aggregate 验收](docs/acceptance/m5-six-domain-aggregate-acceptance.md)：5 张 DWS、1 张 ADS、34/34 Gate、16 项幂等摘要与发布边界。
- [M5 持久化质量结果验收](docs/acceptance/m5-quality-result-acceptance.md)：33 条规则、`FAIL=0`、同一 `run_id` 幂等覆盖与阻断边界。
- [M5 六域跨层对账验收](docs/acceptance/m5-cross-layer-reconciliation-acceptance.md)：8 项代表性指标 × 90 日、720 行、零差异和幂等重跑。
- [M5 Stage Gate Assessment](docs/acceptance/m5-stage-gate-assessment.md)：M5 全部 Acceptance → Evidence 映射与通过结论。
- [M5 Cohort P0 指标验收](docs/acceptance/m5-cohort-metrics-acceptance.md)：`TR-13/TR-14`、41/41 Gate、40 条质量规则和 10 项 × 90 日对账。
- [`hist-v1-001` 固定样本摘要](archive/pilot-v1/offline/reference/hist-001.md)：固定生成参数、订单/明细/支付规模、状态和金额期望值。
- [历史 Milestone 2 业务设计](docs/archive/milestone-2-business-design.md)：仅保留旧 19 表设计背景；对应实现文件已删除，不作为当前 V2 实现依据。
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

Milestone 0、1、3、4、5、6 已完成。根据 `DR-049`，DolphinScheduler 3.4.2 使用 MySQL JDBC Registry，并已通过成功/失败任务和受控重启复跑。M6 的 Doris 90 日离线 Serving、Aggregate Backfill Instance `17` 成功终态与调度后双向对账，以及 Instance `18` 的显式质量失败和下游阻断均已通过；验证专用 Workflow 已切换为 `OFFLINE`。Formal CDC Contract/初始化保持为独立工作流，M8、M9 仍未完成。

根据 `DR-029`，正式实时作业选用 Java DataStream Jar + YARN Application Mode；该选型不解除 Milestone 8 设计评审和 Milestone 9 运行验收门禁。BI/Dashboard/Agent 仅为后续数据应用规划，尚未实施；Doris 4.0.8 受控重启恢复已通过，但正式业务服务表仍待对应阶段验收。
