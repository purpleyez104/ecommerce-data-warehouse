# 电商业务源物理设计规格 V1.0｜21 张 MySQL 表

> 状态：**M2-02 字段级候选物理设计／非 DDL／未部署**，2026-09-18。此版本采用本对话已确认的 21 张 `biz_*` 方案，不沿用服务器旧 19 表 `001_ecommerce_oltp_candidate.sql` 或旧 Generator。任何既有文件不覆盖、不删除。
> 上游：[业务基线](../business/business-baseline-v2.md) · [指标字典](../business/metrics.md) · [逻辑模型](logical-model-v2.md)。已通过的 ENV-05 是**隔离测试表**的 CDC 验证，不等于这 21 张正式源表已经 CDC 验收。

> 后续状态提示（2026-09-20）：以上为 2026-09-18 的设计时点描述；候选 DDL 静态快照见 [M2-03](M2-03-物理设计与静态审查.md)，后来隔离验收库的有限 21 表 CDC 与批次结果、仍未闭合的正式库/离线门禁见 [业务源设计](../design/business-source-design.md)。本文件保留原字段设计，不把历史验收反写为字段冻结或正式部署。

## 1. 物理统一规范

| 项 | V1.0 约定 |
|---|---|
| 数据库/引擎 | `ecommerce_oltp` / InnoDB；已有测试表须保护，不得覆盖 |
| 编码 | utf8mb4 |
| 主键与业务编号 | PK `BIGINT` 稳定 ID；外部业务编号 `VARCHAR(64)` 并按需 UK |
| 金额 | `BIGINT` 分，非负；金融换算仅在展示层/指标层处理，避免 FLOAT/DOUBLE |
| 数量 | `INT`；业务边界使用 CHECK + 事务校验 |
| 时间 | `DATETIME(3)`，源业务统一按 Asia/Shanghai 解释；事件区分 occurred_at/recorded_at |
| 状态 | `VARCHAR(32)`，实际允许集合在 DDL CHECK 中逐项落实 |
| 历史扩展 | 变更事件 before_data/after_data 可用 JSON，强类型核心金额/业务键不只存在 JSON 中 |
| 不可变历史 | 一次合法变更产生唯一事件键；同一 MySQL 事务提交状态与事件 |
| CDC | 仅业务表 Binlog CDC；不启 Outbox，不允许应用双写业务状态到 Kafka |
| 分组 | 用户身份 3 + 商品 4 + 购物车 3 + 订单 3 + 支付 2 + 退款 3 + 券 3 = **21** |

标注约定：PK 主键，UK 唯一键，FK 逻辑/物理外键建议，IDX 查询索引；跨表守恒和并发竞争不能被普通 CHECK/外键替代，须由业务事务及验收测试保证。完整 null/default/ON UPDATE 与索引 DDL 尚未生成。

## 2. 字段清单（逐表）

### 2.1 用户与身份（3）

**01 `biz_user`｜注册用户（当前状态）**

| 字段 | 物理类型 | 约束/用途 |
|---|---|---|
| user_id | BIGINT | PK；稳定标识 |
| user_key | VARCHAR(64) | UK |
| user_name | VARCHAR(64) | 模拟用户名，不作事实关联键 |
| user_status | VARCHAR(32) | ACTIVE / DISABLED |
| registered_at | DATETIME(3) | 注册事件时间 |
| created_at, updated_at | DATETIME(3) | 审计时间 |

建议 IDX：`(registered_at)`（如果增量采集/注册分析需要；最终按执行计划裁剪）。CDC 用于用户维度，历史版本在数仓侧或通过源变化重建。

**02 `biz_visitor`｜匿名访客（当前状态）**

| 字段 | 类型 | 约束/用途 |
|---|---|---|
| visitor_id | BIGINT | PK |
| visitor_key | VARCHAR(64) | UK |
| first_seen_at, last_seen_at | DATETIME(3) | 首次/最近行为 |
| created_at, updated_at | DATETIME(3) | 审计 |

**03 `biz_identity_mapping`｜可靠映射/修订历史**

| 字段 | 类型 | 约束/用途 |
|---|---|---|
| mapping_id | BIGINT | PK |
| visitor_id, user_id | BIGINT | FK → visitor/user；不得推断跨账号合并 |
| session_id | VARCHAR(64) NULL | 会话局部证据 |
| evidence_type | VARCHAR(32) | LOGIN/VERIFIED 等候选类型 |
| evidence_id | VARCHAR(64) | 证据 ID |
| mapping_scope | VARCHAR(32) | SESSION/VISITOR |
| identity_version | BIGINT | 版本号 |
| effective_from, effective_to | DATETIME(3) | 后者可 NULL |
| mapping_status | VARCHAR(32) | CONFIRMED/REVOKED |
| recorded_at | DATETIME(3) | 记录时间 |

