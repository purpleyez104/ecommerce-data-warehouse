-- 回滚只移除新增 DWS 元数据；ADS 新列保留为空，避免破坏性 REPLACE COLUMNS。
DROP TABLE IF EXISTS ecommerce_dws.dws_trade_cohort_day;
