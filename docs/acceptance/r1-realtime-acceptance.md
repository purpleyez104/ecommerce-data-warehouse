# R1 实时链路验收记录

## 1. 记录范围

本记录依据实时链路 Chat 中实际执行的命令和返回结果整理。最后一次有明确时间依据的订单 DWD 运行观察为 2026-09-22 13:44（Asia/Shanghai）。本文记录历史验收结果，不代表组件当前仍在线。

已建设的限定范围链路为：

```text
MySQL ecommerce_oltp_m2_acceptance
  → Flink CDC
  → Kafka ods_cdc_m2_clean_v1
  → Flink OrderDwdJob
  → Doris ecommerce_serving.dwd_order
```

Kafka 承担当前实时 ODS 输入；当前只实现订单当前状态 DWD。DWS、ADS、其他实时事实表和正式实时指标不属于本记录的已建设范围。

## 2. MySQL 基线

| 项目 | 历史验收结果 |
| --- | --- |
| 数据库 | `ecommerce_oltp_m2_acceptance` |
| 业务表 | 21 张 |
| 订单 | 100 |
| `PAID` | 69 |
| `CANCELED` | 31 |
| 金额异常订单 | 0 |
| 孤儿订单明细 | 0 |
| 重复成功支付订单 | 0 |

完整 21 表源 DDL 未在本次实时链路 Chat 中逐表核实。该隔离库结果不能外推为正式源库结构或固定 Seed 已验收。后续 R2 证据见 [R1/R2 验收记录](realtime_r1_r2_verified.md)。

## 3. CDC 与 Kafka

| 项目 | 历史事实或边界 |
| --- | --- |
| Flink CDC | 3.6.0-1.20 |
| Flink Runtime | 1.20.5-cdc |
| CDC Application | `application_1789972455214_0006`；2026-09-21 18:18 曾观察为 `RUNNING`，当前状态 `unknown` |
| Topic | `ods_cdc_m2_clean_v1` |
| Topic 配置 | 3 Partition、3 Replication Factor、`min.insync.replicas=2` |
| Snapshot 审计区间 | Partition 0 `[0,1178)`；Partition 1、2 `[0,0)` |
| Snapshot 结果 | 1,178 条；21 表事件数与 MySQL 行数一致；100 单主键及最终状态一致 |

商品事件增量测试在 `biz_product_change_event` 上观察到同一隔离测试记录的 `op=c` 和 `op=d`。R2 已额外观察到 `biz_order` 的一次合法 `CREATED → CANCELED` 的 `op=u`；这只证明该正常顺序 Upsert，其他 20 表持续增量、乱序及完整一致性仍未验证。

旧 Topic `cdc_m2_21tables_acceptance` 曾包含 12 笔额外历史订单，不作为当前订单 DWD 输入。现有 Topic 不得因复现本文而删除或重建。

私有 CDC 配置位于 `/home/yee/.secrets/cdc-r1/mysql-to-kafka.yaml`，包含凭据，不得进入 Git。历史提交使用 YARN Application Mode、独立 Flink Runtime 和 HDFS Checkpoint 路径：

```text
hdfs://hadoop201:8020/user/hive/warehouse/ecommerce/flink/checkpoints/cdc_r1_clean_v1
```

R2 已从 `chk-328` 恢复并观察到恢复后 6 次 completed Checkpoint；存在 Checkpoint 文件或该次恢复均不等于端到端 Exactly-Once 或完整恢复能力已验收。

## 4. 订单 DWD

仓库工程路径为 `flink/jobs/r1/r1-order-dwd-job/`。实时链路 Chat 记录 `build.sh` 编译成功并生成 `build/r1-order-dwd.jar`；构建产物不进入 Git。

