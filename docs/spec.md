# 电商离实时一体化数据仓库项目规格

版本：`0.3-draft`
状态：Milestone 0 `completed`；Milestone 1、2 `in progress`
更新时间：2026-09-11
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

V1 覆盖五个主题：

- 用户：注册、登录、用户类型、新增、活跃和回流。
- 流量：渠道、会话、页面访问、访问时长、跳出和小时分布。
- 商品：品牌、品类、SPU 和商品详情浏览。
- 交易：加购、下单、支付、取消、退单或退款。
- 营销：优惠券领取、使用和补贴。

具体 OLTP 表、字段、状态机、事实粒度和业务规则必须在进入源数据设计前确认，不得根据指标名称反推并直接生成正式 DDL。

### 3.2 当前非目标

- V1 不建设库存域。
- 当前阶段不确定实时 Topic、窗口、Watermark、迟到、状态 TTL、维度关联和 Doris 实时表模型。
- 不建设生产级 Hadoop HA，也不将三节点开发环境描述为高可用集群。
- 不引入阿里云专有中间件、Kafka ZooKeeper 模式、Spark Standalone、Flink Standalone、Kubernetes、HBase、Redis、Elasticsearch、ClickHouse、Iceberg、Hudi 或 Paimon。
- 不在 Project 1 中实现 DataOps、AI 服务或前端。
- 不预设百万级、QPS、延迟、Exactly-Once 或性能提升数字。

### 3.3 Milestone 1 与 Milestone 2 并行推进

用户已通过 `DR-008` 确认 Milestone 1 与 Milestone 2 同时进入 `in progress`。Milestone 编号继续表示交付和运行依赖，但不要求业务规划等待整个集群安装完成。M1 按既有组件门禁推进；M2 按 `docs/plan.md` 的 M2.1 至 M2.5 小计划推进，先在本地完成业务语义、逻辑/物理模型、固定验收数据和数据生成器设计与实现准备。

并行不等于取消直接依赖。M2.1 至 M2.4 可以在不启动云端数据链路的情况下依次推进；未确认的业务规则必须保留为 `DECISION_REQUIRED`，不得使用经验默认值补全。M2.5 的 MySQL 执行验收必须等待 MySQL 通过 M1 的版本、启动、连接、Binlog 和重启验证。M2 无需等待 Hive、Kafka、Spark、DataX、Doris、DolphinScheduler 或 Flink 全部完成即可推进，但任何未在 MySQL 真实执行的 DDL、seed、生成器或测试只能标记为 `draft` 或 `implemented`，不得标记为 `verified`。

Milestone 3 的进入条件保持不变：既要取得 M2 已确认的 OLTP DDL 和固定数据，也要等待 M1 的 HDFS、Hive、DataX 组合通过验证。M2 本地工作不得修改 ECS 服务或 M1 配置，也不得把静态检查描述为运行证明。

### 3.4 已确认的身份、会话与用户分类语义

`DR-009` 已确认 `M2-DEC-001` 至 `M2-DEC-003`，作为后续 OLTP 模型和指标口径的基础语义：

- 身份：`visitor_id` 与 `user_id` 分离；一个用户允许关联多个 `visitor_id`。登录前事件保留匿名身份且不追溯改写，登录后事件同时记录当时的 `visitor_id` 和 `user_id`，登录动作本身不切断当前会话。
- 会话：连续 30 分钟无活动后，新事件开始新会话；跨 `Asia/Shanghai` 自然日强制切分会话。会话渠道取会话首次进入渠道，会话内渠道变化不拆分会话。
- 访客分类：`visitor_id` 的首次访问日期等于业务日期时为新访客，早于业务日期时为老访客；两类互斥。
- 用户分类：注册日期等于业务日期时为新增用户；业务日期内至少产生一次带 `user_id` 的访问、加购、下单或支付行为时为活跃用户；此前活跃、连续 7 个完整自然日未活跃并在业务日期再次活跃时为回流用户。新增用户与回流用户互斥，活跃用户集合可以包含新增用户和回流用户。
- 首次转化：新增下单人数按个人首次有效订单发生日期识别，新增支付成功人数按个人首次成功支付发生日期识别。这里的“有效订单”和“成功支付”仍分别依赖订单、支付及状态机决策，不在本节提前定义。

上述内容只确认业务语义，不直接确定指标公式或实时身份合并策略。用户与流量源表字段及页面分类已由 `DR-014` 确认；订单有效状态和支付成功状态已由 `DR-011` 确认，其余物理模型按 M2.2 后续批次继续设计。

### 3.5 已确认的商品、加购与订单语义

`DR-010` 已确认 `M2-DEC-004` 至 `M2-DEC-006`，作为商品和交易主题后续建模的基础：

