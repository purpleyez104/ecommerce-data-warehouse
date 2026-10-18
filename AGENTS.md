# Repository Guidelines

## 开工顺序与事实来源

首次接入、跨 Milestone、公共 Contract 变化或状态混乱时，完整核对 `README.md`、`docs/spec.md` 和 `docs/plan.md`。同一目标的连续开发只读取相关章节、代码、配置、测试与当前 Diff。三份文档的职责如下：

- `README.md`：项目总览、当前状态和文档入口。
- `docs/spec.md`：项目范围、业务与技术约束、指标、状态定义和验收标准。
- `docs/plan.md`：Milestone 强制顺序、各阶段进入条件、交付物和阻断规则。

Spec 管 Scope、Contract 与 Acceptance；Plan 管 Stage 路线；Status/Handoff 管进度摘要；当前代码、配置和实际测试管实现与运行事实。进度描述滞后时应提出同步文档，不得为适配旧计划倒推代码。只有影响整体方向或造成高返工成本的冲突才标记 `DECISION_REQUIRED` 并暂停；旧仓库、参考规格、学习笔记和候选实现都不是运行事实来源。

## 当前状态与门禁路由

`AGENTS.md` 只保留稳定规则，不复制容易变化的 Milestone、行数、日期、Runtime 或下一步状态：

- 当前 Milestone、依赖顺序、进入/退出条件：`docs/plan.md`。
- 离线与 Replay 当前事实：`docs/status/offline-current.md`。
- 实时当前事实：`docs/status/realtime-current.md`。
- 文件与外部 Runtime 资产边界：`docs/status/file-baseline.md`。
- 已执行验收及证据边界：`docs/acceptance/`。
- 项目入口与最新能力摘要：`README.md`。

推进任务前只读取与当前 Change 相关的状态章节和 Gate。不得把旧 Pilot、候选设计、文件存在或历史验收外推为当前正式链路事实。禁止格式化已存在的 NameNode；验证脚本只能删除自己创建且经过前缀和运行编号约束的临时对象。

## 项目范围与实施顺序

这是从零搭建的 Project 1 最终仓库，目标是形成真实运行、可验证、可复现、可解释的电商离实时一体化数据仓库。Project 1 是业务语义、SQL、指标和运行结果的唯一事实来源。

完整 Milestone 的依赖顺序保持为：文档基线 → 基础设施与兼容性 → OLTP 模型与固定数据 → DataX 直写 Hive ODS → 离线数仓 MVP → V2 正式指标与质量 → Doris 离线服务与 DolphinScheduler → Spark 性能实验 → 实时设计评审 → 实时链路 → Project 1 发布。Stage/Step 只用于控制依赖、风险和返工，不代表缩减最终交付范围；交易域可以作为实施入口，但不是项目交付终点。完整整改顺序见 `docs/design/project1-completion-remediation-plan.md`。

Project 1 的最终目标是完成离线、实时、调度、性能、治理和可复现交付，并获得足以支撑完整简历描述的真实证据。正式 Flink 业务作业已选定 Java DataStream Jar + YARN Application Mode，但未经 Milestone 8 契约评审不得扩大 Topic、Partition、Schema、窗口、Watermark、迟到、去重、状态 TTL、实时维度、Checkpoint 或 Doris 实时表模型；已有 candidate 不得提升为 `verified`。BI、Dashboard、SQL Assistant、LLM、Agent 和 Project 2 实现不属于当前 M0～M10 交付范围。

Project 1 内部建设轻量 Data Governance：真实 Metadata Snapshot、基于真实 SQL/配置的 Table-level Lineage 和 Project 1-owned Metric Registry；不建设独立平台或 Column-level Lineage。`P1-METADATA-01`、`P1-LINEAGE-01`、`P1-METRIC-01`、`P1-QUALITY-01`、`P1-RECONCILIATION-01` 和 `P1-TASK-01` 首先服务于 Project 1 自身治理、验收和证据组织，同时保留未来只读消费能力。Project 2 暂缓且不属于本仓库实现范围。

## 旧内容迁入与非目标

旧仓库只允许作为外部参考，禁止批量复制或直接依赖旧实现。每次迁入必须记录：

1. 来源及对应版本或路径。
2. 采用理由和不采用的替代内容。
3. 为适配当前规格所做的改造。
4. 可执行验证方法、固定输入和预期结果。
5. 失败时的回滚方式。

