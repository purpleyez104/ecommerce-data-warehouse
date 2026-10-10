# 修改日志

本文件记录项目中面向使用者和维护者的可交付变更。

日志遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 的分类方式；项目形成正式发布版本后再补充版本号和发布日期。开发中的变更统一记录在“未发布”章节，不把草案、占位文件或静态检查写成已经完成运行验证。

## [未发布]

### 新增

- 新增 `DR-033`，确认 GitHub 发布目标使用新用户名 `purpleyez104`，项目内 Trellis/Codex 工具目录不进入公开仓库；2026-09-28 V2 数据规格、实施计划、指标与 Benchmark 作为 `candidate` 设计输入保留，不覆盖正式 Spec、Plan 或 Runtime 证据。
- 整合 V2 Business / Behavior Generator，统一记录为 `candidate / implemented / not_run`；文件和 Targeted Unit Test 不能替代正式数据规模、CSV Contract、`LOAD DATA`、Source Gate 或目标环境 Runtime 验收。
- 新增 `DR-032`，将实时 R1～R3 定位为 Pilot / Acceptance / History，暂停 `R4 Payment DWD`，确认离实时共享 `ecommerce_oltp`、21 表 Source Contract、Generator 与 Metrics Contract；Realtime V2 在 SOURCE GATE 后进入 Formal CDC、Domain DWD/DIM、集中 Gate 与离实时对账。该变更仅冻结方向，不表示 V2 CDC 或模型已实现。
- 新增 `DR-031`，确认离线 100 单链路完成 Pilot / Acceptance 使命并转为 History，正式离线入口切换为 21 表 V2 Source Data Build；固定 Python → CSV → `LOAD DATA`、按层批量实施、通用 ODS Framework 与 Source/ODS/Model Gate 边界。具体数据规模、数据库重置与 BI/Agent 归属仍为待确认项，不构成 Runtime 完成。
- 新增 `biz_order` ODS 历史切片验收记录、`hist-v1-001` 固定样本摘要、87 个剩余 HDFS 分区的一次性发布重建稿及 Spark SQL 九列固定基线质量入口；Runtime 事实限定为用户提供的 2026-09-22 Chat 记录，新脚本状态为 `implemented / not_run`，M3 保持 `in_progress`。
- 新增 R1 实时链路验收记录，保存商品事件 `op=c/d`、订单 DWD Java Job 构建与首次装载、Doris 100 单汇总的历史证据及未验证边界；该记录不代表当前作业在线、Checkpoint、订单 UPDATE、恢复或端到端 Exactly-Once 已通过。
- 新增实际执行过的 Doris `dwd_order` 建表 SQL，以及冻结 100 单的 MySQL/Doris 只读逐行对账脚本；脚本入库状态为 `implemented / not_run`，现有 Doris 表不得重复创建或通过 DROP/重建覆盖。
- 新增 `DR-028`，确认 V2 业务基线、合并后的 `docs/metrics.md`、逻辑模型和 21 张 `biz_*` 字段级候选物理设计成为当前 Milestone 2 实施基线；归档方案及其运行证据继续保留，但不再满足当前 M2/M3 门禁。
- 新增 T7 M2.5 Linux Bash Runtime 验收入口：在目标 MySQL 8.0.46 使用两个受控隔离 Database 联合执行 19 表 DDL、固定 Seed、Generator、约束失败和业务语义检查，并生成去敏的完整结果摘要。
- 新增 T7 MySQL Runtime 验收结果：两套 19 表 DDL、固定 Seed 首次装载与同内容重跑、漂移拒绝、5 个约束失败用例、Generator 确定性装载、金额守恒、生成列、软删除和 `update_time` 语义均通过，两个隔离 Database 均已清理。
- 新增 `DR-026`，采用用户确认的 M1 Step 2～12 Runtime 记录作为当前能力基线，明确能力优先的验收口径、Flink 执行模式与 final-state 判断规则，以及 M3、M8、M9 的业务边界。
- 新增三条已验证的临时技术链路记录：MySQL→DataX→HDFS→Hive→Spark、MySQL Binlog→Flink CDC→Kafka→Flink→Kafka、Kafka→Flink→Checkpoint/Recovery→Doris Connector→Doris；这些结果只证明组件组合兼容性，不代表正式 ODS 或实时业务链路完成。
- 新增 M1 五组件验收共享 Evidence Contract 与最小公共库：统一 `run-id`、私有证据目录、步骤日志、断言、SHA-256、`summary.env`、Secret 去敏和受控 Cleanup；公共库已通过本地 Git Bash Contract Test，不代表组件 VM Runtime 已通过。
- 新增无中断、去敏的三节点 VM 与已安装组件现场采集脚本及 PowerShell Contract Test；脚本只生成 inventory evidence，不执行组件功能、重启或配置修改。
- 新增受控 MySQL 验收入口 `scripts/m1/verify-mysql.sh`：检查精确版本、三节点私网认证、ROW/FULL Binlog I/U/D、预期认证失败、显式授权的重启恢复和严格临时 Database Cleanup；脚本入库与本地 syntax 检查不替代目标 ECS Runtime 证据。
- 新增 `DR-027`，将 M1 组件验收证据划分为 Hard Gate、Process Check 和 Optional Evidence，并以最小充分证据包减少非核心附件的重复采集；Secret、Cleanup、失败传播和破坏性操作授权仍是强制门禁。
- 新增 2026-09-13 三节点 VM 与组件安装现场的去敏事实摘要：确认 VM、网络、磁盘、时间、Java 和当前安装路径，组件功能状态继续按原始证据门禁分别维护。
- 新增 `DR-022` 至 `DR-024`，分别记录 M1 实装候选与证据分级、Kafka 三节点 KRaft 存储保护、DataX 稳定入口与 ODS 类型 workaround 边界。
- 补充 MySQL AppArmor、Hive/Spark Metastore 版本冲突、Kafka KRaft 顺序启动、DataX 包类型及 ORC 类型限制等真实搭建排障摘要。
- 新增 M2.4 确定性参数化 Generator：使用显式随机 seed、严格 `yyyy-MM-dd` 业务开始日期、日期数量与规模参数生成 19 表候选 SQL；Python 跨行 Contract 覆盖 Login/Session/Event 身份与时间、Return Item 归属、支付/退款关联及顺序、Coupon 释放/重锁/一次成功使用和金额守恒，`scale=1` 固定数据覆盖零应付订单、零成功支付业务日及 Coupon 释放、使用和过期场景。Targeted Test、真实生成行 Mutation Test 与 T5 静态 Contract 已通过，产物保持 `implemented`，尚未连接或验证 MySQL。

