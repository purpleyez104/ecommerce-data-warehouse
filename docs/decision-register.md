# 项目决策记录

本文件记录会影响项目范围、业务口径、架构、组件版本、数据模型、接口、安全约束或验收方式的正式决策。临时想法和个人学习笔记不在此记录。

## 使用规则

- 决策编号使用连续格式 `DR-001`、`DR-002`。
- 状态只使用 `proposed`、`accepted`、`superseded` 或 `rejected`。
- 未获得必要证据或确认前，状态保持 `proposed`。
- 新决策不得覆盖旧记录；发生变更时新增决策，并在两条记录中互相引用。
- 涉及旧仓库内容迁入时，必须记录来源、采用理由、必要改造、验证方法和回滚方式。
- 静态检查、文件存在或配置草案不得作为运行验证证据。

## 决策索引

| 编号 | 标题 | 状态 | 决策日期 | 影响范围 |
| --- | --- | --- | --- | --- |
| `DR-001` | DataX 直写 Hive ODS 对应 HDFS 分区 | `accepted` | 2026-09-04 | 离线架构、Milestone 1、3、6、质量与对账 |
| `DR-002` | Agent 答复总结与记录确认门禁 | `accepted` | 2026-09-04 | 协作规则、变更日志、决策治理、Milestone 0 |
| `DR-003` | Milestone 0 验收与 Milestone 1 门禁开放 | `accepted` | 2026-09-04 | 项目状态、阶段顺序、Milestone 0-1 |
| `DR-004` | Milestone 2 受限预设计例外 | `accepted` | 2026-09-04 | 阶段门禁、业务模型预设计、Milestone 1-2 |
| `DR-005` | 采用当前 ECS 集群记录作为 Milestone 1 确认事实基线 | `accepted` | 2026-09-04 | 事实来源、证据状态、集群配置、Milestone 1-2 |
| `DR-006` | Milestone 1 扩展组件顺序、Doris 端口与调度注册中心 | `accepted` | 2026-09-04 | 组件顺序、端口、Kafka、Doris、DolphinScheduler |

## DR-001：DataX 直写 Hive ODS 对应 HDFS 分区

- 状态：`accepted`
- 决策日期：2026-09-04
- 决策人：用户
- 影响范围：离线架构、Milestone 1、3、6、质量与对账
- 替代决策：无

### 背景

原离线架构在 DataX 与 Hive ODS 之间设置独立的 HDFS landing/staging Text/CSV 数据层。用户要求删除该独立层，同时保留 DataX 和以 Hive/HDFS 为核心的离线数仓主线。

### 决策

保留 DataX，并使用 HDFS Writer 直接写入 Hive ODS 对应的 HDFS 业务日期分区，输出目标为 ORC + Snappy。Hive ODS 同时表示 Hive 逻辑表和其 HDFS 物理存储；ODS 装载负责显式分区注册、`business_date`、`extract_time`、`batch_id`、`source_table` 审计字段、幂等发布和失败隔离。不建设独立持久化的 Text/CSV 中间数据层。

### 理由

该方案满足删除独立中间层的要求，同时保留 DataX 的批量抽取职责和 Hive ODS 的正式数据分层。未采用 Spark JDBC 替代 DataX，因为这会超出本次架构调整范围；未采用只删除流程图节点但不重定义写入责任的方案，因为它会造成 ODS 所有权、格式和验收边界不清。

### 验证方法

Milestone 1 验证 DataX、HDFS 和 Hive 的候选版本组合及最小写入/读取能力。Milestone 3 使用固定 MySQL 输入验证 HDFS Writer 的 ORC + Snappy 输出、Hive 分区可见性、四个审计字段、源表与 ODS 对账、首次运行、同日重跑、连续回补、异常批次保护和失败时非零退出状态。只有真实验证通过后，该路径才能标记为 `verified`。

### 影响与风险

