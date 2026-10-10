# 建模说明

本文档是当前业务、数据源和指标建模文档的导航入口，不复制各文档的详细定义，也不提高其证据状态。

## 当前建模入口

- [V2 业务基线](business/business-baseline-v2.md)：自营商城业务规则和验收不变量。
- [业务源设计](design/business-source-design.md)：21 张 MySQL 表、独立行为源及交付边界。
- [V2 逻辑模型](source/logical-model-v2.md)：实体、关系、状态和指标字段覆盖。
- [21 表候选物理设计](source/physical-model-v1.md)：字段级候选设计，不等于现存 MySQL 结构。
- [M2-03 设计快照](source/M2-03-物理设计与静态审查.md)：部署前静态快照，不代表当前 Runtime。
- [V2 指标体系](business/metrics.md)：指标口径、依赖和待细化项。
- [V2 数据规格候选稿](design/v2-data-spec-candidate.md)：2026-09-28 设计输入，整体保持 `candidate`。
- [Benchmark 设计规范](benchmark/spec.md)：规模与性能证据设计，当前为 `DESIGNED / not_run`。
- [R1 全量快照验收冻结记录](acceptance/r1_snapshot_acceptance_frozen.md)：指定隔离库 21 表初始 Snapshot 与订单对账的限定范围证据。
- [R1 实时链路验收记录](acceptance/r1-realtime-acceptance.md)：订单 DWD 首次装载、Doris 100 单汇总及后续验收缺口。

## 状态边界

当前 M2 仍为 `in progress`。R1 冻结记录只把指定初始 Snapshot 与订单对账提升为限定范围 `verified`，它不是项目阶段或 M8/M9 状态依据。后续实时链路 Chat 另证明 `biz_product_change_event` 的 `op=c/d`、订单 DWD Java Job 构建与首次装载，以及 Doris 100 单汇总；订单 UPDATE、逐行对账、Completed Checkpoint、恢复和端到端一致性仍未验证。M8/M9 因此保持 `in progress`，其他事实表、DWS/ADS 和实时指标不得据此提升状态。目录、候选 DDL、Generator 文件和静态检查也不能替代固定 Seed、正式库结构核对、批处理契约、DataX 接续或完整运行验收。旧 19 表代码与设计分别保留在 `archive/legacy-m2-19-table/`、`docs/archive/milestone-2-business-design.md`，仅作为历史材料。
