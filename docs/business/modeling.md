# 建模说明

本文档是当前业务、数据源和指标建模文档的导航入口，不复制各文档的详细定义，也不提高其证据状态。

## 当前建模入口

- [V2 业务基线](business-baseline.md)：自营商城业务规则和验收不变量。
- [业务源设计](../design/business-source-design.md)：21 张 MySQL 表、独立行为源及交付边界。
- [历史初始化与双链路回放设计](../design/historical-incremental-replay-design.md)：正式 90 天数据的切换点、离实时接续、时间审计、重跑和 SCD2 拉链规则。
- [V2 逻辑模型](../source/logical-model.md)：实体、关系、状态和指标字段覆盖。
- [21 表当前物理设计](../source/physical-model.md)：字段级设计与已部署 MySQL / Source Gate 证据边界。
- [M2-03 设计快照](../source/M2-03-物理设计与静态审查.md)：部署前静态快照，不代表当前 Runtime。
- [V2 指标体系](metrics.md)：指标口径、依赖和待细化项。
- [V2 数据规格候选稿](../archive/data-spec-candidate-2026-09-28.md)：2026-09-28 设计输入，整体保持 `candidate`。
- [Benchmark 设计规范](../benchmark/spec.md)：规模与性能证据设计，当前为 `DESIGNED / not_run`。
- [R1 全量快照验收冻结记录](../acceptance/r1_snapshot_acceptance_frozen.md)：指定隔离库 21 表初始 Snapshot 与订单对账的限定范围证据。
- [R1 实时链路验收记录](../acceptance/r1-realtime-acceptance.md)：订单 DWD 首次装载、Doris 100 单汇总及后续验收缺口。
- [M5 退款 Contract 迁移验收](../acceptance/m5-refund-contract-migration-acceptance.md)：申请粒度退款事实、当前 DWS/ADS、Gate、幂等与回滚边界。

## 状态边界

当前 M2 仍为 `in progress`。正式 21 表 DDL、Business 1,328,502 行装载与 45-rule Shared Source Gate 已通过；离线 60/30 Replay、21 表 DataX/Hive ODS、独立 Behavior ODS、14 张 DIM/DWD、6 张 DWS + 1 张 ADS 已完成 Runtime Gate，M3、M4、M5 状态为 `completed`。M5 已完成退款事实迁移、60/60 Model Gate、41/41 Aggregate Gate、36 项 Metric Registry、40 条质量规则与 10 项跨层对账。正式 CDC 尚未通过。R1～R3 只证明 Pilot 范围的 Snapshot、部分 `c/u/d`、Order / OrderItem DWD、Checkpoint 恢复和 Doris Upsert，不是当前在线或正式 CDC 证据，M8/M9 因此保持 `in progress`。旧 19 表实现已删除，仅在 `docs/archive/milestone-2-business-design.md` 保留设计背景。
