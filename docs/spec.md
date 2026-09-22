# 电商离实时一体化数据仓库项目规格

版本：`0.4-draft`
状态：Milestone 0 `completed`；Milestone 1 `in progress`；Milestone 2 `in progress`（V2 业务与源模型重设计）
更新时间：2026-09-20
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
- 在离线主线稳定后，建设基于 Kafka、Flink CDC、Flink 和 Doris 的实时链路。
- 使用 DolphinScheduler 管理依赖、业务日期、失败重试、补数和质量阻断。
- 使用固定输入、预期输出、质量规则和故障实验证明实现结果。
- 区分开发环境方案和生产环境实践，不伪造高可用、Exactly-Once、吞吐或性能提升。

Project 1 是主要面试项目。建议讲述权重：

```text
Project 1：65%
Project 2：35%
```

Project 2 必须等待 Project 1 完成并稳定后再开始，且不得重新定义 Project 1 的业务语义。

## 2. 参考来源与采纳边界

本规格参考《数据开发求职项目总规格 V1.4》，但不整篇照搬。

| 项目 | 处理方式 |
| --- | --- |
| 项目名称、文档使用范围框架 | 采用，并调整为仅适用于 Project 1 |
| 两项目关系及 65% / 35% 比例 | 作为交接约束保留 |
| MySQL、Hadoop/Hive、Spark、Kafka、Flink、Doris、DolphinScheduler 技术方向 | 作为目标技术栈保留 |
| DataX 直接写正式 ODS ORC | 采用；使用 HDFS Writer 写入 Hive ODS 对应 HDFS 分区，分区注册、审计字段、幂等发布和失败隔离由 ODS 装载负责，真实行为在 Milestone 1、3 验证 |
| 参考文件中的候选版本 | 不直接锁定；必须重新完成兼容性和启动验证 |
| 实时 Topic、窗口、迟到处理、维度和 Doris 表模型 | 暂不采用具体设计，保留为实时阶段待决策项 |
| Project 2 业务和应用实现 | 不迁入，只保留六个只读契约 |

采用理由是保留数据开发岗位中具有代表性的完整链路，同时降低一次性引入过多未验证实现的风险。

本次验证仅包含规格内容和结构的静态检查，不代表任何组件已经安装、启动、连通或完成数据对账。需要回滚时，只恢复本次修改前的 `docs/spec.md`；不得因此修改或删除其他用户文件。

## 3. 范围与非目标

### 3.1 V1 业务范围

当前业务基线采用自营商城两期方案。第一期覆盖用户与匿名身份、Category/SPU/SKU、商品展示与行为、购物车、下单与取消、订单券、支付和基础退款，形成可核对的交易与资金闭环；第二期再扩展库存流水/快照、完整履约物流、复杂营销和更完整售后。当前正式业务规则入口为 `docs/business/business-baseline-v2.md`。

分析范围覆盖交易与资金、流量与转化、商品、用户、退款与售后、营销。交易状态由模拟业务服务写入 MySQL，业务交易 CDC 只来自 MySQL Binlog；页面、商品和购物行为由独立行为源写入 Kafka，不得由生成器直接写 Kafka 冒充 CDC。

当前源模型目标为 21 张 `biz_*` MySQL 表及独立行为事件流。逻辑模型见 `docs/source/logical-model-v2.md`，字段级候选物理设计见 `docs/source/physical-model-v1.md`。候选设计及仓库 DDL 不保证与现存 MySQL 结构一致；隔离库历史验收不得外推为正式库或完整链路验收。

### 3.2 当前非目标

