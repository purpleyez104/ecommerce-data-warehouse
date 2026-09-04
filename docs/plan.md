# 电商离实时一体化数据仓库阶段开发计划

版本：`0.3-draft`
状态：Milestone 0 文档修订和静态检查已完成，等待用户评审
更新时间：2026-09-04

## 1. 使用方式

本计划把 [项目规格](spec.md) 拆分为可独立验收的 Milestone。Milestone 编号表示强制顺序，不表示对应组件或目录已经实现。

每个 Milestone 都必须满足：

- 进入条件全部成立后才能开始。
- 只创建本阶段确实需要维护的文件和目录。
- 实现同时提供执行命令、固定输入、预期结果和失败行为。
- 完成后更新 README、规格、计划和相关运行文档。
- 验收证据包含版本、环境、命令、退出状态、关键输出和已知限制。
- 静态检查通过只能标记为 `implemented`，不能直接标记为 `verified`。
- 如果业务语义、版本兼容或资源门禁未通过，停留在当前阶段并记录阻断项。

状态定义：

| 状态 | 含义 |
| --- | --- |
| `pending` | 尚未进入 |
| `in progress` | 当前正在定义或实施 |
| `blocked` | 存在必须由用户或真实环境解决的阻断项 |
| `implemented` | 实现已进入仓库，但运行验收未完成 |
| `verified` | 在记录环境中完成安装、启动、连通、执行和结果核对 |

## 2. 模块与阶段映射

| 模块 | 主要路径 | 负责 Milestone |
| --- | --- | --- |
| 项目规范 | `README.md`、`docs/` | 0-10 |
| 环境与基础设施 | `env/`、计划中的 `infra/`、`scripts/` | 1 |
| 业务源系统 | `mysql/ddl/`、`mysql/seed/`、计划中的 `generator/` | 2 |
| 离线抽取 | `datax/jobs/` | 3 |
| ODS | `hive/ods/`、`spark/sql/` | 3 |
| DIM/DWD | 计划中的 `hive/dim/`、`hive/dwd/`、`spark/sql/` | 4 |
| DWS/ADS | `hive/dws/`、`hive/ads/`、`spark/sql/` | 4-5 |
| 数据质量 | `quality/checks/` | 3-6 |
| 对账 | 计划中的 `reconciliation/` | 5-6、9 |
| Doris 服务层 | `doris/ddl/` | 6、9 |
| 调度 | `scheduler/dolphinscheduler/` | 6 |
| Spark 性能实验 | `spark/sql/`、计划中的 `tests/` 和实验文档 | 7 |
| 实时设计与配置 | 计划中的 `kafka/`、`docs/` | 8 |
| 实时作业 | `flink/jobs/` | 9 |
| Project 2 契约 | `docs/`、质量/对账结果、调度接口 | 10 |

## 3. Milestone 0：项目定义与文档基线

**状态：`in progress`**

### 目标

建立一致的项目范围、架构、模块、阶段、指标数量、状态规则和 Project 2 边界。

### 进入条件

- 仓库路径和项目名称已确认。
- 《数据开发求职项目总规格 V1.4》只作为外部参考，不作为可直接运行的事实来源。

### 涉及模块

```text
README.md
AGENTS.md
CHANGELOG.md
docs/spec.md
docs/plan.md
docs/architecture.md
docs/metrics.md
docs/decision-register.md
.gitattributes
.gitignore
```

### 交付物

- 项目总览、模块边界和当前状态。
- `0.3-draft` 项目规格。
- Milestone 0-10 的阶段开发计划。
- 30 项正式指标、10 项扩展指标和 5 项实时候选的范围。
- Project 2 六个只读交接契约。
- 明确的 `DECISION_REQUIRED` 清单。
- 面向使用者和维护者的可交付变更日志，以及可追溯的正式决策记录。
- Agent 答复后的核心操作、核心决策总结和用户确认后落盘规则。

### 验收

- README、规格和计划对项目名称、离线链路、实时状态、资源和指标数量的描述一致。
- 未把占位目录、静态检查或候选组件写成已实现。
- 实时细节保持 `planned`，没有擅自补全 Topic、窗口、状态或 Doris 模型。
- README、规格、计划和协作规则对 `CHANGELOG.md`、`docs/decision-register.md` 的路径、职责和确认门禁描述一致。
- 文档使用 UTF-8、LF 和末尾换行。
- 用户完成规格和阶段顺序评审。

