# 建模说明

本文档是当前业务、数据源和指标建模文档的导航入口，不复制各文档的详细定义，也不提高其证据状态。

## 当前建模入口

- [V2 业务基线](business/business-baseline-v2.md)：自营商城业务规则和验收不变量。
- [业务源设计](business-source-design.md)：21 张 MySQL 表、独立行为源及交付边界。
- [V2 逻辑模型](source/logical-model-v2.md)：实体、关系、状态和指标字段覆盖。
- [21 表候选物理设计](source/physical-model-v1.md)：字段级候选设计，不等于现存 MySQL 结构。
- [M2-03 设计快照](source/M2-03-物理设计与静态审查.md)：部署前静态快照，不代表当前 Runtime。
- [V2 指标体系](metrics.md)：指标口径、依赖和待细化项。

## 状态边界

当前 M2 仍为 `in progress`。目录、候选 DDL、Generator 文件和静态检查不能替代固定 Seed、正式库结构核对、批处理契约、DataX 接续或运行验收。旧 19 表设计只保留在 `docs/archive/` 和 `archive/legacy-m2-19-table/`，不作为当前 V2 实现输入。
