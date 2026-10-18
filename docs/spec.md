# 电商离实时一体化数据仓库项目规格

版本：`0.5-draft`
状态：离线与实时 Pilot `completed / HISTORY`；Shared Source Data Build `VERIFIED`；批量 ODS 与 Formal CDC 接续 `DOING / DESIGNED`。Milestone 0 `completed`；Milestone 1、2、3、8、9 `in progress`；Milestone 4～7 `pending`
更新时间：2026-10-13
Repository：`ecommerce-data-warehouse`

## 0. 文档使用范围

本规格用于指导 Project 1“电商离实时一体化数据仓库”的设计、开发、部署、验证和求职材料整理。项目必须以真实运行、可验证、可复现和可解释为基本要求。

本规格只定义 Project 1。Project 2“DataOps Lite 数据资产与智能开发平台”不属于本仓库的实现范围，只保留两者的阶段顺序、只读交接契约和面试讲述比例。

### 0.1 项目正式规范

以下内容属于项目正式规范，应进入 Git 并参与实际开发：

```text
架构
组件与版本
部署配置
业务模型
数据分层
数据链路
指标定义
任务调度
数据质量
故障恢复
性能实验
接口定义
安全约束
验收标准
```

正式文档只能记录已采用设计、最终配置、可复现命令、验证结果、已知限制和排障结论。不得把目录存在、静态检查、草案或候选方案描述为真实链路已经运行。

### 0.2 本地辅助资料

学习笔记、面试问答、临时实验、个人决策过程、未采用方案、组件对比和安装草稿不属于运行时规范，应放在不提交 Git 的 `.local-notes/` 中。正式项目不得依赖该目录中的文件才能运行。

### 0.3 变更与决策记录

- `CHANGELOG.md` 是项目可交付变更的统一入口，按新增、变更、修复和移除分类记录，不承载未采纳讨论或未经验证的运行结论。
- `docs/decision-register.md` 是正式决策的统一入口，记录会影响项目范围、业务口径、架构、组件版本、数据模型、接口、安全约束或验收方式的提议与结论，并保留状态、依据、影响、验证和回滚信息。
- 两个文件职责不同；同一事项只有同时构成可交付变更和正式决策时才分别记录。
- Agent 每次最终答复必须总结本轮核心操作和核心决策，并询问用户是否写入上述一个或两个文件。除非用户已在当前请求中明确授权，否则必须在得到确认后再写入。

## 1. 项目定位与目标

项目名称：

```text
电商离实时一体化数据仓库
```

项目面向数据开发岗位求职，目标是通过一个真实、完整且可解释的工程展示以下能力：

- 从业务过程、事实粒度、维度和指标口径出发进行数仓建模。
- 构建可重跑、可回补、可对账的离线数据链路。
- 使用 Spark SQL 和 PySpark 完成分层加工和性能实验。
- 以固定小数据集验证离线和实时最小纵向链路，并继续扩展到完整 Project 1 所需的正式规模、业务域和验收范围；离实时共享业务主键、时间、状态和金额契约。
- 使用 DolphinScheduler 管理依赖、业务日期、失败重试、补数和质量阻断。
- 使用固定输入、预期输出、质量规则和故障实验证明实现结果。
- 区分开发环境方案和生产环境实践，不伪造高可用、Exactly-Once、吞吐或性能提升。

Project 1 是当前唯一实施与面试项目。Project 2 已暂缓，且不得重新定义 Project 1 的业务语义。

### 1.1 完整项目交付口径

完成整个 Project 1 并取得完整简历证据是唯一最终交付目标。下表中的 V1/V2 只保留为既有建设记录和数据规模标识，不是两个发布版本，也不是缩减后的交付终点。

| 既有建设标识 | 状态 | 作用 | 证据边界 |
| --- | --- | --- | --- |
| V1 小规模验证记录 | `HISTORY` | 保留固定小数据集的离线、实时 Pilot 与人工核对证据 | 只陈述已真实执行的范围、数据量、结果和限制；不用小数据结果外推大规模、高吞吐或端到端 Exactly-Once |
| V2 正式建设记录 | `in progress`（Source Data Build 已验收；批量 ODS / Formal CDC 接续中） | 以 21 表正式源模型和 Shared Source Gate 为共同基线，继续完成 ODS、DWD/DIM、DWS、ADS、Doris、正式 CDC、调度、性能、治理和发布证据 | 正式数据规模为 90 天、100,000 笔订单、约 285,000 条订单明细、实测 1,328,502 条 OLTP 记录和 3,000,000～5,000,000 条行为事件；性能实验规模为约 900,000 笔订单和 9,000,000 条行为事件。所有完整链路结论仍须绑定环境、版本、固定输入和实测结果 |

“交付 V1/V2”是项目建设阶段，不替代文档中已有的“V2 业务基线”、“V2 指标体系”等模型或口径版本标识。

## 2. 参考来源与采纳边界

本规格参考《数据开发求职项目总规格 V1.4》，但不整篇照搬。

| 项目 | 处理方式 |
| --- | --- |
| 项目名称、文档使用范围框架 | 采用，并调整为仅适用于 Project 1 |
| 两项目关系及 65% / 35% 比例 | 不采用；Project 2 已暂缓，当前只以完整 Project 1 证据为目标 |
| MySQL、Hadoop/Hive、Spark、Kafka、Flink、Doris、DolphinScheduler 技术方向 | 作为目标技术栈保留 |
| DataX 写入正式 ODS ORC 发布范围 | 采用；HDFS Writer 先写批次隔离 staging，Validation / Publish 按每行 `business_date` 发布 Hive `dt`；不建设独立持久化中间层，真实行为在 Milestone 1、3 验证 |
| 参考文件中的候选版本 | 不直接锁定；必须重新完成兼容性和启动验证 |
| 实时 Topic、窗口、迟到处理、维度和 Doris 表模型 | 暂不采用具体设计，保留为实时阶段待决策项 |
| Project 2 业务和应用实现 | 不迁入；六个只读契约转为 Project 1 内部治理与证据 Contract |

采用理由是保留数据开发岗位中具有代表性的完整链路，同时降低一次性引入过多未验证实现的风险。

本次验证仅包含规格内容和结构的静态检查，不代表任何组件已经安装、启动、连通或完成数据对账。需要回滚时，只恢复本次修改前的 `docs/spec.md`；不得因此修改或删除其他用户文件。

## 3. 范围与非目标

### 3.1 V1 业务范围

当前业务基线采用自营商城两期方案。第一期覆盖用户与匿名身份、Category/SPU/SKU、商品展示与行为、购物车、下单与取消、订单券、支付和基础退款，形成可核对的交易与资金闭环；第二期再扩展库存流水/快照、完整履约物流、复杂营销和更完整售后。当前正式业务规则入口为 `docs/business/business-baseline.md`。

分析范围覆盖交易与资金、流量与转化、商品、用户、退款与售后、营销。交易状态由模拟业务服务写入 MySQL，业务交易 CDC 只来自 MySQL Binlog；页面、商品和购物行为由独立行为源写入 Kafka，不得由生成器直接写 Kafka 冒充 CDC。