- 商品层级：Category 使用三级结构；SPU 归属一个 Brand 和一个末级 Category，一个 SPU 可以包含多个 SKU。SKU 是商品详情浏览、加购和交易的最小商品单位。
- 历史归属：订单明细保存下单时的 Brand、Category、SPU 和 SKU 快照；商品主数据后续变化不改写历史订单的归属。
- 加购粒度：一行加购事件表示一个行为主体对一个 SKU 的一次操作，区分新增、修改数量和移除，并保留操作前、操作后数量。相同 `request_id` 的重复请求只生效一次；数量为非负整数，移除后的数量为 0。
- 加购主体：事件发生时已登录则使用 `user_id`，匿名则使用 `visitor_id` 作为人数去重主体；不追溯合并登录前行为。
- 订单粒度：V1 只有注册用户可以下单。一次结算生成一个订单头，一种 SKU 生成一条订单明细；一个订单允许多条明细，但不进行仓库、商家或物流拆单。
- 订单业务键与幂等：`order_no` 和 `order_item_no` 分别是订单头和订单明细业务键；相同下单 `request_id` 的重复提交返回原订单，不创建新订单。订单明细数量为正整数。

上述结论定义业务粒度和关系。商品源表字段与索引方向已由 `DR-015` 确认，加购、订单和订单明细字段与索引方向已由 `DR-016` 确认；支付、取消、退单、退款与状态机已由 `DR-011` 确认；时间、金额和优惠券语义已由 `DR-012` 确认，支付、逆向交易和营销物理映射继续留在 M2.2。

### 3.6 已确认的支付、逆向交易、状态机与删除语义

`DR-011` 已确认 `M2-DEC-007` 至 `M2-DEC-010`：

- 支付：一个订单允许多次支付尝试，但最多一次成功；V1 不支持分次支付，成功支付金额必须等于订单应付金额。每次尝试使用独立 `payment_no`，相同 `request_id` 只创建一次。重复回调不得重复记成功或修改首次成功时间；支付成功人数按 `paid_at` 所属业务日期对 `user_id` 去重。
- 取消：只有未支付的 `CREATED` 订单可以取消；支付成功后不得取消，只能进入退单与退款流程。
- 退单：退单业务单与资金退款分离。一条退单记录作用于一条订单明细，允许部分数量和多次退单；累计退单数量不得超过原购买数量。退单指标使用原订单明细保存的商品归属快照，退单数以完成的退单业务单为基础，不按退款流水计数。
- 退款：退款关联退单、原订单和原成功支付，允许多次部分退款；累计成功退款金额不得超过成功支付金额。
- 状态机：订单采用 `CREATED`、`PAID`、`CANCELLED`、`PARTIALLY_REFUNDED`、`REFUNDED`；支付尝试和退款尝试采用 `CREATED`、`SUCCESS`、`FAILED`；退单采用 `APPLIED`、`APPROVED`、`REJECTED`、`COMPLETED`。`CANCELLED`、`REFUNDED` 是订单终态，退单只有在关联退款成功后才能成为 `COMPLETED`。
- 状态规则：失败的支付或退款再次尝试时创建新的业务尝试记录。非法迁移必须拒绝且不修改原记录；每次合法状态变化都必须更新 `update_time`。
- 删除：用户、商品、订单、支付、退单、退款和优惠券禁止业务硬删除。主数据使用停用或软删除，交易数据保留原记录；加购事件保持 append-only，错误事件通过有效性标记处理。软删除或停用必须更新 `update_time`。
- 删除边界：V1 不建设周期性全量快照识别硬删除。固定测试数据只允许在隔离测试库整体重建，不能把清理操作当成业务删除。

订单应付金额、退款金额精度、舍入、事件时间和跨日归属已由后续 `DR-012` 确认。支付、退单和退款字段、生成列语义、单行状态组合及索引方向已由 `DR-017` 确认；Candidate DDL 已在 M2.2 `implemented` 并通过静态 Contract 检查，MySQL 运行验证仍留在 M2.5。

### 3.7 已确认的时间、金额与优惠券语义

`DR-012` 已确认 `M2-DEC-011` 至 `M2-DEC-013`，M2.1 的业务语义与状态机评审完成：