- 新增 M2.3 固定验收数据交付：19 表合法固定 Seed、逐表预期结果清单、5 个隔离 MySQL 约束失败用例、幂等入口、静态 Contract 与金额变异回归；产物为 `implemented`，静态检查通过，尚未连接或验证 MySQL。

- 新增 M2.2 的 19 张 `ecommerce_oltp` 源表 Candidate DDL 与 PowerShell 静态 Contract 检查：覆盖 230 个字段、命名台账、FK 目标、关键 CHECK、唯一/二级索引列、生成列配对及建表/回滚顺序；产物为 `implemented`，尚未在 MySQL 执行或验证。

- 创建项目修改日志和决策记录入口。
- 建立 Agent 每次最终答复总结核心操作和核心决策、并在用户确认后按职责写入修改日志或决策记录的协作规则。
- 在 README、项目规格和阶段计划中补充修改日志与决策记录的路径、作用和 Milestone 0 验收边界。
- 增加仓库级 LF 换行约束，避免本机 Git 配置破坏文档格式基线。
- 新增 Milestone 2 业务设计文档，集中记录五个主题的业务过程、概念关系、30 项正式指标的过程依赖、验收场景和待确认决策。
- 新增 Milestone 1 集群事实基线、组件兼容性矩阵、安装排障记录、基础设施端口/hosts 边界和 Hadoop 验收脚本。
- 将 `.local-notes/` 纳入 Git 忽略范围，作为从 ECS 接收原始 M1 证据的本地隔离区，防止运行日志和现场值被误提交。

### 变更