DataX HDFS Writer 的格式、依赖和文件行为尚未在目标 ECS 环境验证。直接写 ODS 还要求明确批次发布原子性、临时文件处理和失败回滚；这些内容是 Milestone 3 的实现与验收责任，当前决策不构成运行证明。

### 回滚方式

若 Milestone 1 或 3 证明直写方案不可行，保留失败日志、版本、配置和固定输入，新增后续决策记录替代本决策，并经用户评审后调整架构；不得静默恢复旧链路或改用 Spark JDBC。

## DR-002：Agent 答复总结与记录确认门禁

- 状态：`accepted`
- 决策日期：2026-09-04
- 决策人：用户
- 影响范围：协作规则、变更日志、决策治理、Milestone 0
- 替代决策：无

### 背景

项目需要在每轮协作结束时明确本轮实际执行的核心操作和形成的核心决策，并由用户控制这些内容是否成为仓库内的正式记录，避免关键变化遗失，也避免把普通讨论自动升级为项目事实。

### 决策

Agent 每次最终答复必须简要总结核心操作和核心决策，并询问用户是否将本轮总结写入 `CHANGELOG.md`、`docs/decision-register.md` 或两者。除用户已在当前请求中明确授权记录的内容外，未获得确认前不得自动写入。确认后，只有可交付变更写入 `CHANGELOG.md`，只有影响范围、业务口径、架构、版本、模型、接口、安全或验收方式的正式决策写入 `docs/decision-register.md`；同时符合两类用途时可以分别记录。

### 理由

该规则让用户保留正式记录的最终控制权，同时通过固定的答复收尾降低遗漏重要变更和决策的风险。按文件职责筛选内容能够避免修改日志退化为对话流水账，也避免决策记录被一般操作淹没。

### 验证方法

静态检查 `AGENTS.md`、`README.md`、`docs/spec.md` 和 `docs/plan.md`，确认两个文件的路径、职责、答复总结要求和用户确认门禁一致。后续每轮协作通过最终答复及用户确认记录抽查该规则是否被遵守；该静态检查不证明未来答复已经执行规则。

### 影响与风险

所有 Agent 答复增加固定的总结与确认步骤。若不按文件职责筛选，可能造成重复记录或无效噪声；若用户未确认却自动写入，则会把尚未采纳的讨论误记为项目事实。

### 回滚方式

若该流程影响协作效率，由用户确认新的收尾或记录方式，新增决策替代本记录，并同步更新 `AGENTS.md`、`README.md`、`docs/spec.md` 和 `docs/plan.md`；不得直接删除历史决策。

## DR-003：Milestone 0 验收与 Milestone 1 门禁开放

- 状态：`accepted`
- 决策日期：2026-09-04
- 决策人：用户
- 影响范围：项目状态、阶段顺序、Milestone 0-1
- 替代决策：无

### 背景

Milestone 0 的项目范围、离线架构、模块边界、指标数量、实时状态、Project 2 只读边界和阶段计划已经完成文档修订及静态一致性检查。用户在评审首轮结果后指示继续执行状态收尾。

### 决策

Milestone 0 状态改为 `completed`。Milestone 1 保持 `pending`，但其 Milestone 0 前置门禁已满足，可以开始基础设施与兼容性工作。`completed` 是 Milestone 验收状态，不提高任何组件、配置、任务或数据链路的证据等级。

### 理由

文档基线已经满足 Milestone 0 的交付和评审要求，而组件兼容性及运行验证属于 Milestone 1 及后续阶段。把 M0 完成和运行对象 `verified` 分开，可以在推进阶段的同时保持证据边界真实。

### 验证方法

静态核对 `README.md`、`AGENTS.md`、`docs/spec.md` 和 `docs/plan.md`：M0 均为 `completed`，M1 均为 `pending` 且注明进入门禁已满足；旧离线中间层引用保持为零；30 项正式指标、10 项扩展指标、5 项实时候选和六个 Project 2 只读契约数量不变；执行编码、换行和 `git diff --check` 检查。