- 时间：所有业务时间统一按 `Asia/Shanghai` 解释并保留毫秒精度，MySQL 物理基线为 `DATETIME(3)`。业务日期分别由页面访问 `event_time`、加购 `action_time`、下单 `ordered_at`、首次成功支付 `paid_at`、取消 `cancelled_at`、退单完成 `completed_at`、成功退款 `refunded_at` 和注册 `registered_at` 计算。跨日过程按各自事件时间独立归属。
- 审计与到达：`create_time`、`update_time` 只表示记录审计时间，不替代指标业务时间；合法状态迁移必须更新 `update_time`，重复回调不得改变首次成功业务时间。数据到达时间与事件时间分离，迟到数据仍按事件时间归属；实时迟到处理留到 Milestone 8。
- 金额：V1 仅支持 `CNY`，MySQL 金额物理基线为 `DECIMAL(18,2)` 并使用 `HALF_UP`；价格含税、不单列税额，运费固定为 `0.00`。订单应付金额等于明细原价金额之和减去商品优惠和优惠券优惠，优惠不得超过原价，负数金额被拒绝。
- 优惠分摊：订单级商品优惠和优惠券优惠分别按明细原价比例分摊；舍入尾差按明细原价金额降序、`order_item_no` 升序依次分配，保证明细与订单金额守恒。
- 退款：部分退货使用累计法计算可退金额，本次退款等于累计可退金额减去此前成功退款金额；全部商品完成退款后，累计成功退款金额必须等于订单应付金额。
- 优惠券：V1 只支持带最低订单原价门槛的固定金额券。仅注册用户可领取和使用，一个订单最多一张券，一个领取实例最多成功使用一次；状态使用 `CLAIMED`、`LOCKED`、`USED`、`EXPIRED`。未支付取消时按是否过期释放或失效，支付成功后不因退单或退款返还。
- 补贴率：`P1_METRIC_030` 按 `paid_at` 业务日期统计毛补贴率，分子为成功支付订单的优惠券优惠金额，分母为同批订单商品原价金额；后续退款不追溯修改。分母为零输出 `0`，比率保留 4 位、百分比展示保留 2 位，均使用 `HALF_UP`。

优惠券与领取实例的物理字段、金额及有效期快照、状态时间组合和索引方向已由 `DR-018` 确认。Candidate DDL 已 `implemented` 并通过静态 Contract 检查；M2.4 Candidate Generator 已实现本地 Python 跨行规则和 Targeted Test，但正式 MySQL 写入层与指标 SQL 尚未实现，MySQL 运行验证仍须等待 M2.5 及其 M1 MySQL 门禁。

### 3.8 已确认的 OLTP 源表与约束基线

`DR-013` 已确认 `M2-DEC-014`、19 张 MySQL 源表及第一批公共物理规范。所有表均属于 MySQL 数据库 `ecommerce_oltp` 的 OLTP 业务源层：

- 用户与流量：`user_account`、`user_address`、`visitor`、`traffic_channel`、`visit_session`、`login_event`、`page_view_event`。
- 商品：`brand`、`category`、`spu`、`sku`。
- 交易：`cart_event`、`sales_order`、`sales_order_item`、`payment_attempt`、`return_order`、`refund_attempt`。
- 营销：`coupon`、`user_coupon`。

`visit_session` 只固定归属 `visitor`，登录事件关联访客、会话和用户；订单保存收货省份及商品归属快照。V1 不创建独立取消表或状态历史表，取消字段保存在 `sales_order`，当前状态、关键事件时间和 `update_time` 保存在对应业务表。

物理基线采用 `InnoDB`、`utf8mb4`、`BIGINT UNSIGNED AUTO_INCREMENT` 内部主键、唯一业务键、`DECIMAL(18,2)` 金额、`INT UNSIGNED` 数量、`DATETIME(3)` 时间、`CHAR(3)` 币种和 `VARCHAR(32)` 状态。状态使用 `CHECK`，不使用 MySQL `ENUM`；`request_id` 只要求在对应业务过程中唯一。主数据使用 `is_deleted` 和可空 `deleted_at`，交易与事件表禁止业务硬删除。

MySQL 负责主键、唯一、非空、核心外键、状态集合及单行金额/数量范围约束；同一订单最多一笔成功支付使用生成列和唯一索引。状态迁移、跨行累计退货/退款、优惠券流程、金额分摊和重复请求返回原对象由 Python 写入层负责。V1 不使用 Trigger 或 Stored Procedure。

正常 seed 只能包含合法数据；数据库约束拒绝场景在独立事务中执行并回滚，跨行或流程异常由 Python 写入层拒绝并返回非零状态。不得通过关闭外键或修改正式 DDL 注入异常。用户与流量 7 张表字段已由 `DR-014` 确认，商品 4 张表字段已由 `DR-015` 确认，正向交易 3 张表字段已由 `DR-016` 确认，支付与逆向交易 3 张表字段已由 `DR-017` 确认，营销 2 张表字段已由 `DR-018` 确认；全部 19 张表共 230 个字段、可命名约束/索引台账、生成列物理形式及建表顺序已按 `DR-020` 确认，Candidate DDL 已 `implemented` 并通过静态 Contract 检查。当前没有在 MySQL 创建任何业务表。

### 3.9 已确认的用户与流量源表字段

`DR-014` 已确认 `user_account`、`user_address`、`visitor`、`traffic_channel`、`visit_session`、`login_event` 和 `page_view_event` 的字段、可空性、关系、单行约束和索引方向。完整字段字典以 `docs/milestone-2-business-design.md` 8.4 节为准，核心边界如下：

