# Project 1 完整交付整改方案

状态：`confirmed / implementation-guidance`
确认日期：2026-10-15
当前执行位置：Stage 1～4 已完成；Stage 5 的 Doris 离线 Serving、DolphinScheduler JDBC Registry 组件门禁及正式 DAG 自动重试/失败阻断已通过。Aggregate Backfill 已验证至 Quality Gate；Doris 调度任务因连续 `EOFException` 暂停，等待新证据后仅从失败 Task 恢复
适用范围：Project 1 Milestone 1～10、离线链路、实时链路、数据治理、验收证据与简历结论

## 1. 目的与事实边界

本方案用于指导后续开发，统一最终目标为：

> 完成整个 Project 1，并获得足以支撑完整简历描述的真实运行证据。

后续仍按 Stage 和 Step 顺序实施，以控制依赖、风险和返工；Stage/Step 只是实施顺序，不代表缩减最终范围。交易域可以作为验证公共框架、模型和验收方法的实施入口，但不是项目交付终点。

本方案不改变以下证据规则：

- 当前代码、配置和实际执行结果决定实现与 Runtime 事实。
- `docs/spec.md` 管 Scope、Contract 与 Acceptance，`docs/plan.md` 管 Milestone 路线。
- 本文件管理跨阶段整改顺序、完整交付约束和 Data Governance 的实施边界。
- 静态文件、设计、Dry-run 和 Unit Test 不得外推为数据库、Hive、Doris、Kafka、Flink 或 DolphinScheduler Runtime。
- 历史 Pilot 证据继续有效，但不能替代 Formal V2 Gate。

## 2. 完整交付范围

Project 1 最终必须覆盖：

1. 21 表 Source、60/30 Replay、ODS 和 ODS Gate。
2. 覆盖完整核心业务过程的 DIM/DWD。
3. 六个指标域的代表性 DWS/ADS 指标。
4. 数据质量、跨层对账、幂等重跑和连续回补。
5. Doris 离线与实时服务。
6. DolphinScheduler 调度、补数、重试和质量阻断。
7. Spark 性能实验及实测证据。
8. Formal CDC、Kafka、Trade 与 Behavior Flink Domain Application。
9. Checkpoint、恢复和故障场景。
10. Offline ↔ Realtime 指标对账。
11. 轻量 Data Governance：Metadata Snapshot、Table-level Lineage、Metric Registry。
12. Project 1 六个稳定、版本化、只读 Contract。
13. 可复现运行材料、验收证据和简历结论映射。

完整交付不要求机械地实现全部候选指标、为 21 张表分别建设长期 Flink Application，或对每张表重复建设一套端到端框架。公共执行框架应复用，业务转换、指标和验收按真实业务过程组织。

## 3. 明确非目标

当前 Project 1 不建设：

- SQL Assistant、Text-to-SQL 或自然语言问数。
- LLM、Agent、FastAPI LLM Adapter 或其他 AI 服务。
- BI、Dashboard 或前端应用。
- Project 2 实现。
- 独立 DataOps 前端、后端或 Database。
- 用户、角色、登录、审批和资产运营系统。
- Column-level Lineage 或 Lineage DAG UI。
- 数据资产评分、标签平台或完整数据目录产品。
- 生产级 Hadoop HA 或未经实测的 Exactly-Once、吞吐和性能结论。

## 4. 高回报实施原则

### 4.1 保留完整能力，减少重复建设

- ODS 使用“一套 Runner + 21 表配置”。
- DWD/DIM 按业务过程组织，不机械地一张源表对应一张模型表。
- Flink 按 Domain Application 组织，不建设 21 个长期 Application。
- 指标覆盖六个域的代表性能力；未实现指标保持 `draft`。
- Source、ODS、Model、Realtime 等 Gate 分层验收，不逐表重复端到端验收。
- Data Governance 复用真实 SQL、指标、质量、对账和任务结果，不复制执行引擎。