### 阻断

- 用户尚未确认规格或阶段顺序时，不进入 Milestone 1。

## 4. Milestone 1：基础设施与兼容性

**状态：`pending`**

### 目标

确认阿里云 ECS 三节点环境、磁盘布局、组件依赖、精确版本、端口、目录、启动顺序和最小连通链路。

### 进入条件

- Milestone 0 通过评审。
- 三节点资源和访问方式已确认：
  - `hadoop201`：阿里云 ECS，集群角色 `master`，4 vCPU / 16 GB，系统盘 50 GiB，数据盘 80 GiB。
  - `hadoop202`：阿里云 ECS，集群角色 `worker01`，8 vCPU / 16 GB，系统盘 50 GiB，数据盘 120 GiB。
  - `hadoop203`：阿里云 ECS，集群角色 `worker02`，8 vCPU / 16 GB，系统盘 50 GiB，数据盘 120 GiB。
- 不使用容器作为兼容性兜底。

### 涉及模块

```text
env/
scripts/
infra/                       # 有可维护配置时创建
docs/compatibility-matrix.md # 开始验证时创建
docs/installation-troubleshooting.md
```

### 实施顺序

```text
主机名、磁盘、时区、用户和网络
→ JDK
→ MySQL
→ HDFS
→ YARN
→ Hive Metastore / HiveServer2
→ Kafka KRaft
→ Spark on YARN
→ DataX
→ Doris FE/BE
→ DolphinScheduler
→ Flink / Flink CDC
```

### 交付物

- 主机和组件分布表。
- ECS 系统盘/数据盘检查结果，以及挂载点、文件系统、目录分配和实际可用容量。
- 端口、目录、用户、权限和启动顺序。
- 组件兼容性矩阵及官方来源。
- 不含秘密值的配置示例。
- 安装、启动、健康检查、停止、日志位置和回滚命令。
- 每个组件的最小启动和上下游连通验证。
- 通过验证后形成的 `infra/versions.env`。

### 验收

- 三节点 ECS 实例身份、`master`/`worker01`/`worker02` 角色映射、双向私网通信、主机名解析和时间一致性通过。
- 三块系统盘和三块数据盘的设备、挂载点、文件系统、容量和读写权限已实测记录。
- HDFS 写入/读取、YARN 最小任务、Hive 连接、Kafka 生产消费和 Spark on YARN 最小 SQL 通过。
- DataX、Doris、DolphinScheduler、Flink 只在前置依赖通过后验证。
- YARN ResourceManager 与 Doris FE 的 `8030` 端口冲突已解决。
- 所有精确版本都能追溯到官方来源和真实测试。
- 重启后关键配置仍有效。

### 阻断

- 任何组件无法启动、版本不兼容、端口未解决或资源不足时，停止后续组件接入。
- hadoop201 是否扩容只能依据磁盘空间不足、OOM、持续 Swap、频繁 Full GC、进程被杀或关键服务无法共存等实测证据。

## 5. Milestone 2：业务模型与数据生成

**状态：`pending`**

### 目标

建立用户、流量、商品、交易和营销五个主题的源系统模型，以及可复现的验收数据。

### 进入条件

- MySQL 已通过 Milestone 1 的启动和连接验证。
- 用户确认 OLTP 表、字段、主外键、状态机和硬删除策略。
- 30 项正式指标所需业务过程已识别，但指标公式可以继续保持 draft。

### 涉及模块

```text
mysql/ddl/
mysql/seed/
mock/
generator/ # 业务模型确认后创建
docs/
tests/     # 首个可执行测试出现时创建
```

### 交付物

- 业务过程矩阵和源表关系。
- OLTP DDL、索引、约束和状态枚举。
- 用户、访客、会话、商品、加购、订单、支付、取消、退单/退款和优惠券数据。
- 固定 seed 验收数据生成入口。
- 可调规模的基准数据生成入口。
- 固定输入、预期源表结果和异常数据说明。

### 必测场景

- 正常注册、访问、加购、下单和支付。
- 取消、退单或退款。
- 重复业务请求和重复数据。
- 跨日订单、支付和退款。
- 非法状态迁移、主外键缺失、空值和金额边界。
- 用户属性变化和维度关联。

### 验收

- 相同 seed 生成相同数据。
- 主外键、金额和状态逻辑符合已确认规则。
- `update_time` 在需要增量抽取的变化上正确更新。
- 硬删除策略有明确设计和测试。
- 固定验收集能够人工核对，基准集规模可参数化。