当前源模型为 21 张 `biz_*` MySQL 表及独立行为事件流。逻辑模型见 `docs/source/logical-model.md`，字段级物理设计见 `docs/source/physical-model.md`。2026-10-12 已在 MySQL 8.0.46 的正式库部署 21 表，装载固定输入生成的 1,328,502 行，并通过事务内及提交后独立 Shared Source Gate；隔离库历史验收仍不得外推为正式 CDC 或完整链路验收。

### 3.2 当前非目标

- 第一期不建设完整库存域或库存流水；当前已部署 21 表基线没有 SKU 库存字段。是否新增最小库存属性或简单扣减仍为 `DECISION_REQUIRED`，若采纳必须执行 Schema / Generator / DataX Contract 迁移并重新验收。
- 当前阶段不确定实时 Topic、窗口、Watermark、迟到、状态 TTL、维度关联和 Doris 实时表模型。
- 不建设生产级 Hadoop HA，也不将三节点开发环境描述为高可用集群。
- 不引入阿里云专有中间件、Kafka ZooKeeper 模式、Spark Standalone、Flink Standalone、Kubernetes、HBase、Redis、Elasticsearch、ClickHouse、Iceberg、Hudi 或 Paimon。
- 当前 M0～M10 不实现 DataOps、AI 服务或前端；BI/Dashboard/Agent 只列入后续数据应用规划，其仓库归属与实施门禁另行评审。
- V1 不实施大规模数据扩展，不预设百万级、QPS、延迟、Exactly-Once 或性能提升数字；这些候选目标进入 V2 后仍须通过实测确定。

### 3.3 Milestone 1 与 Milestone 2 并行推进

`DR-008` 允许 M1 与 M2 分轨推进，但不取消直接依赖。上一版 M2 的代码材料保留在 `archive/legacy-m2-19-table/`，对应设计文档保留在 `docs/archive/milestone-2-business-design.md`；二者均为历史材料，不作为当前 V2 实现依据。

2026-09-18 的业务重设计不沿用归档实现作为当前模型依据。当前采用已部署并通过 Source Gate 的 21 张 `biz_*` 表、独立行为事件流和新版指标口径。Seed `20260105` 的 Business Replay Baseline 已完成 r6 Day 60～90 隔离 MySQL Runtime，另一个隔离环境已完成 Day 60 + Day 61 ODS Smoke；Seed `20260928` 的正式终态 Snapshot 已完成正式 21 表 ODS Bootstrap 与独立 Gate。Behavior Bundle、Day 62～90 ODS、Kafka 与时间推进式 CDC Runtime 仍未完成完整验收，因此 Milestone 2、3 保持 `in progress`。

Milestone 3 所需的 HDFS/Hive/DataX 技术组合已有环境验证。2026-10-17 正式 `ecommerce_oltp` 1,328,502 行终态 Snapshot 已完成 DataX/HDFS/Hive/Spark Runtime、21 表分区发布和 1,476 项独立 ODS Gate；旧 100 单 Pilot 三表保留为 HISTORY。2026-10-18 又完成 Day 60～90 时间推进式链路、跨日恢复、29/29 Daily Checkpoint、连续回补和 1,498 项最终 ODS Gate，因此 M3 已完成；该证据不外推到 M4 及后续分层。

用户于 2026-09-22 确认实时链路已经建设到一半，因此 Milestone 8、9 记录为 `in progress`。后续实时链路 R1～R3 的历史输出证明 `biz_product_change_event` 的 `op=c/d`、Order / OrderItem DWD Java Job 构建与首次装载、CDC / Order DWD Checkpoint 恢复、订单与明细正常顺序 `op=u`，以及 Doris 101 单、320 明细汇总；当前在线、全字段/乱序、物理 DELETE、更新故障恢复和完整对账仍未验证。R1/R1-7 只是限定切片记录，不是项目阶段编号，也不把 M9 提升为完整 `verified`。这些事实现作为 Pilot History 保留，不解除 M2/M3 或 M8/M9 其余门禁。

### 3.4 当前业务语义基线

`docs/business/business-baseline.md` 是当前业务规则入口，核心约束包括：

- 身份：匿名访客与注册用户分离，只在可靠证据下建立可版本化映射；歧义事件保持匿名，不能静默覆盖历史结果。
- 会话与漏斗：同一访客按事件时间连续 30 分钟无活动开启新会话；同时保留自然日经营漏斗和 7×24 小时同群组漏斗。
- 商品与订单：Category 1:N SPU 1:N SKU；每单 1～5 个不重复 SKU，订单明细冻结成交时商品与金额快照；第一期不拆单。
- 购物车：登录合并按 SKU 数量相加，单 SKU 上限 99，超限裁剪并记录；相同合并操作重试不得再次累加。
- 订单与支付：订单状态为 `CREATED / PAID / CANCELED`，支付有效期 15 分钟；允许失败重试，但每单最多一次有效成功支付。
- 退款：一笔申请只关联一条订单明细，可多次资金尝试，但申请最终完整成功或失败；纯金额补偿不能反推退款件数。
- 优惠券：订单级最多一张固定金额券；锁定覆盖订单支付期限，取消时释放或过期，支付后 `USED`，退款不返券。
- 金额：源候选模型统一使用整数分，订单头、明细、优惠分摊、支付和退款必须满足守恒，不使用浮点财务金额。

### 3.5 当前逻辑与物理模型

当前逻辑模型见 `docs/source/logical-model.md`，字段级物理设计见 `docs/source/physical-model.md`。21 张正式 MySQL 表按以下七组组织：

- 用户与身份 3 张：`biz_user`、`biz_visitor`、`biz_identity_mapping`。
- 商品 4 张：`biz_category`、`biz_spu`、`biz_sku`、`biz_product_change_event`。
- 购物车 3 张：`biz_cart`、`biz_cart_item`、`biz_cart_merge_record`。
- 订单 3 张：`biz_order`、`biz_order_item`、`biz_order_status_event`。
- 支付 2 张：`biz_payment_attempt`、`biz_payment_event`。
- 退款 3 张：`biz_refund_request`、`biz_refund_transaction`、`biz_refund_event`。
- 优惠券 3 张：`biz_coupon_template`、`biz_coupon`、`biz_coupon_event`。

行为事件不计入 21 张 MySQL 表，逻辑上包含页面浏览、商品曝光、商品点击、加购和移除，至少保留稳定事件键、事件时间、采集时间、访客/用户、会话及按事件适用的 SKU、页面和数量字段。精确 Kafka Schema、Topic key 和保留策略仍待实施设计。

Behavior Replay 固定采用一次生成完整 90 天事件后切包：Day 1～60 形成历史 Bootstrap，Day 61～90 形成 30 个按 `event_time + event_id` 排序的 Daily Package。Bundle 必须绑定精确 Business Entity Manifest，并校验 SHA-256、窗口、Schema、Visitor/User/SKU 有效期、Session 与全局 `event_id` 唯一性。当前范围不包含通用倍速回放平台、内置 Kafka Producer 或 Flink 历史状态初始化。

21 表设计已作为当前正式源模型落地。`mysql/ddl/001_ecommerce_oltp.sql` 与 21 CSV Contract 对齐，订单/优惠券采用 `biz_order.coupon_id` 单向物理 FK，券表反向订单引用由索引与 Source Gate 校验；生成列不进入 CSV。2026-10-12 已完成 Business 21 表 1,328,502 行的目标 MySQL 装载与 45-rule Source Gate，Behavior 3,000,000 事件的 Entity Manifest 绑定验证也已完成；DataX/CDC 初始化接续尚未完成。