- 第一期不建设完整库存域或库存流水；SKU 最小库存属性与是否扣减仍需在正式 DDL 前确认。
- 当前阶段不确定实时 Topic、窗口、Watermark、迟到、状态 TTL、维度关联和 Doris 实时表模型。
- 不建设生产级 Hadoop HA，也不将三节点开发环境描述为高可用集群。
- 不引入阿里云专有中间件、Kafka ZooKeeper 模式、Spark Standalone、Flink Standalone、Kubernetes、HBase、Redis、Elasticsearch、ClickHouse、Iceberg、Hudi 或 Paimon。
- 当前 M0～M10 不实现 DataOps、AI 服务或前端；BI/Dashboard/Agent 只列入后续数据应用规划，其仓库归属与实施门禁另行评审。
- 不预设百万级、QPS、延迟、Exactly-Once 或性能提升数字。

### 3.3 Milestone 1 与 Milestone 2 并行推进

`DR-008` 允许 M1 与 M2 分轨推进，但不取消直接依赖。上一版 M2 的设计与验收材料已整体迁入 `docs/archive/milestone-2-business-design.md`，不在当前规格中继续展开。

2026-09-18 的 V2 业务重设计不沿用归档实现作为当前模型依据。当前采用 21 张 `biz_*` 表的候选设计、独立行为事件流和新版指标口径，Milestone 2 保持 `in progress`。旧 19 表归档验证不能证明 V2 实现。后续用户提供的 2026-09-19～20 历史摘要记录了新 21 表隔离验收库的限定范围结果；它不证明正式源库、固定 Seed、90 天数据、DataX 接续或 M2 完成。

Milestone 3 所需的 HDFS/Hive/DataX 技术组合已有环境验证，但当前 M2 的正式 DDL、固定数据和抽取语义尚未闭合，M3 进入门禁未满足。

### 3.4 当前业务语义基线

`docs/business/business-baseline-v2.md` 是当前业务规则入口，核心约束包括：

- 身份：匿名访客与注册用户分离，只在可靠证据下建立可版本化映射；歧义事件保持匿名，不能静默覆盖历史结果。
- 会话与漏斗：同一访客按事件时间连续 30 分钟无活动开启新会话；同时保留自然日经营漏斗和 7×24 小时同群组漏斗。
- 商品与订单：Category 1:N SPU 1:N SKU；每单 1～5 个不重复 SKU，订单明细冻结成交时商品与金额快照；第一期不拆单。
- 购物车：登录合并按 SKU 数量相加，单 SKU 上限 99，超限裁剪并记录；相同合并操作重试不得再次累加。
- 订单与支付：订单状态为 `CREATED / PAID / CANCELED`，支付有效期 15 分钟；允许失败重试，但每单最多一次有效成功支付。
- 退款：一笔申请只关联一条订单明细，可多次资金尝试，但申请最终完整成功或失败；纯金额补偿不能反推退款件数。
- 优惠券：订单级最多一张固定金额券；锁定覆盖订单支付期限，取消时释放或过期，支付后 `USED`，退款不返券。
- 金额：源候选模型统一使用整数分，订单头、明细、优惠分摊、支付和退款必须满足守恒，不使用浮点财务金额。

### 3.5 当前逻辑与候选物理模型

当前逻辑模型见 `docs/source/logical-model-v2.md`，字段级候选物理设计见 `docs/source/physical-model-v1.md`。21 张候选 MySQL 表按以下七组组织：

- 用户与身份 3 张：`biz_user`、`biz_visitor`、`biz_identity_mapping`。
- 商品 4 张：`biz_category`、`biz_spu`、`biz_sku`、`biz_product_change_event`。
- 购物车 3 张：`biz_cart`、`biz_cart_item`、`biz_cart_merge_record`。
- 订单 3 张：`biz_order`、`biz_order_item`、`biz_order_status_event`。
- 支付 2 张：`biz_payment_attempt`、`biz_payment_event`。
- 退款 3 张：`biz_refund_request`、`biz_refund_transaction`、`biz_refund_event`。
- 优惠券 3 张：`biz_coupon_template`、`biz_coupon`、`biz_coupon_event`。