UK `(visitor_id, identity_version)` 为前版建议；还须由业务校验身份歧义、同作用范围时间区间不产生非法冲突，不能把该 UK 当作全部身份一致性证明。IDX `(visitor_id,effective_from)`、`(user_id,effective_from)`。

### 2.2 商品（4）

**04 `biz_category`｜类目当前状态**：`category_id BIGINT PK`；`category_code VARCHAR(64) UK`；`category_name VARCHAR(128)`；`category_status VARCHAR(32)`；`created_at DATETIME(3)`；`updated_at DATETIME(3)`。

**05 `biz_spu`｜SPU 当前状态**：`spu_id BIGINT PK`；`spu_code VARCHAR(64) UK`；`category_id BIGINT FK→biz_category`；`brand_code VARCHAR(64)`；`brand_name VARCHAR(128)`；`spu_name VARCHAR(255)`；`spu_status VARCHAR(32)`；`created_at/updated_at DATETIME(3)`。IDX `(category_id)`。本 21 表不增加独立品牌表。

**06 `biz_sku`｜销售 SKU 当前状态**：`sku_id BIGINT PK`；`sku_code VARCHAR(64) UK`；`spu_id BIGINT FK→biz_spu`；`sku_name VARCHAR(255)`；`sale_price_cents BIGINT CHECK >=0`；`sku_status VARCHAR(32)`（ON_SALE/OFF_SALE）；`created_at/updated_at DATETIME(3)`。IDX `(spu_id)`；`(updated_at)` 按增量场景决定。**库存能力缺口**：已确认业务要求 SKU 有独立库存，但此 21 表最新字段草案未给库存字段；正式 DDL 前需补充/确认最小库存属性及扣减范围，不能在本文冒称已落实。

**07 `biz_product_change_event`｜商品变更不可变事件**：`change_id BIGINT PK`；`event_key VARCHAR(64) UK`；`target_type VARCHAR(32)`（CATEGORY/SPU/SKU）；`target_id BIGINT`；`change_type VARCHAR(32)`（价格/类目/品牌/状态）；`before_data JSON`；`after_data JSON`；`effective_at DATETIME(3)`；`recorded_at DATETIME(3)`。IDX `(target_type,target_id,effective_at)`；多态 target_id 不能用单一 FK 实现，业务事务校验目标存在且 before/after 匹配。

### 2.3 购物车（3）

**08 `biz_cart`｜当前购物车**：`cart_id BIGINT PK`；`user_id BIGINT NULL FK→biz_user`；`visitor_id BIGINT NULL FK→biz_visitor`；`created_at/updated_at DATETIME(3)`。CHECK：两者恰有一方非 NULL；分别 UK `(user_id)`、`(visitor_id)`，MySQL UNIQUE 对 NULL 的语义与互斥 CHECK 配合。

**09 `biz_cart_item`｜当前购物明细**：`cart_item_id BIGINT PK`；`cart_id BIGINT FK`；`sku_id BIGINT FK`；`quantity INT CHECK BETWEEN 1 AND 99`；`created_at/updated_at DATETIME(3)`；UK `(cart_id,sku_id)`；按 FK 建索引（避免重复左前缀索引）。

**10 `biz_cart_merge_record`｜幂等合并记录**：`merge_id BIGINT PK`；`operation_id VARCHAR(64) UK`；`visitor_cart_id BIGINT FK`；`user_cart_id BIGINT FK`；`user_id BIGINT FK`；`merge_detail JSON`（逐 SKU 的原数量/目标原数量/新数量/截断原因）；`truncated_quantity INT`；`merged_at DATETIME(3)`。同 operation_id 重试只返回既有结果，合并及记录原子提交；避免重复累加。

### 2.4 订单（3）

**11 `biz_order`｜订单当前状态/金额**

| 字段 | 类型 | 约束/用途 |
|---|---|---|
| order_id | BIGINT | PK |
| order_no | VARCHAR(64) | UK |
| user_id, visitor_id | BIGINT NULL | 分别关联注册/匿名身份；结算归属互斥或组合规则在正式 DDL 前收敛 |
| coupon_id | BIGINT NULL | 可选券，最多一张 |
| order_status | VARCHAR(32) | CREATED / PAID / CANCELED |
| gross_amount_cents | BIGINT | 原价总额 >=0 |
| discount_amount_cents | BIGINT | 折扣总额 >=0 |
| payable_amount_cents | BIGINT | 应付=原价−优惠 >=0 |
| created_at | DATETIME(3) | GMV 的日期归属 |
| payment_deadline_at | DATETIME(3) | created_at + 15min |
| paid_at, canceled_at | DATETIME(3) NULL | 对应有效终态时间 |
| updated_at | DATETIME(3) | 审计/增量 |