- 规范化文档结构：V2 数据规格与实施计划候选稿归入 `docs/design/`，Benchmark 规范归入 `docs/benchmark/spec.md`，指标唯一入口归入 `docs/business/metrics.md`；恢复 `docs/archive/milestone-2-business-design.md` 作为旧 19 表历史设计归档。
- 将旧 21 表 Pilot Generator 归档到 `archive/pilot-v1/ecommerce_generator_v1/` 并恢复原 package layout；其状态保持 `PILOT / ACCEPTANCE / HISTORY`，不作为 V2 正式入口。
- DataX 仓库配置改为 `datax/config/datax.env.example`，本地 `datax.env` 被 Git 忽略；候选 Job Generator 展开嵌套环境变量、生成严格合法 JSON，并由 Targeted Test 覆盖；运行脚本在配置缺失时显式失败，并统一使用 `DATAX_LOG_DIR`。上述检查不替代 DataX/HDFS/Hive Runtime 验收。
- 实时开发从逐表 Pilot 切换为 V2 正式业务路线：`ecommerce_oltp_m2_acceptance`、`ods_cdc_m2_clean_v1`、`all-to-zero`、Pilot `kafka_offset` Sequence 与旧 Checkpoint 仅保留为 History；Order / OrderItem Job 保留为 Verified Prototype。正式 Topic、Partition、`event_version`、Domain Job、增量生成器和 Doris 初始化仍待实现与验证。
- 离线开发从逐表 Pilot 切换为 V2 按层批量路线：正式源库使用 `ecommerce_oltp`，保留 `ecommerce_oltp_m2_acceptance` 作为历史验收环境；停止执行 F2 `ods_order_item_create.sql`，旧 Generator 不再作为正式入口。当前只进入 21 表 DDL 核对和数据规格冻结，尚未创建新 Generator、CSV、`LOAD DATA`、Source Gate 或 V2 ODS。
- 同步 README、规格、阶段计划、DataX 与测试导航：记录 `hist-v1-001` 的 100 单、319 明细、82 支付尝试、69 `PAID`、31 `CANCELED`、88 分区及三项金额基线，并区分历史 Runtime、仓库实现和本轮 `not_run` 边界。
- 同步 README、规格、阶段计划、架构、实时设计、业务源、建模导航和测试入口中的实时链路状态：M8/M9 保持 `in progress`，订单 DWD 首次装载仅为限定范围历史 Runtime 事实，逐行对账、Checkpoint、订单 UPDATE 和恢复仍待验收。
- Milestone 2 调整为 `in progress`：当前采用自营商城 V2 业务规则、六域指标体系、21 张 `biz_*` 候选源表和独立行为事件流；正式 DDL、Seed、Generator、正式表 CDC/离线接续及 Runtime 尚未完成，Milestone 3 因此继续阻断。
- 将 `docs/metrics/metrics-v2.md` 合并到 `docs/metrics.md`，保留原 V2 指标正文，仅调整移动后的相对链接并补充实现状态边界；仓库内指标入口统一为 `docs/metrics.md`。
- Milestone 2 更新为 `completed`：M2.1～M2.5 的进入条件、交付物和验收项均已满足；Candidate DDL、固定 Seed 与 Generator 的 T7 验收范围由 `implemented` 提升为 `verified`，不代表 M3 ODS 或后续数据链路完成。
- M1 当前状态同步为 Step 2～12 已通过：MySQL 8.0.46、Hive 3.1.3、Spark 3.5.9 on YARN、DataX 202309、Kafka 3.9.1 KRaft、Flink 1.20.5、Flink CDC 3.6、Doris 4.0.8 和 Flink Doris Connector 26.1.1 均已确认；当前唯一剩余门禁为 DolphinScheduler 3.4.2。
- 更新 MySQL、Hive、Kafka 和 Doris 端口与恢复状态；DataX 实际 Runtime 入口记录为 `/data/module/datax-current`。继续禁止创建 `infra/versions.env`，直至 DolphinScheduler 通过且 M1 全部组件完成运行验收。
- M1 MySQL 直接门禁已满足，M2.5 仍等待当前 checkout 的 M2.2～M2.4 前置闭合；HDFS/Hive/DataX 的环境前置已满足，但 Milestone 3 仍需完成正式 ODS Schema、装载、幂等与对账验收。

- 确认 `M2-DEC-015` 的固定验收数据规模：以可人工核对的小型固定集覆盖 19 张源表和 `M2-SC-001` 至 `012`，业务日期固定为 `2025-01-29` 至 `2025-02-01`，正常 seed 首次运行与同日重跑各 1 次，并设置 14 个独立失败用例；该决策解除 M2.3/M2.4 的数据规模门禁，不表示 Seed、Generator 或 MySQL 验收已完成。
- M2.2 OLTP 逻辑与物理模型已完成：T2 静态验收通过并归档；19 张表 Candidate DDL 保持 `implemented`，MySQL 执行与行为验证仍待 T7。

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
- 完成 M2.2 Schema 物理规范收口：确认 19 张表的命名台账、两个唯一成功生成列的 `VIRTUAL` 形式、FK 建表/回滚拓扑及 MySQL `PRIMARY` 命名边界；下一步为 Candidate DDL 静态检查，不表示已在 MySQL 创建或验证。

### 修复

- 修复 T7 Cleanup 安全边界：只清理由当前进程成功创建并登记的合法前缀 Database；目标已存在时不执行 `DROP DATABASE`，单库创建后失败仅清理该库，任一 DROP 失败会返回非零并将结果摘要标记为 `failed`。
- 修复 M1 Evidence 公共库的脱敏误伤、未初始化 API 继续执行及 Cleanup Owner 延迟拒绝问题：非密码参数保持不变，需初始化的 Public API 统一以退出码 `2` 拒绝，Owner 在注册与执行阶段双重校验。
- 修复 VM 现场采集器对历史 `/data/module/datax-current` 入口的漏检，并新增 Java 8、Java 进程实际可执行文件、Hive 并存版本和三节点 Hive 软链接漂移证据。

- 修复 Hadoop 受控重启验证对 `jps -lv` 完整 Java 类名的匹配错误，避免在 NameNode 等进程实际存在时误报缺失；修复后已在目标 ECS 完成复测。

### 移除

- 从公开仓库移除 `.agents/`、`.codex/`、`.trellis/` 项目工具文件，保留根 `AGENTS.md` 作为协作规则入口。
- 移除不完整且库名冲突的 `mysql/ecommerce_oltp_v1/` 骨架，以及已被正式设计文档覆盖的 `docs/design/mock-data-design.md`、`docs/design/mysql-source-design.md` 碎片；当前权威 21 表 DDL 入口仍为 `DECISION_REQUIRED`。
- 移除仍依赖旧 Pilot Generator、已删除 DDL 或旧验收 SQL 的重复脚本与测试入口；旧 Generator 的代码和测试只在 `archive/pilot-v1/ecommerce_generator_v1/` 中保留。
- 从正式离线架构中移除独立的 HDFS landing/staging Text/CSV 中间数据层。