### 4.2 证据先于结论

每个进入简历的结论必须绑定真实代码、SQL、配置、固定输入、命令、退出状态、结果、日志摘要或验收文件。没有 Runtime 时只能标记为 `implemented / not_run` 或 `DESIGNED`。

### 4.3 当前 Step 详细、后续 Stage 粗粒度

当前 Step 明确输入、输出、涉及模块、Targeted Test 和完成条件；后续 Stage 只冻结高返工 Contract 与 Gate，不提前铺开全部实现细节。

## 5. 整改实施路线

### Stage 0：同步 Scope、Architecture 与 Acceptance

同步项目总目标、Data Governance Scope、六个 Contract 的内部治理责任及明确非目标。同步后检查文档链接、状态词、Project 2 边界和 SQL Assistant/Agent 残留冲突。

退出条件：README、Spec、Plan、Architecture、Decision Register 与本方案不存在公共 Scope 冲突。

### Stage 1：收口 Replay 与 ODS 本地实现

保护当前 Dirty Worktree，不重做已完成的 Replay、Manifest、DataX Job Generator、Stage Runner 和 Spark Validation/Publish Renderer。

必须闭合：

- Replay Manifest、Daily Package、ODS Batch Contract 一致。
- 21 表字段、主键、业务日期和抽取策略校验完整。
- Bootstrap 与 Daily Package Dry-run 通过。
- DataX/Spark 注入接口稳定。
- 文件缺失、Hash 错误、字段不匹配和配置缺失均 fail-fast。
- 本地测试通过，但状态保持 `implemented / not_run`。

### Stage 2：执行正式 21 表 ODS Runtime

获得单独 Database Operation 授权后：

1. 创建隔离 Source 并装载 Day 60 Bootstrap。
2. 单独执行和验收 `day_61`。
3. 验证 DataX Stage、Spark Validation、Publish 和 Hive 分区注册。
4. 执行 ODS Gate。
5. 顺序执行 `day_62`～`day_90`。
6. 验证历史业务日期分区重建、同批重跑和失败恢复。

MySQL/DataX ODS Gate 至少覆盖 21 表行数、主键、字段、业务日期、审计字段、分区集合、跨表引用以及失败批次禁止发布。Behavior 60/30 Bundle 另以 `ods_behavior_event` 作为第 22 张离线 ODS 表，必须校验 Manifest/SHA-256、`event_id` 唯一、事件枚举、时间、身份、Session 和按业务日分区。

2026-10-18，Business 21 表 ODS Stage Gate 与独立 Behavior ODS Gate 均已完成；Behavior 结果为 3,000,000 行、90 个业务日分区、95/95 项断言通过。Stage 2 已完成。

同步形成 MySQL/Hive ODS Metadata Snapshot 与 MySQL → ODS Table-level Lineage；没有真实采集或真实 SQL 时不得生成 `VERIFIED` 治理结果。

### Stage 3：建设 DIM/DWD 与 Model Gate

状态：`VERIFIED / HISTORY`。修改前 6 张 DIM、8 张 DWD 已完成 Spark on YARN Runtime，59/59 Model Gate 通过；2 张日粒度 DWS 与 1 张 ADS 的 M4 技术 MVP 另已通过 18/18 Aggregate Gate 和幂等重跑。M5-02 修正版现已通过 60/60 Model Gate、18/18 Aggregate Gate 与幂等重跑；M4 技术 MVP 仍作为旧 Contract HISTORY 保留。

DIM/DWD 覆盖用户与身份、商品历史变化、购物车、订单与明细、支付、退款、优惠券和 Behavior Event 等核心业务过程。

建议模型入口包括但不限于：

```text
DIM
├── dim_user
├── dim_product_zip
├── dim_category
└── dim_coupon

DWD
├── dwd_order
├── dwd_order_item
├── dwd_payment
├── dwd_refund
├── dwd_coupon_event
└── dwd_behavior_event
```