第一期不建设完整库存域或库存流水，也不建设生产级 Hadoop HA、Project 2 应用、DataOps、AI 服务或前端；不引入阿里云专有中间件、Kafka ZooKeeper 模式、Spark/Flink Standalone、Kubernetes、HBase、Redis、Elasticsearch、ClickHouse、Iceberg、Hudi 或 Paimon。不得预设或虚构数据规模、QPS、延迟、Exactly-Once 或性能提升数字。

## 数据链路与模块责任

离线主线固定为：

```text
MySQL ecommerce_oltp
  → DataX
  → Hive ODS（ORC + Snappy）
  → Spark SQL：DIM/DWD → DWS → ADS
  → 数据质量与逐层对账
  → Spark Doris Connector
  → Doris 离线服务表
```

DataX 使用 HDFS Writer 将 ORC + Snappy 写入 Hive ODS 发布范围内的批次隔离 staging；Spark Validation / Publish 根据每行 `business_date` 或显式快照日原子发布并注册最终 Hive `dt` 分区，不建设独立持久化的中间数据层。DataX 多表配置的字段顺序统一引用 Business Generator 的 `TABLE_COLUMNS`，字段类型以正式 MySQL DDL 为准，不重复维护第二套逐表 columns 清单。ODS 装载负责分区注册、审计字段、幂等发布和失败隔离；DataX 不负责决定正式金额精度、状态枚举和最终字段类型。ODS 保留源语义，DWD 保存原子事实，DIM 保存一致维度，DWS 保存可复用度量以及比率的分子和分母，ADS 负责最终指标表达。DolphinScheduler 只能在任务独立运行通过后接入，负责参数、依赖、重试、回补、质量阻断、装载和对账，不承载业务计算逻辑。

仓库中的 `mysql/`、`datax/`、`hive/`、`spark/`、`flink/`、`doris/`、`scheduler/`、`quality/`、`env/`、`mock/` 和 `scripts/` 按阶段承担模块责任。`infra/` 已在 Milestone 1 开始后建立，只允许保存去敏的主机、端口、配置和兼容性内容；`infra/versions.env` 必须等待全部 M1 版本通过真实验证后再创建。旧 19 表的 Seed、Generator、脚本和测试位于 `archive/legacy-m2-19-table/`；旧 21 表 Pilot Generator 位于 `archive/pilot-v1/ecommerce_generator_v1/`，均不得作为当前正式入口。`mock/generator/business_generator/` 已完成正式规模生成、目标 MySQL 装载与 Source Gate；`mock/generator/behavior_generator/` 已完成本地正式规模与 Entity Manifest 绑定。两者的证据边界不得外推为正式 ODS、Kafka 或 CDC 已完成。`hive/dim/`、`kafka/` 和部分 Flink/DataX/Spark/Doris 子目录已按用户批准建立为 `placeholder`，但可执行内容仍须满足 `README.md` 与 `docs/plan.md` 的对应 Milestone 门禁；`reconciliation/` 仍在结果结构稳定后创建，`tests/` 仅按已进入阶段的验证范围扩展。

## 业务语义与待决策项

先确认业务过程、事实粒度、业务键、时间语义、状态机和指标口径，再设计物理表、任务和 SQL。以下事项不得使用经验默认值补全：

- OLTP 表、字段、主外键、状态机和硬删除策略。
- 用户、访客、会话、回流和活跃定义。
- 订单、支付、取消、退款申请与资金退款的关系和去重对象。
- 指标公式、粒度、时间归属、过滤、精度、舍入和零分母规则。
- 维度历史策略、数据规模、保留周期、实时语义和精确组件版本。

发现缺失或冲突时，先在相关规格中记录 `DECISION_REQUIRED`、影响范围和阻断阶段；未经用户确认，不得生成正式实现。

## 状态与证据边界

统一使用以下状态，不得提高证据等级：

| 状态 | 使用条件 |
| --- | --- |
| `draft` | 规格、设计或口径仍待评审 |
| `candidate` | 已选为候选，但版本或实现尚未完成真实验证 |
| `planned` | 只有目标和进入条件，尚未完成详细设计 |
| `implemented` | 实现已进入仓库，但运行验收尚未完成 |
| `verified` | 已在记录的环境和版本中完成安装、启动、连通、执行和结果核对 |