### 阻断

- 不知道事实粒度、状态机、退单/退款关系或用户/访客标识时，不生成正式 DDL。

## 6. Milestone 3：DataX 直写 Hive ODS

**状态：`pending`**

### 目标

打通 MySQL 经 DataX 直接写入 Hive ODS 对应 HDFS ORC 分区的可重跑链路，不建设独立持久化的中间数据层。

### 进入条件

- Milestone 1 的 HDFS、Hive、DataX 组合通过验证。
- Milestone 2 的 OLTP DDL 和固定数据已确认。
- 全量、增量和硬删除处理方式已确定。

### 涉及模块

```text
datax/jobs/
hive/ods/
spark/sql/
quality/checks/
scripts/
tests/
```

### 交付物

- MySQL 到 Hive ODS 对应 HDFS 分区的全量抽取任务。
- 基于 `update_time` 时间区间的增量抽取任务。
- Hive ODS ORC + Snappy 业务日期分区写入和显式分区注册。
- `business_date`、`extract_time`、`batch_id`、`source_table` 审计字段，以及批次发布和失败隔离规则。
- 源表与 ODS 的行数、主键和分区到达检查。

### 验收

- 固定源数据能够真实写入 Hive ODS 对应的 HDFS ORC + Snappy 业务日期分区。
- DataX 失败返回非零退出状态。
- Hive 能注册并读取 ODS 分区，源字段语义、审计字段和批次标识符合已确认设计。
- 首次运行、同日重跑和连续日期回补结果可解释且无不可控重复。
- DataX 不直接负责正式金额和状态类型建模。
- 异常批次不会覆盖已验证分区。

### 阻断

- DataX HDFS Writer 的 ORC/Snappy、依赖、Hive 分区可见性、审计字段、幂等发布或失败隔离未验证时，不得把直写 ODS 链路标记为 `verified`。
- 硬删除无法被当前增量方案识别时，不宣称增量链路完整。

## 7. Milestone 4：离线数仓 MVP

**状态：`pending`**

### 目标

建立一个从 ODS 到 DIM/DWD、DWS 和 ADS 的最小垂直闭环。

### 进入条件

- Milestone 3 的固定业务日期 ODS 分区通过验收。
- 首批业务过程、事实粒度、业务键、时间语义和金额精度已确认。
- 需要的维度及历史策略已确认。

### 涉及模块

```text
hive/dim/ # 维度设计确认后创建
hive/dwd/
hive/dws/
hive/ads/
spark/sql/
quality/checks/
tests/
docs/
```

### 交付物

- 一致维度及必要的历史变化处理。
- 交易、流量、用户和营销原子事实。
- 可复用 DWS 主题汇总。
- 最小 ADS 结果表。
- ODS → DIM/DWD → DWS → ADS 血缘。
- 每层固定输入和预期输出。

### 验收

- Spark on YARN 能读取 Hive、执行转换并写回 ORC 分区。
- 每张事实表明确“一行代表什么”。
- 业务主键、事件时间、处理时间、金额精度和状态枚举可追溯。
- 各层主键、行数和金额/数量守恒检查通过。
- 首次运行、同日重跑、连续回补和失败退出通过。

### 阻断

- 事实粒度、维度历史策略或关键业务口径不明确时，只保留草案，不生成正式模型。

## 8. Milestone 5：正式指标与数据质量

**状态：`pending`**

### 目标

完成 `P1_METRIC_001` 至 `P1_METRIC_030` 的离线口径、血缘、实现、固定样例和质量检查。

### 进入条件

- Milestone 4 的最小离线闭环通过。
- 30 项指标的统计粒度、公式、时间归属、过滤、去重、精度、舍入和零分母规则已确认。

### 涉及模块

```text
hive/dws/
hive/ads/
spark/sql/
quality/checks/
reconciliation/ # 结果结构稳定后创建
tests/
docs/metrics.md
```

### 交付物

- 30 项正式指标字典和稳定编号。
- 指标到 DWS、DWD/DIM、ODS 和源字段的血缘。
- 比率和平均值对应的分子、分母及加权方式。
- `data_quality_result` 结果结构。
- 跨层行数、业务键、金额和数量对账。
- 每项指标的固定输入、预期结果和边界样例。

### 验收