- 内部主键统一使用 `<table>_pk`，业务键使用 `VARCHAR(32)` 并在各自表内唯一；子表通过 `*_pk` 外键关联，不冗余复制主表业务键。
- `user_account`、`user_address`、`visitor`、`traffic_channel` 是可更新的软删除主数据，保留 `create_time`、`update_time`、`is_deleted` 和可空 `deleted_at`。
- `visit_session` 归属一个访客和一个首次渠道，保留 `started_at`、`last_event_at`、可空 `ended_at` 以及审计时间，不直接绑定用户。
- `login_event` 只记录成功登录并关联事件发生时的访客、会话和用户；`page_view_event` 同时保留访客、会话、可空用户、事件渠道、页面类型、页面路径、可空 SKU 和 `event_time`。两张事件表保持 append-only，只保留 `create_time` 到达审计时间。
- 页面类型只允许 `HOME`、`PRODUCT_DETAIL`、`OTHER`。商品详情页必须关联 SKU，其他页面不得关联 SKU；未知或直接访问统一引用 `channel_code = 'DIRECT'` 的渠道字典记录，不使用空渠道。
- 所有外键采用 `RESTRICT`，不使用级联删除。MySQL 检查软删除字段一致性、事件时间先后和页面类型等单行规则；会话切分、首渠道、登录前后身份、访客/会话一致性及首末访问时间维护由 Python 写入层负责。
- 查询索引覆盖注册、首次访问、访客会话、渠道会话、登录用户、页面访问主体、渠道、页面类型、SKU 和事件时间；可变表使用 `(update_time, <table>_pk)`，append-only 事件使用 `(create_time, <table>_pk)` 支持增量抽取。

该确认不表示 MySQL 已执行。`page_view_event.sku_pk` 的外键目标已由 `DR-015` 确认，完整物理命名与依赖顺序见 `DR-020`；Candidate DDL 已 `implemented` 并通过静态 Contract 检查。

### 3.10 已确认的商品源表字段

`DR-015` 已确认 `brand`、`category`、`spu` 和 `sku` 的 35 个字段、可空性、关系、单行约束和索引方向。完整字段字典以 `docs/milestone-2-business-design.md` 8.5 节为准，核心边界如下：

- 四张表均使用 `<table>_pk` 内部自增主键和 `VARCHAR(32)` 唯一业务键，并保留 `create_time`、`update_time`、`is_deleted` 和可空 `deleted_at`。
- `category` 通过可空 `parent_category_pk` 建立自关联，`category_level` 只允许 1、2、3；Level 1 没有父节点，Level 2、3 必须有父节点。
- `spu` 归属一个 Brand 和一个 Level 3 Category；`sku` 归属一个 SPU，并保存当前 `sale_price DECIMAL(18,2)` 和 `currency CHAR(3)`。
- 所有外键使用 `RESTRICT`，不级联删除。MySQL 检查软删除组合、Category 层级与父节点空值组合、非负价格和 `CNY`；父子层级连续、Category 无循环及 SPU 只引用末级 Category 由 Python 写入层保证。
- 商品当前属性、归属和价格允许更新并刷新 `update_time`；历史订单使用后续订单明细快照，不因商品主数据变化而回写。
- 索引覆盖 Category 父子查找、Brand/Category 下的 SPU、SPU 下的 SKU 和四张表的 `update_time` 增量抽取。
- V1 不加入库存、商家、仓库、复杂规格 JSON、图片或搜索字段。

该确认使 `page_view_event.sku_pk → sku.sku_pk` 的外键目标完整，但仍不表示 MySQL 已执行。其余逐表字段已由 `DR-016` 至 `DR-018` 确认，完整物理命名与依赖顺序见 `DR-020`；Candidate DDL 已在 M2.2 `implemented` 并通过静态 Contract 检查。

### 3.11 已确认的正向交易源表字段

`DR-016` 已确认 `cart_event`、`sales_order` 和 `sales_order_item` 的 57 个字段、可空性、关系、单行约束和索引方向。完整字段字典以 `docs/milestone-2-business-design.md` 8.6 节为准，核心边界如下：

