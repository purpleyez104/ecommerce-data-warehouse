# V2 Generators

当前整体状态为 `candidate / implemented / not_run`：文件和 Targeted Unit Test 已进入仓库，但正式数据规模、DDL/CSV Contract、`LOAD DATA`、Source Gate 与目标环境 Runtime 尚未完成。

两个生成器完全分开，可独立安装、运行和测试：

- [`business_generator/`](business_generator/)：21 张业务表 CSV + Dataset Manifest。
- [`behavior_generator/`](behavior_generator/)：Bootstrap / Continuous 行为 JSONL + Manifest。

两者只通过显式配置中的用户、Visitor、SKU 数量和 Seed 约定共享业务世界，不存在 Python Package 依赖。
