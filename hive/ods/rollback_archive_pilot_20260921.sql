-- 仅在正式 ods_order 尚未创建或已按单独授权移除时执行；本文件不会删除数据。
USE `ecommerce_ods`;

ALTER TABLE `pilot_20260921_ods_order` RENAME TO `ods_order`;
ALTER TABLE `pilot_20260921_order_stage` RENAME TO `m3_order_stage_20260921_01`;
ALTER TABLE `pilot_20260921_order_stage_hist` RENAME TO `m3_order_stage_hist_20260921_01`;