- `cart_event` 保留事件业务键、请求幂等键、事件时访客/会话/可空用户、SKU、动作类型、前后数量、有效性、无效原因、业务时间和到达审计时间；动作只允许 `ADD`、`CHANGE_QUANTITY`、`REMOVE`。
- 有效加购事件必须满足对应前后数量规则；无效事件必须填写原因并保留原始数量。相同 `request_id` 返回原事件，由 Python 写入层保证流程幂等。
- `sales_order` 保存下单用户、地址、可空优惠券领取实例、订单状态、收货省份快照、四项订单金额、币种、下单/取消时间和审计时间；`CANCELLED` 状态必须同时保存取消时间和原因。
- `sales_order_item` 保存 SKU、购买数量、Brand、三级 Category、SPU、SKU 的业务键与名称快照、原始单价及四项明细金额；商品主数据后续变化不回写历史订单。
- 订单与明细金额非负且分别满足应付金额公式，明细原价等于原始单价乘数量；订单头与明细合计、优惠分摊、地址/优惠券归属、状态迁移等跨行或流程规则由 Python 写入层保证。
- `cart_event` 和 `sales_order_item` 保持 append-only，`sales_order` 的合法状态变化刷新 `update_time`；三张表均禁止业务删除。
- 所有外键使用 `RESTRICT`。`sales_order.user_coupon_pk → user_coupon.user_coupon_pk` 已由 `DR-018` 补齐目标字段；显式约束名称已由 `DR-020` 确认。
- 索引覆盖加购主体/会话/SKU 与事件时间、订单用户/状态/优惠券与下单时间、订单明细的订单/SKU 查询，以及 append-only 或可变表对应的增量抽取方向。

该确认不表示 MySQL 已执行。支付与逆向交易 3 张表字段已由 `DR-017`、营销 2 张表字段已由 `DR-018` 确认；19 张表的完整物理命名与依赖顺序见 `DR-020`，Candidate DDL 已在 M2.2 `implemented` 并通过静态 Contract 检查。

### 3.12 已确认的支付与逆向交易源表字段

`DR-017` 已确认 `payment_attempt`、`return_order` 和 `refund_attempt` 的 49 个字段、可空性、关系、单行状态组合、生成列语义和索引方向。完整字段字典以 `docs/milestone-2-business-design.md` 8.7 节为准，核心边界如下：

- `payment_attempt` 保存支付业务键、请求幂等键、订单、状态、金额、币种、尝试/成功/失败时间、终态回调幂等键、失败原因和审计时间。生成列 `successful_order_pk` 在成功时取订单主键，并通过唯一索引限制一单最多一笔成功支付。
- `return_order` 保存退单业务键、请求幂等键、原订单与明细、状态、退单数量及原因、批准后的应退金额、币种、申请/批准/拒绝/完成时间、拒绝原因和审计时间。状态只允许 `APPLIED → APPROVED → COMPLETED` 或 `APPLIED → REJECTED`。
- `refund_attempt` 保存退款业务键、请求幂等键、退单、原订单、原成功支付、状态、金额、币种、尝试/成功/失败时间、终态回调幂等键、失败原因和审计时间。生成列 `successful_return_order_pk` 限制一张退单最多一笔成功退款。
- 支付与退款尝试的 `CREATED`、`SUCCESS`、`FAILED` 状态和对应时间、回调、失败原因组合由 MySQL 单行约束检查；支付/退款金额非负，退单数量为正数，币种只允许 `CNY`。
- 支付成功金额等于订单应付金额、退单累计数量上限、累计可退金额、退款与退单/订单/成功支付归属、累计退款上限和状态迁移由 Python 写入层保证。
- 退单应退金额为 `0.00` 时仍创建一笔零金额成功退款，再把退单更新为 `COMPLETED`；失败重试创建新的尝试记录，相同请求或回调不得重复改变首次终态结果。
- 三张表均为可更新交易记录，合法状态变化必须刷新 `update_time`；禁止业务硬删除，所有外键使用 `RESTRICT`。

该确认不表示任何规则已在 MySQL 运行验证。营销 2 张表字段已由 `DR-018` 确认；两个生成列的 `VIRTUAL` 物理形式及显式约束名称已由 `DR-020` 确认，M2.2 Candidate DDL 已 `implemented` 并通过静态 Contract 检查。

### 3.13 已确认的营销源表字段

`DR-018` 已确认 `coupon` 和 `user_coupon` 的 28 个字段、可空性、关系、单行状态组合、领取快照规则和索引方向。完整字段字典以 `docs/milestone-2-business-design.md` 8.8 节为准，核心边界如下：