- 30 项指标均能追溯到源字段。
- 每项指标在固定样例中得到预期结果。
- 唯一性、完整性、状态、范围、分区到达和守恒检查通过。
- 质量规则失败能够返回失败状态。
- 质量结果可重复执行，重复执行行为明确。
- `P1_METRIC_031` 至 `040` 保持扩展候选，不提前实施。

### 阻断

- 指标公式或粒度存在冲突时保持 draft，不生成正式指标 SQL。
- 原材料序号 32 的指标不改名、不采用。

## 9. Milestone 6：Doris 离线服务与 DolphinScheduler

**状态：`pending`**

### 目标

把 Hive ADS 发布为 Doris 离线服务表，并形成可补数、可阻断的 T+1 工作流。

### 进入条件

- Milestone 5 的离线指标和质量检查通过。
- Spark Doris Connector 的版本和类型映射通过验证。
- DolphinScheduler 已完成启动、Worker、日志和任务失败验证。

### 涉及模块

```text
doris/ddl/
scheduler/dolphinscheduler/
quality/checks/
reconciliation/
scripts/
tests/
docs/
```

### 目标 DAG

```text
DataX ODS Load
→ ODS Ready Check
→ DIM/DWD
→ DWS
→ ADS
→ Quality Check
→ Doris Load
→ Reconciliation
```

### 交付物

- Doris 离线服务表 DDL 和装载任务。
- 业务日期参数化的 DolphinScheduler DAG。
- 失败重试、依赖、补数、日志查看和质量阻断。
- Hive ADS 与 Doris 结果对账。
- Project 2 可读取的任务状态和失败信息边界。

### 验收

- Doris FE/BE、表创建、写入、查询和重启验证通过。
- Spark Doris Connector 能写入固定 ADS 结果。
- Doris 与 Hive ADS 的行数、业务键和指标值一致。
- T+1 首次运行、同日重跑、连续回补、任务失败和重试通过。
- 质量失败不会被工作流误标为成功。

### 阻断

- Doris 表模型、Connector 类型映射或 `8030` 端口冲突未解决时，不接入正式 DAG。

## 10. Milestone 7：Spark 性能实验

**状态：`pending`**

### 目标

用可复现的真实实验展示 Spark 性能诊断和优化能力。

### 进入条件

- Milestone 4-6 的 Spark 任务和固定数据链路稳定。
- 基准数据规模通过资源评估，不使用虚构规模。

### 涉及模块

```text
spark/sql/
tests/
docs/benchmark/
```

### 实验

1. 数据倾斜：普通聚合与两阶段聚合。
2. Join：Sort Merge Join 与 Broadcast Hash Join。
3. 分区裁剪：无效过滤与正确分区过滤。

### 交付物

- 固定版本、配置、输入和重复执行命令。
- 优化前后的执行计划和 Spark UI 指标。
- Input Size、扫描量、Shuffle、Stage 和 Job 耗时。
- 实验限制、失败场景和回滚方法。

### 验收

- 相同输入可以重复实验。
- 原始日志或截图能够支持结论。
- 只描述真实测得的差异，不把建议写成已成功优化。

## 11. Milestone 8：实时数仓设计评审

**状态：`pending`**

### 目标

在不编写正式实时业务作业前，完成实时语义、存储、接口和验收设计。

### 进入条件

- 离线主线至少完成 Milestone 6。
- 五项实时候选的离线口径稳定：
  - `P1_METRIC_014` 加购人数。
  - `P1_METRIC_015` 下单人数。
  - `P1_METRIC_016` 支付成功人数。
  - `P1_METRIC_025` 订单总额。
  - `P1_METRIC_026` 订单数。

### 涉及模块

```text
docs/
kafka/     # 评审通过后创建
flink/jobs/
doris/ddl/
reconciliation/
tests/
```

### 必须决策

- Topic 按表、按业务域还是统一设计。
- Partition、副本、保留期、压缩和 Schema。
- CDC、清洗和聚合的作业拆分。
- 事件时间、Watermark、窗口和允许迟到。
- 去重键、状态 TTL、撤回和补偿语义。
- 实时维度使用当前快照还是历史版本。
- Checkpoint、Savepoint、重启和一致性目标。
- Doris Key 模型、分区、分桶和更新语义。
- 实时明细归档和离实时对账阈值。

### 交付物

