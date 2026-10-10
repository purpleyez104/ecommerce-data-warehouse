# R1 全量快照验收冻结记录

- **冻结日期**：2026-09-21（Asia/Shanghai）
- **验收对象**：电商实时数仓第一阶段 MySQL → Flink CDC → Kafka 初始全量快照
- **冻结结论**：全量快照的表级行数及订单主键、最终状态对账通过；增量、完整内容、Checkpoint 成功次数不包含在本结论内。
- **证据来源**：本轮用户在 hadoop201 执行并回传的 SQL、YARN、Kafka、HDFS 和 Kafka/MySQL 对账输出。
- **用途边界**：本文件是 2026-09-21 的事实快照。文中的原 `R1-6`、`R1-7` 仅是当时对话与执行建议的内部编号，不是项目 Milestone、当前阶段或 M8/M9 状态依据。

## 1. 冻结配置与有效范围

| 项目 | 冻结值或事实 |
|---|---|
| MySQL 数据库 | `ecommerce_oltp_m2_acceptance` |
| 业务表数量 | 21 |
| Kafka 正式开发输入 | `ods_cdc_m2_clean_v1` |
| Topic 元数据 | 3 分区、3 副本、`min.insync.replicas=2`，创建时各分区 ISR 3/3 |
| Flink CDC YARN Application | `application_1789972455214_0006`；2026-09-21 16:06 的检查显示 RUNNING |
| 启动方式 | YARN Application，显式 `--flink-home /data/module/flink-1.20.5-cdc` |
| 全量与增量模式 | `scan.startup.mode: initial` |
| 连接与认证 | CDC 用户 `caching_sha2_password`；客户端 TLS 测试的 `Ssl_cipher=TLS_AES_256_GCM_SHA384`，配置已增加 JDBC 和 Debezium TLS 参数 |
| Checkpoint 位置 | `hdfs://hadoop201:8020/user/hive/warehouse/ecommerce/flink/checkpoints/cdc_r1_clean_v1` |
| Checkpoint 观察 | 目录内存在 `chk-9/_metadata`；尚未核验 Web UI 的 Completed 次数 |
| Kafka 快照审计边界 | Partition 0：`[0,1178)`，Partition 1：`[0,0)`，Partition 2：`[0,0)`；为本次审计固定读取区间，并非持续消费终点 |
| Kafka 数据来源 | 审计区间共 1,178 条，`source.db` 全部等于目标数据库，没有缺失 `source.table` |

## 2. 21 张表逐表行数核对

以下为审计时 MySQL 当前行数与 Kafka 固定边界内事件数；这批消息的 `op` 均为 `c`。仅表示该审计区间的表级计数一致，不等价于全部字段逐行对账。

| 业务表 | MySQL 行数 | Kafka 事件数 |
|---|---:|---:|
| biz_cart | 6 | 6 |
| biz_cart_item | 3 | 3 |
| biz_cart_merge_record | 2 | 2 |
| biz_category | 6 | 6 |
| biz_coupon | 60 | 60 |
| biz_coupon_event | 180 | 180 |
| biz_coupon_template | 3 | 3 |
| biz_identity_mapping | 2 | 2 |
| biz_order | 100 | 100 |
| biz_order_item | 319 | 319 |
| biz_order_status_event | 200 | 200 |
| biz_payment_attempt | 82 | 82 |
| biz_payment_event | 82 | 82 |
| biz_product_change_event | 3 | 3 |
| biz_refund_event | 54 | 54 |
| biz_refund_request | 18 | 18 |
| biz_refund_transaction | 18 | 18 |
| biz_sku | 15 | 15 |
| biz_spu | 8 | 8 |
| biz_user | 12 | 12 |
| biz_visitor | 5 | 5 |
| **合计** | **1178** | **1178** |

## 3. 订单对账

