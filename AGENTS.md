# Repository Guidelines

## 开工顺序与事实来源

每次修改仓库前，必须依次完整阅读 `README.md`、`docs/spec.md` 和 `docs/plan.md`，确认当前 Milestone、进入条件、交付物、验收标准和阻断项。三份文档的职责如下：

- `README.md`：项目总览、当前状态和文档入口。
- `docs/spec.md`：项目范围、业务与技术约束、指标、状态定义和验收标准。
- `docs/plan.md`：Milestone 强制顺序、各阶段进入条件、交付物和阻断规则。

发生冲突时不得自行选择或静默修正。应指出冲突位置及影响，将需要用户确认的内容记录为 `DECISION_REQUIRED`，并停留在当前阶段。旧仓库、参考规格、学习笔记和候选实现都不是本仓库的运行事实来源。

## 当前阶段门禁

Milestone 0“项目定义与文档基线”已于 2026-09-04 通过用户评审，状态为 `completed`。Milestone 1“基础设施与兼容性”和 Milestone 2“业务模型与数据生成”状态均为 `in progress`。当前 ECS 集群记录中的 `CONFIRMED` 已由用户确认为本项目事实；Ubuntu、网络、磁盘、`yee` 用户和 Hadoop 3.4.1 运行拓扑不重新初始化。根据 `DR-026`，M1 Step 2～12 已完成 Runtime 验收，Milestone 1 当前唯一剩余门禁为 DolphinScheduler 3.4.2。推进 Milestone 1 时：

- 严格按 `docs/plan.md` 的主机、网络、JDK 和组件前置顺序实施，不跳过兼容性与资源门禁。
- 不得以 Milestone 1 的名义创建业务表、数据模型、指标 SQL、离线任务或实时作业；Milestone 2 的本地产物只按 `DR-008` 和 M2 小计划门禁创建。
- 不把预留目录、占位文件、候选组件或静态检查描述为已经实现或运行通过。
- Milestone 1 的变更只创建其确实需要维护的环境、基础设施、兼容性、安装排障和验证内容，不夹带 M2 实现。
- 禁止格式化已存在的 NameNode；验证脚本只能删除自己创建且经过前缀和运行编号约束的临时对象。

`DR-008` 允许 Milestone 1 与 Milestone 2 分轨推进。当前 M2 以 `docs/business/business-baseline-v2.md`、`docs/metrics.md`、`docs/source/logical-model-v2.md` 和 `docs/source/physical-model-v1.md` 为设计输入。21 表候选 DDL 的 `M2-03` 静态快照属于部署前事实；用户提供的 2026-09-19～20 摘要记录了后来隔离验收库的有限 21 表 CDC 和 10/100 单结果，不证明当前在线状态或正式库结构。新 Generator 文件已入库，但固定 Seed、显式日期/重跑契约、精确依赖版本、90 天数据和离线接续未完成；M2 仍为 `in progress`，M3 仍阻断。`docs/acceptance/env-05-cdc-acceptance.md` 只证明单个隔离测试表和指定故障场景，不得单独外推到正式 21 表。

旧方案完整保留在 `docs/archive/milestone-2-business-design.md`，仅作为历史证据，不与当前 M2 状态混用。M1 与 M2 的并行不解除直接运行依赖；当前 Milestone 3 的 M2 交付门禁未满足。

`completed` 只表示对应 Milestone 的进入条件、交付物和验收项已满足，不替代 `draft`、`candidate`、`planned`、`implemented`、`verified` 等内容证据状态。M0 完成不证明任何组件已经安装或数据链路已经运行。

除 `DR-008` 明确允许的 M1/M2 并行方式外，所有后续 Milestone 必须满足 `docs/plan.md` 的进入条件后才能开始。上一阶段存在未解决阻断项时，不得提前开发下一阶段内容。

## 项目范围与实施顺序

这是从零搭建的 Project 1 最终仓库，目标是形成真实运行、可验证、可复现、可解释的电商离实时一体化数据仓库。Project 1 是业务语义、SQL、指标和运行结果的唯一事实来源。

实施顺序必须保持为：文档基线 → 基础设施与兼容性 → OLTP 模型与固定数据 → DataX 直写 Hive ODS → 离线数仓 MVP → V2 正式指标与质量 → Doris 离线服务与 DolphinScheduler → Spark 性能实验 → 实时设计评审 → 实时链路 → Project 1 发布。

优先完成稳定的最小离线闭环。实时链路当前仅为 `planned`；正式 Flink 业务作业已选定 Java DataStream Jar + YARN Application Mode，但在 Milestone 8 评审前，不得自行确定 Topic、Partition、Schema、窗口、Watermark、迟到、去重、状态 TTL、实时维度、Checkpoint 或 Doris 实时表模型，也不得生成正式 Flink 业务作业。BI、Dashboard、Agent 暂列后续规划，不计入当前 M0～M10 已交付能力。