行为事件不计入 21 张 MySQL 表，逻辑上包含页面浏览、商品曝光、商品点击、加购和移除，至少保留稳定事件键、事件时间、采集时间、访客/用户、会话及按事件适用的 SKU、页面和数量字段。精确 Kafka Schema、Topic key 和保留策略仍待实施设计。

21 表设计仍为 `candidate`：仓库 `mysql/ddl/001_ecommerce_oltp_v1.sql` 与 `docs/source/M2-03-物理设计与静态审查.md` 记录的是当时已生成、静态通过但未执行的快照。用户提供的后续摘要记录了隔离验收库 19 张非空表共 32 条初始 Snapshot、两张原空表的 INSERT/DELETE 探针，以及 10 单和 100 单批次的订单 CDC 核对；这是限定范围的历史验收，不是仓库 DDL 与当前 MySQL 逐字一致的证明。新生成器文件已入库，但显式业务日期、重跑契约和精确依赖版本未定；固定 Seed、90 天规模、DataX/CDC 初始化接续及正式源库验收均未完成。正式实施前仍需收敛 SKU 库存属性、订单身份、回调去重、状态 JSON、循环 FK、状态枚举与零元订单等问题。

### 3.6 历史材料边界

旧 19 表设计保留在 `docs/archive/milestone-2-business-design.md`，对应 Seed、Generator、脚本和测试位于 `archive/legacy-m2-19-table/`。这些归档内容不作为当前 21 表的实现依据，也不直接满足 M2/M3 门禁；不得混用旧表名、字段和指标编号。

### 3.7 CDC 环境验收边界

`docs/acceptance/env-05-cdc-acceptance.md` 记录了 MySQL 8.0.46 测试表 `cdc_acceptance.probe_order` 经 Flink CDC 3.6.0-1.20、Flink 1.20.5 和 Kafka 3.9.1 的隔离验收：Snapshot、Binlog INSERT/UPDATE/DELETE、HDFS Checkpoint、一次 TaskManager 故障恢复及恢复后继续采集均为 `CONFIRMED`。

该结论只适用于指定测试表和故障场景，不证明 21 张正式业务表 CDC、三组行为 Topic、90 天初始化接续、端到端 Exactly-Once、性能目标或完整离实时对账。

另据用户提供的 2026-09-19～20 终端结果摘要，隔离验收库的 21 表 CDC 初始快照和两张原空表探针有有限范围记录；`smoke-v1-001` 为 10 单 34 明细，`hist-v1-001` 为 100 单 319 明细，订单 CDC 创建与最终状态分别核对。摘要未入库，且本次未重新连接 VM、未运行导入的 `.sh`；这些历史结果不证明当前在线状态、逐表完整 CRUD、正式 Topic、端到端 Exactly-Once、Hive ODS 或 Doris 业务层。

### 3.8 当前模型状态总结

| 范围 | 状态 | 证据边界 |
| --- | --- | --- |
| V2 业务规则 | baseline | `docs/business/business-baseline-v2.md`；不是业务系统上线证明 |
| V2 逻辑模型 | design archive | `docs/source/logical-model-v2.md`；不是 SQL 或部署证据 |
| 21 表候选物理模型 | `candidate` | 字段设计、仓库候选 DDL 和 `M2-03` 静态快照；与现存 MySQL DDL 未做逐字核对 |
| V2 Generator | `implemented`（文件级） | `mock/generator/ecommerce_generator_v1/`；日期默认行为与依赖版本待决，未作为正式批任务验收 |
| 21 表隔离验收历史 | 限定范围的用户提供结果 | 2026-09-19～20 摘要；不代表当前在线状态或正式链路通过 |
| V2 指标体系 | `draft` / 部分待细化 | `docs/metrics.md`；尚无 DWS/ADS SQL 或引擎结果 |
| ENV-05 CDC | `CONFIRMED`（限定范围） | 单隔离测试表与指定故障场景，不外推正式 21 表 |

## 4. 技术栈与开发方式