### 3.6 历史材料边界

旧 19 表的 Seed、Generator、脚本和测试位于 `archive/legacy-m2-19-table/`，对应设计文档位于 `docs/archive/milestone-2-business-design.md`；旧 21 表 Pilot Generator 位于 `archive/pilot-v1/ecommerce_generator_v1/`。这些历史内容不作为当前 21 表的正式实现依据，也不直接满足 M2/M3 门禁；不得混用旧表名、字段和指标编号。

### 3.7 CDC 环境验收边界

`docs/acceptance/env-05-cdc-acceptance.md` 记录了 MySQL 8.0.46 测试表 `cdc_acceptance.probe_order` 经 Flink CDC 3.6.0-1.20、Flink 1.20.5 和 Kafka 3.9.1 的隔离验收：Snapshot、Binlog INSERT/UPDATE/DELETE、HDFS Checkpoint、一次 TaskManager 故障恢复及恢复后继续采集均为 `CONFIRMED`。

该结论只适用于指定测试表和故障场景，不证明 21 张正式业务表 CDC、三组行为 Topic、90 天初始化接续、端到端 Exactly-Once、性能目标或完整离实时对账。

`docs/acceptance/r1_snapshot_acceptance_frozen.md` 已冻结 2026-09-21 的限定范围证据：指定隔离库 21 表在 Kafka 固定审计区间内为 1,178 / 1,178，100 笔订单主键与最终状态无多余、缺失或不一致；作业在当次观察时为 `RUNNING`，HDFS 存在 `chk-9/_metadata`。该记录没有核验 Flink Web UI 的 Completed Checkpoint 次数，不包含真实 Binlog 增量、全字段逐行对账、当前在线状态、端到端 Exactly-Once、Hive ODS 或 Doris 业务层。Topic `ods_cdc_m2_clean_v1` 只作为 Pilot / Acceptance / History 保留，不得作为 Realtime V2 正式 Topic 契约或继续写入目标。

`docs/acceptance/realtime_r1_r2_verified.md` 进一步记录 R2 的限定范围历史事实：CDC 与订单 DWD 分别从 `chk-328`、`chk-114` 恢复，并观察到恢复后的 completed Checkpoint；订单 `CREATED → CANCELED` 产生 `biz_order op=u` 并在 Doris 完成正常顺序 Upsert，历史结果为 101 单、69 `PAID`、32 `CANCELED`。该记录不包含当前在线状态、21 表全字段、乱序/物理 DELETE、R2 更新故障恢复或端到端 Exactly-Once。

### 3.8 当前模型状态总结

| 范围 | 状态 | 证据边界 |
| --- | --- | --- |
| V2 业务规则 | baseline | `docs/business/business-baseline.md`；不是业务系统上线证明 |
| V2 逻辑模型 | current design | `docs/source/logical-model.md`；不是 SQL 或部署证据 |
| 21 表物理模型 | `verified`（DDL、正式装载与 Source Gate） | MySQL 8.0.46 已部署 `mysql/ddl/001_ecommerce_oltp.sql`，装载 1,328,502 行并通过事务内及提交后独立 45-rule Source Gate |
| 旧 Pilot Generator | `PILOT / ACCEPTANCE / HISTORY` | `archive/pilot-v1/ecommerce_generator_v1/`；保留历史，不作为 V2 正式入口 |
| Business / Behavior Generator | `verified`（Business 目标 Runtime；Behavior 本地正式规模） | `mock/generator/business_generator/`、`mock/generator/behavior_generator/`；Business 1,328,502 行已完成目标 MySQL 装载与 Source Gate，Behavior 3,000,000 事件的 Entity Manifest SHA-256、实体引用、Session 和事件唯一性通过 |
| R1 21 表初始快照 | `verified`（冻结范围） | `docs/acceptance/r1_snapshot_acceptance_frozen.md`；1,178 / 1,178 表级计数及 100 单主键/最终状态对账，不含增量、全字段或 Exactly-Once |
| R1～R3 Order / OrderItem DWD | `verified`（历史限定范围） | 商品事件 `op=c/d`、Java Job 构建与提交、CDC / Order DWD Checkpoint 恢复、正常顺序 Upsert，以及 Doris 101 单 / 320 明细汇总；不含全字段/乱序、物理 DELETE、更新故障恢复或 Exactly-Once |
| `biz_order` ODS 历史切片 | `verified`（历史限定范围） | 用户提供的 2026-09-22 Chat：100 单、69 `PAID`、31 `CANCELED`、88 分区及金额汇总；发布重建稿和质量入口为 `implemented / not_run`，不含增量、重跑/回补或 M3 完整验收 |
| V2 指标体系 | `draft` / 部分待细化 | `docs/business/metrics.md`；尚无 DWS/ADS SQL 或引擎结果 |
| ENV-05 CDC | `CONFIRMED`（限定范围） | 单隔离测试表与指定故障场景，不外推正式 21 表 |

### 3.9 离线 Pilot 收口与 V2 正式开发边界

根据 `DR-031`，`hist-v1-001`、100 单 Generator、`ods_order`、`dwd_order` 及其验收资产统一作为 `PILOT / ACCEPTANCE / HISTORY` 保留。历史 Runtime 证据继续有效，但不再作为 V2 正式数据开发入口；`ods_order_item_create.sql` 保持 F2 `CONFIRMED_CREATED / NOT EXECUTED`，停止后续执行。

V2 正式源库为 `ecommerce_oltp`，沿用 7 个业务域、21 张 `biz_*` 表；`ecommerce_oltp_m2_acceptance` 保留为 Pilot、CDC、R1～R3/M3 历史环境。正式数据生成路径为 Python Generator → CSV → MySQL `LOAD DATA`，Generator 与数据库写入解耦。正式数仓继续使用 `ecommerce_ods`、`ecommerce_dwd`、`ecommerce_dim`、`ecommerce_dws`、`ecommerce_ads`，不新增 `_v2` database。

工程按层批量推进，并以 Source Gate、ODS Gate、Model Gate 和最终整链路验收控制质量。ODS 使用通用 DataX Job Generator、Stage Runner、Spark Validation、Publish 与多表配置；DWD/DIM 的业务转换 SQL 分表维护，执行框架通用化。正式源库已与历史 Pilot 库隔离；任何非空正式源表的重置、回滚或重新装载仍需单独 Database Operation 授权。

## 4. 技术栈与开发方式

选型结论：MySQL、Hadoop/Hive、Spark、Kafka、Flink、Doris 和 DolphinScheduler 构成了数据开发岗位中辨识度较高的经典开源技术组合，能够覆盖本项目计划展示的离线、实时、服务和调度能力。这里的“主流”表示技术方向和岗位能力具有代表性，不表示所有组件都采用最新版本；当前版本兼容与临时链路的实际结论以 `DR-026` 为准。DataX 属于成熟的传统离线同步工具，本项目保留它用于批量抽取，并通过 HDFS Writer 写入 Hive ODS 发布范围内的批次隔离 staging；正式 Snapshot 的 ORC + Snappy、分区发布、审计与失败隔离已验证，时间推进式增量与完整 Stage Gate 仍由 Milestone 3 验收。

