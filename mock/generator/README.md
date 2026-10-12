# V2 Generators

当前整体状态为 `candidate / implemented`，并已完成本地正式规模生成与 Entity Manifest 绑定：Business 21 表 1,329,480 行，Behavior 3,000,000 事件；正式规模全量实体引用、Session 边界和 `event_id` 唯一性检查为 0 违规。DDL/CSV 字段已对齐，但 `LOAD DATA`、Source Gate 与目标环境 Runtime 尚未完成。

两个生成器完全分开，可独立安装、运行和测试：

- [`business_generator/`](business_generator/)：21 张业务表 CSV + Dataset Manifest + Entity Manifest。
- [`behavior_generator/`](behavior_generator/)：读取 Business Entity Manifest，生成 Bootstrap / Continuous 行为 JSONL + Manifest。

两者只通过显式配置中的用户、Visitor、SKU 数量和 Seed 约定共享业务世界，不存在 Python Package 依赖。
