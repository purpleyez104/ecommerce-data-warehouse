-- 将 M3 Pilot 元数据迁入明确的 HISTORY 名称；EXTERNAL 数据位置保持不变，因此不会删除 HDFS 数据。
USE `ecommerce_ods`;

ALTER TABLE `ods_order` RENAME TO `pilot_20260921_ods_order`;
ALTER TABLE `m3_order_stage_20260921_01` RENAME TO `pilot_20260921_order_stage`;
ALTER TABLE `m3_order_stage_hist_20260921_01` RENAME TO `pilot_20260921_order_stage_hist`;
