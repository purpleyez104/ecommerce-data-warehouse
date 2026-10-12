# MySQL 模块边界

本目录保留 V2 正式源库的模块入口。`ddl/001_ecommerce_oltp.sql` 是 2026-10-11 根据目标 MySQL 只读结构核对、业务基线、指标口径和候选物理模型整理的 21 表候选 DDL；它尚未执行、部署或通过 Source Gate，不是 Runtime `verified` 事实。

当前正式库 `ecommerce_oltp` 只存在 3 张技术测试表，没有 21 张 `biz_*`。历史验收库的 21 表主体可复用，但候选 DDL 已移除订单/优惠券循环 FK：保留 `biz_order.coupon_id` 的单向外键，券表反向订单字段只建索引并交由 Source Gate 校验。DDL 不含 `DROP`、`TRUNCATE`、`DELETE`、`INSERT` 或 `IF NOT EXISTS`，对象冲突必须显式失败。

DDL、CSV Contract、Targeted Test、本地正式规模生成和 Behavior 对 Business Entity Manifest 的复用已经完成；下一步是补充可重复、可失败退出的 `LOAD DATA` 和 Source Gate。正式库部署和装载仍需单独数据库变更授权。历史 19 表与 Pilot 资产分别保留在 `archive/legacy-m2-19-table/` 和 `archive/pilot-v1/`。
