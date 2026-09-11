# 修改日志

本文件记录项目中面向使用者和维护者的可交付变更。

日志遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 的分类方式；项目形成正式发布版本后再补充版本号和发布日期。开发中的变更统一记录在“未发布”章节，不把草案、占位文件或静态检查写成已经完成运行验证。

## [未发布]

### 新增

- 创建项目修改日志和决策记录入口。
- 建立 Agent 每次最终答复总结核心操作和核心决策、并在用户确认后按职责写入修改日志或决策记录的协作规则。
- 在 README、项目规格和阶段计划中补充修改日志与决策记录的路径、作用和 Milestone 0 验收边界。
- 增加仓库级 LF 换行约束，避免本机 Git 配置破坏文档格式基线。
- 新增 Milestone 2 业务设计文档，集中记录五个主题的业务过程、概念关系、30 项正式指标的过程依赖、验收场景和待确认决策。
- 新增 Milestone 1 集群事实基线、组件兼容性矩阵、安装排障记录、基础设施端口/hosts 边界和 Hadoop 验收脚本。
- 将 `.local-notes/` 纳入 Git 忽略范围，作为从 ECS 接收原始 M1 证据的本地隔离区，防止运行日志和现场值被误提交。

### 变更

- 建立 Trellis Data Engineering 工作流基线：移除默认 Fullstack spec，明确 `AGENTS.md`、项目 docs、Trellis Task 的事实优先级，转换 bootstrap Task，并关闭 Trellis 自动 Commit 与 Codex Hook 注册；该变更不改变任何业务模型、Milestone 门禁或运行验证结论。
- 离线主线调整为 DataX 直接写入 Hive ODS 对应的 HDFS ORC + Snappy 分区，并明确分区注册、审计字段、幂等发布和失败隔离责任。
- Milestone 0 已通过用户评审并标记为 `completed`；Milestone 1 保持 `pending`，进入门禁已满足但尚未开始实施。
- 在 Milestone 1、2 均保持 `pending` 的前提下，允许开展受限的 M2 文档预设计；该活动不豁免 MySQL 运行门禁，也不产生 DDL、seed 或其他可执行产物。
- Milestone 1 更新为 `in progress`；把当前 ECS 集群记录中的 `CONFIRMED` 作为确认事实，并将当前门禁调整为补齐 Hadoop HDFS、MapReduce 和重启证据。
- M1 统一沿用 `yee`、`/data` 和 Hadoop 独立 JDK 11 基线；Doris FE HTTP 使用 `18030`，DolphinScheduler 使用仅服务自身的单节点 ZooKeeper。
- 统一 M1 仓库与证据流转方式：`hadoop201` 仅拉取仓库并执行脚本，原始证据通过 MobaXterm 下载到 Windows 本地隔离区，仓库只接收经审查和去敏后的摘要或配置。
- Hadoop 3.4.1 已完成固定 HDFS 文件、MapReduce WordCount、YARN application、聚合日志、临时对象清理和受控重启验证，项目状态提升为 `verified`；M1 当前技术门禁切换到 MySQL 8.0.46。
- Milestone 1 与 Milestone 2 调整为同时 `in progress`；M2 拆分为 M2.1 至 M2.5，本地业务设计与实现准备不等待整个集群完成，MySQL 运行验收和 Milestone 3 仍保留直接依赖门禁。
- 确认 M2.1 的身份、会话和用户分类基础语义：身份分离且登录前事件不回写，会话采用 30 分钟无活动与 `Asia/Shanghai` 自然日边界，新老访客、新增、活跃、回流及首次转化的分类框架已形成；商品和交易规则仍待后续评审。
- 将 M2 文档正式定位并更名为 `docs/milestone-2-business-design.md`；文档角色正式化不改变其中未确认条目的 `DECISION_REQUIRED` 状态。
- 确认 M2.1 的商品层级、加购事件和订单粒度：采用 Brand → SPU → SKU 与三级 Category、订单时商品快照、加购和下单请求幂等、注册用户下单及 V1 不拆单边界；支付、逆向交易、状态和金额规则仍待后续评审。
- 确认 M2.1 的支付、取消、退单、退款、状态机和删除策略：支付支持多次尝试但最多一次成功，退单与退款分离并支持部分处理，核心业务对象禁止硬删除。
- 确认 M2.1 的时间、金额和优惠券语义：采用 `Asia/Shanghai` 事件时间归属、CNY 两位小数与确定性优惠/退款分摊、固定金额券状态机及 `P1_METRIC_030` 支付日毛补贴率；M2.1 标记为 `completed`，M2.2 进入 `in progress`，不表示候选 DDL 或 MySQL 已验证。
- 确认 M2.2 第一批源模型基线：在 MySQL `ecommerce_oltp` 规划 19 张 OLTP 源表，采用 InnoDB、utf8mb4、统一主键/金额/数量/时间/状态规范，明确 MySQL 与 Python 写入层的约束分工及异常事务隔离；逐表字段、候选 DDL 和 MySQL 运行验证尚未完成。
- 确认 M2.2 用户与流量源模型：完成 `user_account`、`user_address`、`visitor`、`traffic_channel`、`visit_session`、`login_event` 和 `page_view_event` 的字段、可空性、关系、单行约束及索引方向设计；商品、交易、营销表和候选 DDL 仍待后续完成。
- 确认 M2.2 商品源模型：完成 `brand`、`category`、`spu` 和 `sku` 共 35 个字段及三级 Category、商品关系、价格、软删除和索引方向设计；交易、营销表和候选 DDL 仍待后续完成。
- 确认 M2.2 正向交易源模型：完成 `cart_event`、`sales_order` 和 `sales_order_item` 共 57 个字段、加购动作与有效性、订单状态与取消字段、完整商品快照、金额关系、约束分工及索引方向设计；当前累计 14 张表 153 个字段，支付、逆向交易和营销 5 张表及候选 DDL 仍待完成。
- 确认 M2.2 支付与逆向交易源模型：完成 `payment_attempt`、`return_order` 和 `refund_attempt` 共 49 个字段、支付/退款终态字段组合、退单状态路径、零金额退款、唯一成功生成列语义及索引方向设计；当前累计 17 张表 202 个字段，仅营销 2 张表及候选 DDL 仍待完成。
- 确认 M2.2 营销源模型：完成 `coupon` 和 `user_coupon` 共 28 个字段、固定金额与最低原价门槛、领取快照、锁定/释放/使用/过期状态时间组合、外键及索引方向设计；至此 19 张源表共 230 个字段全部确认，候选 DDL 和 MySQL 运行验证仍未完成。

### 修复

- 修复 Hadoop 受控重启验证对 `jps -lv` 完整 Java 类名的匹配错误，避免在 NameNode 等进程实际存在时误报缺失；修复后已在目标 ECS 完成复测。

### 移除

- 从正式离线架构中移除独立的 HDFS landing/staging Text/CSV 中间数据层。
