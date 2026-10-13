# Formal Data Generators

当前整体状态为 `verified`（证据范围不同）：Business 21 表 1,328,502 行已在目标 MySQL 完成 `LOAD DATA` 与 45-rule Shared Source Gate；Behavior 3,000,000 事件已完成本地正式规模生成与 Entity Manifest 绑定，全量实体引用、Session 边界和 `event_id` 唯一性检查为 0 违规。Behavior Kafka 与正式 CDC 尚未完成。

两个生成器完全分开，可独立安装、运行和测试：

- [`business_generator/`](business_generator/)：21 张业务表 CSV + Dataset Manifest + Entity Manifest。
- [`behavior_generator/`](behavior_generator/)：读取 Business Entity Manifest，生成 Bootstrap / Continuous 行为 JSONL + Manifest。

两者只通过显式配置中的用户、Visitor、SKU 数量和 Seed 约定共享业务世界，不存在 Python Package 依赖。