Project 2 不属于本仓库的实现范围。它只能在 Project 1 稳定后消费 `P1-METADATA-01`、`P1-LINEAGE-01`、`P1-METRIC-01`、`P1-QUALITY-01`、`P1-RECONCILIATION-01` 和 `P1-TASK-01` 六个只读契约；不得回写数据、重新定义指标、推断不存在的血缘或重复实现质量执行引擎。

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

DataX 使用 HDFS Writer 直接写入 Hive ODS 对应的 HDFS 业务日期分区，输出格式为 ORC + Snappy；不建设独立持久化的中间数据层。Hive ODS 同时表示 Hive 逻辑表和其 HDFS 物理存储，ODS 装载负责分区注册、审计字段、幂等发布和失败隔离。DataX 不负责决定正式金额精度、状态枚举和最终字段类型。ODS 保留源语义，DWD 保存原子事实，DIM 保存一致维度，DWS 保存可复用度量以及比率的分子和分母，ADS 负责最终指标表达。DolphinScheduler 只能在任务独立运行通过后接入，负责参数、依赖、重试、回补、质量阻断、装载和对账，不承载业务计算逻辑。

仓库中的 `mysql/`、`datax/`、`hive/`、`spark/`、`flink/`、`doris/`、`scheduler/`、`quality/`、`env/`、`mock/` 和 `scripts/` 按阶段承担模块责任。`infra/` 已在 Milestone 1 开始后建立，只允许保存去敏的主机、端口、配置和兼容性内容；`infra/versions.env` 必须等待全部 M1 版本通过真实验证后再创建。旧 19 表的 Seed、Generator、脚本和测试位于 `archive/legacy-m2-19-table/`，不得作为当前 V2 实现；`mock/generator/ecommerce_generator_v1/` 是新包的文件级实现，不表示正式批任务已验收。`hive/dim/`、`kafka/` 和部分 Flink/DataX/Spark/Doris 子目录已按用户批准建立为 `placeholder`，但可执行内容仍须满足 `README.md` 与 `docs/plan.md` 的对应 Milestone 门禁；`reconciliation/` 仍在结果结构稳定后创建，`tests/` 仅按已进入阶段的验证范围扩展。

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

从首个可执行链路开始，至少验证：

- 首次运行、同日重跑、连续业务日期回补和上游重复输入。
- 空分区、迟到输入、非法状态、空值和主外键缺失。
- 业务键唯一性、引用完整性、状态合法性和分区按期到达。
- 源表、ODS 及后续各层行数可解释。
- 订单、明细、支付、退款之间的金额或数量守恒。
- 比率指标的分子、分母、精度、舍入和零分母边界。
- 配置缺失、依赖不可用和任务失败时返回非零状态，并阻断下游。

版本、配置和性能结论必须绑定真实环境与固定输入。性能优化只有保存执行计划、扫描量、Shuffle、Stage 和作业耗时等实测证据后才能描述为有效。

## 文档与变更同步

正式文档只记录已采用设计、最终配置、可复现命令、验证结果、已知限制和排障结论。学习笔记、临时实验、个人决策过程、未采用方案和安装草稿放入不提交 Git 的 `.local-notes/`；项目运行不得依赖该目录。

每次变更应小而聚焦，只完成用户指定且属于当前阶段的内容。实现发生变化时，同步检查并更新相关 README、规格、计划、架构、指标、运行说明和测试；不得一次性生成整个项目或擅自引入新框架。修改前说明计划，修改后列出变更文件、验证结果、未决事项和验证边界。

`CHANGELOG.md` 记录面向使用者和维护者的可交付变更，包括新增、变更、修复和移除；不得把仅讨论、未采纳方案或未完成的运行验证写成已交付事实。`docs/decision-register.md` 记录已经提出或确认、且会影响项目范围、业务口径、架构、组件版本、数据模型、接口、安全约束或验收方式的正式决策；不得用它代替一般变更日志。

## 答复收尾与记录确认

Agent 每次最终答复都必须包含以下内容：

1. 用简短条目总结本轮核心操作和核心决策；没有文件修改或没有形成决策时也应明确说明。
2. 明确询问用户，是否需要把本轮总结写入 `CHANGELOG.md`、`docs/decision-register.md`，或两者都写入。
3. 在用户明确确认前，不得仅因完成了答复就自动写入这两个文件；用户在当前请求中已经明确要求记录的内容除外。
4. 获得确认后，按文件职责筛选内容：可交付变更写入 `CHANGELOG.md`；正式决策写入 `docs/decision-register.md`。同一事项同时属于两类时可以分别记录，但内容必须各自符合对应文件的用途。
5. 写入后在答复中列出新增或更新的条目；决策记录必须使用下一个连续编号，并保留状态、依据、影响、验证方法和回滚方式。

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