### 影响与风险

下一阶段允许开展主机、网络、磁盘、JDK 和组件兼容性验证，但不得把 M0 的文档验收当作安装、启动、连通或链路运行证明。业务模型、指标口径、精确版本和实时细节中的未决事项继续保持原状态。

### 回滚方式

如果后续发现 M0 基线存在影响 M1 的冲突，停止 M1，保留已取得证据，由用户确认后新增决策记录并将 M0 重新置为 `in progress` 或 `blocked`；不得修改或删除本历史决策。

## DR-004：Milestone 2 受限预设计例外

- 状态：`accepted`
- 决策日期：2026-09-04
- 决策人：用户
- 影响范围：阶段门禁、业务模型预设计、Milestone 1-2
- 替代决策：无（补充 `DR-003`，不改变其状态）

### 背景

Milestone 1 的进入门禁已经开放，但尚未实际启动。用户希望暂缓 Milestone 1 并先推进 Milestone 2；现行阶段计划则要求 MySQL 先通过 Milestone 1 的启动和连接验证，且禁止在门禁未满足时创建正式业务模型和运行性产物。为在不虚构环境能力、不改变强制顺序的前提下提前收敛业务问题，需要定义一个边界明确的文档预设计例外。

### 决策

Milestone 1、2 均保持 `pending`，允许先创建和维护 `docs/milestone-2-predesign-review.md`。预设计只整理五个主题的业务过程、概念关系、30 项正式指标的过程依赖、验收场景和 `DECISION_REQUIRED`，不构成正式进入 Milestone 2。

预设计期间不得创建或修改正式 DDL、seed、数据生成器、测试程序、运行脚本、字段类型、状态枚举或可执行接口；`mysql/ddl/`、`mysql/seed/` 和 `mock/` 继续保持占位状态，不创建 `generator/` 或 `tests/`。只有 MySQL 通过 Milestone 1 的启动和连接验证，且 OLTP 表、字段、主外键、状态机和硬删除策略经用户确认后，才能正式进入 Milestone 2。

### 理由

该方案允许在暂时无法或不准备实施基础设施时先完成业务问题梳理，同时保留环境验证、业务确认和正式实现之间的证据边界。未采用直接把 Milestone 2 标记为 `in progress` 的方案，因为其进入条件尚未满足；未采用生成不可执行候选 DDL 的方案，因为候选字段和状态容易被误当成已采用模型，并会绕过必须由用户确认的业务语义。

### 验证方法

静态核对 `AGENTS.md`、`README.md`、`docs/spec.md` 和 `docs/plan.md`：Milestone 1、2 均为 `pending`，预设计允许范围、禁止范围和正式进入条件一致。执行 `git diff --check`；检查 `mysql/ddl/`、`mysql/seed/` 和 `mock/` 没有新增运行性内容，`generator/`、`tests/` 不存在；确认 30 项正式指标、10 项扩展指标、5 项实时候选和六个 Project 2 只读契约范围未改变。上述检查只证明文档和门禁一致，不证明 MySQL 或任何数据模型已经运行。

### 影响与风险

预设计评审包会成为后续业务确认的输入，但其中所有对象关系仍为 `draft`。若读者忽略状态说明，可能误把概念关系当成物理模型；因此所有未确认内容必须显式标记 `DECISION_REQUIRED`，README、规格和计划必须持续说明该活动不属于正式 M2 实施。

### 回滚方式

若用户决定停止预设计，新增后续决策将本记录标记为 `superseded`，同步移除四份治理文档中的例外入口并恢复“当前只推进 M1”。评审包保留为未采用的 `draft` 历史输入，除非用户另行明确授权删除；不得覆盖或删除本决策记录。

## DR-005：采用当前 ECS 集群记录作为 Milestone 1 确认事实基线

- 状态：`accepted`
- 决策日期：2026-09-04
- 决策人：用户
- 影响范围：事实来源、证据状态、集群配置、Milestone 1-2
- 替代决策：补充 `DR-003`、`DR-004`，不改变其历史状态

