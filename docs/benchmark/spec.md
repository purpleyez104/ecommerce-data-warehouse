# 离实时一体化数仓数据规模与 Benchmark 设计规范

> 版本：v1.2
> 状态：`candidate / DESIGNED / not_run`
> 数据基线：本规范不单独定义业务生成规则；候选设计参考 [V2 数据规格候选稿](../design/v2-data-spec-candidate.md)，正式范围和门禁以 `docs/spec.md`、`docs/plan.md` 为准。


## 1. 文档目标

本规范用于统一离线链路与实时链路的数据规模、统计口径、Benchmark 指标和证据留存方式。

最终目标不是简单证明：

```text
链路能跑通
```

而是能够在简历和面试中用真实数据回答：

```text
处理了多少数据？
每天多少数据？
峰值是多少？
批处理多快？
实时吞吐多少？
延迟多少？
存储节省多少？
Spark 优化了多少？
Doris 查询多快？
数据质量怎么保证？
```

所有简历中的数字必须来自真实执行结果。

禁止先写：

```text
性能提升 40%
吞吐 1 万条/s
延迟 2 秒
压缩率 70%
```

再反过来凑实验结果。

---

# 2. 数据集整体规模

## 2.1 历史时间范围

V2 正式历史数据：

```text
history_start = 2025-12-01 00:00:00
history_end   = 2026-02-28 23:59:59

timezone      = Asia/Shanghai
history_days  = 90
```

2026-03-01 起进入持续业务增量阶段（Continuous Business Increment）。

这里不是重新生成另一套“实时数据”，而是同一个 Business Generator 继续在同一个 `ecommerce_oltp` 中产生 `INSERT / UPDATE` 业务变化。实时链路通过 Binlog/Flink CDC 立即消费这些变化，离线链路通过 DataX 在后续 T+1 任务中再次同步同一业务源。

---

# 2.2 离实时统一数据来源与生成阶段

业务数据只有一个正式事实源：

```text
ecommerce_oltp
```

项目只定义两个逻辑 Generator：

```text
1. Business Generator
2. Behavior Generator
```

其中 Business Generator 不是“历史生成器 + 实时生成器”两套实现，而是同一套业务规则下的两个运行阶段：

```text
Bootstrap Historical Initialization
    ↓
Python → 21 CSV → LOAD DATA → ecommerce_oltp

Continuous Business Increment
    ↓
Business Generator → INSERT / UPDATE → ecommerce_oltp
```

Bootstrap 负责一次性初始化 2025-12-01 至 2026-02-28 的 90 天历史业务状态；Continuous 从 2026-03-01 起，在已有用户、商品、订单等业务状态基础上继续运行。

离线与实时对同一业务源采用不同采集方式：

```text
                    ecommerce_oltp
                          │
             ┌────────────┴────────────┐
             │                         │
           DataX                    Binlog
             │                         │
             ▼                         ▼
          Offline                  Flink CDC
             │                         │
             ▼                         ▼
      ODS → Spark → ...          Kafka → Flink
             │                         │
             └────────────┬────────────┘
                          ▼
                        Doris
```

因此 Benchmark 中不得把“离线历史数据”和“实时业务数据”当作两套互不相关的数据集。

行为数据仍由独立 Behavior Generator 负责：

```text
Bootstrap Behavior
→ 历史行为文件
→ Offline ODS

Continuous Behavior
→ Kafka
→ Flink
```

但两种模式共享相同用户、Visitor、SKU、Session 和事件口径。

---

# 3. MySQL OLTP 基础规模

正式唯一业务源库：

```text
ecommerce_oltp
```

`ecommerce_oltp` 在 Bootstrap 完成后不会重新初始化；Continuous 阶段持续在该库中新增和更新业务数据。

业务模型：

```text
7 个业务域
21 张业务表
```

核心规模：

