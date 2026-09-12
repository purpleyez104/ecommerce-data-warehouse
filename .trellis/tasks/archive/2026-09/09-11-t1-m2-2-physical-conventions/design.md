# T1 M2.2 物理规范收口设计

## 设计边界

本 Task 只冻结 19 张 MySQL 源表的 Schema 级物理规则，作为 T2 Candidate DDL 的输入。它不生成 SQL，不连接 MySQL，也不改变 `DR-013` 至 `DR-018` 已确认的 19 张表、230 个字段、关系或业务约束语义。

## 命名台账

- 台账共 183 项：19 个逻辑 PK、30 个 UQ、42 个 CHECK、32 个 FK、60 个非唯一二级索引。
- `pk_<table>` 是文档与静态检查中的逻辑标识；MySQL Candidate DDL 使用 `PRIMARY KEY`，实际 Primary Key 索引名为 `PRIMARY`。
- 其余 `UNIQUE`、`CHECK`、`FOREIGN KEY` 和非唯一二级索引使用 `docs/milestone-2-business-design.md` 8.9.1 的显式名称，并在 19 张表范围内唯一。

## 生成列

- `payment_attempt.successful_order_pk` 使用 `VIRTUAL GENERATED ALWAYS`，成功时派生 `order_pk`，并由 `uq_payment_attempt_successful_order` 保证一单最多一笔成功支付。
- `refund_attempt.successful_return_order_pk` 使用 `VIRTUAL GENERATED ALWAYS`，成功时派生 `return_order_pk`，并由 `uq_refund_attempt_successful_return_order` 保证一张退单最多一笔成功退款。
- 采用 `VIRTUAL` 是因为派生值没有独立读取或审计保留需求；唯一二级索引仍保存判重键。该结论是 MySQL 8.0.46 Candidate DDL 的静态设计，运行行为留到 M2.5 验证。

## FK 拓扑与顺序

19 表创建顺序固定为：

1. `user_account`
2. `visitor`
3. `traffic_channel`
4. `brand`
5. `category`
6. `coupon`
7. `user_address`
8. `visit_session`
9. `spu`
10. `sku`
11. `user_coupon`
12. `login_event`
13. `page_view_event`
14. `cart_event`
15. `sales_order`
16. `sales_order_item`
17. `payment_attempt`
18. `return_order`
19. `refund_attempt`

回滚顺序必须是上述顺序的精确反向。`category.parent_category_pk` 是唯一同表自引用，不构成表级创建循环；seed 必须先写父级再写子级。

## 证据与状态边界

- 静态检查可以证明台账唯一性、FK 父表先建和回滚顺序一致。
- 静态检查不能证明 MySQL 语法、生成列唯一索引行为、约束执行效果或索引性能。
- T1 完成后进入 T2 生成 Candidate DDL；MySQL 运行验收仍受 M1 MySQL 门禁和 M2.5 隔离测试库约束。

## 回滚

如目标 MySQL 版本或迁移工具证明物理映射不可用，保留 `DR-017` 的业务语义，新增替代决策并同步调整设计、Candidate DDL 和静态检查；不得静默切换 Trigger、Stored Procedure 或取消唯一保护。
