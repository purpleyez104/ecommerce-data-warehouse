# V2 业务源设计与交付边界

状态：业务规则已形成基线；21 表设计与仓库 DDL 仍为候选。隔离验收库有用户提供的有限历史结果，正式源库和离线接续未验收。更新时间：2026-09-20。

本文件是[最终工程架构](final-architecture-v1.0.md)的业务源视图，服务于当前 Milestone 2，不表示 `docs/plan.md` 的 Milestone 3 已进入。业务语义以[业务基线](business/business-baseline-v2.md)、指标以[指标口径](metrics.md)、实体关系以[逻辑模型](source/logical-model-v2.md)、字段以[候选物理设计](source/physical-model-v1.md)为准；本文不复制字段级契约。

## 数据源与业务边界

模拟自营商城服务通过 MySQL 事务写入交易当前状态和不可变关键事件，Binlog 是交易 CDC 的唯一来源。页面、商品和购物车行为来自独立行为源，写入 Kafka；不得让生成器直接写 Kafka 冒充 MySQL CDC，也不得使用业务服务对 MySQL/Kafka 双写交易状态。当前一期覆盖身份、商品、购物车、订单、支付、基础退款和订单券；库存流水、完整物流、复杂营销及完整售后留待二期。

| 分组 | 当前 21 张候选 MySQL 表 | 核心责任 |
| --- | --- | --- |
| 身份（3） | `biz_user`、`biz_visitor`、`biz_identity_mapping` | 用户/访客分离、可靠映射及版本修订 |
| 商品（4） | `biz_category`、`biz_spu`、`biz_sku`、`biz_product_change_event` | Category→SPU→SKU 与属性变更历史 |
| 购物车（3） | `biz_cart`、`biz_cart_item`、`biz_cart_merge_record` | 所有者互斥、SKU 数量与合并幂等 |
| 订单（3） | `biz_order`、`biz_order_item`、`biz_order_status_event` | 成交快照、金额分摊、订单状态历史 |
| 支付（2） | `biz_payment_attempt`、`biz_payment_event` | 多次尝试、唯一有效成功及回调幂等 |
| 退款（3） | `biz_refund_request`、`biz_refund_transaction`、`biz_refund_event` | 单明细申请、资金重试及额度守恒 |
| 优惠券（3） | `biz_coupon_template`、`biz_coupon`、`biz_coupon_event` | 模板、实例、锁定/使用/释放历史 |

行为事件不计入这 21 张表。其稳定事件键、业务时间、采集时间、访客/用户、会话及适用的 SKU/页面/数量字段须在正式 Kafka Schema 评审时冻结；三组正式 Topic 名称、分区和保留期目前未确认。

## 一期不可变规则

- 订单每单 1～5 个不重复 SKU，明细冻结商品和价格快照；`CREATED` 只能转 `PAID` 或 `CANCELED`，支付窗口为 15 分钟，已支付不得取消。
- 所有资金金额使用整数分。订单头、明细、优惠分摊、有效成功支付和退款必须可对账；一单最多一次有效成功支付，一次退款申请只关联一条订单明细且最终完整成功或失败。
- 当前状态和事件历史在同一 MySQL 事务提交；历史事件不能被当作第二份可累加交易事实。身份歧义保持匿名并保留映射版本，不静默覆盖历史归属。
- 购物车登录合并按 SKU 数量相加、单 SKU 上限 99，超限裁剪并留证；重复合并操作不得再次累加。订单级至多使用一张固定金额券，退款不返券。

## 当前交付与未验证项

仓库保留候选 SQL `mysql/ddl/001_ecommerce_oltp_v1.sql` 和 `docs/source/M2-03-物理设计与静态审查.md`。后者记录的是当时 21 张 `biz_*` 建表语句已生成、结构性静态检查通过、尚未部署的设计快照；不能用它否定后续历史验收，也不能用后续摘要推断仓库 DDL 与当前 MySQL 逐字一致。`mysql/ddl/reference/001_ecommerce_oltp_m2_acceptance.sql` 仅为隔离库参考 DDL，旧同名 Seed 已单独归档。

用户提供的 2026-09-19～20 终端结果摘要记录：隔离验收库的 21 表 CDC 初始快照中 19 张非空表合计 32 条，两张原空表的 INSERT/DELETE 探针成功；`smoke-v1-001` 有 10 单 34 明细，`hist-v1-001` 有 100 单 319 明细，两个批次的订单 CDC 创建及最终状态得到核对。摘要未保存在仓库，本次未连接 VM 或执行导入的 `.sh`。这些结果只支持指定隔离库、批次和订单 CDC 范围，不代表逐表完整 CRUD、正式 Topic、当前在线状态或端到端 Exactly-Once。

`mock/generator/ecommerce_generator_v1/` 与对应测试已入库，属于文件级 `implemented`。其可缺省的 `--anchor`、重复 run-id 拒绝和浮动依赖版本与项目正式批任务契约尚未收敛；固定 Seed、现存 MySQL DDL 导出比对、90 天数据、DataX/CDC 接续均仍待完成。

90 天历史及日均约 1 万单/10 万行为事件是[业务基线](business/business-baseline-v2.md)中的设计目标，不是已生成规模或实测吞吐；历史 100 单批次不能替代它们。当前仍需确认零元订单、SKU 最小库存属性、行为 Topic/归档、身份版本边界和 DataX/CDC 初始化切换点；正式源库、固定 Seed、Generator 契约和离线接续均须分别验收。

## 进入后续阶段的门禁

先导出当前 MySQL 的 `SHOW CREATE TABLE`，与候选 DDL 比对并确认正式源库；补齐固定 Seed、显式日期/重跑/版本契约及事务不变量，再验证正式 21 表 Binlog、历史初始化和 DataX 抽取接续。已有[ENV-05 验收](acceptance/env-05-cdc-acceptance.md)只覆盖单个隔离测试表；后续用户提供的隔离库 21 表结果也不足以解除全部业务源门禁。Milestone 3 继续保持 `pending`。