| 指标 | 目标 |
|---|---:|
| 历史周期 | 90 天 |
| 订单 | 100,000 |
| 订单明细 | ≈285,000 |
| 用户 | 40,000 |
| Visitor | 80,000 |
| SKU | 4,000 |
| SPU | 1,200 |
| 类目 | 60 |
| 支付尝试 | ≈95,300 |
| 退款申请 | 9,000 |
| 优惠券实例 | 60,000 |
| OLTP 总业务记录 | 约 100 万级 |

这些属于：

```text
DESIGNED SCALE
```

生成完成以后必须由 Manifest 和 MySQL COUNT 转为：

```text
MEASURED SCALE
```

以后简历优先使用实测数量，而不是目标数量。

---

# 4. 行为数据规模

行为数据不写入 21 张 MySQL OLTP 表。

单独模拟：

```text
曝光
浏览
点击
加购
移除
```

建议正式目标：

```text
3,000,000 ～ 5,000,000 条行为事件
```

用于：

```text
Kafka
Flink
行为 ODS
用户行为 DWD
漏斗
UV
实时指标
```

因此最终整个项目可以形成：

```text
百万级交易业务数据
+
数百万级行为日志
```

这比单纯把订单扩到数百万更符合真实电商流量特征。

---

# 5. 数据分布不能完全均匀

Generator 必须主动制造真实数据特征。

## 5.1 时间波动

至少包含：

```text
工作日 / 周末差异
小时级高峰
午间高峰
晚间高峰
随机日波动
少量促销峰值日
```

例如：

```text
普通日       ≈ 800～1300 orders/day
较高流量日   ≈ 1500～2000
活动峰值日   ≈ 普通日 2～4 倍
```

具体数值由 Generator 实际结果为准。

---

# 6. 商品长尾

不能让 4000 个 SKU 均匀销售。

建议形成明显长尾：

```text
Top 5% SKU
承担约 35%～45% 销量

Top 20% SKU
承担约 65%～75% 销量

剩余 80% SKU
承担约 25%～35% 销量
```

目的不是人为制造异常，而是为：

```text
Spark GROUP BY
Join
Shuffle
数据倾斜
TopN
热门商品
```

提供真实 Benchmark 场景。

---

# 7. 用户活跃度长尾

用户也不能完全平均。

建议：

```text
少量高频用户
中等活跃用户
大量低频用户
匿名 Visitor
登录后身份合并用户
```

这样后续：

```text
UV
复购
用户分层
漏斗
用户日汇总
```

才更真实。

---

# 8. 业务复杂场景覆盖

数据必须实际覆盖：

```text
正常支付
支付失败
支付失败后重试成功
订单取消
支付超时
优惠券使用
优惠券取消释放
优惠券过期
部分退款
退款失败
退款失败后重试
金额退款
数量退款
游客购物车
登录购物车
购物车合并
身份映射修订
商品价格变化
商品状态变化
商品类目变化
商品品牌变化
```

否则后面的 DWD、DIM、指标层虽然写了逻辑，却没有真实数据验证。

---

# 9. Generator 阶段必须立刻记录的数据

这些数据应该从生成器第一版开始就记录，不应该等项目结束后补。

建议每次生成输出：

```text
dataset_manifest.json
```

至少包含：

## 9.1 数据版本

```text
dataset_version
generator_version
seed
generated_at

history_start
history_end
history_days
timezone
```

---

## 9.2 表规模

记录 21 张表：

```text
table_name
row_count
csv_file_size_bytes
```

例如：

```text
biz_order
rows = 100000
csv_size = xxx MB

biz_order_item
rows = 285xxx
csv_size = xxx MB
```

---

## 9.3 业务状态统计

必须记录：

```text
paid_orders
canceled_orders
created_orders

payment_success
payment_failed
payment_init
retry_payment_orders

refund_success
refund_failed
refund_processing
refund_requested

coupon_used
coupon_locked
coupon_unused
coupon_expired

product_change_events
changed_sku_count
multi_change_sku_count
```

---