- `coupon` 共 11 个字段，保存唯一业务键、名称、固定优惠金额、最低订单原价门槛、定义有效期、软删除和审计时间。优惠金额必须大于 0，门槛不得为负，有效期结束不得早于开始；软删除后不得新领取，已领取实例不受影响。
- `user_coupon` 共 17 个字段，保存唯一实例业务键、领取请求幂等键、优惠券与用户外键、`CLAIMED`、`LOCKED`、`USED`、`EXPIRED` 状态、领取时金额/门槛/有效期快照、领取/锁定/释放/使用/过期时间和审计时间。
- 同一用户可以拥有同一优惠券定义的多个独立实例，不设置 `(coupon_pk, user_pk)` 唯一约束。领取时复制快照，后续优惠券定义变化不得回写历史实例；重复 `request_id` 返回原实例。
- `user_coupon.coupon_pk → coupon.coupon_pk`、`user_coupon.user_pk → user_account.user_account_pk`、`sales_order.user_coupon_pk → user_coupon.user_coupon_pk`，全部使用 `RESTRICT`。不增加反向 `locked_order_pk`，当前订单关系通过 `sales_order.user_coupon_pk` 查询，避免循环外键。
- 锁券时检查用户所有权、领取实例状态、快照有效期和订单原价门槛。实际优惠必须等于快照金额；若会使订单应付金额为负，则拒绝用券，不自动截断或降低优惠。
- 一个领取实例最多关联一个成功支付订单，但可以多次锁定、取消和释放。重新锁定更新 `locked_at` 并清空 `released_at`；未支付取消时，未过期回到 `CLAIMED`，已过期进入 `EXPIRED`。支付成功进入 `USED`，后续退单或退款不返券。
- MySQL 负责业务键唯一、软删除组合、金额范围、有效期和本行状态时间组合；所有权、状态迁移、一次成功使用、订单关联和快照正确性由 Python 写入层负责。
- V1 不增加发行额度、库存、抢券、每用户领取上限或比例折扣券。查询索引覆盖定义有效期、用户持券状态、优惠券下实例状态、过期处理和 `update_time` 增量抽取。

该确认使全部 19 张源表共 230 个字段完成评审，但不表示 Python 写入层或 MySQL 运行验证已经完成。`DR-020` 已统一可命名约束与索引名称、生成列物理形式和建表顺序；M2.2 Candidate DDL 已 `implemented` 并通过静态 Contract 检查。

## 4. 技术栈与开发方式

选型结论：MySQL、Hadoop/Hive、Spark、Kafka、Flink、Doris 和 DolphinScheduler 构成了数据开发岗位中辨识度较高的经典开源技术组合，能够覆盖本项目计划展示的离线、实时、服务和调度能力。这里的“主流”表示技术方向和岗位能力具有代表性，不表示所有组件都采用最新版本，也不构成版本兼容、资源充足或链路已经运行的证明。DataX 属于成熟的传统离线同步工具，本项目保留它用于批量抽取，并通过 HDFS Writer 直接写入 Hive ODS 对应的 HDFS 分区；格式、依赖、分区发布和失败行为仍需真实验证。

| 职责 | 技术 | 当前状态 |
| --- | --- | --- |
| 业务数据源 | MySQL | candidate；尚未安装验证 |
| 离线抽取 | DataX | candidate；尚未安装验证 |
| 分布式存储与资源管理 | Hadoop HDFS、YARN | verified；固定 HDFS 文件、MapReduce、聚合日志和受控重启已通过 |
| 数仓元数据与 SQL | Hive | candidate；尚未安装验证 |
| 离线计算 | Spark SQL、PySpark，运行于 YARN | candidate；尚未安装验证 |
| 消息传输 | Kafka KRaft | candidate；尚未安装验证 |
| CDC 与实时计算 | Flink CDC、Flink SQL、Java DataStream，运行于 YARN | planned |
| 分析服务 | Doris | candidate；尚未安装验证 |
| 工作流调度 | DolphinScheduler | candidate；尚未安装验证 |
| 数据生成和质量工具 | Python、SQL | candidate |

开发方式：

- Spark SQL 负责主要离线转换；只有 SQL 不适合表达的复杂逻辑才使用 PySpark。
- Flink SQL 负责常规实时 ETL 和聚合；Java DataStream 只用于状态、定时器、去重、迟到处理和恢复等需要细粒度控制的逻辑。
- Python 用于固定 seed 数据生成器和轻量质量工具。
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

## 8. 版本与兼容性门禁

Hadoop 3.4.1 已于 2026-09-05 在当前集群完成版本、三节点守护进程 Java、HDFS 固定文件 SHA-256、MapReduce WordCount、YARN application 与聚合日志、临时对象清理和受控重启验证，项目状态为 `verified`。其余精确版本仍为候选。候选组件只有依次完成以下检查，才能写入 `infra/versions.env`：

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

基础门禁顺序：

```text
主机与网络
→ JDK
→ MySQL
→ HDFS
→ YARN
→ Hive
→ Kafka KRaft
→ Spark on YARN
→ DataX
→ Doris
→ DolphinScheduler
→ Flink / Flink CDC
```

必须验证 Hadoop/JDK、Hive/Hadoop、Hive Metastore/MySQL、Spark/Hadoop/Hive、Kafka/JDK/KRaft、Flink/JDK、Flink CDC/Flink/MySQL、Spark Doris Connector/Spark/Doris、Flink Doris Connector/Flink/Doris、DolphinScheduler/JDK/MySQL 和 DataX/MySQL/HDFS 的组合。

不允许使用容器作为兼容性兜底。兼容失败时应暂停、保存证据、调整版本或架构并重新验证。

YARN ResourceManager Scheduler 已确认使用 `8030`。Doris FE HTTP 已决定使用 `18030`；Doris 配置前必须确认端口未占用，并同步客户端、健康检查、安全组和文档。

