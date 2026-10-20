# Doris 验证与分析 SQL

Doris 离线服务表的验证、查询和对账 SQL 放在本目录。M6 当前采用单表 `ecommerce_serving.ads_daily_business_overview`，以 `business_date` 为 `UNIQUE KEY`，同日重跑使用 Merge-on-Write 覆盖同键结果。DDL Contract 位于 `../serving_contract.json`；90 日装载、幂等重跑和 Hive↔Doris 22 字段逐行对账均已 `VERIFIED`。