选型结论：MySQL、Hadoop/Hive、Spark、Kafka、Flink、Doris 和 DolphinScheduler 构成了数据开发岗位中辨识度较高的经典开源技术组合，能够覆盖本项目计划展示的离线、实时、服务和调度能力。这里的“主流”表示技术方向和岗位能力具有代表性，不表示所有组件都采用最新版本；当前版本兼容与临时链路的实际结论以 `DR-026` 为准。DataX 属于成熟的传统离线同步工具，本项目保留它用于批量抽取，并通过 HDFS Writer 直接写入 Hive ODS 对应的 HDFS 分区；ORC + Snappy 与失败非零的技术能力已验证，正式分区发布、审计、幂等和失败隔离仍由 Milestone 3 验收。

| 职责 | 技术 | 当前状态 |
| --- | --- | --- |
| 业务数据源 | MySQL | verified；8.0.46、私网连接、ROW/FULL Binlog 与受控重启已通过 |
| 离线抽取 | DataX | verified；202309 运行包的 MySQL Reader、HDFS Writer、ORC 输出和失败返回已通过；正式 ODS 行为留在 M3 |
| 分布式存储与资源管理 | Hadoop HDFS、YARN | verified；固定 HDFS 文件、MapReduce、聚合日志和受控重启已通过 |
| 数仓元数据与 SQL | Hive | verified；3.1.3、MySQL Metastore、HiveServer2、Beeline 与 ORC 访问已通过 |
| 离线计算 | Spark SQL、PySpark，运行于 YARN | verified；Spark 3.5.9 on YARN 可读写 Hive/HDFS ORC |
| 消息传输 | Kafka KRaft | verified；Kafka 3.9.1 三节点 Quorum、生产消费、ISR 与单 Broker 恢复已通过 |
| CDC 与实时计算 | Flink CDC、Java DataStream Jar + YARN Application Mode；SQL Client + YARN Session 用于技术验证 | 组件兼容性 verified；Application Mode、Flink CDC 和 YARN Session Kafka Source/Sink 已通过，正式业务实时链路仍为 planned |
| 分析服务 | Doris | verified；4.0.8 FE/BE、SQL 与受控重启已通过 |
| 工作流调度 | DolphinScheduler | candidate；3.4.2 尚未完成 M1 验收 |
| 数据生成和质量工具 | Python、SQL | V2 Generator 与验收辅助文件已入库，文件级 `implemented`；固定 Seed、批处理契约与 Runtime 仍未完成 |

开发方式：

- Spark SQL 负责主要离线转换；只有 SQL 不适合表达的复杂逻辑才使用 PySpark。
- 正式 Flink 业务 ETL 与聚合作业采用 Java DataStream Jar + YARN Application Mode；Flink SQL Client + YARN Session 仅保留为 Kafka SQL 技术验证，不作为正式业务部署模式。该选择不提前确定窗口、状态或指标实现。
- Python 用于固定 seed 数据生成器和轻量质量工具。
- 当前 `mock/generator/ecommerce_generator_v1/` 仍允许缺省 `--anchor` 并使用执行时刻；其依赖版本也未锁定。在日期契约及精确版本获确认前，该目录只作待完善实现，不作为符合本节批任务要求的正式入口。
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

总体技术路线见[最终工程架构 V1.0](final-architecture-v1.0.md)；节点、源系统和实时作业的责任分别见[部署拓扑](deployment-topology.md)、[业务源设计](business-source-design.md)和[实时链路规范](realtime-pipeline-design.md)。这些文档只按各自证据范围解释，不改变本规格的 Milestone 门禁。

### 5.1 离线主线