当前候选基线为 MySQL 8.0.46、Connector/J 8.0.33、Hive 4.1.0、Kafka 3.9.1 Scala 2.12、Spark 3.5.9-bin-hadoop3、DataX 202309、Doris 4.0.8、DolphinScheduler 3.4.2、Flink 1.20.5 和 Flink CDC 3.6.0。候选值不构成运行证明，具体状态和官方依据见 [组件兼容性矩阵](compatibility-matrix.md)。

实时组件可以完成安装兼容性验证，但在实时规格确认前不得进入正式业务开发。

## 9. 数据生成、任务参数与幂等

采用双数据集：

- 验收数据集：规模小、固定 seed、逐层结果可人工核对。
- 基准数据集：规模、并发和实时产生速率可配置，具体数值在资源实测后决定。

验收数据必须覆盖：

- 正常注册、访问、加购、下单和支付。
- 取消、退单或退款。
- 重复输入和同一批次重跑。
- 跨日订单、支付和退款。
- 非法状态迁移和主外键缺失。
- 用户属性变化和维度关联。
- 零分母、空值、金额精度和舍入边界。
- 为未来实时验证准备的乱序、迟到和重复事件，但当前不定义处理策略。

所有批任务必须显式接收业务日期或起止时间，不得依赖执行机器当前日期推断数据范围。装载和转换应支持首次运行、同日重跑、连续回补和失败退出。

## 10. 指标范围与编号

建议数量：

```text
30 项 V1 正式离线指标
+
10 项扩展候选指标
+
5 项候选实时指标
```

指标使用本项目稳定编号；原材料序号只用于来源追溯，Project 2 和后续代码不得继续使用原序号作为正式标识。

### 10.1 V1 正式指标

| 新指标编号 | 原序号 | 指标名称 | 首版实时候选 |
| --- | ---: | --- | --- |
| `P1_METRIC_001` | 1 | 各渠道独立访客数 | 否 |
| `P1_METRIC_002` | 2 | 各渠道会话总数 | 否 |
| `P1_METRIC_003` | 3 | 各渠道会话平均浏览页数 | 否 |
| `P1_METRIC_004` | 4 | 各渠道会话平均停留时长 | 否 |
| `P1_METRIC_005` | 5 | 各渠道跳出率 | 否 |
| `P1_METRIC_006` | 6 | 各小时独立访客数 | 否 |
| `P1_METRIC_007` | 7 | 各小时页面浏览数 | 否 |
| `P1_METRIC_008` | 9 | 各类访客数 | 否 |
| `P1_METRIC_009` | 15 | 回流用户数 | 否 |
| `P1_METRIC_010` | 16 | 新增用户数 | 否 |
| `P1_METRIC_011` | 17 | 活跃用户数 | 否 |
| `P1_METRIC_012` | 18 | 首页浏览人数 | 否 |
| `P1_METRIC_013` | 19 | 商品详情页浏览人数 | 否 |
| `P1_METRIC_014` | 20 | 加购人数 | 是 |
| `P1_METRIC_015` | 21 | 下单人数 | 是 |
| `P1_METRIC_016` | 22 | 支付成功人数 | 是 |
| `P1_METRIC_017` | 23 | 新增下单人数 | 否 |
| `P1_METRIC_018` | 24 | 新增支付成功人数 | 否 |
| `P1_METRIC_019` | 25 | 各品牌订单数 | 否 |
| `P1_METRIC_020` | 27 | 各品牌订单金额 | 否 |
| `P1_METRIC_021` | 28 | 各品牌退单数 | 否 |
| `P1_METRIC_022` | 30 | 各品类订单数 | 否 |
| `P1_METRIC_023` | 35 | 各 SPU 订单数 | 否 |
| `P1_METRIC_024` | 37 | 各 SPU 订单金额 | 否 |
| `P1_METRIC_025` | 38 | 订单总额 | 是 |
| `P1_METRIC_026` | 39 | 订单数 | 是 |
| `P1_METRIC_027` | 40 | 订单人数 | 否 |
| `P1_METRIC_028` | 41 | 退单数 | 否 |
| `P1_METRIC_029` | 44 | 各省份订单金额 | 否 |
| `P1_METRIC_030` | 45 | 优惠券补贴率 | 否 |

### 10.2 扩展候选指标

| 新指标编号 | 原序号 | 指标名称 |
| --- | ---: | --- |
| `P1_METRIC_031` | 11 | 各类访客跳出率 |
| `P1_METRIC_032` | 13 | 各类访客平均访问页数 |
| `P1_METRIC_033` | 26 | 各品牌订单人数 |
| `P1_METRIC_034` | 29 | 各品牌退单人数 |
| `P1_METRIC_035` | 31 | 各品类订单人数 |
| `P1_METRIC_036` | 33 | 各品类退单数 |
| `P1_METRIC_037` | 34 | 各品类退单人数 |
| `P1_METRIC_038` | 36 | 各 SPU 订单人数 |
| `P1_METRIC_039` | 42 | 退单人数 |
| `P1_METRIC_040` | 43 | 各省份订单数 |