| 职责 | 技术 | 当前状态 |
| --- | --- | --- |
| 业务数据源 | MySQL | verified；8.0.46、私网连接、ROW/FULL Binlog 与受控重启已通过 |
| 离线抽取 | DataX | verified；202309 运行包的 MySQL Reader、HDFS Writer、ORC 输出和失败返回已通过；`biz_order` 固定历史 ODS 切片另有 2026-09-22 限定 Runtime 证据，完整 ODS 行为仍留在 M3 |
| 分布式存储与资源管理 | Hadoop HDFS、YARN | verified；固定 HDFS 文件、MapReduce、聚合日志和受控重启已通过 |
| 数仓元数据与 SQL | Hive | verified；3.1.3、MySQL Metastore、HiveServer2、Beeline 与 ORC 访问已通过 |
| 离线计算 | Spark SQL、PySpark，运行于 YARN | verified；Spark 3.5.9 on YARN 可读写 Hive/HDFS ORC |
| 消息传输 | Kafka KRaft | verified；Kafka 3.9.1 三节点 Quorum、生产消费、ISR 与单 Broker 恢复已通过 |
| CDC 与实时计算 | Flink CDC、Java DataStream Jar + YARN Application Mode；SQL Client + YARN Session 用于技术验证 | 组件兼容性 verified；R1～R3 Snapshot、商品事件 `c/d`、Order / OrderItem 正常顺序 Upsert 和 CDC / Order DWD Checkpoint 恢复在限定范围内 verified；这些结果现为 Pilot History，正式 V2 尚未实现，M8/M9 保持 `in progress` |
| 分析服务 | Doris | verified；4.0.8 FE/BE、SQL 与受控重启已通过 |
| 工作流调度 | DolphinScheduler | candidate；3.4.2 尚未完成 M1 验收 |
| 数据生成和质量工具 | Python、SQL | 旧 Generator 已转为 Pilot History；Business / Behavior Generator 已完成正式规模生成与 Entity Manifest 绑定，Business `LOAD DATA`、Source Gate 与目标 MySQL Runtime 已通过；Incremental Business Generator 尚未完成 |

开发方式：

- Spark SQL 负责主要离线转换；只有 SQL 不适合表达的复杂逻辑才使用 PySpark。
- 正式 Flink 业务 ETL 与聚合作业采用 Java DataStream Jar + YARN Application Mode；Flink SQL Client + YARN Session 仅保留为 Kafka SQL 技术验证，不作为正式业务部署模式。该选择不提前确定窗口、状态或指标实现。
- Python 用于固定 seed 数据生成器和轻量质量工具。
- `archive/pilot-v1/ecommerce_generator_v1/` 仅保留 Pilot History；即使 package layout 已恢复，也不得作为 V2 正式入口或用历史运行结果证明当前代码通过 Runtime。
- `mock/generator/business_generator/` 与 `mock/generator/behavior_generator/` 已完成正式规模生成、Entity Manifest 绑定与 Targeted Test。21 CSV 字段、装载顺序和 Shared Source Gate 已完成目标 MySQL 验收；该事实不提升 Behavior Kafka、DataX/Hive ODS 或正式 CDC 状态。
- 不得使用多种语言重复实现同一个生产任务。

技术能力依据：