## 9.4 时间分布

记录：

```text
min_event_time
max_event_time

min_daily_orders
max_daily_orders
avg_daily_orders

peak_date
peak_date_orders

peak_hour
peak_hour_orders
```

这类数字以后非常适合写项目介绍。

---

## 9.5 商品分布

记录：

```text
distinct_sku
distinct_spu

top_1_sku_sales_share
top_10_sku_sales_share
top_5_percent_sku_share
top_20_percent_sku_share
```

用于证明存在合理商品长尾和热点数据。

---

## 9.6 用户分布

记录：

```text
registered_users
visitors
mapped_visitors

active_users
repeat_buyers

avg_orders_per_user
max_orders_per_user
```

---

# 10. CSV → MySQL 阶段立即记录

LOAD DATA 时必须记录：

```text
table_name
csv_rows
mysql_rows

file_size_bytes

load_start_time
load_end_time
load_elapsed_seconds

rows_per_second
MB_per_second
```

这样可以形成第一组真实性能数字：

```text
MySQL 大批量导入吞吐
```

但只有实际运行以后才能进入简历。

---

# 11. Source Gate 必须记录

Source Gate 不只是输出：

```text
PASS
```

而应形成指标结果。

至少记录：

```text
total_tables
total_rows

duplicate_pk_count
orphan_fk_count

order_amount_mismatch_count
order_item_count_violation_count

invalid_paid_order_count
multiple_success_payment_count
payment_timeout_violation_count

refund_overflow_count
invalid_refund_reference_count

invalid_coupon_state_count
invalid_time_range_count
```

理想结果：

```text
duplicate_pk = 0
orphan_fk = 0
amount_mismatch = 0
critical_business_violation = 0
```

这可以成为简历中的数据质量证据。

---

# 12. 离线链路需要记录的数据

离线正式链路：

```text
ecommerce_oltp
→ DataX
→ HDFS / Hive ODS
→ Spark SQL
→ DWD / DIM
→ DWS
→ ADS
→ Doris
```

离线需要分别覆盖两种场景：

```text
1. Bootstrap Historical Full Load
2. Continuous T+1 Incremental Load
```

Bootstrap 阶段验证历史批量初始化能力；Continuous 阶段验证每天对同一 `ecommerce_oltp` 的新增与更新数据进行增量同步。

每层都需要留 Benchmark。

---

# 13. DataX Benchmark

## 一开始记录

每个批次：

```text
run_mode
source_table
extract_start_time
extract_end_time

source_rows
target_rows

input_bytes
output_bytes

start_time
end_time
elapsed_seconds

affected_partition_count
```

其中：

```text
run_mode = FULL 或 INCREMENTAL
```

Continuous 阶段必须区分“增量抽取时间”和“业务分区时间”：

- 当前状态表主要根据 `updated_at` 判断本次 DataX 要抓哪些发生变化的记录。
- 事件表主要根据 `recorded_at` 判断本次要抓哪些新增事件。
- Hive `dt` 按数据实际所属的业务日期确定，而不是直接使用 `updated_at` 或 `recorded_at`。

因此一次 T+1 增量任务可能回刷一个或多个历史业务分区，`affected_partition_count` 必须留证。

计算：

```text
rows_per_second
MB_per_second
```

---

## 后续性能测试

可以测试：

```text
不同 channel 数量
单表 vs 多表
不同 DataX 并发
不同文件数量
```

但不需要为了调优而做很多无意义参数组合。

重点找 1～2 个代表表：

```text
biz_order_item
行为日志
```

做 Benchmark 即可。

---

# 14. HDFS / ORC Benchmark

必须记录：

```text
CSV 原始文件大小
ORC 文件大小
ORC + Snappy 文件大小
文件数量
平均文件大小
```

最终可以算：

```text
compression_ratio = 1 - (ORC_SIZE ÷ CSV_SIZE)
```

以后如果实测明显，可以写：