文件存在、格式检查、语法检查、静态契约检查或官方文档中的能力说明，最多证明相应静态范围，不等于组件兼容、任务成功或链路通过。没有真实证据时必须明确写出“未验证”。开发环境不能描述为生产级高可用环境；配置 Checkpoint 或连接器声明支持 Exactly-Once，也不能替代端到端故障恢复和一致性验证。

## 实现、测试与验收

新增实现必须同时提供：可执行命令、固定输入、预期结果、预期退出状态、日志或结果位置、已知限制和回滚方式。所有批任务必须显式接收业务日期或起止时间，不得使用执行机器当前日期推断数据范围；业务日期格式统一为 `yyyy-MM-dd`。

以下内容是相关 Stage 或完整功能链的 Acceptance Matrix，不要求每个普通 Task / Step 全量重复。Step 只执行当前风险所需的局部验证；Stage Gate 选择能够证明当前 Acceptance 的最小充分集合，关键数据正确性、完整性和失败阻断仍不得跳过：

- 首次运行、同日重跑、连续业务日期回补和上游重复输入。
- 空分区、迟到输入、非法状态、空值和主外键缺失。
- 业务键唯一性、引用完整性、状态合法性和分区按期到达。
- 源表、ODS 及后续各层行数可解释。
- 订单、明细、支付、退款之间的金额或数量守恒。
- 比率指标的分子、分母、精度、舍入和零分母边界。
- 配置缺失、依赖不可用和任务失败时返回非零状态，并阻断下游。

版本、配置和性能结论必须绑定真实环境与固定输入。性能优化只有保存执行计划、扫描量、Shuffle、Stage 和作业耗时等实测证据后才能描述为有效。

验证满足当前 Acceptance 后停止，不因非阻塞建议或可选优化自动开启新一轮 Review / Fix / Test。同一问题连续两轮修复仍未解决时重新分析根因、假设、测试边界和方案；没有新证据或新假设时不得重复相同失败路径。隔离测试只在能够缩小根因范围时按需使用，不作为普通功能开发的无限循环阶段。

## 文档与变更同步

正式文档只记录已采用设计、最终配置、可复现命令、验证结果、已知限制和排障结论。学习笔记、临时实验、个人决策过程、未采用方案和安装草稿放入不提交 Git 的 `.local-notes/`；项目运行不得依赖该目录。

每次变更应小而聚焦，只完成用户指定且属于当前阶段的内容。Agent 自行判断文档是否具有后续参考价值；用户已对 Feature、Stage 或明确任务范围授权文档同步时，可直接更新相关正式文档且不逐文件重复确认。没有该授权时，先提出“文件、内容、理由、影响”，确认后修改。Scope、Contract、Architecture、Schema、Acceptance、Migration、安全与正式决策应即时提出；普通进度和验证结果在 Step / Stage Gate 集中处理。不得一次性生成整个项目或擅自引入新框架。

`CHANGELOG.md` 记录面向使用者和维护者的可交付变更，包括新增、变更、修复和移除；不得把仅讨论、未采纳方案或未完成的运行验证写成已交付事实。`docs/decision-register.md` 记录已经提出或确认、且会影响项目范围、业务口径、架构、组件版本、数据模型、接口、安全约束或验收方式的正式决策；不得用它代替一般变更日志。

## 答复收尾与记录确认

完成工程任务后使用 `Changed / Verified / Notes` 简短汇报。只有形成可交付变更或正式决策且值得长期保留时，才提出对应的 `CHANGELOG.md` 或 `docs/decision-register.md` 更新；没有记录价值时直接说明“不需要记录”，不得例行询问两份文件。

## 编码、命名与配置

- 文本文件使用 UTF-8、LF 和末尾换行。
- Python 使用 4 空格；SQL、YAML 和 Shell 使用 2 空格。
- 文件、变量和表名使用 `snake_case`。
- 数仓表使用清晰的层级前缀，例如 `ods_`、`dim_`、`dwd_`、`dws_`、`ads_`。
- Spark SQL 负责主要离线转换；只有 SQL 不适合表达时才使用 PySpark。
- 正式 Flink 业务作业使用 Java DataStream Jar + YARN Application Mode；Flink SQL Client + YARN Session 仅用于限定范围的技术验证，不作为正式业务部署方式。
- 不得使用多种语言重复实现同一生产任务。
- 未锁定依赖不得使用 `latest`、浮动版本或动态下载地址。

## 提交、安全与评审