```text
MySQL ecommerce_oltp
        │
        │ DataX 全量或基于 update_time 的增量抽取
        ▼
Hive ODS
HDFS 业务日期分区，ORC + Snappy
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

- DataX 使用 HDFS Writer 直接写入 Hive ODS 对应的 HDFS 业务日期分区，不建设独立持久化的中间数据层。
- Hive ODS 同时表示 Hive 逻辑表和其 HDFS 物理存储；ODS 装载负责分区注册、审计字段、幂等发布和失败隔离。
- DataX 不负责决定正式金额精度、状态枚举或最终 Hive 字段类型；这些内容必须随源模型和 ODS 设计确认。
- Hive ODS 保留源字段语义，并包含 `business_date`、`extract_time`、`batch_id` 和 `source_table` 等审计字段；最终字段以源模型评审结果为准。
- DataX HDFS Writer 的 ORC/Snappy、Hive 分区可见性、审计字段写入和失败行为必须在 Milestone 1、3 真实验证，当前仅为已采用架构。
- 正式 ODS、DIM、DWD、DWS、ADS 使用 ORC + Snappy。
- ODS 保留源语义；DWD 保存原子事实；DIM 保存一致维度；DWS 保存可复用的可加度量和比率分子/分母；ADS 负责最终指标表达。
- 离线 ADS 默认通过 Spark Doris Connector 写入 Doris，具体 Connector 版本必须经过 Spark、Scala、Java 和 Doris 兼容性验证。
- DolphinScheduler 只能在离线任务独立运行通过后接入，负责业务日期、依赖、重试、回补、质量阻断、Doris 装载和对账，不承载业务计算逻辑。
- DataX 基于 `update_time` 的增量抽取不能天然捕获硬删除。进入 OLTP 设计前必须确认使用软删除或状态字段，或者增加周期性全量快照和删除对账。

### 5.2 暂缓细化的实时目标链路

```text
MySQL Binlog
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

该链路当前只表示目标架构。Flink CDC 是运行在 Flink 上的采集任务，不是独立于 Flink 的常驻平台。实时部分在完成单独评审前保持 `planned`，不得生成正式业务作业或宣称已经实现。

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

Doris 4.0.8 的受控重启恢复已通过，`docs/final-architecture-v1.0.md` 中的 Step 11 已按此事实修正。Hive 3.1.3 当前在 Java 17 环境通过验收；不能把 Java 11 的设计偏好记成 Hive 已切换的事实。

## 9. 数据生成、任务参数与幂等

采用双数据集：

- 验收数据集：规模小、固定 seed、逐层结果可人工核对。
- 基准数据集：规模、并发和实时产生速率可配置，具体数值在资源实测后决定。

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

本次并入的 Generator 尚未符合上述全部条件：`--anchor` 可省略，重复 run-id 会拒绝执行，`pyproject.toml` 仍使用浮动范围。代码文件的存在与历史批次运行结果不能替代这些契约的确认和验收；在确认前不安装未锁定依赖、不将其作为正式批任务。

## 10. 指标范围与编号

当前指标口径唯一入口为 `docs/metrics.md`。V2 按六个域提供 47 个检索条目：交易与资金 `TR-01`～`TR-14`、流量与转化 `TF-01`～`TF-08`、商品 `PR-01`～`PR-05`、用户 `US-01`～`US-06`、退款与售后 `RF-01`～`RF-07`、营销 `MK-01`～`MK-07`。

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

## 12. Project 2 只读交接契约

Project 1 是业务语义、SQL、指标和运行结果的唯一事实来源。保留以下六个只读契约：

| 契约编号 | Project 1 提供内容 | 当前状态 |
| --- | --- | --- |
| `P1-METADATA-01` | MySQL、Hive、Doris 的库表字段、逻辑层、物理存储、分区和保留策略 | draft |
| `P1-LINEAGE-01` | 进入 Git 的真实 SQL、任务依赖和层级映射 | draft |
| `P1-METRIC-01` | 已发布指标的稳定 ID、名称、公式、粒度、维度、时间口径、来源、版本和状态 | draft；V2 检索编号尚未确认是否直接作为发布 ID |
| `P1-QUALITY-01` | `data_quality_result` 的规则、对象、期望值、实际值和状态 | draft |
| `P1-RECONCILIATION-01` | `reconciliation_result` 的实时值、离线值、差异和状态 | draft |
| `P1-TASK-01` | DolphinScheduler 工作流、任务状态、时间、耗时、失败日志和依赖 | draft |