IDX `(user_id,created_at)`、`(order_status,created_at)`；若匿名订单支持按访客查询，则评审 `(visitor_id,created_at)`。注意该候选稿没有确认匿名是否允许不登录完成支付，**不得把某种 guest-checkout 策略当作既定事实**。coupon FK 与券中的订单关联形成潜在建表顺序循环，需要先创建可空列再补 FK 或明确单向引用。

**12 `biz_order_item`｜订单 SKU 成交快照**

| 字段 | 类型 | 约束/用途 |
|---|---|---|
| order_item_id | BIGINT | PK |
| order_id | BIGINT | FK→biz_order |
| sku_id | BIGINT | FK→biz_sku；UK(order_id,sku_id) |
| spu_id, category_id | BIGINT | 成交时商品快照键 |
| brand_code | VARCHAR(64) | 成交时品牌 |
| sku_name | VARCHAR(255) | 成交时名称 |
| quantity | INT | 正整数；整单 1~5 个不同 SKU |
| unit_price_cents | BIGINT | 成交单价 |
| gross_amount_cents | BIGINT | unit_price × quantity |
| allocated_discount_cents | BIGINT | 明细应承担券额 |
| payable_amount_cents | BIGINT | 明细原价−分摊优惠 |
| refund_reserved_cents | BIGINT | 处理中锁定退款额度 |
| refunded_cents | BIGINT | 累计已成功退款 |
| refunded_quantity | INT | 明确成功退货件数 |
| created_at | DATETIME(3) | 明细创建时间 |

CHECK 非负、`refunded_cents+refund_reserved_cents<=payable_amount_cents`、成功退款数量不大于购买数量；整单 1~5 条和金额守恒需要事务跨表校验。数量不从退款金额推断。商品维度使用本行成交快照。

**13 `biz_order_status_event`｜订单不可变状态历史**：`order_event_id BIGINT PK`；`event_key VARCHAR(64) UK`；`order_id BIGINT FK`；`event_type VARCHAR(32)`（CREATE/PAY/CANCEL）；`from_status VARCHAR(32) NULL`；`to_status VARCHAR(32)`；`occurred_at DATETIME(3)`；`recorded_at DATETIME(3)`。IDX `(order_id,occurred_at)`。状态变更与事件原子提交。

### 2.5 支付（2）

**14 `biz_payment_attempt`｜执行尝试与稳定资金 ID**：`payment_attempt_id BIGINT PK`；`order_id BIGINT FK`；`attempt_no INT`；`funding_txn_id VARCHAR(64) UK`；`amount_cents BIGINT`；`payment_status VARCHAR(32)`（INIT/FAILED/SUCCESS）；`initiated_at DATETIME(3)`；`succeeded_at DATETIME(3) NULL`；`updated_at DATETIME(3)`。UK `(order_id,attempt_no)`；候选生成列 `successful_order_id = CASE WHEN payment_status='SUCCESS' THEN order_id ELSE NULL END` 配 UK，依靠唯一值和 NULL 可重复性质约束每单最多一次有效 SUCCESS。金额须与订单应付一致、业务时间合法、订单行锁与状态事件事务一致；单纯唯一索引不处理跨表金额/超时。

**15 `biz_payment_event`｜支付关键事件/通知去重**：`payment_event_id BIGINT PK`；`event_key VARCHAR(64) UK`；`payment_attempt_id BIGINT FK`；`callback_event_id VARCHAR(64) NULL UK`；`from_status VARCHAR(32)`；`to_status VARCHAR(32)`；`occurred_at DATETIME(3)`；`recorded_at DATETIME(3)`。IDX `(payment_attempt_id,occurred_at)`；NULL 回调 ID 的语义及重放事件规则实施前审核；已成功资金不可重复入账。

### 2.6 退款（3）

**16 `biz_refund_request`｜明细退款申请**：`refund_request_id BIGINT PK`；`refund_request_no VARCHAR(64) UK`；`order_id BIGINT FK`；`order_item_id BIGINT FK`；`requested_amount_cents BIGINT`；`refund_quantity INT NULL`；`refund_status VARCHAR(32)`（REQUESTED/PROCESSING/SUCCESS/FAILED）；`requested_at DATETIME(3)`；`completed_at DATETIME(3) NULL`；`updated_at DATETIME(3)`。IDX `(order_item_id,refund_status)`；须校验该明细确属对应 order_id。金额预留、成功、失败释放在事务内更新明细，禁止超额；纯金额补偿 quantity=NULL。