Model Gate 验证事实粒度、业务键、事件时间、状态、金额/数量守恒、SCD2 当前版本唯一、有效区间不重叠、事实按业务时间唯一命中，以及重跑、回补、重复输入和迟到修正。

同步形成 ODS → DIM/DWD Table-level Lineage、Metadata Snapshot 和 SQL Artifact Hash。

### Stage 4：建设六域 DWS/ADS、指标与质量

状态：`VERIFIED`。稳定 Metric ID、退款事实修正、6 DWS + 1 ADS 六域 Runtime、41/41 Gate、36 项 Metric Registry、40 条持久化质量结果和 10 项 × 90 日跨层对账已完成；`TF-05` 已收敛为加购行为量，`TR-13/TR-14` Cohort 输出已通过 Runtime 与 Stage Gate。

交易与资金、流量与转化、商品、用户、退款与售后、营销六个域均须具有代表性指标。所有进入实现或简历的指标必须定义稳定 ID、版本、粒度、维度、公式、分子分母、时间归属、过滤、去重、零分母、精度、舍入、完整血缘、固定输入、预期结果和质量规则。

`docs/business/metrics.md` 继续管理业务定义与草案；Metric Registry 只发布已经实现并通过验收的指标，通过 Definition Reference 与 Definition Hash 绑定正式定义，不重定义指标公式。

首批实现范围按“全部 P0 + 补足流量与营销域的代表性 FROZEN P1”收敛；`US-06`、`RF-07`、`MK-07`、细分漏斗固定分母和 `RF-06` 精确支付分母截止规则继续保持 `TBD`，不得进入首批正式 SQL。M5-01 已确认 `TR / TF / PR / US / RF / MK` 编号直接成为稳定 `metric_id`，首版使用 `definition_version=1.0.0`。Metric Registry 仍只发布已经实现并通过验收的指标。

Contract 审计发现 P0 `RF-01` 不能由原成功资金粒度的 `dwd_refund` 计算。M5-02 已确认不新增重叠表，而是将现有 `dwd_refund` 改为每个退款申请一行的累积事实，成功资金结果保持可空；DWS 再计算申请数、成功申请数、成功金额和退款件数。当前实现与真实集群 Runtime 均已验证。M5-01 稳定 Metric ID 已确认，当前无剩余高返工 Contract 决策。

### Stage 5：Doris Serving 与 DolphinScheduler

Doris 验证 Spark Doris Connector 写入、服务表模型、重复写入/更新语义以及 Hive ADS 与 Doris 的行数、业务键和指标值一致。

当前 Doris 90 日装载、幂等重跑及 22 字段逐行对账已通过。DolphinScheduler 3.4.2 按 `DR-049` 使用 MySQL JDBC Registry，其成功/失败任务、受控重启复跑以及正式 DAG 自动重试/失败阻断已通过。Aggregate Backfill 的 Model Ready、DWS/ADS 和 Quality 已通过；Doris Load 连续 EOF，最终对账未运行。剩余工作是基于新证据修复 Doris 调度边界、从失败 Task 恢复、完成调度后对账和人为注入质量失败验证，不再建设 ZooKeeper。

历史回补遵循“从最低失效层恢复”。ODS、DIM、DWD 已通过 Gate 时，不重跑 DataX 或原子模型，也不把 Type 1 当前态维度改造成每日全量快照；独立 Aggregate Backfill 先执行 Model Ready Gate，再运行 DWS/ADS、Quality、Doris 和 Reconciliation。`business_date` 与 Cohort 的 `model_as_of_date` 必须独立传入，避免在同表混入不同观察窗口。只有下层数据本身缺失或失效时，才回到完整 DAG 的相应入口。

DolphinScheduler 只编排已经独立运行成功的任务：

