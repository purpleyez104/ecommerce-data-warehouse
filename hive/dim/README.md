# Hive DIM

Milestone 4 已进入 Model Contract 实施。当前原则是：用户、访客、类目和优惠券模板等当前值维度采用 Type 1；商品价格、类目归属、品牌和上下架状态采用 `dim_product_zip` SCD2；身份映射使用源有效区间，不重复建设第二套拉链。具体 DDL/SQL 和 Runtime 验收尚未完成。