**17 `biz_refund_transaction`｜退款资金执行尝试**：`refund_txn_id BIGINT PK`；`refund_request_id BIGINT FK`；`attempt_no INT`；`funding_refund_txn_id VARCHAR(64) UK`；`refund_amount_cents BIGINT`；`refund_txn_status VARCHAR(32)`（INIT/FAILED/SUCCESS）；`initiated_at DATETIME(3)`；`succeeded_at DATETIME(3) NULL`；`updated_at DATETIME(3)`。UK `(refund_request_id,attempt_no)`；候选条件生成列/唯一索引限定一申请最多一 SUCCESS；成功金额必须=申请金额；失败尝试保留但不累计。

**18 `biz_refund_event`｜退款申请/执行历史**：`refund_event_id BIGINT PK`；`event_key VARCHAR(64) UK`；`refund_request_id BIGINT FK`；`refund_txn_id BIGINT NULL FK`；`event_type VARCHAR(32)`（REQUEST/PROCESS/SUCCESS/FAIL）；`from_status VARCHAR(32) NULL`；`to_status VARCHAR(32)`；`occurred_at DATETIME(3)`；`recorded_at DATETIME(3)`；IDX `(refund_request_id,occurred_at)`。

### 2.7 优惠券（3）

**19 `biz_coupon_template`｜固定金额订单券模板**：`template_id BIGINT PK`；`template_code VARCHAR(64) UK`；`template_name VARCHAR(128)`；`face_value_cents BIGINT`；`min_spend_cents BIGINT`；`valid_from/valid_to DATETIME(3)`；`issue_limit INT`；`template_status VARCHAR(32)`（ACTIVE/DISABLED）；`created_at/updated_at DATETIME(3)`。CHECK 金额/上限合法及有效期顺序；发放上限跨行并发需事务控制。

**20 `biz_coupon`｜已发放券实例**：`coupon_id BIGINT PK`；`coupon_code VARCHAR(64) UK`；`template_id BIGINT FK`；`user_id BIGINT FK`；`coupon_status VARCHAR(32)`（UNUSED/LOCKED/USED/EXPIRED）；`locked_order_id BIGINT NULL`；`used_order_id BIGINT NULL`；`issued_at/expires_at DATETIME(3)`；`locked_at/used_at DATETIME(3) NULL`；`updated_at DATETIME(3)`。IDX `(user_id,coupon_status,expires_at)`；锁券与订单创建、用券与支付成功、释放与取消须同事务。退款不返券。locked_order_id/used_order_id 与订单券 FK 可能循环，DDL 应按依赖顺序处理。

**21 `biz_coupon_event`｜券历史**：`coupon_event_id BIGINT PK`；`event_key VARCHAR(64) UK`；`coupon_id BIGINT FK`；`order_id BIGINT NULL`；`event_type VARCHAR(32)`（ISSUE/LOCK/USE/UNLOCK/EXPIRE）；`from_status VARCHAR(32) NULL`；`to_status VARCHAR(32)`；`occurred_at DATETIME(3)`；`recorded_at DATETIME(3)`；IDX `(coupon_id,occurred_at)`。

## 3. 源表分组、采集策略与权威事实

| 表类 | 离线 DataX | 实时 Flink CDC | 权威统计输入 |
|---|---|---|---|
| 用户/商品/券当前状态 | 有需求时全量或增量快照 | 通过 Binlog 保留变化 | DIM 当前值与 SCD2 对应快照/变更事件 |
| 订单头/明细 | 初始化与后续 T+1 增量 | INSERT/UPDATE/DELETE | 创建事实按 order_id、成交金额按明细粒度防重复 |
| 支付尝试/退款执行 | T+1 资金事实 | Binlog | 有效唯一 SUCCESS，只选一次，不叠加事件历史 |
| 订单/支付/退款/券/商品事件 | 历史补全 | 关键变化 INSERT 经 CDC | 状态转变及 as-of 回放，不与当前状态双计 |
| 购物车状态/合并记录 | 有需求时采集 | 可采，按指标依赖白名单 | 购物车当前状态/幂等合并；行为次数以 Kafka 行为流为主 |
| 行为事件 | 不从 MySQL 业务表取代 | 不经 MySQL CDC | 页面/商品/购物三组 Kafka 源事件 |