```text
Source Ready
→ DataX Stage
→ ODS Validation
→ ODS Publish
→ DIM/DWD
→ DWS
→ ADS
→ Quality Gate
→ Doris Load
→ Reconciliation
```

验收显式业务日期、首次运行、同日重跑、连续回补、失败重试、质量阻断和最终任务状态。Data Governance 关联 Table、Metric、Quality、Reconciliation 与 Task，不复制调度、质量或对账执行逻辑。

### Stage 6：Spark 性能实验

性能实验必须由真实 Job 和执行计划驱动。至少完成分区裁剪，以及 Join 策略或数据倾斜中的一个真实场景；保存固定输入、SQL、执行计划、Input Size、扫描量、Shuffle、Stage、Job 耗时、多次执行结果和适用限制。

### Stage 7：Formal CDC 与 Realtime Domain

进入实现前冻结 Topic Namespace、Partition/Key、Schema、`event_version`、Checkpoint Root、Doris 实时表模型、Watermark、迟到、状态 TTL、恢复和对账目标。

- Trade Domain 处理订单、支付、取消、退款的 INSERT/UPDATE/DELETE、去重、版本顺序和 Doris Upsert。
- Behavior Domain 处理 `event_id` 去重、Visitor/User、Session、Event Time、Watermark、允许迟到及选定流量指标。

必须通过 CDC Gate、Realtime Model Gate、Checkpoint/故障恢复和 Doris 结果验收。同步补充实时 Metadata、Table-level Lineage 和 Realtime Metric Registry 关联。

### Stage 8：Offline ↔ Realtime Reconciliation

对有效订单数、成功支付订单数、成功支付金额、成功退款金额以及至少一项流量指标执行离实时对账。结果必须绑定 Metric ID/Version、业务日期、截止时间、离线值、实时值、差异、阈值、状态和解释。

### Stage 9：完成轻量 Data Governance

建议模块边界：

```text
governance/
├── metadata/
├── lineage/
├── metrics/
├── schemas/
└── README.md

tests/
└── governance/

runtime/governance/
├── catalog.db
├── snapshots/
├── lineage/
└── exports/
```

`runtime/governance/` 保存本地运行产物，不提交 Secret 或原始运行日志。

#### Metadata Gate

- 从 MySQL、Hive、Doris 真实采集 database、table、column、type、key、partition、storage、location 和数仓层级等信息。
- Snapshot 记录来源、时间、版本、状态和内容 Hash。
- Snapshot 可重复生成并支持 Schema Diff。
- 采集失败保留最后一次成功 Snapshot，并标记 `STALE`。

#### Lineage Gate

- 只从 DataX 配置、真实版本化 SQL、Doris 装载和 DolphinScheduler 依赖生成 Table-level Lineage。
- 每条边记录上游、下游、Artifact Path/Hash、任务和解析状态。
- CTE、Join、`INSERT SELECT` 和多上游输入具有固定测试。
- 无法解析时标记 `UNKNOWN`，不得根据表名、目录或设计意图猜测。
- 只实现 Table-level Lineage，不实现 Column-level Lineage。

Table-level Lineage 需要可靠的 AST Parser。仓库没有合适现成实现时，应先评估并申请一个锁定版本的新 Dependency，不通过正则表达式构建正式血缘。

#### Metric Gate

- Released Metric 具有稳定 ID、状态、版本、Definition Reference/Hash、粒度、维度、时间、Source/DWD/DWS/ADS 依赖、任务、质量规则和 Evidence Path。
- 指标能够关联 Metadata、Lineage、Quality、Reconciliation 和 Task。
- Draft Metric 不进入发布 Registry。

### Stage 10：完整简历证据收口

建立统一 Evidence Index：

```text
Source Gate
→ ODS Gate
→ Model Gate
→ Metric Acceptance
→ Quality / Reconciliation
→ Doris Serving
→ Scheduler Acceptance
→ Spark Benchmark
→ CDC Gate
→ Realtime Model Gate
→ Recovery Gate
→ Offline-Realtime Reconciliation
→ Metadata Snapshot
→ Table-level Lineage
→ Metric Registry
→ Release Evidence Index
```