```text
通过 ORC + Snappy 将核心明细数据存储体积降低 XX%
```

但 XX 必须来自真实 HDFS 数据。

---

# 15. Spark SQL Benchmark

这是离线链路最重要的性能证据。

每个核心 Job 建议记录：

```text
application_id
job_name

input_rows
output_rows

input_bytes

duration_seconds

task_count

shuffle_read_bytes
shuffle_write_bytes

spill_memory
spill_disk

executor_cpu_time
executor_run_time
```

不一定每个指标都写进简历，但需要留证据。

---

# 16. Spark 优化实验

不需要每张表都做优化实验。

选择 1～2 个代表 Job。

建议：

## Benchmark A

```text
订单明细
JOIN
商品
GROUP BY
dt / sku
```

例如：

```text
dws_product_sales_day
```

## Benchmark B

```text
订单
JOIN
支付
JOIN
退款
```

例如交易汇总。

---

# 17. Spark Baseline 必须先保存

优化之前先保存：

```text
duration
shuffle read
shuffle write
task count
input size
```

然后再根据真实执行计划选择优化：

```text
Partition Pruning
Broadcast Join
AQE
Shuffle Partition 调整
Predicate Pushdown
Column Pruning
Pre-Aggregation
避免数据倾斜
```

不是所有优化都必须用。

只应用真正有效的。

---

# 18. Spark 优化后记录

记录：

```text
before_duration
after_duration

before_shuffle_read
after_shuffle_read

before_shuffle_write
after_shuffle_write

before_tasks
after_tasks
```

计算：

```text
duration_improvement_pct
shuffle_reduction_pct
```

简历才能真实写：

```text
核心 Spark SQL 作业耗时降低 XX%

Shuffle 数据量降低 XX%
```

---

# 19. ODS Gate 记录

批量 ODS 完成后：

```text
mysql_rows
ods_rows

partition_count
affected_partition_count

duplicate_count
missing_count
extra_count

invalid_partition_count
incremental_missing_count
incremental_extra_count
```

需要同时证明：

```text
Bootstrap：
21 张源表历史批量同步完成
核心表全量行数一致

Continuous：
T+1 新增/更新数据完整捕获
受影响业务分区识别正确
增量回刷后核心表一致
```

这种比“完成 DataX 同步”更有说服力。

---

# 20. DWD / DIM Gate 记录

至少记录：

```text
order_count
order_item_count
payment_fact_count
refund_fact_count

amount_mismatch_count
dimension_missing_count
duplicate_fact_count
```

V2 只对商品维度正式实现 SCD Type 2：

```text
dim_product_zip
```

用户维度使用普通 `dim_user`，不额外建设 `dim_user_zip`。

商品拉链必须记录：

```text
distinct_sku
product_zip_rows

multi_version_sku_count
invalid_effective_range_count
overlap_version_count
multiple_current_version_count
```

目标质量：

```text
invalid_effective_range_count = 0
overlap_version_count = 0
multiple_current_version_count = 0
```

这样可以证明 `dim_product_zip` 确实保存了商品价格、状态、类目或品牌的历史版本，而不是只建了一个拉链表 DDL。

---

# 21. DWS / ADS 记录

为核心指标记录：

```text
GMV
paid_order_count
order_user_count
sales_quantity
refund_amount
net_payment
conversion_rate
```

重点不是数字大小，而是：

```text
同指标离线结果
与
实时结果
```

后面可以做一致性对账。

---

# 21.1 DolphinScheduler Workflow Evidence

DolphinScheduler 在本项目中属于批处理 Control / Orchestration Plane。

Benchmark 不把 DolphinScheduler 当作数据计算引擎，
也不要求专门进行 DolphinScheduler TPS 压测。

正式 T+1、历史 Behavior 批处理与 Reconciliation Workflow
需要保留运行证据。

每次正式 Workflow Instance 至少记录：