使用 Conventional Commits，例如 `docs: define initial project scope`、`feat(ods): add order ingestion`。提交和合并请求应说明目标、影响范围、验证命令及结果、未决事项、已知限制和回滚方式。

禁止提交密码、密钥、Token、`.env`、真实生产地址、个人数据或原始运行日志。仓库只保留环境变量名、去敏示例和安全默认值，不硬编码密码、IP 或 Token。组件端口默认只允许 VPC 私网访问；公网暴露必须单独评审。MySQL CDC、Doris、Hive、调度器和 Project 2 使用各自的最小权限身份，其中 Project 2 必须只读。


## Project State、Stage 与 Handoff

详细流程见 `docs/workflow/README.md`。当前状态维护于：

```text
docs/status/
├── offline-current.md
├── realtime-current.md
└── file-baseline.md
```

### Source of Truth

实现事实以当前代码、配置、Git Diff 和实际执行/验收结果为准；Confirmed Spec 与业务 Contract 管范围和语义；`docs/status/` 管当前进度；`docs/plan.md` 管阶段路线；Architecture / Decision Register 管长期约束；Handoff 只传递这些事实，不覆盖它们。后续 VERIFIED 事实可以纠正旧进度描述，但不得未经确认改变已冻结的 Scope 或 Contract。

### Status

统一使用：

- `VERIFIED`：真实执行并验收成功
- `DOING`：正在推进
- `DESIGNED`：已确认但未验证
- `HISTORY`：已被替代
- `UNKNOWN`：证据不足

必须遵守：

`FILE EXISTS ≠ VERIFIED`

聊天中出现的代码、文件名或建议路径，也不代表文件真实存在或已执行。

### Stage-Step Workflow

项目开发使用滚动设计：Stage 开始时确认 Goal、Scope、Contract、Acceptance、风险和粗粒度 Step Map，只详细设计当前 Step。在已批准范围内连续完成 Step 中的内部 Task，不因普通步骤完成暂停等待授权。Step Gate 只做局部判断：局部问题直接修复；只影响后续实现时调整剩余 Step；改变 Scope、核心 Contract、Schema 或 Architecture 时执行 Correct Course 并等待确认。普通 Step 不自动启动 Reviewer、Tester、Handoff、Commit 或完整验收。

对于多表、多分区或连续业务日期的批量链路，默认采用“批量推进 + 分层验证”，避免把每一天、每张表变成人工 Gate：

1. 运行前一次性完成相关 Code Review、配置检查和完整范围 Preflight。
2. 先用最小代表性输入执行 Smoke Test；只有真实边界风险需要时才增加隔离 Integration Test。
3. 预检与代表性验证通过后，一次运行已批准的完整表/日期范围；每个表或业务日只作为自动 Checkpoint 和失败定位点，不要求用户逐项验收。
4. 批处理必须记录可恢复状态，支持基于已提交 Ledger/Checkpoint 的幂等重跑或断点恢复；恢复前先核对运行证据与目标状态，不得从固定首日盲目重放。
5. 只在批次失败、证据冲突、Contract 变化或需要新授权时中断；批次完成后统一执行 Stage Gate、对账和验收。

该机制是工作方式，不代表跨阶段复用同一实现。MySQL Replay、DataX/ODS、Spark 分层和实时链路分别使用自己的 Ledger/Checkpoint、质量规则与验收证据。

Stage 结束时根据 Stage Acceptance 执行最小充分验证；只有公共 Contract、关键数据、安全、重大重构或交付风险需要时才增加独立 Review、Integration 或 Full Validation。文档按已授权范围同步，其他更新集中提议；最后单独申请一次 Git Commit。显式 BMad 调用也不自动授予 Commit 权限。

### Handoff

Handoff 只用于换 Chat、换 Agent/执行环境、跨 Worktree、阶段成果交给另一执行者，或用户明确要求。同一 Chat 直接操作本 Repository 时不生成内部 Handoff。生成时只传递当前目标、状态、Diff 边界、实际验证、风险和下一入口；接收时必须用 Repository 证据复核。

### Conflict Handling

如果 Handoff、Status、仓库文件或历史文档之间存在冲突：

- 不得猜测
- 标记为 `CONFLICT`
- 无法确认的内容保持 `UNKNOWN`

### Repository Stability

除非当前任务或用户明确要求，不得：

- 大规模重构目录
- 删除历史文件
- 批量重命名
- 顺手修改无关阶段

项目当前优先级是：

**保证工程事实可信，并持续推进开发。**