每项 Evidence 包含环境、版本、固定输入、命令、预期结果、实际结果、退出状态、日志或结果位置、已知限制和回滚方式。最终简历结论必须逐条绑定 Evidence ID。

## 6. Project 1 六个只读 Contract

以下 Contract 首先服务于 Project 1 自身的数据治理、验收和证据组织，同时保留未来供其他项目只读消费的能力：

| Contract | Project 1 内部责任 |
| --- | --- |
| `P1-METADATA-01` | 发布真实、版本化的 MySQL/Hive/Doris Metadata Snapshot |
| `P1-LINEAGE-01` | 发布由真实 SQL、配置和任务生成的 Table-level Lineage |
| `P1-METRIC-01` | 发布已实现并验收的 Metric Registry |
| `P1-QUALITY-01` | 发布质量规则、期望值、实际值和状态 |
| `P1-RECONCILIATION-01` | 发布跨层及离实时对账值、差异和状态 |
| `P1-TASK-01` | 发布 DolphinScheduler 工作流、任务状态、时间、耗时、失败和依赖 |

Data Governance 实现前三个 Registry，并只关联后三个执行模块的结果；不得重复实现质量、对账或调度引擎。Project 2 暂缓不影响 Project 1 完成这些 Contract。

## 7. 验证顺序

每个 Stage 采用：

```text
Targeted Test
→ Module Test
→ Integration Test
→ Runtime Gate
→ Evidence Review
```

静态验证只证明对应文件、Contract 和本地行为；外部系统能力必须绑定真实 Runtime。Stage Gate 时再集中同步 Status、Acceptance、README 和 Evidence Index。

## 8. 风险与控制

| 风险 | 控制方式 |
| --- | --- |
| Data Governance 演变为第二个平台 | 禁止 UI、独立后端、Agent、SQL Assistant、权限系统和 Column-level Lineage |
| Metadata 与环境漂移 | Snapshot、Hash、采集状态、Schema Diff 和 `STALE` |
| Lineage 被推断或伪造 | 只接受真实 SQL/配置；解析失败保持 `UNKNOWN` |
| Metric Registry 与指标文档冲突 | Definition Reference/Hash 绑定，不在 Registry 重定义公式 |
| 当前 Dirty Worktree 继续膨胀 | 按完整可验证功能块推进，不混入无关重构 |
| 文档职责重叠 | Spec 管 Contract，Plan 管路线，Status 管进度，Acceptance 管证据 |
| 简历结论先于 Runtime | 所有结论绑定 Evidence ID |

## 9. 当前执行入口

当前执行顺序为：

1. Stage 1～3 已完成：Scope/Architecture/Plan、Source/Replay、正式 ODS、DIM/DWD、Model Gate 与 M4 Aggregate MVP 均已有对应证据。
2. Stage 4 已完成：六域 DWS/ADS、Metric Acceptance、Quality、Reconciliation 与 Cohort P0 指标均已通过 Runtime Gate。
3. Stage 5 的 Doris Serving 独立任务、DolphinScheduler JDBC Registry 组件门禁及正式 DAG 自动重试/失败阻断已通过；Aggregate Backfill 已验证至 Quality Gate。当前先定位 Doris `frame.count()` EOF，再从失败 Task 恢复并完成调度后对账与质量失败注入，完成 Stage 5 Gate。
4. 后续依次完成 Spark 性能实验、正式实时链路与轻量 Data Governance。
5. `docs/status/resume-evidence-current.md` 持续收集已验证候选数据；最后统一完成 Release Evidence Index 和简历结论映射。

本方案不授权数据库清理、外部系统写入、安装新 Dependency、Commit 或 Push。相关操作仍按项目授权规则单独确认。
