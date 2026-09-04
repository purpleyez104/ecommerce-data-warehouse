# 架构说明

版本：`0.2-draft`
状态：设计边界已建立，尚未部署

## 离线主线

```text
MySQL → DataX → Hive ODS（HDFS ORC + Snappy）→ DIM / DWD → DWS → ADS → 数据质量与逐层对账 → Doris
```

- `mysql/`：源表 DDL 与固定种子数据。
- `datax/`：通过 HDFS Writer 直接写入 Hive ODS 对应 HDFS 业务日期分区的全量和增量抽取任务；真实兼容性与运行行为待 Milestone 1、3 验证。
- `hive/`：离线分层 SQL，按 ODS、DWD、DWS、ADS 组织；ODS 同时具有 Hive 逻辑表和 HDFS 物理存储两层含义。
- `quality/`：可阻断流程的数据质量检查。
- `mock/`：最小样例、边界场景和逐层预期结果。
- `scripts/`：参数化、可重跑的本地运行入口。

DIM 的具体实现位置和历史策略尚待第一阶段业务模型确认。

本项目不建设独立持久化的中间数据层。ODS 装载负责 ORC + Snappy 输出、Hive 分区注册、`business_date`、`extract_time`、`batch_id`、`source_table` 审计字段、幂等发布和失败隔离；在真实验证完成前不得把该路径标记为 `verified`。

## 可选扩展

```text
MySQL Binlog → Flink → Doris
```

`spark/`、`flink/`、`doris/` 和 `scheduler/` 仅预留模块边界。它们必须在离线闭环稳定后，分别完成规格、依赖版本、运行命令、恢复策略和验收测试，才能成为正式链路的一部分。

## 配置边界

环境变量示例位于 `env/.env.example`。本仓库不保存真实密码、密钥、生产地址或渲染后的连接配置。
