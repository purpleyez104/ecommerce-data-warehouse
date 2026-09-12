# T4 M2-DEC-015 验收数据规模决策

## Goal

确认固定验收数据的对象数量、日期跨度、边界组合和人工核对成本，形成 `M2-DEC-015` 决策输入。

## Scope

- 确定各业务对象数量与业务日期跨度。
- 确定正常场景和非法场景的数量与组合。
- 将固定数据映射到 `M2-SC-001` 至 `M2-SC-012`。
- 明确固定 Seed 与参数化 Generator 的边界。
- 评估人工核对成本和 ECS 资源限制。

## Confirmed Decisions

- 用户已确认固定验收集采用“人工可核对的小型固定验收集”定位；它不用于 Benchmark 或容量结论。
- 固定验收集覆盖全部 19 张源表与 `M2-SC-001` 至 `M2-SC-012`。
- 固定验收集使用 4 个连续业务日期；异常场景通过独立事务或失败用例执行，不污染正常 seed。
- 各表正常固定 seed 行数确定为：`user_account` 4、`user_address` 4、`visitor` 5、`traffic_channel` 3、`visit_session` 6、`login_event` 4、`page_view_event` 18、`brand` 2、`category` 6、`spu` 4、`sku` 6、`cart_event` 8、`sales_order` 8、`sales_order_item` 12、`payment_attempt` 10、`return_order` 4、`refund_attempt` 5、`coupon` 3、`user_coupon` 5。
- 4 个连续业务日期为 `2025-01-29` 至 `2025-02-01`；正常 seed 必须执行首次运行 1 次及同日完全重跑 1 次。
- 异常验收包含 14 个独立失败用例：5 个 MySQL 约束失败（唯一键、`NOT NULL`、`CHECK`、外键、生成列唯一约束），以及 9 个 Python 写入层失败（非法状态迁移、支付金额不符、累计退单数量超额、累计退款金额超额、金额分摊或舍入不守恒、优惠券过期锁定、优惠券重复使用、无领取记录使用、跨用户使用）。

## Scenario and Table Coverage

- 正常固定 seed 覆盖全部 19 张表；`M2-SC-001` 验证正常闭环及引用完整性。
- `M2-SC-002` 覆盖取消订单及优惠券锁定释放；`M2-SC-003` 覆盖部分/全部退单与退款；`M2-SC-004` 覆盖业务键重复和生成列唯一约束。
- `M2-SC-005` 使用 4 个连续业务日期覆盖跨日下单、支付、取消、退单或退款；`M2-SC-006` 覆盖数据库单行 `CHECK` 及 Python 非法状态迁移拒绝。
- `M2-SC-007`、`M2-SC-008` 分别覆盖外键和空值约束失败；`M2-SC-009` 覆盖两位小数、尾差分摊、支付金额、累计退单/退款和零应付边界。
- `M2-SC-010` 覆盖用户或商品属性变化前后的归属；`M2-SC-011` 覆盖补贴率零分母；`M2-SC-012` 覆盖 4 个优惠券流程失败用例。

## Out of Scope

- 不编写或修改实现代码。
- 不定义 Benchmark 或性能压测规模。
- 不修改商品字段决策 `DR-015`。

## Acceptance Criteria

- [x] 每类业务对象都有明确数量。
- [x] 4 个业务日期的具体范围、重跑次数和失败用例数量明确。
- [x] 固定验收规模与 Benchmark 规模明确分离。
- [x] `M2-DEC-015` 的选择已得到用户确认。

## Verification

- 检查 `M2-SC-001` 至 `M2-SC-012` 是否逐项映射。
- 检查 19 张源表是否都有验收覆盖方式。
- 检查结果与中央规格、计划和既有决策是否一致。


## Parallelism

仅讨论与只读分析可和 T2 并行；中央文档决策由协调会话串行处理。

## Worktree

不需要；这是共享决策任务。

## Conflicting Files / Modules

- `docs/spec.md`
- `docs/plan.md`
- `docs/milestone-2-business-design.md`
- `docs/decision-register.md`
- M2 验收场景定义

## Dependencies

- T1 M2.2 物理规范收口。