### 背景

Milestone 1 原计划从三节点主机、网络、磁盘、Java 和 Hadoop 的现场盘点开始。用户随后提供 `alibaba-ecs-hadoop-cluster-rebuild-spec.md`，并确认该文件是本项目当前集群的实际搭建记录，不是通用参考方案；文件中的 `CONFIRMED` 可以作为当前确认事实。

来源快照日期为 2026-09-04，SHA-256 为 `0556E06CBF754D01E4CCD451356E0EB15F6BE6A3E7B49E91632FA85313F25264`。文件包含杭州地域、VPC/vSwitch、三节点私网地址和规格、`yee` 用户、`/data` 磁盘布局、OpenJDK 17/11 分工以及 Hadoop 3.4.1 的 HDFS/YARN 运行拓扑。

### 决策

把来源文件的状态按以下方式纳入 Project 1：

- `CONFIRMED` 直接作为当前集群确认事实，不降级为候选，也不要求重新证明事实是否存在。
- `CONFIGURED` 作为已采用配置，但不自动补足来源明确缺失的功能测试证据。
- `PLANNED` 保持候选或计划状态，不描述为已安装或已验证。
- `UNKNOWN` 必须现场获取，不猜测、不复制其他节点值，也不把秘密或阿里云账号级资源写入 Git。

Milestone 1 状态改为 `in progress`。现有 Ubuntu、网络、磁盘、用户和 Hadoop 拓扑不重新初始化；组件统一沿用 `yee`、`/data/software`、`/data/module` 和 `/data/<component>`。默认 Java 为 OpenJDK 17，Hadoop 3.4.1 单独使用 OpenJDK 11。NameNode 已存在，禁止再次格式化。

Hadoop 的版本、进程和拓扑已确认，但完整 HDFS 固定文件校验、MapReduce 输出和重启恢复证据尚未保留，因此 Hadoop 整体暂记为 `implemented`；补齐后才能标记 `verified`。`DR-004` 的 M2 文档预设计例外在 M1 为 `in progress`、M2 为 `pending` 时继续有效，允许和禁止范围不变。

### 理由

该记录来自本次项目集群的实际搭建过程，重复把确认事实降级为未知会造成无意义的重建风险，尤其可能误触现有 NameNode 格式化。按来源状态分别处理，既保留用户确认的事实，也不会用进程和静态配置替代项目要求的最小任务与重启证据。

未采用整份复制外部文件的方案，因为其中包含复建说明、Project 2 规划和不得进入 Git 的现场值类别；仓库只提取 M1 所需事实，并保存来源、哈希、适配和验证边界。

### 验证方法

静态核对 `docs/cluster-baseline.md`、兼容性矩阵、README、规格、计划和架构中的节点、私网地址、用户、目录、Java 与 Hadoop 拓扑一致。执行 `scripts/m1/collect-hadoop-evidence.sh`，固定输入为两行 UTF-8 文本，预期 HDFS SHA-256 一致、MapReduce `wordcount` 为 `alpha=2`、`beta=2`、`gamma=1`、退出状态为 0，并保存 YARN application ID 和聚合日志。评审通过后执行带精确确认参数的受控重启脚本，预期恢复 2 个 Live DataNode、2 个 RUNNING NodeManager 和 `hadoop201` 的四个控制进程。

上述补测用于满足项目验收，不否定来源中的确认事实。没有执行 ECS 脚本前，仓库改动最多证明 M1 验证入口已 `implemented`。

### 影响与风险

M1 从“准备开始”变为实际实施，并从 Hadoop 补证门禁继续。外部来源路径不属于仓库，若原文件后续变化，必须重新计算哈希并评审差异；不得用同一路径下的新内容静默替代当前快照。

受控重启会影响现有 Hadoop 服务，因此与非中断测试分离，并要求 `--confirm-restart EXISTING_HADOOP_CLUSTER`。脚本不得格式化 NameNode或删除既有 HDFS 数据。

