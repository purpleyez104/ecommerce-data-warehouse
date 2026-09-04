# 架构说明

版本：`0.1-draft`  
状态：设计边界已建立，尚未部署

## 离线主线

```text
MySQL → 数据采集 → Hive ODS → DIM / DWD → DWS → ADS → 数据质量检查
```

- `mysql/`：源表 DDL 与固定种子数据。
- `datax/`：采集任务的候选位置；是否采用 DataX 需经兼容性验证。
- `hive/`：离线分层 SQL，按 ODS、DWD、DWS、ADS 组织。
- `quality/`：可阻断流程的数据质量检查。
- `mock/`：最小样例、边界场景和逐层预期结果。
- `scripts/`：参数化、可重跑的本地运行入口。

DIM 的具体实现位置和历史策略尚待第一阶段业务模型确认。

## 可选扩展

```text
MySQL Binlog → Flink → Doris
```

`spark/`、`flink/`、`doris/` 和 `scheduler/` 仅预留模块边界。它们必须在离线闭环稳定后，分别完成规格、依赖版本、运行命令、恢复策略和验收测试，才能成为正式链路的一部分。

## 配置边界

环境变量示例位于 `env/.env.example`。本仓库不保存真实密码、密钥、生产地址或渲染后的连接配置。
