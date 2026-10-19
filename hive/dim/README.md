# Hive DIM

Milestone 4 的首批 Model Contract 已在 `hive/model/model_contract.json` 实现：用户、访客、类目和优惠券模板等当前值维度采用 Type 1；商品价格、类目归属、品牌和上下架状态采用 `dim_product_zip` SCD2；身份映射使用源有效区间，不重复建设第二套拉链。6 张 DIM 在旧 Contract 中通过 59/59 Model Gate；M5 退款事实修正后，全量当前 Model Gate 已再次通过 60/60，维度 Contract 未改变。