```text
workflow_name
workflow_instance_id

business_date
scheduled_time

start_time
end_time
duration_seconds

task_success_count
task_failure_count
retry_count

final_status
```

其中：

```text
business_date
```

表示本次调度 / 增量抽取窗口，
不表示所有数据都写入同一个 Hive `dt`。

仍需同时记录：

```text
affected_partition_count
```

用来证明一次 T+1 运行是否正确识别并回刷历史业务分区。

对于被 DolphinScheduler 调起的 Spark 作业，
仍使用 Spark Application ID 和 Spark 自身运行指标作为计算性能证据。

对于被 DolphinScheduler 调起的 DataX、Doris、质量 Gate，
同样保留各执行引擎自己的指标。

DolphinScheduler 负责证明：

```text
任务什么时候运行
依赖是否正确
是否发生失败 / 重试
最终 Workflow 是否成功
```

而不是替代各引擎的性能指标。

---

# 22. 实时链路总体规模

实时业务链路：

```text
Business Generator Continuous
→ INSERT / UPDATE ecommerce_oltp
→ MySQL Binlog
→ Flink CDC
→ Kafka
→ Flink
→ Doris
```

这里的实时业务数据不是单独生成的一套测试数据，而是与 T+1 离线链路共享同一个 `ecommerce_oltp`。

行为：

```text
Behavior Generator
→ Kafka
→ Flink
→ Doris / ODS
```

实时测试不能只拿几条数据。

---

# 23. 实时测试数据必须记录

至少记录：

```text
total_events

events_per_second

peak_events_per_second

event_size_bytes

total_input_bytes

producer_start_time
producer_end_time
```

如果行为事件为：

```text
3M～5M
```

可以控制回放速度，模拟：

```text
正常流量
峰值流量
突发流量
```

---

# 24. Kafka Benchmark

需要记录：

```text
topic
partition_count
replication_factor

produced_messages
consumed_messages

input_MB

producer_throughput
consumer_throughput

max_consumer_lag
avg_consumer_lag
```

不一定全部写进简历，但必须保留原始证据。

---

# 25. Flink Benchmark

实时项目最重要的指标：

```text
input_records_per_second
output_records_per_second

busy_time
backpressure

checkpoint_duration
checkpoint_size
checkpoint_failure_count

restart_count
```

以及：

```text
end_to_end_latency
```

---

# 26. 实时延迟定义必须统一

不要模糊写：

```text
实时延迟 < 5 秒
```

必须明确测量方法。

建议：

```text
latency
=
Doris 可查询时间
-
源业务提交时间（或明确选定的 source event_time）
```

至少统计：

```text
P50
P95
P99
```

如果项目时间紧，最低保留：

```text
average
P95
```

最终简历优先写 P95，而不是最好的一次查询。

---

# 27. Flink 压测设计

至少进行三个负载等级：

```text
LOW
NORMAL
PEAK
```

例如根据实际集群能力逐步升压：

```text
1x
2x
4x
```

测试目的：

```text
最大稳定吞吐
开始产生 Backpressure 的点
Checkpoint 是否稳定
Kafka Lag 是否持续增长
```

不要预设：

```text
必须达到 10 万 events/s
```

真实三节点小集群能稳定处理多少，就记录多少。

---

# 28. Doris Benchmark

Doris 要记录两类性能。

## 写入

```text
rows_loaded
bytes_loaded

load_duration
rows_per_second
```

## 查询

选固定核心 SQL：

```text
GMV 日趋势
TopN 商品
支付订单
退款金额
用户转化
```

每个查询运行多次。

记录：

```text
P50
P95
average
```

---

# 29. 离实时一致性 Benchmark

这是整个项目很有价值的一项。

对于同一个业务日期、同一批 `ecommerce_oltp` 业务事实：

```text
T+1 Offline ADS
与
Realtime Doris
```

实时结果先产生，离线结果在 T+1 对同一业务源重新计算后用于最终确认。

对比：

```text
GMV
paid_order_count
sales_quantity
refund_amount
net_payment
```