### 回滚方式

若事实来源认定需要调整，新增后续决策将本记录标记为 `superseded`，同步回滚仓库中的事实提取、状态和入口。不得因文档回滚而停止 ECS 服务、格式化 NameNode、删除 HDFS 数据、修改云盘或覆盖现有集群配置。

## DR-006：Milestone 1 扩展组件顺序、Doris 端口与调度注册中心

- 状态：`accepted`
- 决策日期：2026-09-04
- 决策人：用户
- 影响范围：组件顺序、端口、Kafka、Doris、DolphinScheduler
- 替代决策：无

### 背景

外部集群记录和仓库阶段计划对核心链路之后的扩展组件顺序存在差异，同时 YARN ResourceManager Scheduler 已确认占用 `hadoop201:8030`，与 Doris FE 默认 HTTP 端口冲突。DolphinScheduler 还需要注册中心，但 Kafka 已确定必须使用 KRaft，不能为 Kafka 引入 ZooKeeper 模式。

### 决策

核心链路通过后，扩展组件严格按 `DataX → Doris → DolphinScheduler → Flink / Flink CDC` 推进。Doris FE HTTP 使用 `hadoop201:18030`，YARN `8030` 保持不变。DolphinScheduler 在 `hadoop201` 使用单节点 ZooKeeper 3.8.4 作为开发环境注册中心；该 ZooKeeper 只服务 DolphinScheduler，Kafka 三节点继续使用 KRaft，不连接 ZooKeeper。

### 理由

沿用仓库顺序可以保持 `docs/plan.md` 为当前权威门禁，并在 Flink Doris Connector 验证前准备好 Doris 目标端。修改 Doris FE HTTP 比调整已运行的 YARN 端口影响更小。单节点 ZooKeeper 满足成本受限开发环境中的 DolphinScheduler 注册需要，同时保持 Kafka KRaft 边界清晰；本项目不把它描述为高可用。

### 验证方法

Doris 安装前在三节点检查 `18030` 未被占用，安装后验证 FE 实际监听 `18030`、BE 注册、临时表写入查询、健康检查、安全组和 SSH 隧道。DolphinScheduler 验证 ZooKeeper 连接、Master/API/Alert、两个 Worker、一个成功任务、一个预期失败任务和重启恢复。Kafka 配置和进程检查不得出现 ZooKeeper 连接参数，并完成 KRaft 仲裁、生产、消费和单 Broker 重启测试。

### 影响与风险

所有引用 Doris FE HTTP 的配置、脚本、健康检查和访问说明必须使用 `18030`。单节点 ZooKeeper 故障会使 DolphinScheduler 注册能力不可用，属于开发环境接受的单点限制。未取得组件真实测试前，版本和拓扑仍保持 `candidate` 或 `planned`。

### 回滚方式

如果 `18030` 被实际占用或组件验证失败，保存端口与启动证据，停止 Doris 门禁并由用户选择新端口；不得改动 YARN `8030`。如果 DolphinScheduler 的 ZooKeeper 方案不可用，保存日志并新增替代决策后再调整注册中心；不得让 Kafka 退回 ZooKeeper 模式。

## 记录模板

复制以下模板新增记录；不要直接修改模板内容。

```markdown
## DR-001：决策标题

- 状态：`proposed`
- 决策日期：`yyyy-MM-dd`
- 决策人：待确认
- 影响范围：待填写
- 替代决策：无

### 背景

说明问题、约束、已知事实和待解决事项。

### 决策

说明最终采用的方案及明确边界。

### 理由

说明采用该方案的依据，以及未采用方案的主要权衡。

### 验证方法

列出可执行命令、固定输入、预期结果和所需运行证据。

### 影响与风险

说明受影响的模块、兼容性、数据口径和已知风险。

### 回滚方式

说明恢复条件、操作步骤和需要保留的数据或证据。
```