历史首次装载的 YARN Application 为 `application_1790055138808_0001`。R2 后从 `chk-114` 恢复为 `application_1790128568803_0002`，并观察到 Flink Job `8d7eef522ff607f5ff9ca07839c916b1` 为 `RUNNING`、恢复后 3 次 completed Checkpoint；当前 Application 状态仍为 `unknown`。

DWD Checkpoint 路径为：

```text
hdfs://hadoop201:8020/user/hive/warehouse/ecommerce/flink/checkpoints/order_dwd_r1_v1
```

订单作业只接受 `biz_order` 的 `c`、`u`、`r`，拒绝物理删除和非法状态。当前以 Kafka Offset 作为 Doris Sequence，只在订单事件全部位于 Partition 0 且 Topic 未重建时有效；该规则不是多分区或 Topic 重建后的通用版本方案。

## 5. Doris 验收

| 项目 | 历史验收结果 |
| --- | --- |
| 数据库与表 | `ecommerce_serving.dwd_order` |
| 模型 | `UNIQUE KEY(order_id)` |
| Sequence | `kafka_offset` |
| 副本与分桶 | `replication_num=2`，2 Buckets |
| BE | 2026-09-21 检查时 `hadoop202`、`hadoop203` 均 Alive |
| 行数 | R1 为 100；R2 探针后为 101 |
| `PAID` | 69 |
| `CANCELED` | R1 为 31；R2 探针后为 32 |
| 不同订单 ID | R1 为 100；R2 探针后为 101 |

R2 已核对测试订单的最终状态与 Doris Upsert 汇总；仓库可复核入口 `scripts/realtime/check_order_dwd_consistency.sh` 为 `implemented / not_run`，尚未形成 101 单逐行核心字段的 ECS Runtime 结论。该入口不涵盖全字段、事务、乱序或恢复一致性。实际执行过的建表语句保存于 `doris/ddl/dwd_order_create.sql`；现有表不得重复创建或通过 DROP/重建覆盖已验收数据。

## 6. 验收结论

### 已通过的限定范围

- 21 表初始 Snapshot 表级行数对账。
- Snapshot 订单主键及最终状态对账。
- `biz_product_change_event` 的 Binlog INSERT、DELETE 到 Kafka。
- Java DataStream Jar 的构建及 YARN Application Mode 提交。
- 订单 DWD 首次装载及 Doris 100 单汇总核对。

### 未通过或未验证

- 当前 CDC、DWD Application 和 Doris BE 在线状态。
- 两个 Flink 作业的 Completed Checkpoint 次数和最近成功时间。
- 合法订单 UPDATE 的 Kafka、DWD 与 Doris Upsert。
- R2 后当前 MySQL 与 Doris 的逐订单主键、状态及核心金额对账（仓库脚本尚未 ECS 执行）。
- Flink 中断期间源端继续写入后的恢复及 R2 更新的一致性。
- 端到端 Exactly-Once、多分区订单版本、Topic 重建后版本和物理 DELETE 语义。
- DWS、ADS、其他实时事实表及离线 T+1 指标对账。

因此，本记录只把订单 DWD 首次装载提升为限定范围的历史 Runtime 事实；Milestone 8、9 继续保持 `in progress`，不能标记为完整 `verified`。

## 7. 后续检查与安全边界

R1 冻结 100 单对账入口为：

```bash
bash tests/realtime/check_dwd_order_consistency.sh
```

该脚本写入仓库时状态为 `implemented / not_run`。R2 的 101 单只读入口为 `scripts/realtime/check_order_dwd_consistency.sh`，同为 `implemented / not_run`；只有在目标 ECS 返回退出码 `0` 并输出相应 PASS 标识后，才能追加对应 Runtime 结论。

在当前状态未知时，不得删除 Topic、Checkpoint、消费者组或 Doris 表，不得重新提交同一写入作业。订单 UPDATE 验收必须选择符合 `CREATED → PAID/CANCELED` 状态机的隔离业务操作，并在执行任何数据写入前单独确认输入、预期结果和回滚边界。