Project 2 不得：

- 回写 Project 1 的业务数据和结果表。
- 修改指标名称、公式、粒度或状态。
- 自行推断不存在的血缘。
- 重复实现第二套质量执行引擎。
- 把样例 SQL、候选结果或未验证数据描述为正式事实。

具体 REST 路径、认证方式和序列化结构只有在真实服务确定后才能进入稳定契约，本规格不虚构接口实现。

## 13. 阶段顺序与进入条件

1. **规格、环境和兼容性基线**：规格通过评审；阻断决策有记录；核心组件具备最小验证方案。
2. **OLTP 模型与数据生成器**：按当前 V2 基线确认业务过程、21 表字段、状态机、事实粒度和固定验收数据，并完成 DDL、Seed、Generator 与运行验收。
3. **离线抽取与 ODS**：DataX 将固定数据真实写入 Hive ODS 对应的 HDFS ORC 分区，Hive 分区可见且失败返回非零状态。
4. **离线数仓 MVP**：Hive ODS 与 Spark DIM/DWD、DWS、ADS 在真实引擎执行并完成逐层对账。
5. **正式指标与质量**：V2 采用的指标具有稳定发布 ID、口径、血缘、固定样例和质量规则。
6. **服务与调度**：Doris 离线服务表和 DolphinScheduler T+1 DAG 通过重跑、补数和失败测试。
7. **Spark 性能实验**：完成倾斜、Join 和分区裁剪的可复现实验。
8. **实时设计评审**：确认 Topic、Schema、窗口、迟到、去重、维度、状态、Doris 模型、归档和阈值。
9. **实时链路与可靠性**：完成 CDC、Kafka、Flink、Doris、恢复及五项离实时对账。
10. **Project 1 面试发布**：所有简历表述均有代码和运行证据。
11. **Project 2**：只消费 Project 1 已稳定发布的只读契约。

BI/Dashboard/Agent 仅为 M0～M10 之后的数据应用规划，不在本阶段顺序中插入新的实施门禁；其归属、安全、接口和验收需另行评审。Project 2 当前的只读边界不变。

`DR-008` 只允许 Milestone 1 与 Milestone 2 按分轨门禁并行。除此之外，上一阶段的阻断项未解决时不得进入下一阶段；Milestone 3 及后续阶段的进入条件没有改变。

## 14. 验收标准

### 14.1 最小离线闭环

只有同时满足以下条件，离线闭环才能标记为 `verified`：

1. 固定 seed 数据能够重复生成相同业务输入。
2. DataX 将 MySQL 数据真实写入 Hive ODS 对应的 HDFS ORC + Snappy 业务日期分区。
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
- 新 Generator 的显式业务日期或起止时间、同日重跑/回补语义，以及经验证的精确 Python 依赖版本。
- 当前 MySQL 的 `SHOW CREATE TABLE` 与仓库候选 DDL 的差异，以及隔离验收结果如何映射到正式源库门禁。
- SKU 最小库存属性及第一期是否执行简单扣减。
- 订单匿名/注册身份互斥规则、guest checkout 边界和精确 CHECK。
- 支付/退款回调去重保留范围、状态 JSON 演进契约、订单与优惠券循环 FK 建立顺序。
- 21 表完整状态枚举、NOT NULL/default、外键策略、生成列、锁顺序与零元订单处理。
- V2 指标检索编号是否直接作为稳定发布 ID，以及复购率、部分退款比例、券核销率、细分漏斗和 30 日退款率的待细化口径。
- 拉链维度及实时维度历史策略。
- 基准数据规模、并发和实时事件速率。
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