记录：

```text
offline_value
realtime_value
difference
difference_ratio
```

理想结果：

```text
difference = 0
```

或者存在合理窗口差异时：

```text
最终收敛一致
```

这比单纯说“实现离实时一体化”更有说服力。

正式运行时可由 DolphinScheduler 在离线 ADS / Doris Publish 完成后，
触发 Reconciliation SQL / Python Task。

职责边界：

```text
DolphinScheduler
→ 调度
→ 依赖
→ 重试
→ Gate / Alert

Reconciliation SQL / Python
→ 读取 offline_value
→ 读取 realtime_value
→ 计算 difference
→ 计算 difference_ratio
```

对账结果建议额外记录：

```text
business_date
workflow_instance_id
check_time
status
```

---

# 30. Benchmark 数据统一分为三类

## A. 一开始必须记录

这些从 Generator 第一版就记录：

```text
数据规模
时间范围
表行数
CSV 大小
订单状态分布
支付/退款比例
日流量
小时流量
SKU 热点
用户活跃度
seed
dataset version
```

---

## B. 每次正式运行自动记录

```text
DataX FULL rows / duration
DataX INCREMENTAL rows / duration
DataX affected partitions

LOAD DATA rows / duration

Spark Application ID
Spark duration

Kafka messages
Flink checkpoint

Doris load rows

数据质量 Gate

DolphinScheduler：
workflow_name
workflow_instance_id
business_date
scheduled_time
start_time
end_time
duration
retry_count
final_status
```

这些应该尽可能自动产生。

注意：

```text
business_date
= 调度 / 增量抽取窗口

affected partitions
= 实际需要重算的业务日期
```

两者不能混为同一个概念。

---

## C. 项目后期专项性能测试

这些不能在开发初期编数字：

```text
Spark 优化前后
DataX 并发优化
ORC 压缩率
Flink 最大稳定吞吐
Flink P95 延迟
Kafka Lag
Doris 查询 P95
离实时一致性
```

只有正式链路稳定以后再做。

---

# 31. 建议统一 Benchmark 输出结构

后续可以统一保存：

```text
benchmarks/
├── dataset/
│   └── dataset-manifest.json
│
├── mysql/
│   └── load-data-results.csv
│
├── datax/
│   └── ingestion-results.csv        # FULL + INCREMENTAL
│
├── spark/
│   ├── baseline.csv
│   └── optimized.csv
│
├── kafka/
│   └── throughput-results.csv
│
├── flink/
│   └── realtime-results.csv
│
├── doris/
│   └── query-results.csv
│
├── dolphinscheduler/
│   └── workflow-runs.csv
│
├── dimension/
│   └── product-scd2-results.csv
│
└── reconciliation/
    └── offline-realtime-results.csv
```

这是建议结构，实际文件只有真正创建后才能进入 File Fact Ledger。

---

# 32. 最终简历可量化的信息

项目完成后，希望最终拥有下面这些真实数字。

## 数据规模

```text
21 张业务表
90 天历史数据
10 万订单
约 28 万订单明细
百万级交易记录
数百万行为事件
商品 SCD Type 2 历史维度
```

---

## 离线

```text
DataX 历史全量同步吞吐
DataX T+1 增量同步吞吐
单批受影响业务分区数
ODS/DWD 行数
ORC 压缩率

Spark 核心作业：
优化前耗时
优化后耗时

Shuffle：
优化前
优化后
```

---

## 实时

```text
Kafka 峰值吞吐
Flink 稳定吞吐
Checkpoint 平均/P95 时间
实时链路 P95 延迟
最大 Kafka Lag
```

---

## Serving

```text
Doris 数据量
导入吞吐

GMV 查询 P95
TopN 查询 P95
漏斗查询 P95
```

---

## 数据质量

```text
PK duplicate = 0
critical FK orphan = 0
amount mismatch = 0

离线 / 实时核心指标最终一致
```