正式采集需使用明确表白名单、主键与 `op` 语义，不采集无关系统表。按表 Topic 是 Step 9 的最小测试方案，**不是**正式 21 表 Topic 划分已确认；CDC 正式 Topic 组织另行确定。行为三组 Topic 的具体字符串仅作为建议，不代表已经部署。

## 4. 可靠事件发布与一致性边界

```text
模拟业务服务(Python 模块化单体)
  └─ MySQL InnoDB 事务：状态/余额或额度更新 + 专用历史事件 INSERT
       ├─ DataX → HDFS/Hive ODS（T+1）
       └─ ROW/FULL Binlog → Flink CDC → Kafka Raw CDC Topic
独立行为模拟器 → 页面/商品/购物 Kafka Topic
```

不使用 Outbox/应用 MySQL+Kafka 双写；关键历史事件本身要可靠入库。应用需以行锁/条件更新处理订单取消 vs 支付、优惠券锁定 vs 核销、退款并发申请额度。CDC 可能重放，消费端按主键、事件键、资金业务 ID 和源位置/版本幂等，不能把测试中的“未观察到重复”当作通用端到端 Exactly-Once 保证。

## 5. 快照与 Binlog 接续

1. 基线：使用一致性快照 + 持续增量接续；记录启动模式、源库表白名单、快照/位点边界、版本、时间和 CDC 作业 ID。
2. 初始化期间保留正常增量写入，先验证快照与 Binlog 无漏事实、重复可控；与 DataX 离线初始化重叠部分按业务键及变更位置去重。**ENV-05 已验证单测试表 snapshot + c/u/d + Checkpoint 恢复，未完成 21 表全量历史接续/离实时最终对账。**
3. Binlog 配置曾确认 `ROW/FULL`、`server_id=201`；保留期设置存在两组变量（expire_logs_days=7、seconds=0、auto_purge=ON），正式运维须再次检查 MySQL 实际生效保留期，不能未经核实认定无限保留。
4. 密钥使用非 Git 私有配置，禁止把 YAML 明文凭据、YARN 完整启动参数及未脱敏日志提交仓库；只记录脱敏配置模板和有限验收摘要。

## 6. 开发实施顺序与门槛

| 顺序 | 操作 | 完成条件 |
|---|---|---|
| 1 | 冻结字段和遗漏规则，检查独立数据库/旧测试表 | 未确认字段有决策记录；无覆盖旧 19 表 |
| 2 | 生成**全新** 21 表 DDL 并静态校验 | FK/循环引用/唯一/状态 CHECK/索引无明显冲突 |
| 3 | 隔离创建用户/商品/券/车等基础对象 | 主键唯一及商品/身份约束合格 |
| 4 | 订单+优惠分摊+取消/支付 | 金额守恒、15分钟竞态、最多一次成功 |
| 5 | 退款申请/资金重试及事件历史 | 无超额、单申请完整结果、状态事件同事务 |
| 6 | 约100单固定种子、反例测试 | 可复现，正常/异常案例全覆盖 |
| 7 | 行为三组 Topic/事件契约 | event_id、身份、session、跨 Topic 时间一致 |
| 8 | 正式表快照/CDC接续与离实时对账 | 检查缺失、重复、历史修订和故障恢复 |
| 9 | 90日标准模拟与压测 | 达到已确认目标规模前不声称已达标 |

**尚未实施**：正式 DDL、正式源表、Python 新版 Generator、21 表 CDC、DataX 与 CDC 全链路对账、3 组正式行为 Topic、正式指标计算。

## 7. 最终 DDL 必须先收敛的项目

- SKU 库存最小属性与库存是否仅展示，不改变一期不做完整库存流水的边界。
- 订单匿名/注册身份归属 CHECK、用户券与访客支付业务的兼容关系；不要擅自增加 guest checkout 规则。
- 状态字段所有合法枚举、NOT NULL/默认值、时间一致性、外键 ON DELETE/UPDATE 策略及 FK 建立顺序（特别是订单与优惠券相互关联）。
- 条件唯一索引对应生成列的精确 DDL、资金/回调幂等语义、跨表并发锁顺序。
- 券优惠额度与订单应付的零元订单处理（若现有业务规则未覆盖，需单独决策）；30日退款分母的精确资金截点由指标文档指明未决。
- JSON 商品变更事件强制核心字段与 Schema 版本、Topic key/schema/retention/ISR，历史 CDC 与离线初始化对齐规则。
- 当前仅完成候选规格设计；旧候选 SQL 和测试脚本**不得**被视为此文档的自动实现。
