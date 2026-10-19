-- M5-02 元数据回滚：新表是 EXTERNAL，DROP 只移除元数据，不删除新 Location 数据。
-- 仅在需要恢复旧 Contract 时执行；旧 HISTORY 表及其原数据必须仍存在。

DROP TABLE ecommerce_dwd.dwd_refund;
ALTER TABLE ecommerce_dwd.m5_20261018_history_dwd_refund
RENAME TO ecommerce_dwd.dwd_refund;

DROP TABLE ecommerce_dws.dws_trade_day;
ALTER TABLE ecommerce_dws.m5_20261018_history_dws_trade_day
RENAME TO ecommerce_dws.dws_trade_day;

DROP TABLE ecommerce_ads.ads_daily_business_overview;
ALTER TABLE ecommerce_ads.m5_20261018_history_ads_daily_business_overview
RENAME TO ecommerce_ads.ads_daily_business_overview;