| 检查项 | 实际结果 |
|---|---|
| MySQL 订单数 / Kafka 重建最终订单数 | 100 / 100 |
| MySQL 状态 / Kafka 状态 | PAID 69、CANCELED 31 / PAID 69、CANCELED 31 |
| Kafka `biz_order` 创建事件 / 不同创建主键 | 100 / 100 |
| 多余订单 | 0 |
| 缺失订单 | 0 |
| 订单最终状态不一致 | 0 |
| 非目标数据库事件、缺少表名、额外表 | 均为 0 |
| 最终订单对账结果 | `ORDER RECONCILIATION: PASS` |

此前旧 Topic `cdc_m2_21tables_acceptance` 的审计出现比 MySQL 多 12 笔订单，已经隔离，不作为正式开发输入。本次新 Topic 的快照审计不含该 12 笔。

## 4. 冻结边界和后续约束

1. 不再重建 MySQL 100 单样本、不重建新 Topic、不重新提交正常运行中的 CDC 作业；不从旧污染 Topic 回放历史消息。
2. 保持当前 CDC YAML、TLS 和运行环境不变；若发生故障，先核对当前 Application/Checkpoint/Offset，再按实际异常修复。
3. 后续正常增量从快照审计区间的末端继续出现。审计边界是 `[0,1178)`，不要求业务运行期间 Offset 永远为 1178。
4. 未完成验证的事项：Flink Web UI Checkpoints Completed 次数；真实 Binlog 新增、更新、删除事件；除订单主键和最终状态之外的全字段对账；Doris 业务模型与指标口径验收。
5. 不能仅凭 HDFS 存在 `chk-9/_metadata` 就宣称端到端 Exactly-Once 或完整恢复保障已经验收。

## 5. 冻结时点的后续建议（非项目阶段）

### 当时建议一：Checkpoint 与增量 CDC 验收

- 在 YARN Application 的 Flink Web UI → Checkpoints 核对至少一次 Completed，并记录 Job ID 和最近完成时间。
- 优先只读确认可用的业务事件表 DDL、主键、约束与测试写入路径；不要盲目更改 100 单订单状态或任意制造脏数据。
- 选择一个可标记且可审计的隔离测试业务操作，记录三分区变更前 Offset、提交时间、变更主键、变更后 Offset。
- 对照消息中的 `source.db`、`source.table`、`op`、主键和 after/before 字段，证明真实 Binlog 增量写入；按既定业务规则确认清理或长期保留测试事件。
- 检查 CDC 持续 RUNNING 和后续 Checkpoint Completed；禁止失败后直接盲目重新提交，尤其当 Kafka 已有增量时。

### 当时建议二：实时数仓 DWD 最小闭环

- Kafka 的 `ods_cdc_m2_clean_v1` 作为实时 ODS；先做 `biz_order` → `dwd_order` 一张事实表，不新增无必要的 Doris 原始 ODS。
- 粒度固定为一个 `order_id` 一行；梳理 `c/u/d`、空值、状态机、主键去重、字段单位（分）及迟到乱序处理。不要将毫秒级 `updated_at` 直接视为全局唯一严格递增版本。
- Doris 设计以实际数据结构和已冻结的指标口径为准；先完成订单明细/状态与 MySQL 对账，再接 `biz_order_item`、支付和退款。
- DWD 验收通过后才建设 DWS/ADS 的有效下单金额、支付订单数及退款指标；按业务日期处理取消订单对原下单日 GMV 的冲回，区分资金发生日与订单累计口径。

## 6. 当时建议的最小只读命令

```bash
APP=application_1789972455214_0006
yarn application -status "$APP" | grep -E 'State :|Final-State :|Tracking-URL :|Diagnostics :'

sudo mysql --table -e "SHOW CREATE TABLE ecommerce_oltp_m2_acceptance.biz_product_change_event;"
sudo mysql --table -e "SHOW CREATE TABLE ecommerce_oltp_m2_acceptance.biz_sku;"

kafka-get-offsets.sh --bootstrap-server hadoop201:9092,hadoop202:9092,hadoop203:9092 --topic ods_cdc_m2_clean_v1 --time -1
```

> 先依据实际 DDL 与业务写入方式设计增量测试。不要直接执行未经审查的 INSERT/UPDATE/DELETE。
