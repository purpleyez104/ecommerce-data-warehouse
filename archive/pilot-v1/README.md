# Pilot V1 历史归档

本目录保存离线 100 单与实时 R1～R3 Pilot 的代码、脚本和参考文件。它们统一属于 `PILOT / ACCEPTANCE / HISTORY`，不是 Shared V2 Source Data Build 的正式入口。

## 目录

- `ecommerce_generator_v1/`：旧 100 单 Generator。
- `offline/reference/`：`ods_order` DDL、分区发布重建稿和固定基线质量检查；仓库文件状态为 `implemented / not_run`。
- `realtime/flink/order-dwd-job/`：Order DWD Prototype / Framework Reference。历史 Chat 有限定范围 Runtime 证据，但当前文件与当次服务器执行内容未逐字核对。
- `realtime/cdc/`、`realtime/kafka/`：隔离验收配置模板和提交辅助脚本。
- `realtime/doris/`：历史订单 DWD 建表语句。
- `realtime/acceptance/`：只读订单对账脚本，状态为 `implemented / not_run`。

历史 ECS 路径继续保留在验收和 File Baseline 文档中作为来源证据。归档路径变化不表示脚本重新执行、组件当前在线或链路状态提升。运行任何归档资产前，必须重新确认目标环境、输入、Checkpoint、表数据和回滚边界。
