# V2 业务源设计与交付边界

状态：业务规则已形成基线；21 表 DDL、Business Generator、正式源库 `LOAD DATA` 与 Shared Source Gate 已完成 Runtime 验收。离线 100 单与实时 R1～R3 已转为 Pilot / Acceptance / History；60 天初始化与 30 天双链路回放为 `DESIGNED / not_run`，批量 ODS、Formal CDC 和离线接续仍未验收。更新时间：2026-10-13。

本文件是[最终工程架构](../architecture/final-architecture.md)的业务源视图。业务语义以[业务基线](../business/business-baseline.md)、指标以[指标口径](../business/metrics.md)、实体关系以[逻辑模型](../source/logical-model.md)、字段以[当前物理设计](../source/physical-model.md)为准；本文不复制字段级契约。Milestone 2 的 Source Gate 和 Milestone 3 的 ODS Runtime Gate 已通过，当前进入 Milestone 4 DIM/DWD 模型门禁。

## 数据源与业务边界

模拟自营商城服务通过 MySQL 事务写入交易当前状态和不可变关键事件，Binlog 是交易 CDC 的唯一来源。页面、商品和购物车行为来自独立行为源，写入 Kafka；不得让生成器直接写 Kafka 冒充 MySQL CDC，也不得使用业务服务对 MySQL/Kafka 双写交易状态。当前一期覆盖身份、商品、购物车、订单、支付、基础退款和订单券；库存流水、完整物流、复杂营销及完整售后留待二期。

| 分组 | 当前 21 张正式 MySQL 表 | 核心责任 |
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

仓库保留 `docs/source/M2-03-物理设计与静态审查.md` 作为早期设计快照。2026-10-12 已在正式库 `ecommerce_oltp` 部署并验收 21 张 `biz_*` 表，原有 3 张技术测试表未删除或覆盖；历史验收库 `ecommerce_oltp_m2_acceptance` 继续仅作为 1,178 行 Pilot 与 CDC 历史证据。

`mysql/ddl/001_ecommerce_oltp.sql` 已在正式库部署，CSV Contract 已补齐 `biz_order_item.updated_at`、`biz_payment_attempt.created_at`、`biz_refund_request.created_at`、`biz_refund_transaction.created_at`。DDL 保留 `biz_order.coupon_id → biz_coupon.coupon_id` 单向物理 FK；`locked_order_id`、`used_order_id` 只建索引，反向一致性由 Generator 与 Source Gate 校验，避免循环 FK 阻碍 21 CSV 装载。生成列不进入 CSV Contract。后续结构或 CSV Contract 变化必须重新执行 Schema Contract 与 Source Gate。

`docs/acceptance/r1_snapshot_acceptance_frozen.md` 已保存 2026-09-21 的限定范围证据：`ecommerce_oltp_m2_acceptance` 的 21 表共 1,178 行，与 `ods_cdc_m2_clean_v1` 固定审计区间内的 1,178 条初始快照事件一致；100 笔订单主键和最终状态对账通过，旧污染 Topic 已隔离。该结果只支持指定隔离库、固定 Offset 区间和订单对账范围，不代表逐字段对账、正式源库、当前在线状态或端到端 Exactly-Once；acceptance 源库与 Topic 现只作为 Pilot History 保留。

后续 [R1 实时链路验收记录](../acceptance/r1-realtime-acceptance.md)补充证明 `biz_product_change_event` 的隔离 INSERT、DELETE 已分别以 `op=c`、`op=d` 到达 Kafka。该证据不包含 `biz_order` 的 `op=u`，也不证明其他 20 表持续增量、恢复后接续或正式源库 CDC 已通过。

仓库内 `archive/pilot-v1/ecommerce_generator_v1/` 与对应测试定位为 Pilot History，不作为正式入口；服务器工作目录中的旧 19 表 `generator/` 和旧 21 表 Pilot `tools/ecommerce_generator_v1/` 已按用户指示删除。`mock/generator/business_generator/` 已完成正式规模生成、目标 MySQL 装载与 Source Gate，`mock/generator/behavior_generator/` 已完成本地正式规模及 Entity Manifest 绑定；共享历史生成路径为 Python Generator → 21 CSV → `LOAD DATA` → `ecommerce_oltp`。后续逐日实时回放仍需 Incremental Business Generator 通过 MySQL Transaction 产生 Binlog，禁止直接写 Kafka。各 Generator 可共享业务规则，但数据库写入方式和验收责任不同。

正式数据规模为 90 天、100,000 笔订单、285,000 条订单明细、实测 1,328,502 条 OLTP 记录和 3,000,000～5,000,000 条行为事件；性能实验规模为约 900,000 笔订单和 9,000,000 条行为事件。新 Generator 不建设独立 Smoke 数据档位，仓库中的 `smoke.json` 仅是快速单元测试 Fixture，历史 100 单批次仍只作 Pilot History。Business 输出版本化 Entity Manifest 与 SHA-256，已在目标 MySQL 完成装载与 45-rule Source Gate；Behavior 强制读取该 Manifest，并在 3,000,000 事件规模全量验证实体引用、30 分钟 Session 和 `event_id` 唯一性。行为 Topic/归档、DataX 批量 ODS 和正式 CDC 初始化切换点仍待实施。

## 历史初始化与每日回放 Contract

根据 `DR-037`，90 天正式观察窗口的链路验收采用“前 60 天历史初始化 + 后 30 天逐日双链路回放”。`cutover_time` 为第 61 个业务日零点；初始化源必须呈现该时点的正确当前状态，不能包含后 30 天才发生的最终变化。

Generator 后续需要在不改变既有正式 bundle 证据的前提下，增加一个 bootstrap 包和 30 个 daily 操作包。bootstrap 包含切换点当前状态、前 60 天事实/事件和维度变化历史；daily 包包含当天新增、对历史记录的更新、状态事件、维度变化及预期对账。交易 daily 包必须通过 MySQL Transaction 产生 Binlog；Behavior daily 包由独立行为源写 Kafka。

现有一次性 90 天最终 bundle、正式 MySQL 和 Source Gate 继续作为规模与业务 Contract 证据，不能外推为时间推进式回放已实现。完整时间、分区、离实时接管与拉链规则见[历史初始化与双链路回放设计](historical-incremental-replay-design.md)。

## 进入后续阶段的门禁

Shared Source Gate 已通过。下一步先实现 bootstrap/daily 输入 Contract 与隔离的时间推进式源状态，再让离线进入批量 ODS、实时进入 Topic/Checkpoint Inventory、Formal CDC Contract 和 21 表 Snapshot。已有正式源、Pilot 与 ENV-05 证据继续保留，但不足以解除 60/30 回放、CDC、ODS 或模型门禁；本设计不授权重置现有正式库。