- [Spark on YARN 官方文档](https://spark.apache.org/docs/latest/running-on-yarn)
- [Kafka KRaft 官方文档](https://kafka.apache.org/39/operations/kraft/)
- [Flink CDC MySQL Connector](https://nightlies.apache.org/flink/flink-cdc-docs-release-3.6/docs/connectors/flink-sources/mysql-cdc/)
- [Flink CDC Kafka Pipeline Connector](https://nightlies.apache.org/flink/flink-cdc-docs-release-3.1/docs/connectors/pipeline-connectors/kafka/)
- [Flink Doris Connector](https://doris.apache.org/docs/3.x/ecosystem/flink-doris-connector/)
- [Spark Doris Connector](https://doris.apache.org/docs/3.x/ecosystem/spark-doris-connector/)
- [DataX HDFS Writer](https://github.com/alibaba/DataX/blob/master/hdfswriter/doc/hdfswriter.md)

上述文档只能证明组件具有相应能力，不能证明本项目的候选版本组合已经兼容或能够稳定运行。

## 5. 目标架构与实施链路

总体技术路线见[最终工程架构 V1.0](architecture/final-architecture.md)；节点、源系统和实时作业的责任分别见[部署拓扑](deployment-topology.md)、[业务源设计](design/business-source-design.md)和[实时链路规范](design/realtime-pipeline-design.md)。这些文档只按各自证据范围解释，不改变本规格的 Milestone 门禁。

### 5.1 离线主线

```text
MySQL ecommerce_oltp
        │
        │ DataX 全量、可靠更新时间增量、事件记录水位增量或每日全量快照
        ▼
HDFS batch staging（ORC + Snappy）
        │ Spark Validation / Publish
        ▼
Hive ODS（按每行 business_date 发布 HDFS dt 分区）
        │
        │ Spark SQL
        ▼
DIM / DWD
        │
        │ Spark SQL
        ▼
DWS
        │
        │ Spark SQL
        ▼
ADS
        │
        ├── 数据质量检查
        ├── 逐层对账
        └── Spark Doris Connector
                ▼
        Doris 离线服务表
```

约束：

- DataX 使用 HDFS Writer 写入 Hive ODS 发布范围内的 batch staging，不建设独立持久化的中间数据层；staging 只服务于校验、失败隔离和原子发布。
- 可变表使用可靠的 `updated_at` 半开窗口，Append-only 表使用记录水位半开窗口，没有可靠更新水位的 `biz_identity_mapping` 使用显式快照日的每日全量快照。抽取水位不决定最终业务分区。
- 事实和事件在抽取结果中按行业务时间计算 `business_date`，维度全量快照使用显式快照日；Spark Validation / Publish 根据该字段识别并发布最终 Hive `dt`。
- Hive ODS 同时表示 Hive 逻辑表和其 HDFS 物理存储；ODS 装载负责分区注册、审计字段、幂等发布和失败隔离。
- DataX 不负责决定正式金额精度、状态枚举或最终 Hive 字段类型；这些内容必须随源模型和 ODS 设计确认。
- Hive ODS 保留源字段语义，并包含 `business_date`、`extract_time`、`batch_id` 和 `source_table` 等审计字段；最终字段以源模型评审结果为准。
- DataX HDFS Writer 的 ORC/Snappy 与失败行为已有环境验证；`biz_order` 固定历史切片的分区发布和 Spark 汇总已有 2026-09-22 限定 Runtime 证据。审计字段完整性、同日重跑、连续回补、失败隔离及其他表仍须在 Milestone 3 验证。
- 正式 ODS、DIM、DWD、DWS、ADS 使用 ORC + Snappy。
- ODS 保留源语义；DWD 保存原子事实；DIM 保存一致维度；DWS 保存可复用的可加度量和比率分子/分母；ADS 负责最终指标表达。
- 离线 ADS 默认通过 Spark Doris Connector 写入 Doris，具体 Connector 版本必须经过 Spark、Scala、Java 和 Doris 兼容性验证。
- DolphinScheduler 只能在离线任务独立运行通过后接入，负责业务日期、依赖、重试、回补、质量阻断、Doris 装载和对账，不承载业务计算逻辑。
- 基于更新时间或记录水位的 DataX 增量抽取不能天然捕获硬删除。当前 21 表禁止业务硬删除；没有可靠更新水位的表必须使用全量快照或另行设计删除对账，不得用 `load_time` 冒充源端变化水位。

### 5.2 Realtime V2 目标链路

```text
Historical Generator → CSV → LOAD DATA → MySQL ecommerce_oltp
Incremental Business Generator → MySQL Transaction → MySQL ecommerce_oltp
      │
      │ Binlog
      │
      ▼
Flink CDC 采集任务
      │
      ▼
Kafka Raw CDC Topic
      │
      ▼
Flink 实时清洗与计算
      │
      ├── Kafka 标准事件 Topic
      ├── HDFS/Hive 长期归档
      └── Doris 实时服务表
```

Flink CDC 是运行在 Flink 上的采集任务，不是独立于 Flink 的常驻平台。R1～R3 业务切片止于 `ecommerce_oltp_m2_acceptance` → `ods_cdc_m2_clean_v1` → Order / OrderItem DWD → Doris，现统一定位为 Pilot / Acceptance / History。历史 Runtime 证据继续有效，但 acceptance 源库、Pilot Topic、`all-to-zero`、`kafka_offset` Sequence 与旧 Checkpoint 不进入正式 V2。

Realtime V2 与离线共享 `ecommerce_oltp`、21 表业务模型、Source Gate 与 Metrics Contract。Shared Source Gate 已通过；正式 CDC 尚未启动，必须先完成 60/30 输入 Contract、Topic / Checkpoint Inventory，并冻结 Topic Namespace、Partition 数、Key 和 `event_version`。Flink 工程按业务域组织 Domain Applications，运行框架通用化、业务转换分业务维护。当前这些正式实时内容均为已确认设计，不是实现或 Runtime 证明。

正式业务作业部署方式已选为 Java DataStream Jar + YARN Application Mode；正式 Topic、Schema、窗口、状态、Doris 表模型及端到端一致性仍由 Milestone 8 评审。SQL Client + YARN Session 的 M1 验证不作为正式业务作业验收。

## 6. 数据分层与存储责任

| 逻辑层或区域 | 主要物理位置 | 责任 |
| --- | --- | --- |
| 源系统层 | MySQL `ecommerce_oltp` | 业务交易和状态维护 |
| 离线 ODS | Hive/HDFS ORC + Snappy | 保留源语义和审计字段 |
| 离线 DWD | Hive/HDFS ORC + Snappy | 原子事实、标准字段、去重和状态统一 |
| 离线 DIM | Hive/HDFS ORC + Snappy | 一致维度及待确认的历史变化策略 |
| 离线 DWS | Hive/HDFS ORC + Snappy | 可复用主题汇总、分子和分母 |
| 离线 ADS | Hive/HDFS ORC + Snappy | T+1 正式指标结果 |
| 离线服务层 | Doris | 低延迟查询及 Project 2 只读消费 |
| 实时原始层 | Kafka Raw Topic | CDC 传输和短期重放，设计待确认 |
| 实时明细/汇总层 | Kafka、Flink State、HDFS/Hive、Doris | 具体责任待实时阶段确认 |
| 质量与对账结果 | Hive、Doris 或专用结果库 | 质量审计和离实时一致性检查 |

每张核心表、Topic、Doris 表和 HDFS 路径都必须同时标注逻辑层级和物理位置。Kafka 只承担传输和短期缓冲；需要长期保存、审计、补数或重算的数据必须进入 HDFS/Hive 或其他经确认的持久化存储。

离线和实时必须统一业务主键、事实粒度、时间字段、时区、金额精度、状态枚举、维度编码、指标公式和过滤条件。

## 7. 部署拓扑与资源约束

三个节点均运行于阿里云 ECS：

| ECS 节点 | 私网 IPv4 | 集群角色 | 计算资源 | 系统盘 | 数据盘 | 当前与候选职责 |
| --- | --- | --- | --- | --- | --- | --- |
| `hadoop201` | `10.20.1.201` | `master` | 4 vCPU / 16 GB | 50 GiB | 80 GiB | 已确认 NameNode、SecondaryNameNode、ResourceManager、JobHistoryServer；后续 Hive、Kafka、Doris FE、MySQL、DolphinScheduler 控制服务 |
| `hadoop202` | `10.20.1.202` | `worker01` | 8 vCPU / 16 GB | 50 GiB | 120 GiB | 已确认 DataNode、NodeManager；后续 Kafka、Doris BE、DataX、计算任务、DolphinScheduler Worker |
| `hadoop203` | `10.20.1.203` | `worker02` | 8 vCPU / 16 GB | 50 GiB | 120 GiB | 已确认 DataNode、NodeManager；后续 Kafka、Doris BE、DataX、计算任务、DolphinScheduler Worker |

约束：

- 这是成本受限的阿里云 ECS 开发环境，不代表生产拓扑。
- 三台数据盘已确认为 `/dev/vdb`、ext4、挂载到 `/data`；各节点实际 UUID 属于现场值，不进入 Git。
- 组件统一由 `yee` 运行；默认 Java 为 OpenJDK 17，Hadoop 3.4.1 通过 `hadoop-env.sh` 单独使用 OpenJDK 11。
- Hadoop 使用单 NameNode 和双 DataNode，HDFS 副本数为 2；固定文件和受控重启验证均已确认两个 DataNode 为 Live。
- Kafka 三节点 Broker/Controller 混合角色只用于开发环境，不能描述为生产最佳实践。
- 只有 `hadoop201` 需要公网 SSH 管理入口；集群组件端口只允许私网访问，本地 Web UI 优先使用 SSH 端口转发。
- 是否扩容必须依据磁盘空间不足、OOM、持续 Swap、频繁 Full GC、进程被杀或核心组件无法稳定共存等实测证据。
- 不得通过关闭当前链路的关键服务伪装组件兼容或链路稳定。
- 当前事实来源、状态映射和证据缺口以 [集群事实基线](cluster-baseline.md) 为准。
- 节点上当前角色与后续角色的区分见[部署拓扑](deployment-topology.md)。

## 8. 版本与兼容性门禁

Hadoop 3.4.1 已于 2026-09-05 在当前集群完成独立验收。根据 `DR-026`，MySQL、Hive、Spark、DataX、Kafka、Flink、Flink CDC、Doris 及 Flink Doris Connector 的精确版本与核心能力也已验证；当前仅 DolphinScheduler 3.4.2 保持候选。全部 M1 组件完成后，才能写入 `infra/versions.env`。组件验收关注以下能力：

```text
官方版本和兼容依据
→ 操作系统与 JDK 检查
→ 安装
→ 启动
→ 健康检查
→ 上下游连通
→ 最小数据链路
→ 重启验证
```

当前验收进度：

```text
主机与网络
→ JDK
→ HDFS / YARN / Hadoop（已完成）
→ MySQL（已完成）
→ Hive / Spark on YARN / DataX（已完成）
→ Kafka KRaft（已完成）
→ Flink / Flink CDC / Kafka source-sink（已完成，保留执行模式边界）
→ Doris / Flink Doris Connector（已完成）
→ DolphinScheduler（当前剩余门禁）
```

必须验证 Hadoop/JDK、Hive/Hadoop、Hive Metastore/MySQL、Spark/Hadoop/Hive、Kafka/JDK/KRaft、Flink/JDK、Flink CDC/Flink/MySQL、Spark Doris Connector/Spark/Doris、Flink Doris Connector/Flink/Doris、DolphinScheduler/JDK/MySQL 和 DataX/MySQL/HDFS 的组合。

不允许使用容器作为兼容性兜底。兼容失败时应暂停、保存证据、调整版本或架构并重新验证。

YARN ResourceManager Scheduler 已确认使用 `8030`。Doris FE HTTP 已决定使用 `18030`；Doris 配置前必须确认端口未占用，并同步客户端、健康检查、安全组和文档。

当前已验证基线为 MySQL 8.0.46、Connector/J 8.0.33、Hive 3.1.3、Kafka 3.9.1 Scala 2.12 KRaft、Spark 3.5.9-bin-hadoop3、DataX 202309、Doris 4.0.8、Flink 1.20.5、Flink CDC 3.6.0 和 Flink Doris Connector 26.1.1。Hive 4.1.0 因与 Spark 3.5.9 Metastore client 不兼容而退出。DolphinScheduler 3.4.2 仍是待验证候选；具体模式和边界见 [组件兼容性矩阵](compatibility-matrix.md) 与 `DR-026`。

实时组件可以完成安装兼容性验证，但在实时规格确认前不得进入正式业务开发。

Doris 4.0.8 的受控重启恢复已通过，`docs/architecture/final-architecture.md` 中的 Step 11 已按此事实修正。Hive 3.1.3 当前在 Java 17 环境通过验收；不能把 Java 11 的设计偏好记成 Hive 已切换的事实。

## 9. 数据生成、任务参数与幂等

采用两档数据规模，不再使用 V1/V2 作为规模名称，也不为新 Generator 建设独立 Smoke 档位：

- 正式数据规模：90 天、100,000 笔订单、约 285,000 条订单明细、约 100 万条 OLTP 记录和 3,000,000～5,000,000 条行为事件；使用显式 seed、业务起止时间和生成时间。
- 性能实验规模：约 900,000 笔订单和 9,000,000 条行为事件；只在正式数据规模完成业务验收后生成，用于 Spark、Kafka、Flink、Doris 等专项性能实验，不替代正式数据规模的业务验收。

验收数据必须覆盖：

- 正常注册与可靠身份映射、访问、购物车、下单和支付。
- 取消、退款申请、资金失败重试与成功。
- 重复输入和同一批次重跑。
- 跨日订单、支付和退款。
- 非法状态迁移和主外键缺失。
- 身份映射修订、商品属性变化和维度历史关联。
- 零分母、空值、整数分金额、优惠分摊和守恒边界。
- 订单超时与支付成功竞争、券释放/过期、购物车合并截断。
- 为未来实时验证准备的乱序、迟到和重复事件，但当前不定义处理策略。

所有批任务必须显式接收业务日期或起止时间，不得依赖执行机器当前日期推断数据范围。装载和转换应支持首次运行、同日重跑、连续回补和失败退出。

现有 `archive/pilot-v1/ecommerce_generator_v1/` 已转为 Pilot History，不再作为正式入口。当前 Business / Behavior Generator 已完成正式规模生成与 Entity Manifest 绑定；Business 数据已由可失败退出的 `LOAD DATA` 入口装载，并通过状态分布、跨表关系、CSV 依赖和装载顺序的 Shared Source Gate。Business Generator 不包含逐条 INSERT 职责。

根据 `DR-037`，正式 90 天数据的链路验收采用统一切换点：前 60 天建立历史初始化基线，后 30 天逐日驱动离线 DataX 与实时 CDC/Flink。切换点为第 61 个业务日零点；初始化数据必须是该时点的正确状态，不得包含后 30 天才发生的最终变化。现有一次性 90 天最终 bundle、正式 MySQL 装载和 Shared Source Gate 继续作为规模与业务 Contract 证据，不自动证明时间推进式回放已经实现。

正式 Replay 固定输入采用 `replay_formal_20260105.json + Seed 20260105 + generated_at 2026-10-15T10:00:00+08:00`，Dataset Version 保持 `v2.3-replay-formal-20260105-r2`。根据 `DR-044`，当前正式 Baseline 以 Business Hash `ecea32d620bfbf44671ff2c1e1ff765fe4638f330f621229b9dd8f543578deb5` 和 Replay Manifest SHA-256 `5e09633896125c487a9a2d55632507621eb058679f4e30bc83c313c42e46533c` 精确标识：Day 60 Bootstrap 为 438,869 行，Day 61～90 共 1,210,882 个操作（889,622 INSERT、321,260 UPDATE），终态 Source Contract 为 1,328,491 行。2026-10-17 当前 worktree 使用同一固定参数重生成 146 个文件并得到相同 Hash；r6 隔离 Source 完成 Day 60～90 Runtime、30/30 Acceptance 和最终独立 45-rule Gate。旧 `c690b325...` 与 `4abcd890...` 只保留为修复过程中的历史 Baseline，不得用于后续 ODS/CDC Contract。

同日，Behavior Replay 固定输入采用 `replay_formal_20260105.json + Seed 20260105 + generated_at 2026-10-15T10:00:00+08:00`，Dataset 为 `v2.3-behavior-replay-formal-20260105-r1`，绑定上述 Business r2 Entity Manifest。本地生成 3,000,000 条事件，其中 Day 1～60 Bootstrap 895,324 条、Day 61～90 共 2,104,676 条，Content SHA-256 为 `a074cab5cc0b7bf82582242b097cc24534a8f2917485c493743574d98f8baf5e`；独立审计通过且未连接 Kafka。

后续 Generator Contract 必须提供 bootstrap 与 30 个 daily 操作包。事实和事件按照业务发生时间归属 `dt`，维度快照按照快照日期归属；`source_updated_at` 或事件记录水位只决定增量抽取范围，`extract_time`/`load_time` 只用于审计。历史记录在后续日发生变化时，离线任务必须重建受影响的原业务日期分区。

需要历史属性的维度使用 SCD2：前 60 天由变更事件、可靠增量历史或每日快照差异构建版本，后 30 天按业务生效时间关闭旧版本和插入新版本；迟到变化重建受影响业务键的完整时间线。没有切换点前历史输入时，不得虚构旧版本。稳定且只关心当前值的维度使用 Type 1。完整设计见[历史初始化与双链路回放设计](design/historical-incremental-replay-design.md)。

## 10. 指标范围与编号

当前指标口径唯一入口为 `docs/business/metrics.md`。V2 按六个域提供 47 个检索条目：交易与资金 `TR-01`～`TR-14`、流量与转化 `TF-01`～`TF-08`、商品 `PR-01`～`PR-05`、用户 `US-01`～`US-06`、退款与售后 `RF-01`～`RF-07`、营销 `MK-01`～`MK-07`。

这些 `TR/TF/PR/US/RF/MK` 编号是 V2 文档内的检索标识，不自动继承归档方案的编号、实现或验证状态。历史指标清单不再作为当前源模型的直接实现输入。

### 10.1 已确认的共同口径

- 统计时区为 `Asia/Shanghai`，各过程按自身业务事件时间归属；记录时间和采集时间只用于延迟与审计。
- 订单取消回冲原订单创建日的有效 GMV；退款按真实成功日进入资金流，并影响原订单群组截至指定 `as_of_time` 的累计净额。
- 当前状态与不可变状态事件不能重复累计同一交易事实；支付和退款只选择唯一有效成功资金记录。
- 身份敏感指标必须绑定可靠映射版本；无法确认归属的事件保持匿名，历史修订保留版本、原因和影响窗口。
- 订单级金额按商品维度拆分时使用订单明细成交与优惠分摊快照，禁止将订单头金额直接 JOIN 多行明细后重复求和。
- 比率先合并分子和分母再计算，并显式记录零分母规则、`as_of_time` 和计算版本。

### 10.2 尚未冻结的口径

复购率、部分退款比例、券核销率、细分漏斗阶段比率分母、30 日退款率的精确支付分母截止点和支付完成临界时刻仍为 `待细化`。这些指标在口径确认、源字段血缘、固定样例和真实引擎结果完成前保持 `draft`，不得生成正式 SQL 或描述为 `verified`。

### 10.3 实现前契约

每个进入实现的指标必须定义稳定 ID、业务含义、粒度、维度、公式、分子分母、去重规则、事件时间、过滤条件、源字段、ODS/DWD/DWS/ADS 血缘、离实时来源、零分母、精度、舍入、固定样例、修订策略和证据状态。V2 检索编号是否直接成为稳定发布 ID，须在 Milestone 5 实施前明确。

## 11. 数据质量、对账与性能实验

最低离线质量检查：

- 业务键非空和唯一。
- 主外键及维度引用完整。
- 状态值和状态迁移合法。
- 分区按期到达。
- 源表、ODS 和后续各层行数可解释。
- 订单头、订单明细、支付、退款之间金额或数量守恒。
- 比率指标保留分子和分母，避免只保存最终比率。
- 质量失败返回失败状态并能够阻断后续调度。

质量结果使用 `data_quality_result`，至少包含规则编号、对象、分区、规则类型、期望值、实际值、状态和执行时间。

对账结果使用 `reconciliation_result`，至少包含指标编号、业务日期、实时值、离线值、差异、差异率和状态。实时细节未确认前只建立契约，不生成虚假对账结果。

Spark 性能实验至少覆盖：

- 普通聚合与两阶段聚合的数据倾斜对比。
- Sort Merge Join 与 Broadcast Hash Join 对比。
- 无效分区条件与正确分区裁剪对比。

实验必须固定版本、配置和输入，保存执行计划、扫描量、Shuffle、阶段耗时和作业耗时。没有真实实验时不得声称优化有效。

## 12. Project 1 数据治理与只读契约

Project 1 是业务语义、SQL、指标和运行结果的唯一事实来源。当前内部建设轻量 Data Governance：真实 Metadata Snapshot、基于真实 SQL/配置的 Table-level Lineage 和 Project 1-owned Metric Registry；不建设独立平台、SQL Assistant、LLM/Agent 或 Column-level Lineage。完整实施顺序见[Project 1 完整交付整改方案](design/project1-completion-remediation-plan.md)。

保留以下六个稳定、版本化、只读契约，首先服务于 Project 1 自身治理、验收和证据组织，同时保留未来供其他项目只读消费的能力：

| 契约编号 | Project 1 提供内容 | 当前状态 |
| --- | --- | --- |
| `P1-METADATA-01` | MySQL、Hive、Doris 的库表字段、逻辑层、物理存储、分区和保留策略 | draft |
| `P1-LINEAGE-01` | 进入 Git 的真实 SQL、任务依赖和层级映射 | draft |
| `P1-METRIC-01` | 已发布指标的稳定 ID、名称、公式、粒度、维度、时间口径、来源、版本和状态 | draft；V2 检索编号尚未确认是否直接作为发布 ID |
| `P1-QUALITY-01` | `data_quality_result` 的规则、对象、期望值、实际值和状态 | draft |
| `P1-RECONCILIATION-01` | `reconciliation_result` 的实时值、离线值、差异和状态 | draft |
| `P1-TASK-01` | DolphinScheduler 工作流、任务状态、时间、耗时、失败日志和依赖 | draft |

任何未来消费者不得：

- 回写 Project 1 的业务数据和结果表。
- 修改指标名称、公式、粒度或状态。
- 自行推断不存在的血缘。
- 重复实现第二套质量执行引擎。
- 把样例 SQL、候选结果或未验证数据描述为正式事实。

Project 2 已暂缓且不属于本仓库实现范围。具体 REST 路径、认证方式和序列化结构只有在真实服务确定后才能进入稳定契约；Project 1 当前可以通过版本化文件、Metadata Snapshot 和 Registry 交付这些 Contract，不虚构服务接口。

## 13. 阶段顺序与进入条件

Milestone 0～10 用于跟踪模块责任和完整验收。离线按 MySQL → DataX → Hive ODS → Spark DWD/DWS/ADS → Doris 逐段验收，实时按 MySQL Binlog → Flink CDC → Kafka → Flink DWD → Doris 逐段验收。进入某个 Stage 不等于对应 Milestone 的全部交付已完成，也不改变完整 Project 1 的最终验收范围。

1. **规格、环境和兼容性基线**：规格通过评审；阻断决策有记录；核心组件具备最小验证方案。
2. **OLTP 模型与数据生成器**：按当前 V2 基线确认业务过程、21 表字段、状态机、事实粒度和固定验收数据，并完成 DDL、Seed、Generator 与运行验收。
3. **离线抽取与 ODS**：DataX 将固定数据真实写入 HDFS batch staging，经 Validation / Publish 发布 Hive ODS ORC 分区，Hive 分区可见且失败返回非零状态。
4. **离线数仓 MVP**：Hive ODS 与 Spark DIM/DWD、DWS、ADS 在真实引擎执行并完成逐层对账。
5. **正式指标与质量**：V2 采用的指标具有稳定发布 ID、口径、血缘、固定样例和质量规则。
6. **服务与调度**：Doris 离线服务表和 DolphinScheduler T+1 DAG 通过重跑、补数和失败测试。
7. **Spark 性能实验**：完成倾斜、Join 和分区裁剪的可复现实验。
8. **实时设计评审**：确认 Topic、Schema、窗口、迟到、去重、维度、状态、Doris 模型、归档和阈值。
9. **实时链路与可靠性**：完成 CDC、Kafka、Flink、Doris、恢复及五项离实时对账。
10. **Project 1 面试发布**：所有简历表述均有代码和运行证据。
BI、Dashboard、SQL Assistant、LLM/Agent 和 Project 2 实现不属于当前 Project 1 范围，不在 M0～M10 中插入新的实施门禁。

2026-09-27 用户确认离线 100 单 Pilot 已完成使命并转为 History。2026-10-12 已完成正式源库 21 表部署、1,328,502 行装载与 45-rule Source Gate。2026-10-17 已完成正式终态 Snapshot 的 DataX/HDFS/Hive/Spark ODS Runtime 与 1,476 项独立 Gate，并完成临时权限回收；Seed `20260105` 的时间推进式 ODS 仍只验证到 Day 61。M3、M8、M9 的完整状态不因 Snapshot Bootstrap 通过而自动提升。

## 14. 验收标准

### 14.1 最小离线闭环

只有同时满足以下条件，离线闭环才能标记为 `verified`：

1. 固定 seed 数据能够重复生成相同业务输入。
2. DataX 将 MySQL 数据真实写入 HDFS ORC + Snappy batch staging，并由 Publish 按每行 `business_date` 发布 Hive ODS 业务日期分区。
3. Hive 能够注册并读取 ODS 分区，审计字段、源字段语义和批次发布结果符合已确认设计。
4. Spark on YARN 能够读取 Hive、完成 DIM/DWD、DWS 和 ADS 加工并写回 Hive。
5. 首次运行、同日重跑和连续业务日期回补没有不可解释的重复。
6. DataX、Spark 或质量任务失败时返回非零状态，调度不得误报成功。
7. 主键、行数、状态、金额和数量完成逐层对账。
8. Doris 离线服务结果与 Hive ADS 一致。
9. 版本、配置、命令、结果、日志位置和已知限制均有记录。

### 14.2 实时链路

实时链路只有在详细规格确认，并完成 Snapshot、Binlog 增删改、Kafka 生产消费、Flink 状态和 Checkpoint、任务中断恢复、Doris 写入及离实时对账后，才能从 `planned` 变为 `verified`。

配置 Checkpoint 或使用声称支持 Exactly-Once 的连接器，不等于本项目已经证明端到端 Exactly-Once。

### 14.3 交付 V1 展示与简历门禁

V1 可以在完整 V2 扩展前形成可展示版本，但必须同时满足：

1. 至少一条离线最小纵向链路在记录环境中执行，并完成源表、ODS、DWD/DWS/ADS 和 Doris 范围内对账。
2. 至少一条实时最小纵向链路完成 Snapshot 和一个可审计的 Binlog 变更，并核对 Kafka、Flink Checkpoint/YARN 状态与 Doris 结果。
3. 仓库内的脚本和 SQL 显式接收业务日期、环境参数或运行批次，失败返回非零，不包含 Secret、真实公网地址或不受限的清理操作。
4. README 能导航到架构、运行入口、验收记录、已知限制和回滚方式；新环境的复现步骤不依赖 `.local-notes/`。
5. 简历仅写已有代码、命令、日志摘要、截图或对账结果支持的能力和数字；V2 规划不写成 V1 成果。

规模扩展前，必须先让正式数据规模通过业务验收，再结合实际运行数据确认瓶颈、验收指标和资源上限；性能实验规模不能在正式数据规模尚未通过时提前替代业务验收。

## 15. 状态、安全与配置规则

状态定义：

| 状态 | 含义 |
| --- | --- |
| `draft` | 规格或口径仍待评审 |
| `candidate` | 已选为候选，但版本或实现尚未通过真实验证 |
| `planned` | 只保留目标和进入条件，尚未完成详细设计 |
| `implemented` | 实现已进入仓库，但未完成全部运行验收 |
| `verified` | 已在记录的环境和版本中完成安装、启动、连通、执行和结果核对 |

安全规则：

- 不提交密码、密钥、Token、`.env`、真实生产地址、个人数据和原始运行日志。
- 仓库只记录环境变量名和去敏示例。
- 组件端口默认只允许 VPC 私网访问；公网访问必须单独评审。
- MySQL CDC、Doris、Hive 和调度器使用独立最小权限账号。
- Project 2 的查询身份必须是只读身份。
- 未锁定依赖不得使用 `latest`、浮动版本或动态下载地址。

## 16. DECISION_REQUIRED

以下内容尚不知道或尚未确认，进入对应阶段前必须询问用户，不得由实现者自行补全：

历史 M2 决策与实现已经整体归档，不自动决定当前 V2 的 21 表实现。当前仍需确认：
- 当前实时链路已确认实际开发 Topic、订单 DWD 代码/构建/提交、Doris 表模型、两作业 Checkpoint 恢复与正常顺序订单 Upsert；仍须确认当前 YARN/Flink/BE 状态、21 表全字段、乱序/物理 DELETE、R2 更新恢复、完整对账及正式 Topic/Schema。完成这些验收和 M8 评审前不得将 M9 提升为完整 `verified` 或扩展到其他实时表和指标。
- 21 表 DDL、正式装载与 Source Gate 已通过 Runtime 验收；后续结构变更仍需逐项记录与重新验收。
- 21 表的状态分布、跨表关系、依赖和生成顺序已由 45-rule Source Gate 验证；更大性能实验规模仍为 `DESIGNED / not_run`。
- 现有正式 Business / Behavior Generator 的确定性 Seed、显式时间范围、输出 Contract 与失败行为已完成对应证据范围验收；Seed `20260105` 的 Business Bootstrap、30 个 Daily Package、Manifest、预期结果和 r6 Day 60～90 MySQL Runtime 已验证，当前 worktree 重生成的 146 个文件与 r6 复现相同 Business Hash、Replay Manifest 和 Package Manifest。Behavior Bootstrap、30 个 Daily Package、Manifest、Hash 和实体/时间审计仍只完成本地验证；Kafka 写入、依赖锁定和跨链路 Runtime 仍待实现或验收。
- `LOAD DATA` 的文件格式、装载顺序、事务/失败边界与 Source Gate 入口已实现并验收；非空目标的重跑按设计 fail-fast，任何重置方案仍须单独批准。
- `ecommerce_ods`、`ecommerce_dwd` 中 Pilot 数据的精确隔离/重置对象、备份、验证和回滚方式；未经单独授权不得执行清理。
- `BI / Agent` 是否进入当前 V2 正式交付，还是继续遵循 `DR-029` 作为 M0～M10 之后规划。
- 正式源库的回滚/重置方法及其备份边界仍需在发生重跑需求时单独设计和批准。
- SKU 最小库存属性及第一期是否执行简单扣减。
- 订单匿名/注册身份互斥 CHECK 已部署并验收；完整 guest checkout 产品边界仍待确认。
- 支付/退款回调去重保留范围、状态 JSON 演进契约；订单/优惠券单向 FK 与 Source Gate 反向引用校验已验收，后续契约变化必须重新验证。
- 当前 21 表状态枚举、NOT NULL/default、外键策略与生成列已部署并通过 Source Gate；业务服务并发锁顺序、扩展状态和零元订单处理仍待确认。
- V2 指标检索编号是否直接作为稳定发布 ID，以及复购率、部分退款比例、券核销率、细分漏斗和 30 日退款率的待细化口径。
- SCD2 的 60 天初始化、30 天增量维护及迟到修正原则已由 `DR-037` 确认；精确 `dim_*` 表、跟踪属性和实时维度物理实现仍须在 Milestone 4/8 实施前冻结。
- 性能实验的并发模型、实时事件速率、资源上限和具体执行参数；性能实验规模本身已于 2026-10-11 确认。
- HDFS/Hive、Kafka 和 Doris 的保留周期。
- Topic 划分、Partition、Schema 和重放策略。
- Flink 作业拆分、窗口、Watermark、允许迟到、去重键、状态 TTL 和补偿规则。
- Checkpoint、Savepoint、重启和端到端一致性目标。
- Doris 实时表 Key 模型、分区、分桶和更新语义。
- 实时明细是否长期归档到 HDFS/Hive。
- 实时与离线对账阈值。
- DolphinScheduler 3.4.2 的 MySQL Metadata Schema、ZooKeeper Registry、Master/Worker/API/Alert、失败识别、重试和补数行为。
- 未在 `DR-026` 中锁定的后续 Connector 补丁版本及兼容失败后的调整方案。
- hadoop201 是否需要扩容。

未解决事项应保持 `draft`、`candidate` 或 `planned`，不得通过默认值伪装为正式决策。
