# 实时链路 R1/R2 验收记录（仅已发生事实）

> 证据截止：2026-09-23，本 Chat 中最后一次 R2 验收输出。本文不是实时健康报告；仓库提交状态 unknown。

## 已完成范围

- MySQL：`ecommerce_oltp_m2_acceptance` 21 张业务表。冻结样本：100 单（`PAID` 69、`CANCELED` 31）、319 条订单明细。21 表初始快照共 1,178 条，逐表事件数与当时 MySQL 行数相同；只有订单主键及最终状态做过逐条对账，不能据此宣称 21 表全部字段一致。
- Kafka：`ods_cdc_m2_clean_v1` 创建时为 3 partitions、replication factor 3、`min.insync.replicas=2`。冻结快照区间为 partition 0 `[0,1178)`、partition 1/2 均为空。商品变更探针产生 offset 1178、1179（`c`、`d`）；取消事务产生 1183—1184，已逐条核对。最后一次观察的 latest offset 为 `0:1185,1:0,2:0`；这是下一个待写入位置，不是第 1185 条消息的编号。
- CDC：Flink CDC 3.6.0-1.20、独立 Flink Runtime `/data/module/flink-1.20.5-cdc`；私有配置为 `$HOME/.secrets/cdc-r1/mysql-to-kafka.yaml`。2026-09-23 从 `chk-328` 恢复，YARN Application 为 `application_1790128568803_0001`；随后 REST API 观察到 Flink Job `e1364b409a02cb06fec2ae8a14a905c7` 为 `RUNNING`、`restored=1`、恢复后 completed=6、latest=334。当前是否仍在线 unknown。
- 订单 DWD：`OrderDwdJob.java` 的两处 import 已修复；`bash build.sh` 输出 `BUILD_CHECK: PASS` 并生成 `build/r1-order-dwd.jar`。首次装载 100 单后，2026-09-23 从 `chk-114` 恢复，YARN Application 为 `application_1790128568803_0002`；REST API 观察到 Flink Job `8d7eef522ff607f5ff9ca07839c916b1` 为 `RUNNING`、`restored=1`、恢复后 completed=3、latest=117。当前是否仍在线 unknown。
- Doris：`ecommerce_serving.dwd_order` 一行一 `order_id`，采用 `UNIQUE KEY(order_id)`、`function_column.sequence_col=kafka_offset` 和两副本。R2 测试订单经 `CREATED → CANCELED`，对应 offset 从 1180 到 1183；最终总数 101、`PAID` 69、`CANCELED` 32、`CREATED` 0、不同 `order_id` 101。
- R2 Kafka 消息逐条读取通过：offset 1183 是 `biz_order` 的 `op=u`，状态 `CREATED → CANCELED`；offset 1184 是 `biz_order_status_event` 的 `op=c`、`event_type=CANCEL`。这只证明正常顺序的 Upsert，不证明乱序防护或端到端 Exactly-Once。

## 仓库操作入口

- 首次编译：在 `flink/jobs/r1/r1-order-dwd-job/` 执行 `bash build.sh`。
- 首次装载：同目录的 `bash run.sh` 仅适用于目标 Doris 表为空、独立 Checkpoint 尚不存在且无重复写入者的场景；不得用于当前已验收表。
- CDC 恢复：本次从 `hdfs://hadoop201:8020/user/hive/warehouse/ecommerce/flink/checkpoints/cdc_r1_clean_v1/0400e22ef4fa90549e56b94698fe5a81/chk-328/_metadata` 以 `NO_CLAIM` 恢复成功。这是历史记录，不是下一次重启的默认路径。
- DWD 恢复：本次从 `hdfs://hadoop201:8020/user/hive/warehouse/ecommerce/flink/checkpoints/order_dwd_r1_v1/7bc74b857c2db20af92a4c7ed49320d4/chk-114/_metadata` 以 `NO_CLAIM` 恢复成功。这是历史记录，不是下一次重启的默认路径。
- 对账：`scripts/realtime/check_order_dwd_consistency.sh` 是只读 R2 候选脚本，尚未在 ECS 执行；它仅校验 101 单基线与订单核心字段。

## 保留的未知与边界

- 私有 CDC YAML 的完整可公开模板、是否已 `git add/commit/push`、首次提交脚本最终内容以及重启后当前在线状态均为 unknown。
- MySQL 21 表完整最终 DDL unknown；不得据此宣称可完整重建 21 表源库。
- 21 表全字段对账、跨分区版本排序、订单物理 DELETE、旧消息乱序覆盖及本次 R2 更新的故障恢复一致性均未验证；不得写成 Exactly-Once 通过。
- 订单 DWD 仅覆盖 `biz_order`。`biz_order_item`、支付、退款 DWD 和 DWS/ADS 均未在本 Chat 中创建或运行。100 单历史快照与含 `R2_ACCEPT_` 测试订单的 101 单实时状态必须分开记录，经营指标须排除测试订单。