扩展指标只有在 30 项正式指标完成口径、血缘、固定样例和真实引擎验收后才能实施。

### 10.3 不采用指标

| 原序号 | 指标名称 | 原因 |
| ---: | --- | --- |
| 10 | 各类访客页面浏览数 | 与访客数、平均访问页数等保留指标重复度较高 |
| 12 | 各类访客平均在线时长 | 与渠道平均停留时长重复度较高 |
| 32 | 品类子主题中的“各品牌订单金额” | 主题和名称冲突，不知道实际应为品类还是品牌指标 |

不得擅自把原 32 改名后重新加入。

### 10.4 候选实时指标

以下五项只作为未来实时阶段的候选范围：

```text
P1_METRIC_014  加购人数
P1_METRIC_015  下单人数
P1_METRIC_016  支付成功人数
P1_METRIC_025  订单总额
P1_METRIC_026  订单数
```

在实时 Milestone 启动前，必须重新确认事件来源、统计窗口、去重对象、迟到处理、撤回或更新语义和离线对账口径。

每个指标在进入实现前必须定义名称、业务含义、统计粒度、维度、公式、分子分母、去重规则、时间口径、过滤条件、来源字段、离线来源、实时来源、零分母处理、精度、舍入、验证样例和状态。

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
| `P1-METRIC-01` | `P1_METRIC_*` 指标的名称、公式、粒度、维度、时间口径、来源和状态 | draft |
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
2. **OLTP 模型与数据生成器**：确认业务过程、字段、状态机、事实粒度和固定验收数据。
3. **离线抽取与 ODS**：DataX 将固定数据真实写入 Hive ODS 对应的 HDFS ORC 分区，Hive 分区可见且失败返回非零状态。
4. **离线数仓 MVP**：Hive ODS 与 Spark DIM/DWD、DWS、ADS 在真实引擎执行并完成逐层对账。
5. **正式指标与质量**：30 项正式指标具有口径、血缘、固定样例和质量规则。
6. **服务与调度**：Doris 离线服务表和 DolphinScheduler T+1 DAG 通过重跑、补数和失败测试。
7. **Spark 性能实验**：完成倾斜、Join 和分区裁剪的可复现实验。
8. **实时设计评审**：确认 Topic、Schema、窗口、迟到、去重、维度、状态、Doris 模型、归档和阈值。
9. **实时链路与可靠性**：完成 CDC、Kafka、Flink、Doris、恢复及五项离实时对账。
10. **Project 1 面试发布**：所有简历表述均有代码和运行证据。
11. **Project 2**：只消费 Project 1 已稳定发布的只读契约。

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

`M2-DEC-001` 至 `M2-DEC-003` 已通过 `DR-009` 确认，`M2-DEC-004` 至 `M2-DEC-006` 已通过 `DR-010` 确认，`M2-DEC-007` 至 `M2-DEC-010` 已通过 `DR-011` 确认，`M2-DEC-011` 至 `M2-DEC-013` 已通过 `DR-012` 确认，`M2-DEC-014` 已通过 `DR-013` 确认，`M2-DEC-015` 已通过 `DR-021` 确认，不再属于待决策项；其结论见 3.4 至 3.8 节。用户与流量 7 张源表字段已通过 `DR-014` 确认，商品 4 张源表字段已通过 `DR-015` 确认，正向交易 3 张源表字段已通过 `DR-016` 确认，支付与逆向交易 3 张源表字段已通过 `DR-017` 确认，营销 2 张源表字段已通过 `DR-018` 确认，见 3.9 至 3.13 节。`DR-015` 与已确认的 `M2-DEC-015` 属于不同编号体系。Candidate DDL 及静态检查已完成，但尚未在 MySQL 验证。当前仍需确认：
- 30 项正式指标的完整公式、时间归属、过滤、精度、舍入和零分母规则。
- 拉链维度及实时维度历史策略。
- 基准数据规模、并发和实时事件速率。
- HDFS/Hive、Kafka 和 Doris 的保留周期。
- Topic 划分、Partition、Schema 和重放策略。
- Flink 作业拆分、窗口、Watermark、允许迟到、去重键、状态 TTL 和补偿规则。
- Checkpoint、Savepoint、重启和端到端一致性目标。
- Doris 实时表 Key 模型、分区、分桶和更新语义。
- 实时明细是否长期归档到 HDFS/Hive。
- 实时与离线对账阈值。
- 组件精确版本及兼容失败后的版本调整方案。
- hadoop201 是否需要扩容。

未解决事项应保持 `draft`、`candidate` 或 `planned`，不得通过默认值伪装为正式决策。