---

# 33. 简历写法原则

最终简历不要堆所有数据。

每个项目 bullet 最多选择一个主要量化方向。

例如：

### 数据规模

```text
基于 21 张电商 OLTP 业务表构建 90 天模拟业务数据，
覆盖 10 万级订单、百万级交易记录及数百万用户行为事件。
```

### 离线性能

```text
通过 ORC+Snappy、分区裁剪及 Spark SQL Join/Shuffle 优化，
将核心 ETL 作业耗时由 X 降至 Y，降低 XX%。
```

### 实时性能

```text
构建 Kafka + Flink 实时计算链路，
在三节点集群下稳定处理 X events/s，
端到端 P95 延迟为 X 秒。
```

### Serving

```text
基于 Doris 构建实时指标服务，
核心 GMV/TopN 查询 P95 控制在 X ms。
```

### 数据质量

```text
建立订单、支付、退款跨表质量校验，
覆盖主键重复、孤儿记录、金额守恒和状态一致性，
核心交易链全量对账无差异。
```

其中：

```text
X
Y
XX%
events/s
P95
```

全部必须后续实测再填写。

---

# 34. 当前阶段的实施重点

现在还不需要开始做 Spark/Flink 性能实验。

当前只需要确保新的 V2 Business Generator 在 Bootstrap 第一版就输出：

```text
数据规模
状态分布
时间分布
商品分布
用户分布
商品变化分布
CSV 大小
Manifest
```

同时从工程设计上保留 Continuous 模式：Bootstrap 完成后，同一 Business Generator 从 2026-03-01 起继续通过业务事务 `INSERT / UPDATE ecommerce_oltp` 产生增量。

DolphinScheduler 当前阶段只需要保留编排设计和运行证据字段，
不需要在每建设一层时同步制作 DAG。

正确顺序：

```text
批处理任务独立验证
→ 参数化
→ Workflow Integration
→ Continuous T+1 正式由 DolphinScheduler 运行
```

然后：

```text
CSV
→ LOAD DATA
```

阶段开始记录：

```text
导入数据量
导入时间
吞吐
```

等离线和实时链路全部建成后，再分别进行：

```text
Spark Benchmark
Flink Benchmark
Kafka Benchmark
Doris Benchmark
离实时一致性 Benchmark
```

这样最后写进简历的所有数字都有完整工程证据链，而不是开发结束后临时补性能数据。

---

# 35. 与 V2-DATA-SPEC v2.4 的对齐基线

本 Benchmark 规范不再单独维护另一套数据生成语义。

当前固定基线：

```text
唯一业务源：
ecommerce_oltp

逻辑 Generator：
1 个 Business Generator
1 个 Behavior Generator

Business Bootstrap：
Python
→ 21 CSV
→ LOAD DATA
→ ecommerce_oltp

Business Continuous：
Business Transactions
→ INSERT / UPDATE
→ ecommerce_oltp

离线：
ecommerce_oltp
→ DataX T+1
→ ODS
→ Spark
→ DWD / DIM / DWS / ADS
→ Doris

实时：
ecommerce_oltp
→ Binlog
→ Flink CDC
→ Kafka
→ Flink
→ Doris

唯一正式 SCD2：
dim_product_zip

普通用户维度：
dim_user

批处理编排：
DolphinScheduler

主要编排对象：
Continuous T+1
Historical Behavior Batch
Reconciliation

实时 Flink：
长期运行
不按分钟由 DolphinScheduler 重复启动
```

Benchmark 的作用是测量这套正式架构的实际数据量、吞吐、延迟、存储、查询性能、数据质量、工作流运行证据和离实时一致性，不重新定义业务数据模型。

如果 `V2-DATA-SPEC` 后续发生正式版本升级，应先判断是否影响本规范中的：

```text
数据规模
运行阶段
增量同步
SCD2
离实时对账口径
```

只有这些基线变化时才需要同步升级本 Benchmark 规范。