- 实时分层和物理存储设计。
- Topic 与 Schema 契约。
- 五项指标的离实时统一口径。
- 故障恢复和对账测试方案。
- 资源预算和退出/回滚方案。

### 验收

- 所有 `DECISION_REQUIRED` 项有明确结论或被标记为阻断。
- 版本、连接器、状态、存储和验收方案一致。
- 不使用 Kafka Topic 冒充长期数仓存储。

### 阻断

- 上述设计未通过时，不进入 Milestone 9，不生成正式 Flink 业务作业。

## 12. Milestone 9：实时链路与可靠性

**状态：`pending`**

### 目标

实现 MySQL Binlog → Flink CDC → Kafka → Flink → Doris，并完成恢复和五项离实时对账。

### 进入条件

- Milestone 8 通过评审。
- Flink、Flink CDC、Kafka Connector 和 Doris Connector 完成精确版本验证。

### 涉及模块

```text
kafka/
flink/jobs/
doris/ddl/
reconciliation/
quality/checks/
tests/
docs/
```

### 交付物

- MySQL Snapshot 与 Binlog 采集。
- Kafka Raw 和标准事件 Topic。
- Flink 清洗、去重、维度关联和五项指标计算。
- HDFS/Hive 归档和 Doris 实时服务表。
- Checkpoint、Savepoint、重启和故障恢复配置。
- 五项指标的 `reconciliation_result`。
- 实时延迟、积压、重复、丢失和写入失败检查。

### 验收

- INSERT、UPDATE、DELETE 均被正确捕获和解释。
- Kafka 能生产、消费、重放并验证副本恢复。
- Flink 中断期间源端继续产生数据，恢复后结果符合确认的一致性目标。
- Doris 重复写入和更新行为符合表模型。
- 五项实时结果与 T+1 离线结果完成可解释对账。
- 理论语义和实测结果分别记录。

### 阻断

- 不能仅凭配置 Checkpoint 宣称端到端 Exactly-Once。
- 无法解释重复、丢失、迟到或对账差异时，不得标记 verified。

## 13. Milestone 10：Project 1 面试发布与 Project 2 交接

**状态：`pending`**

### 目标

形成他人可复现、本人可解释且证据完整的 Project 1 发布版本。

### 进入条件

- Milestone 0-7 全部 verified。
- 如果简历包含实时能力，Milestone 8-9 也必须 verified；否则实时内容只能描述为规划，不进入成果数字。

### 涉及模块

```text
README.md
docs/
scripts/
tests/
quality/
reconciliation/
scheduler/
```

### 交付物

- 完整 README、架构图、数据流图和分层说明。
- 安装、运行、重跑、补数、停止和故障恢复说明。
- 指标字典、血缘、质量、对账和性能实验结果。
- 去敏后的日志摘要、截图和已知限制。
- 六个 Project 2 只读契约：
  - `P1-METADATA-01`
  - `P1-LINEAGE-01`
  - `P1-METRIC-01`
  - `P1-QUALITY-01`
  - `P1-RECONCILIATION-01`
  - `P1-TASK-01`
- Project 1 面试版本标签候选 `v1.0-interview`。

### 验收

- 新环境可以按文档完成部署和最小链路运行。
- 所有简历数字都有代码、命令、日志或截图支持。
- 六个契约只暴露真实、稳定、只读的 Project 1 数据。
- Project 2 不重新定义指标、不伪造血缘、不重复实现质量引擎。

## 14. 全阶段通用回归场景

从首个可执行链路开始，每次变更至少评估：

- 首次运行。
- 同日重跑。
- 连续业务日期回补。
- 上游重复输入。
- 空分区和上游迟到。
- 非法状态、空值和主外键缺失。
- 金额、数量、分子和分母守恒。
- 任务失败退出码和下游阻断。
- 配置缺失和依赖不可用。
- 版本升级或回滚后的兼容性。

## 15. 当前下一步

当前只推进 Milestone 0：

1. 完成 `README.md`、`docs/spec.md` 和 `docs/plan.md` 的离线链路修订与静态一致性检查。
2. 用户评审修订结果，并确认 Milestone 0 的范围和阶段顺序。
3. 保留业务口径、版本和实时细节为待决策项。
4. 用户确认后，将 Milestone 0 标记为 `completed`，Milestone 1 保持 `pending` 但解除进入门禁。

在 Milestone 0 完成前，不安装软件、不锁定精确版本、不创建业务表，也不生成离线或实时业务代码。
